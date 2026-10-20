"""
Publisher Service:
Coordinates multi-platform publishing across mock and real platform adapters.
Enforces campaign idempotency and concurrent fan-out publishing.
"""

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
import httpx

from platform_adapters.base import BasePlatformAdapter
from platform_adapters.discord_adapter import DiscordAdapter
from platform_adapters.mock_adapter import MockPlatformAdapter
from platform_adapters.telegram_adapter import TelegramAdapter
from schemas import (
    CampaignPublishRequest,
    CampaignPublishResponse,
    PlatformPublishResult,
    PlatformType,
    PublishStatus,
)

logger = logging.getLogger("publisher_service")


class PublisherService:
    def __init__(self, mock_client: Optional[httpx.AsyncClient] = None):
        self.mock_client = mock_client
        self._idempotency_cache: Dict[str, CampaignPublishResponse] = {}
        self._lock = asyncio.Lock()

    def _get_adapter(self, platform: PlatformType) -> BasePlatformAdapter:
        if platform == PlatformType.MOCK_TWITTER:
            return MockPlatformAdapter(
                platform_type=PlatformType.MOCK_TWITTER, client=self.mock_client
            )
        elif platform == PlatformType.MOCK_LINKEDIN:
            return MockPlatformAdapter(
                platform_type=PlatformType.MOCK_LINKEDIN, client=self.mock_client
            )
        elif platform == PlatformType.DISCORD:
            return DiscordAdapter()
        elif platform == PlatformType.TELEGRAM:
            return TelegramAdapter()
        else:
            # Fallback to mock adapter
            return MockPlatformAdapter(
                platform_type=platform, client=self.mock_client
            )

    def _resolve_idempotency_key(self, request: CampaignPublishRequest) -> str:
        if request.idempotency_key and request.idempotency_key.strip():
            return request.idempotency_key.strip()
        # Derive key deterministically from payload content
        hasher = hashlib.sha256()
        hasher.update(request.campaign_id.encode())
        hasher.update(request.content.text.encode())
        for p in sorted([pl.value for pl in request.platforms]):
            hasher.update(p.encode())
        return f"auto_{hasher.hexdigest()[:16]}"

    async def broadcast_campaign(
        self, request: CampaignPublishRequest
    ) -> CampaignPublishResponse:
        idempotency_key = self._resolve_idempotency_key(request)

        # 1. Idempotency Check (Prevent duplicate campaign broadcast)
        async with self._lock:
            if idempotency_key in self._idempotency_cache:
                cached = self._idempotency_cache[idempotency_key]
                logger.info(
                    f"🔁 [PublisherService] Duplicate campaign caught for key: {idempotency_key}. "
                    f"Returning cached broadcast result."
                )
                # Return copy with is_duplicate_run=True
                return CampaignPublishResponse(
                    campaign_id=cached.campaign_id,
                    idempotency_key=cached.idempotency_key,
                    total_platforms=cached.total_platforms,
                    successful_platforms=cached.successful_platforms,
                    failed_platforms=cached.failed_platforms,
                    results=cached.results,
                    is_duplicate_run=True,
                    completed_at=cached.completed_at,
                )

        logger.info(
            f"🚀 [PublisherService] Broadcasting campaign '{request.campaign_id}' "
            f"across {len(request.platforms)} platforms..."
        )

        # 2. Concurrently execute across all selected platform adapters
        tasks = []
        for platform in request.platforms:
            adapter = self._get_adapter(platform)
            task = adapter.publish(
                content=request.content,
                idempotency_key=f"{idempotency_key}_{platform.value}",
                callback_url=request.callback_url,
                simulate_rate_limit=request.simulate_rate_limit,
            )
            tasks.append(task)

        results: List[PlatformPublishResult] = await asyncio.gather(*tasks)

        successful_count = sum(1 for r in results if r.status == PublishStatus.PUBLISHED)
        failed_count = sum(1 for r in results if r.status == PublishStatus.FAILED)

        response = CampaignPublishResponse(
            campaign_id=request.campaign_id,
            idempotency_key=idempotency_key,
            total_platforms=len(request.platforms),
            successful_platforms=successful_count,
            failed_platforms=failed_count,
            results=results,
            is_duplicate_run=False,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        async with self._lock:
            self._idempotency_cache[idempotency_key] = response

        logger.info(
            f"✅ [PublisherService] Broadcast complete for '{request.campaign_id}': "
            f"{successful_count}/{len(request.platforms)} succeeded."
        )
        return response

    async def clear_cache(self) -> None:
        async with self._lock:
            self._idempotency_cache.clear()


# Global singleton instance
publisher_service = PublisherService()
