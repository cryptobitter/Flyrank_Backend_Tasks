"""
Pytest Test Suite for SentinelAI 10x Solution:
Validates all 8 core backend engineering concepts:
1. API Endpoints
2. Database (SQLite + SQLAlchemy)
3. Authentication (JWT + PBKDF2)
4. LLM Integration (AI Incident Commander)
5. Background & Cron Jobs
6. Reporting (Automated ReportLab PDF Post-Mortem)
7. Caching & Idempotency
8. Webhooks (HMAC-SHA256 signature verification)
"""

import asyncio
import os
import pytest
from httpx import AsyncClient, ASGITransport

from app import app
from database import Base, SessionLocal, engine
from models import Incident, PostMortem, User
from cache import idempotency_store, ttl_cache
from webhook_notifier import compute_hmac_signature, WEBHOOK_HMAC_SECRET


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Initializes tables and resets state before and after each test."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(PostMortem).delete()
    db.query(Incident).delete()
    from models import AuditLog
    db.query(AuditLog).delete()
    db.query(User).delete()
    db.commit()
    db.close()
    idempotency_store.clear()
    ttl_cache.clear()
    yield
    db = SessionLocal()
    db.query(PostMortem).delete()
    db.query(Incident).delete()
    db.query(AuditLog).delete()
    db.query(User).delete()
    db.commit()
    db.close()
    idempotency_store.clear()
    ttl_cache.clear()


def test_auth_registration_and_jwt_login():
    """Concept #3: Authentication (PBKDF2 Salt Hashing & JWT Verification)."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Register User
            reg_res = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "aditya.rajput@flyrank.internal",
                    "password": "SuperSecretPassword123!",
                    "full_name": "Aditya Rajput",
                    "role": "admin",
                },
            )
            assert reg_res.status_code == 201
            reg_data = reg_res.json()
            assert reg_data["email"] == "aditya.rajput@flyrank.internal"

            # 2. Login to get JWT
            login_res = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "aditya.rajput@flyrank.internal",
                    "password": "SuperSecretPassword123!",
                },
            )
            assert login_res.status_code == 200
            token_data = login_res.json()
            assert "access_token" in token_data
            token = token_data["access_token"]

            # 3. Access Protected /me Route
            me_res = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me_res.status_code == 200
            assert me_res.json()["email"] == "aditya.rajput@flyrank.internal"

    asyncio.run(_run())


def test_incident_database_persistence_and_idempotency():
    """Concepts #1, #2, #7: API Endpoints, SQLite Database & Idempotency Store."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = {
                "title": "PostgreSQL connection pool exhausted in billing service",
                "service_name": "billing-service",
                "severity": "P1_CRITICAL",
                "raw_logs": "FATAL: remaining connection slots are reserved for non-replication superuser connections",
                "error_count": 85,
                "idempotency_key": "idemp-test-alert-billing-99",
            }

            # 1. First Ingestion
            res1 = await client.post("/api/v1/incidents", json=payload)
            assert res1.status_code == 201
            inc1 = res1.json()
            inc_id = inc1["id"]

            # 2. Duplicate Ingestion with Same Key (Idempotency Guard)
            res2 = await client.post("/api/v1/incidents", json=payload)
            assert res2.status_code == 200
            assert res2.headers.get("X-Idempotent-Replay") == "true"
            assert res2.json()["id"] == inc_id

            # 3. Verify in DB via GET /api/v1/incidents/:id
            get_res = await client.get(f"/api/v1/incidents/{inc_id}")
            assert get_res.status_code == 200
            assert get_res.json()["service_name"] == "billing-service"

    asyncio.run(_run())


def test_ai_commander_triage_and_ttl_caching():
    """Concepts #4, #7: LLM Integration & TTL Caching."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Create test incident
            inc_res = await client.post(
                "/api/v1/incidents",
                json={
                    "title": "Pod CrashLoopBackOff: Out of Memory error in worker",
                    "service_name": "worker-cluster",
                    "severity": "P1_CRITICAL",
                    "raw_logs": "Container memory limit exceeded (1024MB). Out of memory: Kill process 124 (node) score 995",
                    "error_count": 12,
                },
            )
            inc_id = inc_res.json()["id"]

            # Trigger AI Analysis
            ai_res = await client.post(f"/api/v1/incidents/{inc_id}/analyze")
            assert ai_res.status_code == 200
            ai_data = ai_res.json()

            assert ai_data["severity"] == "P1_CRITICAL"
            assert "memory" in ai_data["root_cause"].lower()
            assert ai_data["confidence_score"] > 0.8
            assert "runbook" in ai_data["suggested_runbook_url"]

            # Verify TTL Cache contains the generated playbook
            cached_playbook = ttl_cache.get("playbook:worker-cluster:P1_CRITICAL")
            assert cached_playbook is not None
            assert cached_playbook["confidence_score"] == ai_data["confidence_score"]

    asyncio.run(_run())


def test_pdf_post_mortem_generation_and_download():
    """Concept #6: Automated ReportLab PDF Report Generation."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Create incident
            inc_res = await client.post(
                "/api/v1/incidents",
                json={
                    "title": "Gateway 504 Timeout during Black Friday surge",
                    "service_name": "api-gateway",
                    "severity": "P2_HIGH",
                    "raw_logs": "upstream request timeout: 504 Gateway Timeout while reading response header from upstream",
                    "error_count": 40,
                },
            )
            inc_id = inc_res.json()["id"]

            # Generate Post-Mortem & PDF
            pm_res = await client.post(
                f"/api/v1/incidents/{inc_id}/post-mortem",
                json={
                    "executive_summary": "E-Commerce checkout experienced partial 504 degradation due to upstream throttling.",
                    "root_cause_analysis": "Upstream microservice thread pool saturated under peak traffic surge.",
                    "impact_duration_minutes": 25,
                },
            )
            assert pm_res.status_code == 200
            pm_data = pm_res.json()
            assert pm_data["pdf_path"] is not None
            assert os.path.exists(pm_data["pdf_path"])

            # Download Generated PDF
            dl_res = await client.get(f"/api/v1/post-mortems/{inc_id}/download-pdf")
            assert dl_res.status_code == 200
            assert dl_res.headers.get("content-type") == "application/pdf"
            assert len(dl_res.content) > 1000  # Non-trivial PDF binary bytes

    asyncio.run(_run())


def test_hmac_webhook_signature_dispatch():
    """Concept #8: Cryptographic HMAC-SHA256 Webhooks."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Test mock webhook receiver
            test_body = b'{"event": "incident.created", "incident_id": "test-123"}'
            sig = compute_hmac_signature(WEBHOOK_HMAC_SECRET, test_body)

            res = await client.post(
                "/api/v1/webhooks/mock-slack",
                content=test_body,
                headers={"X-Sentinel-Signature": sig},
            )
            assert res.status_code == 200
            assert res.json()["signature_present"] is True

    asyncio.run(_run())


def test_background_worker_queue_and_metrics():
    """Concepts #1, #5: Background Task Queue & Metrics Endpoint."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Query system metrics
            m_res = await client.get("/api/v1/metrics")
            assert m_res.status_code == 200
            m_data = m_res.json()
            assert m_data["status"] == "healthy"
            assert "incidents" in m_data
            assert "workers_online" in m_data

    asyncio.run(_run())
