"""
Background Worker Engine:
Continuously pulls jobs from the queue and executes the slow AI operation.

Implements the 2nd & 3rd Non-Negotiables:
- Retries with Exponential Backoff + Jitter: When a job fails, backoff exponentially.
- Dead Letter Queue & Alert Trigger: When retries exhaust, transition to DEAD_LETTER and trigger AlertService.
"""

import asyncio
import logging
import random
from typing import List, Optional

from queue_manager import queue_manager, JobQueueManager
from ai_task import execute_slow_ai_triage, SlowAIOperationError
from alert_service import alert_service, AlertService
from schemas import JobStatus

logger = logging.getLogger("background_jobs.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class BackgroundWorker:
    def __init__(
        self,
        queue_mgr: JobQueueManager = queue_manager,
        alert_svc: AlertService = alert_service,
        base_backoff_sec: float = 0.5,
        max_backoff_sec: float = 8.0,
        concurrency: int = 2
    ):
        self.queue_mgr = queue_mgr
        self.alert_svc = alert_svc
        self.base_backoff_sec = base_backoff_sec
        self.max_backoff_sec = max_backoff_sec
        self.concurrency = concurrency
        self._is_running = False
        self._worker_tasks: List[asyncio.Task] = []

    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculates exponential backoff with full jitter:
        backoff = min(max_backoff, base * 2^(attempt-1)) + random_jitter
        """
        exp_delay = self.base_backoff_sec * (2 ** max(0, attempt - 1))
        bounded_delay = min(self.max_backoff_sec, exp_delay)
        jitter = random.uniform(0, 0.2 * bounded_delay)
        return bounded_delay + jitter

    async def start(self) -> None:
        """Spawns background worker coroutines."""
        if self._is_running:
            return

        self._is_running = True
        logger.info(f"🚀 Starting {self.concurrency} background worker instances...")
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker_loop(worker_index=i + 1))
            self._worker_tasks.append(task)

    async def stop(self) -> None:
        """Gracefully halts all worker tasks."""
        if not self._is_running:
            return

        logger.info("🛑 Stopping background worker instances...")
        self._is_running = False
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        logger.info("Background workers shut down.")

    async def _worker_loop(self, worker_index: int) -> None:
        """Main worker loop pulling jobs from queue."""
        logger.info(f"[Worker #{worker_index}] Online and listening for jobs.")
        while self._is_running:
            try:
                # Wait for next available job ID
                job_id = await self.queue_mgr.dequeue()
                await self.process_job(job_id, worker_index)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Worker #{worker_index}] Unexpected loop error: {e}", exc_info=True)
                await asyncio.sleep(0.5)

    async def process_job(self, job_id: str, worker_index: int = 1) -> None:
        """Executes a single job with idempotency protection and retry handling."""
        # 1. Atomic state check & transition
        acquired, job = await self.queue_mgr.mark_processing(job_id)
        if not acquired or not job:
            logger.info(
                f"[Worker #{worker_index}] Skipped job {job_id} "
                f"(already processed or terminal - idempotency guard active)."
            )
            return

        logger.info(
            f"[Worker #{worker_index}] Picked up job {job_id} "
            f"(attempt #{job.attempts}/{job.max_retries}). Executing slow AI triage..."
        )

        # 2. Execute the slow operation
        try:
            result = await execute_slow_ai_triage(
                request=job.request,
                simulate_failure=job.request.simulate_failure,
                attempt=job.attempts
            )

            # Success!
            await self.queue_mgr.mark_completed(job_id, result)
            logger.info(
                f"✅ [Worker #{worker_index}] Job {job_id} COMPLETED successfully in "
                f"{job.duration_ms:.1f}ms. Category: {result.category}, Urgency: {result.urgency}"
            )

        except Exception as exc:
            error_msg = str(exc)
            backoff_sec = self.calculate_backoff(job.attempts)

            logger.warning(
                f"⚠️ [Worker #{worker_index}] Job {job_id} failed on attempt #{job.attempts}: {error_msg}"
            )

            # 3. Check if retryable or dead-letter
            can_retry = await self.queue_mgr.record_retry_attempt(job_id, error_msg, backoff_sec)

            if can_retry:
                logger.info(
                    f"🔄 [Worker #{worker_index}] Re-enqueuing job {job_id} after {backoff_sec:.2f}s backoff..."
                )
                await self.queue_mgr.re_enqueue(job_id, delay_sec=backoff_sec)
            else:
                # 4. Dead-Letter Queue & Alert Dispatching
                logger.error(
                    f"💀 [Worker #{worker_index}] Job {job_id} EXHAUSTED max retries ({job.max_retries}). "
                    f"Moving to DEAD_LETTER and dispatching alerts!"
                )
                await self.alert_svc.dispatch_job_failure_alert(
                    job_id=job_id,
                    attempts=job.attempts,
                    error_message=error_msg,
                    job_metadata={
                        "idempotency_key": job.idempotency_key,
                        "user_id": job.request.user_id,
                        "retry_history": job.retry_history,
                    }
                )
                await self.queue_mgr.mark_alert_dispatched(job_id)


# Global singleton worker instance
worker = BackgroundWorker()
