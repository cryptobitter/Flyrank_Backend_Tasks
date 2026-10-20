"""
Queue Manager & State Machine:
Manages job storage, state transitions, and the 1st Non-Negotiable: Idempotency.

Core guarantees:
1. Idempotency: Jobs with duplicate idempotency keys return existing job records instantly.
2. At-Least-Once Delivery Protection: If a worker receives a job that is already completed
   or currently processing, it safely no-ops.
3. State Transitions: Atomic transitions with state history and duration tracking.
"""

import asyncio
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import uuid

from schemas import (
    JobStatus,
    JobSubmissionRequest,
    JobStatusResponse,
    TriageJudgment,
)


class JobRecord:
    def __init__(
        self,
        job_id: str,
        idempotency_key: str,
        request: JobSubmissionRequest,
        max_retries: int = 3
    ):
        self.job_id = job_id
        self.idempotency_key = idempotency_key
        self.request = request
        self.status = JobStatus.QUEUED
        self.attempts = 0
        self.max_retries = max_retries
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.duration_ms: Optional[float] = None
        self.result: Optional[TriageJudgment] = None
        self.error: Optional[str] = None
        self.alert_dispatched: bool = False
        self.retry_history: List[dict] = []
        self._start_perf: Optional[float] = None

    def to_status_response(self) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            idempotency_key=self.idempotency_key,
            attempts=self.attempts,
            max_retries=self.max_retries,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_ms=self.duration_ms,
            result=self.result,
            error=self.error,
            alert_dispatched=self.alert_dispatched,
            retry_history=self.retry_history,
        )


class JobQueueManager:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._jobs: Dict[str, JobRecord] = {}
        self._idempotency_map: Dict[str, str] = {}  # idempotency_key -> job_id
        self._queue: Optional[asyncio.Queue] = None
        self._lock: Optional[asyncio.Lock] = None
        self._bound_loop = None

    def _ensure_primitives(self):
        """Ensures Queue and Lock are bound to the currently running event loop."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._bound_loop != current_loop or self._queue is None:
            self._queue = asyncio.Queue()
            self._lock = asyncio.Lock()
            self._bound_loop = current_loop

    def generate_idempotency_key(self, request: JobSubmissionRequest, explicit_key: Optional[str] = None) -> str:
        """Derives a deterministic key from header or sha256 of request payload."""
        if explicit_key and explicit_key.strip():
            return explicit_key.strip()
        if request.idempotency_key and request.idempotency_key.strip():
            return request.idempotency_key.strip()

        payload_repr = f"{request.user_id}:{request.message}:{request.simulate_failure}"
        return f"auto-{hashlib.sha256(payload_repr.encode()).hexdigest()[:16]}"

    async def enqueue(
        self,
        request: JobSubmissionRequest,
        idempotency_key: str
    ) -> Tuple[JobRecord, bool]:
        """
        Enqueues a new job or returns existing record if idempotency key matches.
        Returns (job_record, is_duplicate).
        """
        self._ensure_primitives()
        async with self._lock:
            if idempotency_key in self._idempotency_map:
                existing_job_id = self._idempotency_map[idempotency_key]
                existing_job = self._jobs[existing_job_id]
                return existing_job, True

            job_id = f"job-{uuid.uuid4().hex[:12]}"
            record = JobRecord(
                job_id=job_id,
                idempotency_key=idempotency_key,
                request=request,
                max_retries=self.max_retries
            )

            self._jobs[job_id] = record
            self._idempotency_map[idempotency_key] = job_id
            await self._queue.put(job_id)
            return record, False

    async def dequeue(self) -> str:
        """Pulls the next job ID from the queue (blocking until one arrives)."""
        self._ensure_primitives()
        return await self._queue.get()

    async def re_enqueue(self, job_id: str, delay_sec: float = 0.0) -> None:
        """Re-enqueues a job for retry after a backoff delay."""
        self._ensure_primitives()
        async def _delayed_put():
            if delay_sec > 0:
                await asyncio.sleep(delay_sec)
            self._ensure_primitives()
            await self._queue.put(job_id)

        asyncio.create_task(_delayed_put())

    async def get_job(self, job_id: str) -> Optional[JobRecord]:
        self._ensure_primitives()
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(self, limit: int = 50) -> List[JobRecord]:
        self._ensure_primitives()
        async with self._lock:
            return sorted(
                list(self._jobs.values()),
                key=lambda j: j.created_at,
                reverse=True
            )[:limit]

    async def mark_processing(self, job_id: str) -> Tuple[bool, Optional[JobRecord]]:
        """
        Idempotent worker lock:
        Only transitions from QUEUED to PROCESSING. If already completed, returns False.
        """
        self._ensure_primitives()
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False, None
            if job.status == JobStatus.COMPLETED or job.status == JobStatus.DEAD_LETTER:
                return False, job

            job.status = JobStatus.PROCESSING
            job.attempts += 1
            if not job.started_at:
                job.started_at = datetime.now(timezone.utc).isoformat()
                job._start_perf = time.perf_counter()
            return True, job

    async def mark_completed(self, job_id: str, result: TriageJudgment) -> None:
        self._ensure_primitives()
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc).isoformat()
            if job._start_perf:
                job.duration_ms = (time.perf_counter() - job._start_perf) * 1000.0
            job.result = result
            job.error = None

    async def record_retry_attempt(
        self,
        job_id: str,
        error_msg: str,
        backoff_sec: float
    ) -> bool:
        """
        Records a failed attempt.
        Returns True if job can be retried, or False if max retries reached (dead letter).
        """
        self._ensure_primitives()
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            attempt_entry = {
                "attempt": job.attempts,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backoff_sec": round(backoff_sec, 2)
            }
            job.retry_history.append(attempt_entry)
            job.error = error_msg

            if job.attempts < job.max_retries:
                job.status = JobStatus.QUEUED
                return True
            else:
                job.status = JobStatus.DEAD_LETTER
                job.completed_at = datetime.now(timezone.utc).isoformat()
                if job._start_perf:
                    job.duration_ms = (time.perf_counter() - job._start_perf) * 1000.0
                return False

    async def mark_alert_dispatched(self, job_id: str) -> None:
        self._ensure_primitives()
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.alert_dispatched = True

    async def clear_all(self) -> None:
        self._ensure_primitives()
        async with self._lock:
            self._jobs.clear()
            self._idempotency_map.clear()
            if self._queue:
                while not self._queue.empty():
                    try:
                        self._queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break


# Global singleton queue manager
queue_manager = JobQueueManager(max_retries=3)
