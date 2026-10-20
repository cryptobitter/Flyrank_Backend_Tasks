"""
Pytest Test Suite for Social Media Studio:
Validates Mock Platform server, Idempotency, 429 Retry-After handling,
HMAC-SHA256 webhook signatures, and multi-platform campaign broadcasting.
"""

import asyncio
import hashlib
import hmac
import json
import pytest
from httpx import AsyncClient, ASGITransport

from app import app
from mock_platform_server import sign_payload, HMAC_SECRET, MOCK_IDEMPOTENCY_STORE, RATE_LIMIT_STRIKES
from webhook_receiver import DELIVERY_AUDIT_LOG
from publisher_service import publisher_service
from schemas import CampaignPublishRequest, PlatformType, PostContent


@pytest.fixture(autouse=True)
def reset_state():
    """Cleans in-memory caches and logs between tests."""
    async def _clean():
        MOCK_IDEMPOTENCY_STORE.clear()
        RATE_LIMIT_STRIKES.clear()
        DELIVERY_AUDIT_LOG.clear()
        await publisher_service.clear_cache()

    asyncio.run(_clean())
    yield
    asyncio.run(_clean())


def test_mock_platform_token_and_publish():
    """Verifies token generation and basic post creation on mock platform."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Get Token
            tok_res = await client.post("/mock-platform/oauth/token")
            assert tok_res.status_code == 200
            token = tok_res.json()["access_token"]
            assert token.startswith("mock_tok_")

            # 2. Publish Post
            payload = {
                "content": "Hello world from Social Media Studio test!",
                "tags": ["testing", "flyrank"],
            }
            pub_res = await client.post(
                "/mock-platform/v1/posts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": "test-key-basic-101",
                },
            )
            assert pub_res.status_code == 201
            data = pub_res.json()
            assert "post_id" in data
            assert data["idempotency_key"] == "test-key-basic-101"

    asyncio.run(_run())


def test_mock_platform_idempotency_duplicate_prevention():
    """
    Non-Negotiable: Idempotency (Honouring Idempotency-Key).
    Submitting the same idempotency key must return the existing post record
    with X-Idempotent-Replay header and avoid duplicate publication.
    """
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            tok_res = await client.post("/mock-platform/oauth/token")
            token = tok_res.json()["access_token"]

            payload = {"content": "Important financial announcement post"}
            headers = {
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "unique-idemp-key-555",
            }

            # First publish
            res1 = await client.post("/mock-platform/v1/posts", json=payload, headers=headers)
            assert res1.status_code == 201
            post_id_1 = res1.json()["post_id"]

            # Duplicate publish attempt
            res2 = await client.post("/mock-platform/v1/posts", json=payload, headers=headers)
            assert res2.status_code == 200
            assert res2.headers.get("X-Idempotent-Replay") == "true"
            assert res2.json()["post_id"] == post_id_1

    asyncio.run(_run())


def test_mock_platform_rate_limit_429_and_retry_after():
    """
    Non-Negotiable: 429 Rate Limit with Retry-After Header.
    When X-Simulate-Rate-Limit is toggled, mock server returns 429 on strike 1.
    """
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            tok_res = await client.post("/mock-platform/oauth/token")
            token = tok_res.json()["access_token"]

            payload = {"content": "Testing 429 switch"}
            headers = {
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "rate-limit-strike-test-01",
                "X-Simulate-Rate-Limit": "true",
            }

            # 1st attempt triggers 429
            res1 = await client.post("/mock-platform/v1/posts", json=payload, headers=headers)
            assert res1.status_code == 429
            assert res1.headers.get("Retry-After") == "1"

            # 2nd attempt succeeds
            res2 = await client.post("/mock-platform/v1/posts", json=payload, headers=headers)
            assert res2.status_code == 201

    asyncio.run(_run())


def test_hmac_webhook_signature_verification_success():
    """
    Cryptographic Verification:
    Webhook receiver accepts valid HMAC-SHA256 signatures and logs delivery.
    """
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = {
                "event_id": "evt-test-100",
                "event_type": "post.delivered",
                "platform": "mock_platform",
                "post_id": "post_xyz789",
                "campaign_id": "camp-q4-launch",
            }
            raw_bytes = json.dumps(payload).encode("utf-8")
            valid_sig = sign_payload(HMAC_SECRET, raw_bytes)

            res = await client.post(
                "/webhooks/platform-callback",
                content=raw_bytes,
                headers={"X-Hub-Signature-256": valid_sig, "Content-Type": "application/json"},
            )
            assert res.status_code == 200
            assert res.json()["status"] == "accepted"

            # Check delivery audit log
            deliveries_res = await client.get("/webhooks/deliveries")
            deliveries = deliveries_res.json()
            assert len(deliveries) >= 1
            assert deliveries[0]["payload"]["post_id"] == "post_xyz789"

    asyncio.run(_run())


def test_hmac_webhook_signature_verification_rejected():
    """
    Security Verification:
    Webhook receiver strictly rejects tampered payload or invalid signature.
    """
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = {"event_id": "evt-tampered", "post_id": "p-1"}
            raw_bytes = json.dumps(payload).encode("utf-8")
            bogus_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

            res = await client.post(
                "/webhooks/platform-callback",
                content=raw_bytes,
                headers={"X-Hub-Signature-256": bogus_sig, "Content-Type": "application/json"},
            )
            assert res.status_code == 401
            assert "Invalid HMAC signature" in res.json()["detail"]

    asyncio.run(_run())


def test_discord_and_telegram_adapters():
    """Verifies real platform adapters function correctly in sandbox mode."""
    async def _run():
        from platform_adapters.discord_adapter import DiscordAdapter
        from platform_adapters.telegram_adapter import TelegramAdapter

        discord = DiscordAdapter()
        d_res = await discord.publish(
            content=PostContent(text="Discord broadcast test", tags=["community"]),
            idempotency_key="disc-test-key-1",
        )
        assert d_res.status == "published"
        assert d_res.post_id is not None

        telegram = TelegramAdapter()
        t_res = await telegram.publish(
            content=PostContent(text="Telegram broadcast test", tags=["announcements"]),
            idempotency_key="tg-test-key-1",
        )
        assert t_res.status == "published"
        assert t_res.post_id is not None

    asyncio.run(_run())


def test_multi_platform_campaign_broadcast():
    """
    Multi-Platform Fan-Out Broadcast:
    POST /api/v1/campaigns/publish broadcasts to multiple platforms concurrently.
    """
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Wire up mock client inside publisher_service for in-process mock platform calls
            from publisher_service import publisher_service
            publisher_service.mock_client = client

            payload = {
                "campaign_id": "global-launch-2026",
                "content": {
                    "text": "Excited to unveil our new multi-platform publishing suite!",
                    "tags": ["FlyRank", "Engineering", "Launch"],
                },
                "platforms": ["mock_twitter", "mock_linkedin", "discord", "telegram"],
                "idempotency_key": "camp-idemp-broadcast-001",
                "callback_url": "http://testserver/webhooks/platform-callback",
            }

            res = await client.post("/api/v1/campaigns/publish", json=payload)
            assert res.status_code == 200
            data = res.json()

            assert data["campaign_id"] == "global-launch-2026"
            assert data["total_platforms"] == 4
            assert data["successful_platforms"] == 4
            assert data["failed_platforms"] == 0
            assert len(data["results"]) == 4

            # Duplicate campaign run test (Idempotency)
            dup_res = await client.post("/api/v1/campaigns/publish", json=payload)
            assert dup_res.status_code == 200
            dup_data = dup_res.json()
            assert dup_data["is_duplicate_run"] is True

    asyncio.run(_run())


def test_health_check_and_platforms_list():
    """Verifies service health check and platform catalog."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            h_res = await client.get("/api/v1/health")
            assert h_res.status_code == 200
            assert h_res.json()["status"] == "healthy"

            p_res = await client.get("/api/v1/platforms")
            assert p_res.status_code == 200
            assert len(p_res.json()) >= 4

    asyncio.run(_run())
