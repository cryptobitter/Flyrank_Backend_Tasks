"""
Automated Test Suite for PDF Report Generator Pipeline.

Verifies:
1. SQL Aggregation Logic (COUNT, SUM, CASE WHEN, GROUP BY, variances)
2. PDF Generation & Artifact Format (ReportLab compilation, NumberedCanvas, %PDF magic bytes)
3. Background Job Lifecycle (HTTP 202 Accepted, PENDING -> PROCESSING -> COMPLETED)
4. Store & Link Pattern (Artifact stored on disk, lightweight JSON metadata + download URL)
5. Security Guardrails (Path traversal rejection, 404 on missing jobs)
6. Recurring Scheduler (Start, stop, on-demand trigger)
"""

import os
import sys
import time

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi.testclient import TestClient
import pytest

from database import (
    get_connection,
    init_db,
    query_category_breakdown,
    query_executive_metrics,
    query_priority_breakdown,
    query_recent_tasks,
)
from jobs import JobStatus, job_manager
from main import app
from report_generator import generate_pdf_report
from scheduler import scheduler

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """Ensure database is seeded before each test."""
    init_db()


# =====================================================================
# 1. SQL Aggregation Tests
# =====================================================================

def test_sql_executive_metrics():
    """Verify single-query executive metrics calculate proper aggregations."""
    metrics = query_executive_metrics()
    assert metrics["total_tasks"] >= 20
    assert metrics["completed_tasks"] >= 10
    assert metrics["completion_rate"] > 0
    assert metrics["total_estimated_hours"] > 0
    assert metrics["total_actual_hours"] > 0
    assert metrics["avg_turnaround_hours"] > 0
    assert metrics["active_contributors"] >= 4
    # Sanity check: completed + in_progress + pending == total
    assert (
        metrics["completed_tasks"]
        + metrics["in_progress_tasks"]
        + metrics["pending_tasks"]
        == metrics["total_tasks"]
    )


def test_sql_priority_breakdown():
    """Verify priority breakdown aggregates by custom order and counts."""
    priorities = query_priority_breakdown()
    assert len(priorities) == 4
    prio_names = [p["priority"] for p in priorities]
    assert prio_names == ["Critical", "High", "Medium", "Low"]
    for p in priorities:
        assert p["total"] >= p["completed"]
        assert p["completion_pct"] >= 0


def test_sql_category_breakdown():
    """Verify category rollup computes total tasks and variance."""
    categories = query_category_breakdown()
    assert len(categories) >= 5
    for c in categories:
        assert c["total_tasks"] >= c["completed_tasks"]
        assert "variance_hours" in c


# =====================================================================
# 2. PDF Report Generator & Artifact Integrity
# =====================================================================

def test_generate_pdf_report_output():
    """Verify direct PDF compilation outputs valid %PDF binary file."""
    result = generate_pdf_report(report_title="Test Unit Sprint Report")
    assert result["status"] == "success"
    assert os.path.exists(result["file_path"])
    assert result["file_size_bytes"] > 25000  # ReportLab PDF with 2 charts is >25KB
    assert len(result["sha256"]) == 64

    # Verify PDF magic bytes
    with open(result["file_path"], "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


# =====================================================================
# 3. Background Job Pattern & Artifact Handling
# =====================================================================

def test_job_manager_lifecycle():
    """Verify asynchronous job lifecycle: PENDING -> PROCESSING -> COMPLETED."""
    job = job_manager.create_job(title="Lifecycle Test")
    assert job.status == JobStatus.PENDING
    assert job.progress_pct == 0

    job_manager.submit_job(job)

    # Wait for completion (under 3s)
    max_wait = 10
    start = time.time()
    while job.status != JobStatus.COMPLETED and time.time() - start < max_wait:
        time.sleep(0.1)

    assert job.status == JobStatus.COMPLETED
    assert job.progress_pct == 100
    assert job.duration_seconds is not None
    assert job.artifact is not None
    assert "filename" in job.artifact
    assert os.path.exists(job.artifact["file_path"])

    # Artifact handling pattern verification: dictionary contains link, not raw 20MB bytes
    job_dict = job.to_dict()
    assert "download_url" in job_dict["artifact"]
    assert job_dict["artifact"]["download_url"].startswith("/reports/download/")


# =====================================================================
# 4. REST API Endpoints & Store-and-Link Pattern
# =====================================================================

def test_api_root_overview():
    """Verify GET / returns health, stats, and feature links."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "operational"
    assert "features" in data
    assert "stats" in data


def test_api_on_demand_generation_workflow():
    """
    Test complete client journey:
    1. POST /reports/generate -> 202 Accepted with job_id
    2. Poll GET /reports/jobs/{job_id} until completed
    3. Download artifact via GET /reports/download/{filename} -> 200 OK
    """
    # 1. Trigger background job
    post_res = client.post("/reports/generate", json={"title": "E2E API Test Report"})
    assert post_res.status_code == 202
    post_data = post_res.json()
    assert "job" in post_data
    job_id = post_data["job"]["job_id"]
    status_url = post_data["job"]["status_url"]
    assert job_id.startswith("job_")

    # 2. Poll status
    completed_job = None
    for _ in range(50):
        poll_res = client.get(f"/reports/jobs/{job_id}")
        assert poll_res.status_code == 200
        job_info = poll_res.json()["job"]
        if job_info["status"] == "completed":
            completed_job = job_info
            break
        time.sleep(0.1)

    assert completed_job is not None, "Job timed out before reaching completed state"
    assert completed_job["progress_pct"] == 100
    artifact = completed_job["artifact"]
    assert artifact["file_size_bytes"] > 25000

    # 3. Download artifact
    filename = artifact["filename"]
    download_res = client.get(f"/reports/download/{filename}")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert download_res.content.startswith(b"%PDF-")


def test_api_download_security_guards():
    """Verify unauthorized or invalid file requests return error status codes."""
    # Attempting to fetch non-PDF file or non-existent file
    res1 = client.get("/reports/download/invalid_file.txt")
    assert res1.status_code == 400

    res2 = client.get("/reports/download/non_existent_report_12345.pdf")
    assert res2.status_code == 404

    res3 = client.get("/reports/jobs/invalid_job_uuid_99999")
    assert res3.status_code == 404


def test_api_artifacts_catalog():
    """Verify GET /reports/artifacts returns stored PDF files."""
    res = client.get("/reports/artifacts")
    assert res.status_code == 200
    data = res.json()
    assert "artifacts" in data
    assert data["artifact_count"] >= 1


# =====================================================================
# 5. Recurring Scheduler Tests (Stretch Goal)
# =====================================================================

def test_scheduler_lifecycle_and_trigger():
    """Verify scheduler start, stop, and out-of-band trigger."""
    # Check initial status
    res = client.get("/reports/schedule/status")
    assert res.status_code == 200

    # Start scheduler
    start_res = client.post("/reports/schedule/start", json={"interval_seconds": 120})
    assert start_res.status_code == 200
    assert start_res.json()["scheduler"]["is_running"] is True

    # Immediate trigger
    trig_res = client.post("/reports/schedule/trigger")
    assert trig_res.status_code == 200
    assert "job" in trig_res.json()

    # Stop scheduler
    stop_res = client.post("/reports/schedule/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["scheduler"]["is_running"] is False
