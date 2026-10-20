"""
FastAPI Server & REST API for PDF Report Generator Pipeline.

Demonstrates:
- Asynchronous Background Job Pattern (HTTP 202 Accepted)
- Store & Link Artifact Architecture (No heavy binary streaming in responses)
- Real-time job polling and progress tracking
- Scheduled background report generation (Stretch Goal)
- Directory-traversal secure download endpoints
"""

import os
import sys
from typing import Any, Dict, List, Optional

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from database import (
    init_db,
    query_category_breakdown,
    query_executive_metrics,
    query_priority_breakdown,
    query_recent_tasks,
)
from jobs import JobStatus, job_manager
from scheduler import scheduler

# Initialize database schema on startup
init_db()

app = FastAPI(
    title="Flyrank PDF Report Generator API",
    description="Background job pipeline for SQL aggregation, artifact handling, and ReportLab PDF compilation.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# Request / Response Schemas
# =====================================================================

class ReportGenerateRequest(BaseModel):
    title: str = Field(default="Sprint Analytics & Operations Report", description="Custom title for the PDF report")
    db_path: Optional[str] = Field(default=None, description="Optional custom SQLite database path")


class ScheduleConfigRequest(BaseModel):
    interval_seconds: int = Field(default=3600, ge=5, description="Recurring interval in seconds (minimum 5s)")


# =====================================================================
# API Endpoints
# =====================================================================

@app.get("/", tags=["System"])
def root_info(request: Request) -> Dict[str, Any]:
    """System health check and pipeline capability overview."""
    base_url = str(request.base_url).rstrip("/")
    artifacts_dir = os.path.join(CURRENT_DIR, "artifacts", "reports")
    artifact_count = len(os.listdir(artifacts_dir)) if os.path.exists(artifacts_dir) else 0

    return {
        "service": "Flyrank PDF Report Generator Pipeline",
        "version": "2.0.0",
        "status": "operational",
        "pattern": "A7 Background Job (Store & Link Artifact Handling)",
        "features": {
            "on_demand_generation": f"{base_url}/reports/generate",
            "job_status_check": f"{base_url}/reports/jobs/{{job_id}}",
            "download_artifact": f"{base_url}/reports/download/{{filename}}",
            "artifacts_catalog": f"{base_url}/reports/artifacts",
            "scheduler_management": f"{base_url}/reports/schedule/status",
            "sql_aggregations": f"{base_url}/data/summary",
        },
        "stats": {
            "active_tracked_jobs": len(job_manager.list_jobs()),
            "stored_pdf_artifacts": artifact_count,
            "scheduler_active": scheduler.is_running,
        },
    }


@app.post("/reports/generate", status_code=status.HTTP_202_ACCEPTED, tags=["Reports"])
def generate_report_async(
    payload: ReportGenerateRequest,
    request: Request,
) -> Dict[str, Any]:
    """
    On-Demand PDF Generation (A7 Job Pattern):
    - Validates payload and enqueues background worker job
    - Returns HTTP 202 Accepted immediately with unique job_id and status URL
    - Heavy report compilation and chart rendering occurs off the request lifecycle
    """
    base_url = str(request.base_url).rstrip("/")
    job = job_manager.create_job(title=payload.title)
    job_manager.submit_job(job, db_path=payload.db_path)

    return {
        "message": "Report generation job initiated successfully in background.",
        "job": job.to_dict(base_url=base_url),
    }


@app.get("/reports/jobs/{job_id}", tags=["Reports"])
def get_job_status(job_id: str, request: Request) -> Dict[str, Any]:
    """
    Poll status of a background report job.
    When completed, returns metadata including download link and execution timing.
    """
    base_url = str(request.base_url).rstrip("/")
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found in active registry.",
        )

    return {
        "job": job.to_dict(base_url=base_url),
    }


@app.get("/reports/jobs", tags=["Reports"])
def list_jobs(request: Request, limit: int = 20) -> Dict[str, Any]:
    """List recent background jobs and their state."""
    base_url = str(request.base_url).rstrip("/")
    jobs = job_manager.list_jobs(limit=limit)
    return {
        "total_jobs": len(jobs),
        "jobs": [j.to_dict(base_url=base_url) for j in jobs],
    }


@app.get("/reports/download/{filename}", tags=["Artifacts"])
def download_report_artifact(filename: str) -> FileResponse:
    """
    Download a generated PDF artifact securely.
    - Prevents directory traversal attacks
    - Sets standard RFC attachment headers and application/pdf media type
    """
    # Guard against directory traversal
    clean_filename = os.path.basename(filename)
    if clean_filename != filename or not filename.endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report filename.")

    artifacts_dir = os.path.join(CURRENT_DIR, "artifacts", "reports")
    file_path = os.path.join(artifacts_dir, clean_filename)

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report artifact '{filename}' not found on storage.",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=clean_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}"',
            "Cache-Control": "public, max-age=86400",
        },
    )


@app.get("/reports/artifacts", tags=["Artifacts"])
def list_report_artifacts(request: Request) -> Dict[str, Any]:
    """
    Catalog of all PDF artifacts currently persisted in storage.
    Demonstrates 'Store and Link' pattern: lists sizes and download URLs.
    """
    base_url = str(request.base_url).rstrip("/")
    artifacts_dir = os.path.join(CURRENT_DIR, "artifacts", "reports")
    os.makedirs(artifacts_dir, exist_ok=True)

    items: List[Dict[str, Any]] = []
    for f in sorted(os.listdir(artifacts_dir), reverse=True):
        if f.endswith(".pdf"):
            full_path = os.path.join(artifacts_dir, f)
            size_bytes = os.path.getsize(full_path)
            items.append(
                {
                    "filename": f,
                    "file_size_bytes": size_bytes,
                    "file_size_kb": round(size_bytes / 1024, 1),
                    "download_url": f"{base_url}/reports/download/{f}",
                }
            )

    return {
        "artifact_count": len(items),
        "storage_directory": artifacts_dir,
        "artifacts": items,
    }


# =====================================================================
# Scheduler Endpoints (Stretch Goal)
# =====================================================================

@app.get("/reports/schedule/status", tags=["Scheduler"])
def get_scheduler_status() -> Dict[str, Any]:
    """Inspect current periodic scheduler status."""
    return {"scheduler": scheduler.get_status()}


@app.post("/reports/schedule/start", tags=["Scheduler"])
def start_scheduler(payload: ScheduleConfigRequest) -> Dict[str, Any]:
    """Start background recurring report scheduler."""
    status_info = scheduler.start(interval_seconds=payload.interval_seconds)
    return {
        "message": f"Scheduler started with {payload.interval_seconds}s recurring interval.",
        "scheduler": status_info,
    }


@app.post("/reports/schedule/stop", tags=["Scheduler"])
def stop_scheduler() -> Dict[str, Any]:
    """Stop the recurring scheduler."""
    status_info = scheduler.stop()
    return {
        "message": "Scheduler stopped successfully.",
        "scheduler": status_info,
    }


@app.post("/reports/schedule/trigger", tags=["Scheduler"])
def trigger_scheduled_digest_now(request: Request) -> Dict[str, Any]:
    """Trigger a scheduled run immediately out of band."""
    base_url = str(request.base_url).rstrip("/")
    result = scheduler.trigger_now()
    return {
        "message": "Scheduled digest triggered on demand.",
        "job": result,
    }


# =====================================================================
# SQL Data Summary Endpoint
# =====================================================================

@app.get("/data/summary", tags=["Data"])
def get_data_summary() -> Dict[str, Any]:
    """Inspect real-time SQL aggregation calculations from SQLite."""
    metrics = query_executive_metrics()
    priorities = query_priority_breakdown()
    categories = query_category_breakdown()
    recent = query_recent_tasks(limit=5)

    return {
        "executive_metrics": metrics,
        "priority_breakdown": priorities,
        "category_breakdown": categories,
        "sample_tasks": recent,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
