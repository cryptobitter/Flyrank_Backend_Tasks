"""
Pytest Test Suite for Background Job Architecture:
Validates the fast acceptance (202), queue worker lifecycle, and the 3 Non-Negotiables:
1. Idempotency (Jobs will run twice)
2. Retries & Exponential Backoff (Jobs will fail)
3. Alerts & Dead-Letter Handling (Someone must find out)
"""

import asyncio
import time
import pytest
from httpx import AsyncClient, ASGITransport

from app import app
from queue_manager import queue_manager
from worker import BackgroundWorker, worker
from alert_service import alert_service
from schemas import JobStatus, JobSubmissionRequest, TriageCategory, UrgencyLevel


def test_accept_fast_returns_202_instantly():
    """
    Core Pattern Test:
    Verify the slow operation is moved out of the request and answers instantly with 202 Accepted.
    """
    async def _run():
        await queue_manager.clear_all()
        await alert_service.clear_alerts()
        await worker.start()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                payload = {
                    "message": "We have an urgent billing question regarding an unauthorized credit card charge.",
                    "user_id": "usr-100",
                    "simulate_delay_sec": 1.5,  # 1.5 second slow task
                }

                t0 = time.perf_counter()
                res = await client.post("/api/v1/jobs", json=payload)
                latency_ms = (time.perf_counter() - t0) * 1000.0

                # Must return 202 Accepted fast (< 100ms vs 1.5s task)
                assert res.status_code == 202
                assert latency_ms < 100.0

                data = res.json()
                assert "job_id" in data
                assert data["status"] in ["queued", "processing"]
                assert res.headers.get("Location") == f"/api/v1/jobs/{data['job_id']}"
                assert data["is_duplicate"] is False
        finally:
            await worker.stop()

    asyncio.run(_run())


def test_job_status_lifecycle_to_completed():
    """
    Verifies status endpoint reflects queued -> processing -> completed with structured result.
    """
    async def _run():
        await queue_manager.clear_all()
        await alert_service.clear_alerts()
        await worker.start()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                payload = {
                    "message": "Production database is down with 500 internal server errors on checkout!",
                    "simulate_delay_sec": 0.05,
                }

                res = await client.post("/api/v1/jobs", json=payload)
                job_id = res.json()["job_id"]
                status_url = f"/api/v1/jobs/{job_id}"

                # Poll until complete
                completed = False
                result_data = None
                for _ in range(30):
                    st_res = await client.get(status_url)
                    assert st_res.status_code == 200
                    st_data = st_res.json()
                    if st_data["status"] == "completed":
                        completed = True
                        result_data = st_data
                        break
                    await asyncio.sleep(0.1)

                assert completed is True
                assert result_data is not None
                assert result_data["result"] is not None
                assert result_data["result"]["category"] in [c.value for c in TriageCategory]
                assert result_data["result"]["urgency"] in [u.value for u in UrgencyLevel]
                assert result_data["duration_ms"] > 0
                assert result_data["completed_at"] is not None
        finally:
            await worker.stop()

    asyncio.run(_run())


def test_idempotency_header_prevents_duplicate_execution():
    """
    1st Non-Negotiable: Idempotency (Jobs will run twice).
    Submitting the same idempotency key must return the existing job and avoid duplicate work.
    """
    async def _run():
        await queue_manager.clear_all()
        await alert_service.clear_alerts()
        await worker.start()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                key = "idemp-key-unique-998"
                payload = {
                    "message": "Duplicate network retry test message.",
                    "simulate_delay_sec": 0.1,
                }

                # First submission
                res1 = await client.post("/api/v1/jobs", json=payload, headers={"Idempotency-Key": key})
                assert res1.status_code == 202
                data1 = res1.json()
                assert data1["is_duplicate"] is False
                job_id1 = data1["job_id"]

                # Duplicate submission with identical key
                res2 = await client.post("/api/v1/jobs", json=payload, headers={"Idempotency-Key": key})
                assert res2.status_code == 202
                data2 = res2.json()

                # Must return the same job ID and flag as duplicate
                assert data2["is_duplicate"] is True
                assert data2["job_id"] == job_id1
                assert data2["idempotency_key"] == key

                # Verify only one job exists in the queue manager
                all_jobs = await queue_manager.list_jobs()
                matching = [j for j in all_jobs if j.idempotency_key == key]
                assert len(matching) == 1
        finally:
            await worker.stop()

    asyncio.run(_run())


def test_worker_at_least_once_delivery_protection():
    """
    Verifies that if a queue delivers an already-completed job to a worker,
    the worker safely no-ops without modifying state or re-running.
    """
    async def _run():
        await queue_manager.clear_all()
        await alert_service.clear_alerts()
        request = JobSubmissionRequest(
            message="At-least-once idempotency guard check.",
            simulate_delay_sec=0.0
        )
        job, _ = await queue_manager.enqueue(request, "idemp-guard-test")

        # Worker executes job to completion
        await worker.process_job(job.job_id)
        assert job.status == JobStatus.COMPLETED

        first_completed_at = job.completed_at

        # Simulate duplicate delivery of the same job to another worker
        await worker.process_job(job.job_id)

        # State should remain intact and not re-executed
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at == first_completed_at
        assert job.attempts == 1

    asyncio.run(_run())


def test_retries_with_exponential_backoff():
    """
    2nd Non-Negotiable: Retries (Jobs will fail).
    Verifies exponential backoff calculation increases and jitter is bounded.
    """
    worker_inst = BackgroundWorker(base_backoff_sec=1.0, max_backoff_sec=10.0)

    b1 = worker_inst.calculate_backoff(1)  # base ~ 1.0
    b2 = worker_inst.calculate_backoff(2)  # base ~ 2.0
    b3 = worker_inst.calculate_backoff(3)  # base ~ 4.0

    assert 1.0 <= b1 <= 1.3
    assert 2.0 <= b2 <= 2.6
    assert 4.0 <= b3 <= 5.0
    assert b1 < b2 < b3


def test_dead_letter_and_alert_dispatch_on_fatal_failure():
    """
    3rd Non-Negotiable: Alerts (Someone must find out).
    When all retries are exhausted, the job transitions to DEAD_LETTER
    and an alert is dispatched to AlertService.
    """
    async def _run():
        await queue_manager.clear_all()
        await alert_service.clear_alerts()

        # Create worker with very short backoff for fast testing
        fast_worker = BackgroundWorker(base_backoff_sec=0.05, max_backoff_sec=0.2)
        await fast_worker.start()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                payload = {
                    "message": "Testing fatal failure retry exhaustion.",
                    "simulate_failure": True,
                    "simulate_delay_sec": 0.01,
                }

                res = await client.post("/api/v1/jobs", json=payload)
                job_id = res.json()["job_id"]
                status_url = f"/api/v1/jobs/{job_id}"

                # Poll until dead_letter
                dead_letter = False
                st_data = None
                for _ in range(40):
                    st_res = await client.get(status_url)
                    st_data = st_res.json()
                    if st_data["status"] == "dead_letter":
                        dead_letter = True
                        break
                    await asyncio.sleep(0.1)

                assert dead_letter is True
                assert st_data["attempts"] == 3  # Max retries
                assert st_data["alert_dispatched"] is True
                assert len(st_data["retry_history"]) == 3

                # Check alert service received the record
                alerts_res = await client.get("/api/v1/alerts")
                alerts = alerts_res.json()
                assert len(alerts) >= 1
                assert any(a["job_id"] == job_id for a in alerts)
                matching_alert = next(a for a in alerts if a["job_id"] == job_id)
                assert matching_alert["severity"] == "CRITICAL"
                assert matching_alert["attempts_made"] == 3
        finally:
            await fast_worker.stop()

    asyncio.run(_run())


def test_job_not_found_returns_404():
    """Verifies unknown job_id queries return HTTP 404 with helpful detail."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/api/v1/jobs/non-existent-job-999")
            assert res.status_code == 404
            assert "not found" in res.json()["detail"].lower()

    asyncio.run(_run())


def test_health_check_endpoint():
    """Verifies system health and metrics endpoint."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/api/v1/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "healthy"
            assert "metrics" in data
            assert "workers_online" in data

    asyncio.run(_run())
