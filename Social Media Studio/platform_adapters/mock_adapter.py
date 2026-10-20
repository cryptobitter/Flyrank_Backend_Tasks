"""
Mock Platform Adapter:
Integrates with the built-in mock platform server.
Demonstrates Bearer token acquisition, Idempotency-Key propagation,
and 429 Retry-After handling with automatic backoff.
"""

import asyncio
import logging
import time
from typing import Optional
import httpx

from platform_adapters.base import BasePlatformAdapter
from schemas import (
    PlatformPublishResult,
    PlatformType,
    PostContent,
    PublishStatus,
)

logger = logging.getLogger("mock_adapter")


class MockPlatformAdapter(BasePlatformAdapter):
    def __init__(
        self,
        platform_type: PlatformType = PlatformType.MOCK_TWITTER,
        base_url: str = "http://localhost:8000/mock-platform",
        client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(platform_type)
        self.base_url = base_url.rstrip("/")
        self._cached_token: Optional[str] = None
        self._client = client

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        """Retrieves or reuses OAuth Bearer token from mock server."""
        if self._cached_token:
            return self._cached_token

        resp = await client.post(f"{self.base_url}/oauth/token")
        resp.raise_for_status()
        data = resp.json()
        self._cached_token = data["access_token"]
        return self._cached_token

    async def publish(
        self,
        content: PostContent,
        idempotency_key: str,
        callback_url: Optional[str] = None,
        simulate_rate_limit: bool = False,
    ) -> PlatformPublishResult:
        start_time = time.perf_counter()
        attempts = 0
        rate_limit_recovered = False

        # Use injected client (for tests) or create temporary one
        async with httpx.AsyncClient(timeout=8.0) if self._client is None else self._mock_context():
            client = self._client if self._client is not None else httpx.AsyncClient(timeout=8.0)
            token = await self._get_token(client)

            max_attempts = 3
            last_error = None

            while attempts < max_attempts:
                attempts += 1
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": f"{self.platform_type.value}:{idempotency_key}",
                }
                if simulate_rate_limit:
                    headers["X-Simulate-Rate-Limit"] = "true"

                payload = {
                    "content": content.text,
                    "media_urls": content.media_urls,
                    "tags": content.tags,
                    "callback_url": callback_url,
                    "campaign_id": idempotency_key,
                }

                try:
                    resp = await client.post(
                        f"{self.base_url}/v1/posts",
                        json=payload,
                        headers=headers,
                    )

                    # 1. Handle Rate Limit (429 Too Many Requests)
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", "1"))
                        logger.warning(
                            f"🛑 [{self.platform_type.value}] Hit 429 Rate Limit on attempt #{attempts}. "
                            f"Sleeping for {retry_after}s per Retry-After header..."
                        )
                        await asyncio.sleep(retry_after)
                        rate_limit_recovered = True
                        continue

                    # 2. Check for success (200 OK or 201 Created)
                    if resp.status_code in [200, 201]:
                        data = resp.json()
                        latency = (time.perf_counter() - start_time) * 1000.0
                        return PlatformPublishResult(
                            platform=self.platform_type,
                            status=PublishStatus.PUBLISHED,
                            post_id=data.get("post_id"),
                            post_url=data.get("url"),
                            attempts=attempts,
                            latency_ms=latency,
                            rate_limit_recovered=rate_limit_recovered,
                        )

                    # Other error
                    resp.raise_for_status()

                except Exception as exc:
                    last_error = str(exc)
                    logger.error(f"⚠️ [{self.platform_type.value}] Attempt #{attempts} failed: {exc}")
                    await asyncio.sleep(0.3)

            latency = (time.perf_counter() - start_time) * 1000.0
            return PlatformPublishResult(
                platform=self.platform_type,
                status=PublishStatus.FAILED,
                attempts=attempts,
                latency_ms=latency,
                rate_limit_recovered=rate_limit_recovered,
                error=last_error or "Max retry attempts exhausted",
            )

    def _mock_context(self):
        class _DummyContext:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        return _DummyContext()
