"""
Background Job Pattern & Artifact Handling Engine.

Implements the A7 asynchronous job pattern:
1. Enqueue job immediately with unique job_id (HTTP 202 Accepted)
2. State transitions: PENDING -> PROCESSING -> COMPLETED / FAILED
3. Artifact pattern: Persist heavy binary to disk / object storage,
   return lightweight JSON metadata with download links ('store and link, don't pass 20MB around').
4. Thread-safe execution with granular progress updates and timing diagnostics.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum
import os
import sys
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from report_generator import generate_pdf_report


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRecord:
    """Thread-safe representation of an asynchronous report generation job."""

    def __init__(self, job_id: str, title: str = "Sprint Analytics Report") -> None:
        self.job_id: str = job_id
        self.title: str = title
        self.status: JobStatus = JobStatus.PENDING
        self.created_at: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.duration_seconds: Optional[float] = None
        self.progress_pct: int = 0
        self.step_message: str = "Job queued in memory"
        self.artifact: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

    def to_dict(self, base_url: str = "") -> Dict[str, Any]:
        """Convert job metadata to JSON serializable response dict."""
        data: Dict[str, Any] = {
            "job_id": self.job_id,
            "title": self.title,
            "status": self.status.value,
            "progress_pct": self.progress_pct,
            "step_message": self.step_message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "status_url": f"{base_url}/reports/jobs/{self.job_id}",
        }

        if self.artifact:
            download_endpoint = f"/reports/download/{self.artifact['filename']}"
            data["artifact"] = {
                "filename": self.artifact["filename"],
                "file_size_bytes": self.artifact["file_size_bytes"],
                "file_size_kb": self.artifact["file_size_kb"],
                "sha256": self.artifact["sha256"],
                "download_url": f"{base_url}{download_endpoint}",
            }

        if self.error:
            data["error"] = self.error

        return data


class JobManager:
    """
    Central background job registry and worker execution pool.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ReportWorker")

    def create_job(self, title: str = "Sprint Analytics Report") -> JobRecord:
        """Register a new job in PENDING state."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        record = JobRecord(job_id=job_id, title=title)
        with self._lock:
            self._jobs[job_id] = record
        return record

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Retrieve job record by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[JobRecord]:
        """List all tracked background jobs ordered by creation timestamp."""
        with self._lock:
            return sorted(list(self._jobs.values()), key=lambda j: j.created_at, reverse=True)[:limit]

    def submit_job(self, job: JobRecord, db_path: Optional[str] = None) -> None:
        """Submit job for execution in worker thread pool."""
        self._executor.submit(self._execute_report_job, job, db_path)

    def _execute_report_job(self, job: JobRecord, db_path: Optional[str] = None) -> None:
        """Worker execution loop: updates states and generates artifact."""
        start_time = time.time()
        job.started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        job.status = JobStatus.PROCESSING
        job.progress_pct = 15
        job.step_message = "Connecting to SQLite and executing analytical aggregations"

        try:
            # Step 1: SQL Aggregations simulate compute load
            time.sleep(0.15)
            job.progress_pct = 40
            job.step_message = "Rendering high-DPI matplotlib analytical charts"

            # Step 2: Chart rendering and Flowable compilation
            time.sleep(0.15)
            job.progress_pct = 75
            job.step_message = "Assembling multi-page ReportLab PDF layout & NumberedCanvas"

            # Step 3: PDF Generation
            result = generate_pdf_report(
                db_path=db_path,
                report_title=job.title,
            )

            job.progress_pct = 100
            job.status = JobStatus.COMPLETED
            job.step_message = "Report generated and artifact stored securely"
            job.completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            job.duration_seconds = round(time.time() - start_time, 3)
            job.artifact = result

        except Exception as exc:
            job.status = JobStatus.FAILED
            job.step_message = f"Job execution failed: {str(exc)}"
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            job.duration_seconds = round(time.time() - start_time, 3)


# Singleton job manager instance
job_manager = JobManager()
