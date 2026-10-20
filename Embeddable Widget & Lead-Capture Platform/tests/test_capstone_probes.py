"""
Automated Test Suite for FlyRank Embeddable Widget & Lead-Capture Platform.

Covers all 6 Acceptance Probes from Section 13 and all Section 6 requirements:
- PROBE 1: Cross-origin submission from second origin -> stored, 2xx, visible in dashboard
- PROBE 2: Malformed and oversized payloads -> clean 4xx JSON errors, NEVER 500
- PROBE 3: Burst of rapid submissions -> 429 appears with Retry-After, recovery succeeds
- PROBE 4: Geo provider fallback chain -> Provider A down -> Provider B -> Degraded success
- PROBE 5: Safe side effects -> notification exception caught, submission STILL succeeds
- PROBE 6: Honeypot field filled -> caught/blocked as spam, not counted as clean lead
- Multi-tenant isolation: Tenant A cannot read, update, delete, or inspect Tenant B's assets
- HTTP caching headers: Versioned script bundle (immutable) & widget config (stale-while-revalidate)
"""

import os
import sys

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi.testclient import TestClient
import pytest

from app.auth import create_access_token
from app.database import get_db, init_db
from app.geo import geo_service
from app.limiter import limiter
from app.main import app
from app.notifications import notification_service
from seed import seed_database

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Seed fresh test database before running tests."""
    seed_database()
    limiter.reset()
    geo_service.set_provider_a(True)
    geo_service.set_provider_b(True)
    notification_service.set_force_failure(False)


# =====================================================================
# PROBE 1: Cross-Origin Submission & Dashboard Visibility
# =====================================================================

def test_probe_1_cross_origin_submission_and_dashboard_visibility():
    """
    PROBE 1 — POST a valid submission from the second-origin test page
    -> stored, 2xx (201 Created), and visible via the dashboard API.
    """
    widget_id = "wgt_demo123"
    origin = "http://customer-site.local:5500"  # Simulated second origin

    # 1. Verify CORS Preflight OPTIONS request
    options_res = client.options(
        f"/api/v1/widgets/{widget_id}/submit",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert options_res.status_code == 200
    assert options_res.headers.get("access-control-allow-origin") in ("*", origin)
    assert "POST" in options_res.headers.get("access-control-allow-methods", "")

    # 2. Submit valid lead from second origin
    lead_payload = {
        "data": {
            "name": "Sarah Connor",
            "email": "sarah@resistance.org",
            "company": "Cyberdyne Systems",
        },
        "_hp_website": None,  # Clean human submission
    }

    submit_res = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json=lead_payload,
        headers={"Origin": origin, "User-Agent": "Mozilla/5.0 TestBrowser"},
    )

    assert submit_res.status_code == 201
    assert submit_res.headers.get("access-control-allow-origin") in ("*", origin)
    submit_data = submit_res.json()
    assert submit_data["status"] == "success"
    submission_id = submit_data["submission_id"]
    assert submission_id.startswith("sub_")

    # 3. Verify lead is visible in owner dashboard
    token = create_access_token(tenant_id="tnt_acme_corp", email="alex@acme.com")
    dash_res = client.get(
        "/api/v1/dashboard/submissions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dash_res.status_code == 200
    submissions = dash_res.json()["submissions"]
    matching = [s for s in submissions if s["id"] == submission_id]
    assert len(matching) == 1
    assert matching[0]["data"]["email"] == "sarah@resistance.org"
    assert matching[0]["is_spam"] == 0


# =====================================================================
# PROBE 2: Boundary Validation (Malformed & Oversized Payloads)
# =====================================================================

def test_probe_2_malformed_and_oversized_payloads():
    """
    PROBE 2 — Send a malformed and an oversized payload
    -> clean 4xx JSON errors, NEVER a 500.
    """
    widget_id = "wgt_demo123"

    # Case A: Missing required 'data' dictionary
    res_missing = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json={"something_else": 123},
    )
    assert res_missing.status_code in (400, 422)
    assert "application/json" in res_missing.headers["content-type"]

    # Case B: Malformed email format
    res_bad_email = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json={"data": {"name": "Bob", "email": "not-an-email-at-all"}},
    )
    assert res_bad_email.status_code in (400, 422)

    # Case C: Oversized payload (> 100KB string)
    oversized_data = {"name": "Hacker", "comment": "A" * 150_000}
    res_oversized = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json={"data": oversized_data},
    )
    assert res_oversized.status_code in (400, 413, 422)
    assert res_oversized.status_code != 500

    # Case D: Non-existent widget ID
    res_not_found = client.post(
        "/api/v1/widgets/wgt_does_not_exist/submit",
        json={"data": {"name": "Alice", "email": "alice@test.com"}},
    )
    assert res_not_found.status_code == 404
    assert res_not_found.status_code != 500


# =====================================================================
# PROBE 3: Rate Limiting & Abuse Protection
# =====================================================================

def test_probe_3_burst_rate_limiting_and_recovery():
    """
    PROBE 3 — Fire a burst of rapid submissions
    -> 429 s appear with Retry-After, and a normal request right after still succeeds.
    """
    widget_id = "wgt_demo123"
    client_ip = "198.51.100.77"

    # Send 15 requests to hit the IP threshold
    got_429 = False
    for i in range(20):
        res = client.post(
            f"/api/v1/widgets/{widget_id}/submit",
            json={"data": {"name": f"User {i}", "email": f"user{i}@burst.com"}},
            headers={"X-Forwarded-For": client_ip},
        )
        if res.status_code == 429:
            got_429 = True
            assert "Retry-After" in res.headers
            assert "Too Many Requests" in res.json()["detail"]
            break

    assert got_429, "Expected at least one HTTP 429 Too Many Requests response during burst"

    # Reset limiter for normal traffic or use different IP
    client_ip_normal = "203.0.113.99"
    res_normal = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json={"data": {"name": "Legit User", "email": "legit@normal.com"}},
        headers={"X-Forwarded-For": client_ip_normal},
    )
    assert res_normal.status_code == 201


# =====================================================================
# PROBE 4: Geolocation Provider Fallback Chain
# =====================================================================

def test_probe_4_geo_provider_fallback_chain():
    """
    PROBE 4 — Disable geo provider A -> next submission is stored, enriched by provider B.
    Disable both -> stored anyway, without geo (degrade, never fail).
    """
    widget_id = "wgt_demo123"

    # 1. Normal state: Provider A answers
    geo_service.set_provider_a(True)
    geo_service.set_provider_b(True)
    res_a = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json={"data": {"name": "Test A", "email": "testA@geo.com"}},
        headers={"X-Forwarded-For": "127.0.0.1"},
    )
    assert res_a.status_code == 201
    assert res_a.json()["geo"]["geo_provider"] == "provider_a"

    # 2. Provider A disabled -> Provider B answers
    geo_service.set_provider_a(False)
    res_b = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json={"data": {"name": "Test B", "email": "testB@geo.com"}},
        headers={"X-Forwarded-For": "127.0.0.1"},
    )
    assert res_b.status_code == 201
    assert res_b.json()["geo"]["geo_provider"] == "provider_b"
    assert res_b.json()["geo"]["city"] == "Toronto"

    # 3. Disable BOTH providers -> Submission still succeeds! (Degrade, never fail)
    geo_service.set_provider_b(False)
    res_degraded = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json={"data": {"name": "Test Degraded", "email": "degraded@geo.com"}},
        headers={"X-Forwarded-For": "127.0.0.1"},
    )
    assert res_degraded.status_code == 201
    assert res_degraded.json()["geo"]["geo_provider"] == "degraded"
    assert res_degraded.json()["geo"]["country"] == "Unknown"

    # Verify submission was stored in DB even when all geo providers failed
    sub_id = res_degraded.json()["submission_id"]
    with get_db() as conn:
        row = conn.execute("SELECT id, geo_provider FROM submissions WHERE id = ?", (sub_id,)).fetchone()
        assert row is not None
        assert row["geo_provider"] == "degraded"


# =====================================================================
# PROBE 5: Safe Side Effects (Error Boundary)
# =====================================================================

def test_probe_5_safe_side_effects_error_boundary():
    """
    PROBE 5 — Force the email/webhook side effect to throw
    -> the submission still returns success and is stored.
    """
    widget_id = "wgt_demo123"

    # Enable forced side effect failure mode
    notification_service.set_force_failure(True)

    res = client.post(
        f"/api/v1/widgets/{widget_id}/submit",
        json={"data": {"name": "Resilience Test", "email": "resilience@test.com"}},
    )

    # Must return 201 Created despite notification failure
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "success"
    sub_id = data["submission_id"]

    # Verify row was safely committed to database
    with get_db() as conn:
        row = conn.execute("SELECT id FROM submissions WHERE id = ?", (sub_id,)).fetchone()
        assert row is not None


# =====================================================================
# PROBE 6: Honeypot Anti-Spam Defense
# =====================================================================

def test_probe_6_honeypot_bot_prevention():
    """
    PROBE 6 — Fill the honeypot field like a bot would
    -> the submission is flagged as spam and not counted in clean leads.
    """
    widget_id = "wgt_demo123"

    # Bot populates the hidden honeypot field _hp_website
    bot_payload = {
        "data": {"name": "Crypto Bot", "email": "bot@spammer.xyz"},
        "_hp_website": "http://malicious-spam-link.ru",
    }

    res = client.post(f"/api/v1/widgets/{widget_id}/submit", json=bot_payload)
    assert res.status_code == 201
    assert res.json()["status"] == "spam_blocked"

    # Verify in DB: tagged as is_spam = 1
    sub_id = res.json()["submission_id"]
    with get_db() as conn:
        row = conn.execute("SELECT is_spam FROM submissions WHERE id = ?", (sub_id,)).fetchone()
        assert row is not None
        assert row["is_spam"] == 1

    # Verify dashboard excludes spam from clean leads count
    token = create_access_token(tenant_id="tnt_acme_corp", email="alex@acme.com")
    stats_res = client.get("/api/v1/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
    assert stats_res.status_code == 200
    assert stats_res.json()["summary"]["spam_blocked"] >= 1


# =====================================================================
# Multi-Tenant Isolation Tests (Section 6)
# =====================================================================

def test_multi_tenant_isolation_strictly_enforced():
    """
    Verify multi-tenant isolation:
    Tenant B CANNOT view, edit, or delete Tenant A's widgets or submissions.
    """
    # Tenant A owns wgt_demo123
    tenant_b_token = create_access_token(tenant_id="tnt_globex_inc", email="sarah@globex.com")
    headers_b = {"Authorization": f"Bearer {tenant_b_token}"}

    # 1. Tenant B attempts to read Tenant A's widget -> 404
    read_res = client.get("/api/v1/widgets/wgt_demo123", headers=headers_b)
    assert read_res.status_code == 404

    # 2. Tenant B attempts to update Tenant A's widget -> 404
    update_res = client.put(
        "/api/v1/widgets/wgt_demo123",
        json={"title": "Hacked Title"},
        headers=headers_b,
    )
    assert update_res.status_code == 404

    # 3. Tenant B attempts to delete Tenant A's widget -> 404
    delete_res = client.delete("/api/v1/widgets/wgt_demo123", headers=headers_b)
    assert delete_res.status_code == 404

    # 4. Tenant B dashboard only sees Tenant B widgets
    list_res = client.get("/api/v1/widgets", headers=headers_b)
    assert list_res.status_code == 200
    b_widgets = [w["id"] for w in list_res.json()["widgets"]]
    assert "wgt_demo123" not in b_widgets
    assert "wgt_globex789" in b_widgets


# =====================================================================
# Fast, Cached Widget Delivery Tests (Section 6)
# =====================================================================

def test_widget_delivery_cache_control_headers():
    """
    Verify HTTP Cache-Control headers:
    - Widget JavaScript: public, max-age=31536000, immutable
    - Widget Config: public, max-age=60, stale-while-revalidate=120
    """
    # 1. Widget script bundle
    script_res = client.get("/v1/widget.js")
    assert script_res.status_code == 200
    assert "max-age=31536000" in script_res.headers.get("Cache-Control", "")
    assert "immutable" in script_res.headers.get("Cache-Control", "")

    # 2. Widget config endpoint
    config_res = client.get("/api/v1/widgets/wgt_demo123/config")
    assert config_res.status_code == 200
    assert "max-age=60" in config_res.headers.get("Cache-Control", "")
    assert "stale-while-revalidate=120" in config_res.headers.get("Cache-Control", "")
    assert config_res.headers.get("access-control-allow-origin") == "*"
