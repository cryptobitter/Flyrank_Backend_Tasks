"""
Telegram Platform Adapter:
Publishes announcements to Telegram channels or groups via the Telegram Bot API.
Includes retry logic and sandbox fallback.
"""

import asyncio
import logging
import os
import time
import uuid
from typing import Optional
import httpx

from platform_adapters.base import BasePlatformAdapter
from schemas import (
    PlatformPublishResult,
    PlatformType,
    PostContent,
    PublishStatus,
)

logger = logging.getLogger("telegram_adapter")


class TelegramAdapter(BasePlatformAdapter):
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        super().__init__(PlatformType.TELEGRAM)
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    async def publish(
        self,
        content: PostContent,
        idempotency_key: str,
        callback_url: Optional[str] = None,
        simulate_rate_limit: bool = False,
    ) -> PlatformPublishResult:
        start_time = time.perf_counter()

        # If credentials are not set, run in sandbox simulation mode
        if not self.bot_token or not self.chat_id:
            await asyncio.sleep(0.06)
            post_id = f"tg_{uuid.uuid4().hex[:10]}"
            latency = (time.perf_counter() - start_time) * 1000.0
            return PlatformPublishResult(
                platform=PlatformType.TELEGRAM,
                status=PublishStatus.PUBLISHED,
                post_id=post_id,
                post_url=f"https://t.me/sandbox_channel/{post_id}",
                attempts=1,
                latency_ms=latency,
                rate_limit_recovered=False,
            )

        # Real Telegram Bot API Call
        tag_str = " ".join([f"#{t}" for t in content.tags]) if content.tags else ""
        text_payload = f"📢 *Campaign Announcement*\n\n{content.text}\n\n{tag_str}".strip()
        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        async with httpx.AsyncClient(timeout=10.0) as client:
            attempts = 0
            while attempts < 3:
                attempts += 1
                try:
                    resp = await client.post(
                        endpoint,
                        json={
                            "chat_id": self.chat_id,
                            "text": text_payload,
                            "parse_mode": "Markdown",
                        },
                    )

                    if resp.status_code == 429:
                        data = resp.json()
                        retry_after = data.get("parameters", {}).get("retry_after", 1)
                        logger.warning(f"🛑 [Telegram] 429 Rate Limit hit. Backing off {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    msg_id = data.get("result", {}).get("message_id", uuid.uuid4().hex[:8])
                    latency = (time.perf_counter() - start_time) * 1000.0

                    return PlatformPublishResult(
                        platform=PlatformType.TELEGRAM,
                        status=PublishStatus.PUBLISHED,
                        post_id=str(msg_id),
                        post_url=f"https://t.me/{self.chat_id}/{msg_id}",
                        attempts=attempts,
                        latency_ms=latency,
                        rate_limit_recovered=attempts > 1,
                    )
                except Exception as exc:
                    logger.error(f"⚠️ [Telegram] Attempt #{attempts} failed: {exc}")
                    await asyncio.sleep(0.5)

            latency = (time.perf_counter() - start_time) * 1000.0
            return PlatformPublishResult(
                platform=PlatformType.TELEGRAM,
                status=PublishStatus.FAILED,
                attempts=attempts,
                latency_ms=latency,
                error="Telegram API delivery failed after retries",
            )
