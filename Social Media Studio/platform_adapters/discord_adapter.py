"""
Discord Platform Adapter:
Publishes announcements and campaign content to real free Discord webhooks.
Includes rate-limit handling and offline sandbox simulation mode.
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

logger = logging.getLogger("discord_adapter")


class DiscordAdapter(BasePlatformAdapter):
    def __init__(self, webhook_url: Optional[str] = None):
        super().__init__(PlatformType.DISCORD)
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

    async def publish(
        self,
        content: PostContent,
        idempotency_key: str,
        callback_url: Optional[str] = None,
        simulate_rate_limit: bool = False,
    ) -> PlatformPublishResult:
        start_time = time.perf_counter()

        # If no real webhook URL is provided, run in high-fidelity sandbox simulation mode
        if not self.webhook_url or not self.webhook_url.startswith("https://discord.com/api/webhooks"):
            await asyncio.sleep(0.08)  # simulate network
            post_id = f"disc_{uuid.uuid4().hex[:10]}"
            latency = (time.perf_counter() - start_time) * 1000.0
            return PlatformPublishResult(
                platform=PlatformType.DISCORD,
                status=PublishStatus.PUBLISHED,
                post_id=post_id,
                post_url=f"https://discord.com/channels/sandbox/{post_id}",
                attempts=1,
                latency_ms=latency,
                rate_limit_recovered=False,
            )

        # Real Discord Webhook Publishing
        tag_str = " ".join([f"#{t}" for t in content.tags]) if content.tags else ""
        discord_payload = {
            "content": f"{content.text}\n\n{tag_str}".strip(),
            "username": "Social Media Studio Bot",
            "avatar_url": "https://cdn.iconscout.com/icon/free/png-256/free-discord-logo-icon-download-in-svg-png-gif-file-formats--social-media-communication-brand-pack-logos-icons-2873138.png",
            "embeds": [
                {
                    "title": "Campaign Broadcast",
                    "description": content.text[:250],
                    "color": 0x5865F2,  # Discord Blurple
                    "footer": {"text": f"FlyRank Studio • Key: {idempotency_key}"},
                }
            ],
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            attempts = 0
            while attempts < 3:
                attempts += 1
                try:
                    resp = await client.post(self.webhook_url, json=discord_payload)

                    if resp.status_code == 429:
                        data = resp.json()
                        retry_after = data.get("retry_after", 1.0)
                        logger.warning(f"🛑 [Discord] 429 Rate Limit hit. Backing off for {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue

                    resp.raise_for_status()
                    latency = (time.perf_counter() - start_time) * 1000.0
                    post_id = f"disc_{uuid.uuid4().hex[:10]}"
                    return PlatformPublishResult(
                        platform=PlatformType.DISCORD,
                        status=PublishStatus.PUBLISHED,
                        post_id=post_id,
                        post_url=f"{self.webhook_url}/messages/{post_id}",
                        attempts=attempts,
                        latency_ms=latency,
                        rate_limit_recovered=attempts > 1,
                    )
                except Exception as exc:
                    logger.error(f"⚠️ [Discord] Attempt #{attempts} failed: {exc}")
                    await asyncio.sleep(0.5)

            latency = (time.perf_counter() - start_time) * 1000.0
            return PlatformPublishResult(
                platform=PlatformType.DISCORD,
                status=PublishStatus.FAILED,
                attempts=attempts,
                latency_ms=latency,
                error="Discord webhook delivery failed after retries",
            )
