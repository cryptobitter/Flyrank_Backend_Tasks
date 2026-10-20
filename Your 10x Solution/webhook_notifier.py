"""
Webhook Alert Dispatcher:
Sends HMAC-SHA256 cryptographically signed alerts to Slack, Discord, or monitoring endpoints.
"""

import hashlib
import hmac
import json
import logging
from typing import Optional
import httpx

from config import ALERT_WEBHOOK_URL, WEBHOOK_HMAC_SECRET

logger = logging.getLogger("webhook_notifier")


def compute_hmac_signature(secret: str, payload_bytes: bytes) -> str:
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


async def dispatch_incident_webhook(
    incident_id: str,
    title: str,
    service_name: str,
    severity: str,
    webhook_url: Optional[str] = None,
    secret: str = WEBHOOK_HMAC_SECRET,
) -> bool:
    """Dispatches HMAC-signed alert event."""
    url = webhook_url or ALERT_WEBHOOK_URL
    if not url:
        logger.info(f"ℹ️ [WebhookNotifier] No webhook URL configured. Simulated alert for {incident_id}.")
        return False

    payload = {
        "event": "incident.created",
        "incident_id": incident_id,
        "title": title,
        "service_name": service_name,
        "severity": severity,
        "timestamp": "2026-10-20T20:30:00Z",
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_hmac_signature(secret, raw_bytes)

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                url,
                content=raw_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Sentinel-Signature": sig,
                    "User-Agent": "SentinelAI-Notifier/1.0",
                },
            )
            logger.info(f"📡 [WebhookNotifier] Alert sent to {url} -> HTTP {resp.status_code}")
            return resp.status_code in [200, 201, 202, 204]
    except Exception as e:
        logger.warning(f"⚠️ [WebhookNotifier] Failed to dispatch webhook: {e}")
        return False
