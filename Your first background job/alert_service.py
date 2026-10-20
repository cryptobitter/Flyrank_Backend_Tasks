"""
Alert Service:
Responsible for notifying on-call engineers, Slack channels, or webhooks
when background jobs experience fatal failures or exhaust retry thresholds.

Implements the 3rd Non-Negotiable: Someone must find out (Alerts).
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
import httpx

from schemas import AlertRecord

logger = logging.getLogger("background_jobs.alerts")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class AlertService:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self._alerts_history: List[AlertRecord] = []
        self._lock: Optional[asyncio.Lock] = None
        self._bound_loop = None

    def _ensure_lock(self):
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._bound_loop != current_loop or self._lock is None:
            self._lock = asyncio.Lock()
            self._bound_loop = current_loop

    async def dispatch_job_failure_alert(
        self,
        job_id: str,
        attempts: int,
        error_message: str,
        job_metadata: Optional[dict] = None
    ) -> AlertRecord:
        """
        Creates and emits an alert when a background job fails permanently.
        """
        alert = AlertRecord(
            alert_id=f"alt-{uuid.uuid4().hex[:8]}",
            job_id=job_id,
            event="JOB_DEAD_LETTER_EXHAUSTED",
            severity="CRITICAL",
            attempts_made=attempts,
            error_message=error_message,
            dispatched_at=datetime.now(timezone.utc).isoformat(),
            target_channel="slack-ops-alerts",
            payload=job_metadata or {}
        )

        self._ensure_lock()
        async with self._lock:
            self._alerts_history.insert(0, alert)

        # 1. Console structured alert log
        logger.error(
            f"🚨 [ALERT DISPATCHED] ID={alert.alert_id} | Job={job_id} | Attempts={attempts} | "
            f"Error='{error_message}' | Channel={alert.target_channel}"
        )

        # 2. Webhook post if configured
        if self.webhook_url:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    await client.post(self.webhook_url, json=alert.model_dump())
            except Exception as e:
                logger.warning(f"Failed to post alert to webhook {self.webhook_url}: {e}")

        return alert

    async def get_alerts(self, limit: int = 50) -> List[AlertRecord]:
        self._ensure_lock()
        async with self._lock:
            return list(self._alerts_history[:limit])

    async def clear_alerts(self) -> None:
        self._ensure_lock()
        async with self._lock:
            self._alerts_history.clear()


# Global singleton alert service instance
alert_service = AlertService()
