"""
Mock Social Platform Server (~150 lines):
Implements the mock platform required by the capstone brief:
1. OAuth token endpoint (/oauth/token)
2. Publish endpoint honouring Idempotency-Key (/v1/posts)
3. Rate-limit switch returning HTTP 429 with Retry-After header
4. HMAC-SHA256 signed delivery callback to webhook
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
import httpx

from schemas import MockTokenResponse

logger = logging.getLogger("mock_platform")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

router = APIRouter(prefix="/mock-platform", tags=["Mock Social Platform"])

# In-memory stores
MOCK_TOKENS: Dict[str, dict] = {}
MOCK_POSTS_BY_ID: Dict[str, dict] = {}
MOCK_IDEMPOTENCY_STORE: Dict[str, dict] = {}  # idempotency_key -> post_dict
RATE_LIMIT_STRIKES: Dict[str, int] = {}       # tracks 429 hits per idempotency key

# Default HMAC secret
HMAC_SECRET = os.getenv("WEBHOOK_HMAC_SECRET", "super-secret-hmac-key-flyrank-2026")


class MockPublishPayload(BaseModel):
    content: str
    media_urls: Optional[list] = []
    tags: Optional[list] = []
    callback_url: Optional[str] = None
    campaign_id: Optional[str] = "camp-default"


def sign_payload(secret: str, payload_bytes: bytes) -> str:
    """Computes HMAC-SHA256 signature in sha256=<hex> format."""
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


async def deliver_signed_webhook_callback(
    callback_url: str,
    event_payload: dict,
    secret: str = HMAC_SECRET
) -> None:
    """Dispatches an asynchronous HMAC-signed delivery callback to the client's webhook."""
    try:
        raw_bytes = json.dumps(event_payload).encode("utf-8")
        signature_header = sign_payload(secret, raw_bytes)

        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                callback_url,
                content=raw_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature_header,
                    "X-Platform-Origin": "MockSocialEngine/1.0",
                },
            )
            logger.info(
                f"📡 [MockPlatform] Webhook callback delivered to {callback_url} -> Status: {resp.status_code}"
            )
    except Exception as e:
        logger.warning(f"⚠️ [MockPlatform] Webhook callback failed for {callback_url}: {e}")


@router.post("/oauth/token", response_model=MockTokenResponse)
async def create_oauth_token():
    """Generates a mock OAuth Bearer token."""
    token = f"mock_tok_{uuid.uuid4().hex}"
    MOCK_TOKENS[token] = {"created_at": time.time(), "expires_in": 3600}
    return MockTokenResponse(access_token=token)


@router.post("/v1/posts", status_code=status.HTTP_201_CREATED)
async def publish_mock_post(
    payload: MockPublishPayload,
    response: Response,
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_simulate_rate_limit: Optional[str] = Header(None, alias="X-Simulate-Rate-Limit"),
):
    """
    Publish mock post:
    - Enforces Bearer token auth
    - Enforces Idempotency-Key (prevents double post)
    - Returns 429 with Retry-After if rate limit simulation is toggled
    - Dispatches HMAC-signed delivery callback
    """
    # 1. Verify Auth
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token. Call /mock-platform/oauth/token first.",
        )

    # 2. Check Idempotency Store (Non-Negotiable: Idempotency)
    if idempotency_key:
        if idempotency_key in MOCK_IDEMPOTENCY_STORE:
            existing = MOCK_IDEMPOTENCY_STORE[idempotency_key]
            response.headers["X-Idempotent-Replay"] = "true"
            response.status_code = status.HTTP_200_OK
            logger.info(f"🔁 [MockPlatform] Duplicate request caught for key: {idempotency_key}. Returning existing post.")
            return existing

    # 3. Simulate Rate Limit (429 Too Many Requests with Retry-After)
    simulate_429 = x_simulate_rate_limit == "true" or os.getenv("MOCK_RATE_LIMIT_CHANCE") == "1.0"
    if simulate_429 and idempotency_key:
        strikes = RATE_LIMIT_STRIKES.get(idempotency_key, 0)
        if strikes == 0:
            # First strike: return 429 with 1-second Retry-After
            RATE_LIMIT_STRIKES[idempotency_key] = 1
            logger.warning(f"🛑 [MockPlatform] Simulating 429 Rate Limit for key: {idempotency_key}")
            return Response(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=json.dumps({"error": "Rate limit exceeded. Please back off.", "retry_after_sec": 1}),
                media_type="application/json",
                headers={"Retry-After": "1"},
            )

    # 4. Create Post Record
    post_id = f"post_{uuid.uuid4().hex[:10]}"
    post_record = {
        "post_id": post_id,
        "platform": "mock_platform",
        "content": payload.content,
        "media_urls": payload.media_urls,
        "tags": payload.tags,
        "idempotency_key": idempotency_key,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "url": f"https://mock-social.flyrank.internal/posts/{post_id}",
    }

    MOCK_POSTS_BY_ID[post_id] = post_record
    if idempotency_key:
        MOCK_IDEMPOTENCY_STORE[idempotency_key] = post_record

    # 5. Trigger Asynchronous HMAC-Signed Webhook Callback
    if payload.callback_url:
        callback_event = {
            "event_id": f"evt_{uuid.uuid4().hex[:8]}",
            "event_type": "post.delivered",
            "platform": "mock_platform",
            "post_id": post_id,
            "campaign_id": payload.campaign_id,
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        }
        asyncio.create_task(
            deliver_signed_webhook_callback(payload.callback_url, callback_event)
        )

    logger.info(f"✅ [MockPlatform] Successfully created post {post_id}")
    return post_record


@router.get("/v1/posts/{post_id}")
async def get_mock_post(post_id: str):
    """Retrieve post by ID."""
    if post_id not in MOCK_POSTS_BY_ID:
        raise HTTPException(status_code=404, detail="Post not found")
    return MOCK_POSTS_BY_ID[post_id]
