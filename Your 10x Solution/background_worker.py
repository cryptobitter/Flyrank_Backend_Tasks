"""
Background Worker & Cron Task Engine:
- Asynchronous queue worker processing incident triage tasks
- Retry mechanism with exponential backoff
- Scheduled background cron monitoring task
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional
from datetime import datetime, timezone

from ai_commander import ai_commander
from cache import ttl_cache
from webhook_notifier import dispatch_incident_webhook

logger = logging.getLogger("background_worker")


class BackgroundWorkerPool:
    def __init__(self, concurrency: int = 2):
        self.concurrency = concurrency
        self._queue: Optional[asyncio.Queue] = None
        self._is_running = False
        self._tasks: List[asyncio.Task] = []
        self._cron_task: Optional[asyncio.Task] = None
        self._cron_count = 0
        self._bound_loop = None

    def _ensure_queue(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if self._bound_loop != loop or self._queue is None:
            self._queue = asyncio.Queue()
            self._bound_loop = loop

    async def start(self):
        if self._is_running:
            return
        self._ensure_queue()
        self._is_running = True
        logger.info(f"🚀 [WorkerPool] Spawning {self.concurrency} background workers + 1 cron monitor...")
        for i in range(self.concurrency):
            t = asyncio.create_task(self._worker_loop(i + 1))
            self._tasks.append(t)
        self._cron_task = asyncio.create_task(self._cron_monitor_loop())

    async def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        for t in self._tasks:
            t.cancel()
        if self._cron_task:
            self._cron_task.cancel()
        await asyncio.gather(*self._tasks, self._cron_task, return_exceptions=True)
        self._tasks.clear()
        self._cron_task = None
        logger.info("🛑 [WorkerPool] Background workers and cron stopped.")

    async def enqueue_triage_job(self, incident_id: str, title: str, service: str, logs: str, count: int = 1):
        self._ensure_queue()
        job = {
            "incident_id": incident_id,
            "title": title,
            "service": service,
            "logs": logs,
            "count": count,
            "attempts": 0,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._queue.put(job)
        logger.info(f"📥 [WorkerPool] Enqueued triage job for incident {incident_id}")

    async def _worker_loop(self, worker_id: int):
        logger.info(f"[Worker #{worker_id}] Online and listening.")
        while self._is_running:
            try:
                self._ensure_queue()
                job = await self._queue.get()
                await self._process_job(job, worker_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Worker #{worker_id}] Unhandled error: {e}")
                await asyncio.sleep(0.5)

    async def _process_job(self, job: dict, worker_id: int):
        job["attempts"] += 1
        incident_id = job["incident_id"]
        logger.info(f"[Worker #{worker_id}] Processing incident {incident_id} (Attempt #{job['attempts']})...")

        try:
            # 1. Run AI analysis
            triage = await ai_commander.analyze_incident(
                title=job["title"],
                service_name=job["service"],
                raw_logs=job["logs"],
                error_count=job["count"],
            )

            # 2. Cache playbook in TTL Cache
            cache_key = f"playbook:{job['service']}:{triage.severity.value}"
            ttl_cache.set(cache_key, triage.model_dump(), ttl=600)

            # 3. Dispatch Webhook
            await dispatch_incident_webhook(
                incident_id=incident_id,
                title=job["title"],
                service_name=job["service"],
                severity=triage.severity.value,
            )

            logger.info(f"✅ [Worker #{worker_id}] Finished triage for incident {incident_id}: {triage.severity.value}")

        except Exception as e:
            if job["attempts"] < 3:
                backoff = (2 ** job["attempts"]) + random.uniform(0, 0.5)
                logger.warning(f"⚠️ [Worker #{worker_id}] Failed, retrying in {backoff:.1f}s: {e}")
                await asyncio.sleep(backoff)
                await self._queue.put(job)
            else:
                logger.error(f"💀 [Worker #{worker_id}] Job {incident_id} dead-lettered after 3 attempts: {e}")

    async def _cron_monitor_loop(self):
        """Simulates periodic SRE health probe run every 30 seconds."""
        logger.info("⏱️ [CronMonitor] Scheduled periodic health check active.")
        while self._is_running:
            try:
                await asyncio.sleep(30.0)
                self._cron_count += 1
                logger.info(f"⏰ [CronMonitor] Pulse #{self._cron_count}: All monitored service heartbeats healthy.")
            except asyncio.CancelledError:
                break


worker_pool = BackgroundWorkerPool()
