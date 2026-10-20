"""
FastAPI Application: Asynchronous Background Job System.

The Professional Pattern for Slow Operations:
1. Accept Fast: Web endpoint accepts the request, validates it, and answers instantly with 202 Accepted.
2. Work in the Background: A background worker pulls jobs from the queue and executes the slow AI triage call.
3. Report Status: A dedicated status endpoint reports real-time state, results, or errors.

Handles the 3 Non-Negotiables:
- Idempotency (Jobs will run twice)
- Retries with backoff (They will fail)
- Alerts (Someone must find out)
"""

from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, Response, status
from fastapi.responses import JSONResponse

from schemas import (
    JobSubmissionRequest,
    JobSubmissionResponse,
    JobStatusResponse,
    JobStatus,
    AlertRecord,
)
from queue_manager import queue_manager
from worker import worker
from alert_service import alert_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts the background worker on startup and shuts it down on exit."""
    await worker.start()
    yield
    await worker.stop()


app = FastAPI(
    title="Asynchronous Background Job API",
    description=(
        "Production-grade background worker architecture that moves slow operations "
        "out of the HTTP request lifecycle. Answers in <20ms with HTTP 202 Accepted, "
        "enforces idempotency, retries with exponential backoff, and alerts on fatal failures."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.post(
    "/api/v1/jobs",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a slow AI triage job (Answers instantly with 202 Accepted)",
    responses={
        202: {
            "description": "Request accepted for asynchronous processing",
            "headers": {
                "Location": {
                    "description": "URI of the status endpoint to poll for completion",
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
async def submit_job(
    request: JobSubmissionRequest,
    response: Response,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Accepts a slow AI triage request and immediately returns HTTP 202 Accepted.

    - Computes or extracts the idempotency key.
    - If the idempotency key already exists, returns the existing job record (prevents double work).
    - If new, enqueues the job for background worker execution.
    - Sets the HTTP Location header to the status inspection endpoint.
    """
    # 1. Resolve idempotency key (Header takes precedence over body, then auto-hash)
    idempotency_key = queue_manager.generate_idempotency_key(
        request, explicit_key=idempotency_key_header
    )

    # 2. Enqueue job
    record, is_duplicate = await queue_manager.enqueue(request, idempotency_key)

    # 3. Formulate status URL and set Location header
    status_url = f"/api/v1/jobs/{record.job_id}"
    response.headers["Location"] = status_url

    return JobSubmissionResponse(
        job_id=record.job_id,
        status=record.status,
        status_url=status_url,
        idempotency_key=record.idempotency_key,
        is_duplicate=is_duplicate,
        message=(
            "Existing job returned via idempotency key"
            if is_duplicate
            else "Job accepted and enqueued for background worker"
        ),
    )


@app.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll job status, progress, and results",
)
async def get_job_status(job_id: str):
    """
    Returns the real-time status of a submitted job.

    Possible statuses:
    - `queued`: Waiting for an available background worker
    - `processing`: Worker is actively executing the slow AI task
    - `completed`: Successfully finished; `result` field populated
    - `dead_letter`: All retries exhausted; alerts dispatched
    """
    job = await queue_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found in registry",
        )
    return job.to_status_response()


@app.get(
    "/api/v1/jobs",
    response_model=List[JobStatusResponse],
    summary="List recent background jobs",
)
async def list_jobs(limit: int = 50):
    """Lists recent background jobs for observability and monitoring."""
    jobs = await queue_manager.list_jobs(limit=limit)
    return [j.to_status_response() for j in jobs]


@app.get(
    "/api/v1/alerts",
    response_model=List[AlertRecord],
    summary="List dispatched failure alerts",
)
async def list_alerts(limit: int = 50):
    """Lists alerts triggered by dead-letter jobs (3rd Non-Negotiable verification)."""
    return await alert_service.get_alerts(limit=limit)


@app.get(
    "/api/v1/health",
    summary="System and worker health check",
)
async def health_check():
    """Health check endpoint reporting worker concurrency and queue state."""
    jobs = await queue_manager.list_jobs()
    queued_count = sum(1 for j in jobs if j.status == JobStatus.QUEUED)
    processing_count = sum(1 for j in jobs if j.status == JobStatus.PROCESSING)
    completed_count = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
    dead_letter_count = sum(1 for j in jobs if j.status == JobStatus.DEAD_LETTER)

    return {
        "status": "healthy",
        "workers_online": worker._is_running,
        "concurrency": worker.concurrency,
        "metrics": {
            "total_jobs": len(jobs),
            "queued": queued_count,
            "processing": processing_count,
            "completed": completed_count,
            "dead_letter": dead_letter_count,
        },
    }
