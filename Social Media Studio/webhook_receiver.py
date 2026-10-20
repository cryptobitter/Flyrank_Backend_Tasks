"""
Webhook Delivery Receiver & HMAC-SHA256 Verification:
Listens for platform delivery callbacks, enforces cryptographic signature checks,
and maintains an audit log of verified deliveries.
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel

logger = logging.getLogger("webhook_receiver")

router = APIRouter(prefix="/webhooks", tags=["Webhooks & Callbacks"])

HMAC_SECRET = os.getenv("WEBHOOK_HMAC_SECRET", "super-secret-hmac-key-flyrank-2026")

# Audit log of verified deliveries
DELIVERY_AUDIT_LOG: List[dict] = []


def verify_hmac_signature(payload_bytes: bytes, signature_header: Optional[str], secret: str = HMAC_SECRET) -> bool:
    """
    Verifies that X-Hub-Signature-256 matches HMAC-SHA256(payload_bytes, secret)
    using constant-time hmac.compare_digest to prevent timing attacks.
    """
    if not signature_header:
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    provided_hex = signature_header[len(prefix):].strip()
    expected_hex = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    return hmac.compare_digest(provided_hex, expected_hex)


@router.post("/platform-callback", status_code=status.HTTP_200_OK)
async def receive_platform_callback(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Receives platform delivery confirmation callbacks.
    Cryptographically verifies the HMAC-SHA256 signature before processing.
    """
    raw_body = await request.body()

    # 1. Cryptographic HMAC Verification
    is_valid = verify_hmac_signature(raw_body, x_hub_signature_256, HMAC_SECRET)
    if not is_valid:
        logger.warning(
            f"❌ [WebhookReceiver] Signature verification FAILED. Signature header: {x_hub_signature_256}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature. Request signature verification failed.",
        )

    # 2. Parse verified payload
    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_record = {
        "verified": True,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "signature": x_hub_signature_256,
        "payload": data,
    }

    DELIVERY_AUDIT_LOG.insert(0, event_record)
    logger.info(
        f"✅ [WebhookReceiver] HMAC verified delivery for post '{data.get('post_id')}' "
        f"from platform '{data.get('platform')}'"
    )

    return {"status": "accepted", "event_id": data.get("event_id")}


@router.get("/deliveries")
async def list_verified_deliveries(limit: int = 50):
    """Returns the list of cryptographically verified platform callback deliveries."""
    return DELIVERY_AUDIT_LOG[:limit]


@router.delete("/deliveries")
async def clear_deliveries():
    """Clears the delivery log (for test resets)."""
    DELIVERY_AUDIT_LOG.clear()
    return {"message": "Delivery audit log cleared"}
