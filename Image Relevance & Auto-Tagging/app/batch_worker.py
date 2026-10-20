"""
Asynchronous Batch Processing Engine with Retries.

Teaches: Batch AI Discipline & Cost Tracking
- Runs vision understanding and vector embedding generation asynchronously
- Features retry resilience for transient model timeouts
- Tracks per-job progress and flags low-confidence images
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from app.cost_tracker import cost_tracker
from app.database import get_db, utc_now_iso
from app.embeddings import embedding_engine
from app.vision import vision_pipeline

logger = logging.getLogger("batch_worker")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")


class BatchJobRecord:
    def __init__(self, job_id: str, total_items: int) -> None:
        self.job_id = job_id
        self.status = "PENDING"
        self.total_items = total_items
        self.processed = 0
        self.successful = 0
        self.flagged_low_confidence = 0
        self.retry_count = 0
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "total_items": self.total_items,
            "processed": self.processed,
            "successful": self.successful,
            "flagged_low_confidence": self.flagged_low_confidence,
            "retry_count": self.retry_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


class BatchProcessingManager:
    """Manages asynchronous batch ingestion jobs."""

    def __init__(self, max_workers: int = 4) -> None:
        self._jobs: Dict[str, BatchJobRecord] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="BatchWorker")

    def get_job(self, job_id: str) -> Optional[BatchJobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def trigger_corpus_ingestion(self, max_retries: int = 2) -> BatchJobRecord:
        """Scan data/images/ and launch asynchronous batch processing."""
        image_files = []
        if os.path.exists(IMAGES_DIR):
            image_files = [f for f in sorted(os.listdir(IMAGES_DIR)) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

        job_id = f"batch_{uuid.uuid4().hex[:10]}"
        record = BatchJobRecord(job_id=job_id, total_items=len(image_files))

        with self._lock:
            self._jobs[job_id] = record

        self._executor.submit(self._run_batch, record, image_files, max_retries)
        return record

    def _run_batch(self, job: BatchJobRecord, image_files: List[str], max_retries: int) -> None:
        job.status = "RUNNING"
        job.started_at = utc_now_iso()

        for filename in image_files:
            img_id = os.path.splitext(filename)[0]
            full_path = os.path.join(IMAGES_DIR, filename)

            # Retry resilience loop
            success = False
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    # 1. Vision Analysis & Schema Validation
                    vision_out = vision_pipeline.analyze_image(image_id=img_id, file_path=full_path)

                    # 2. Persist to Database
                    with get_db() as conn:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO images (
                                id, filename, file_path, subject, category, attributes,
                                caption, confidence, flagged, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                img_id,
                                filename,
                                full_path,
                                vision_out.subject,
                                vision_out.category,
                                json.dumps(vision_out.attributes),
                                vision_out.caption,
                                vision_out.confidence,
                                1 if vision_out.flagged_for_review else 0,
                                utc_now_iso(),
                            ),
                        )
                        conn.commit()

                    # 3. Generate Vector Embedding for Caption + Attributes
                    combined_text = f"{vision_out.subject} {vision_out.caption} {' '.join(vision_out.attributes)}"
                    embedding_engine.generate_embedding(
                        text=combined_text,
                        entity_id=img_id,
                        entity_type="image",
                    )

                    success = True
                    job.successful += 1
                    if vision_out.flagged_for_review:
                        job.flagged_low_confidence += 1
                    break

                except Exception as exc:
                    last_exc = exc
                    job.retry_count += 1
                    time.sleep(0.05 * (attempt + 1))

            if not success:
                logger.error(f"Failed to process {img_id} after {max_retries} retries: {last_exc}")

            job.processed += 1

        job.status = "COMPLETED"
        job.completed_at = utc_now_iso()


batch_manager = BatchProcessingManager()
