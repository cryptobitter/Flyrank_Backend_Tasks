"""
Scheduled Report Generation Engine (Stretch Goal).

Automates recurring periodic generation of production PDF reports
(e.g., hourly health digests, daily midnight executive rollups, or sprint reviews).
"""

from datetime import datetime, timedelta, timezone
import os
import sys
import threading
import time
from typing import Any, Dict, Optional

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from jobs import job_manager


class ReportScheduler:
    """
    Recurring scheduler running as a resilient background worker thread.
    Can be configured on-the-fly via REST API or CLI.
    """

    def __init__(self, default_interval_seconds: int = 3600) -> None:
        self.interval_seconds: int = default_interval_seconds
        self.is_running: bool = False
        self.last_run_at: Optional[str] = None
        self.next_run_at: Optional[str] = None
        self.total_runs_completed: int = 0
        self.last_job_id: Optional[str] = None
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self, interval_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Start the background recurring scheduler."""
        with self._lock:
            if self.is_running:
                return self.get_status()

            if interval_seconds and interval_seconds > 0:
                self.interval_seconds = interval_seconds

            self.is_running = True
            self._stop_event.clear()
            self._compute_next_run()

            self._worker_thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="SchedulerThread",
            )
            self._worker_thread.start()
            return self.get_status()

    def stop(self) -> Dict[str, Any]:
        """Signal the scheduler to stop running."""
        with self._lock:
            if not self.is_running:
                return self.get_status()

            self.is_running = False
            self._stop_event.set()
            self.next_run_at = None
            return self.get_status()

    def trigger_now(self, title: str = "Scheduled Digest (Manual Trigger)") -> Dict[str, Any]:
        """Immediately trigger a scheduled run out-of-band."""
        return self._execute_run(title=title)

    def _compute_next_run(self) -> None:
        next_dt = datetime.now(timezone.utc) + timedelta(seconds=self.interval_seconds)
        self.next_run_at = next_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _execute_run(self, title: Optional[str] = None) -> Dict[str, Any]:
        run_title = title or f"Automated Scheduled Digest #{self.total_runs_completed + 1}"
        job = job_manager.create_job(title=run_title)
        self.last_job_id = job.job_id
        self.last_run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.total_runs_completed += 1

        # Submit to worker pool
        job_manager.submit_job(job)
        return job.to_dict()

    def _run_loop(self) -> None:
        """Background loop executing scheduled report generations."""
        while not self._stop_event.is_set():
            # Wait for either interval expiration or stop signal
            if self._stop_event.wait(timeout=self.interval_seconds):
                break

            if self.is_running and not self._stop_event.is_set():
                self._execute_run()
                with self._lock:
                    self._compute_next_run()

    def get_status(self) -> Dict[str, Any]:
        """Return real-time operational status of the scheduler."""
        return {
            "is_running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "interval_human": f"{self.interval_seconds // 60}m {self.interval_seconds % 60}s"
            if self.interval_seconds < 3600
            else f"{self.interval_seconds / 3600:.1f}h",
            "total_runs_completed": self.total_runs_completed,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "last_job_id": self.last_job_id,
        }


# Singleton scheduler instance
scheduler = ReportScheduler(default_interval_seconds=3600)
