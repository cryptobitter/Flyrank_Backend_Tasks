"""
Evidence Generation Script: Executes live end-to-end scenarios against the service,
capturing real request/response transcripts and database state for EVIDENCE.md.
"""

import json
import time
import hmac
import hashlib
from fastapi.testclient import TestClient

from app import app
from seed import seed_database
from database import get_db
from config import STRIPE_WEBHOOK_SECRET, PRICING

def run_and_capture_evidence():
    print("=" * 80)
    print("RUNNING LIVE EVIDENCE GENERATION FOR CAPSTONE REQUIREMENTS")
    print("=" * 80)

    seed_database()
    client = TestClient(app)

    evidence_records = {}

    # -------------------------------------------------------------
    # 1. Metering & Idempotency: Double-count prevention
    # -------------------------------------------------------------
    print("\n--- [EVIDENCE 1] Testing Idempotent Metering (No Double Count) ---")
    idemp_key = "idemp_proof_live_run_001"
    payload = {
        "tenant_id": "tenant_fresh",
        "prompt": "Synthesize a technical post-mortem on database replication lag.",
        "prompt_tokens": 120,
        "cached_prompt_tokens": 30,
        "completion_tokens": 80,
        "reasoning_tokens": 25
    }

    # Initial DB count
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM usage_events WHERE tenant_id = 'tenant_fresh';")
        count_0 = c.fetchone()[0]

    # Request 1 (Initial)
    r1 = client.post("/api/v1/generate", json=payload, headers={"Idempotency-Key": idemp_key})
    r1_json = r1.json()
    r1_cache = r1.headers.get("X-Cache")

    # Request 2 (Network Retry with exact same Idempotency-Key)
    r2 = client.post("/api/v1/generate", json=payload, headers={"Idempotency-Key": idemp_key})
    r2_json = r2.json()
    r2_cache = r2.headers.get("X-Cache")

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM usage_events WHERE tenant_id = 'tenant_fresh';")
        count_final = c.fetchone()[0]
        c.execute("SELECT * FROM usage_events WHERE tenant_id = 'tenant_fresh' ORDER BY id DESC LIMIT 1;")
        recorded_event = dict(c.fetchone())

    evidence_records["metering_idempotency"] = {
        "initial_db_count": count_0,
        "final_db_count": count_final,
        "delta_events_created": count_final - count_0,
        "request_1_status": r1.status_code,
        "request_1_cache_header": r1_cache,
        "request_1_body": r1_json,
        "request_2_status": r2.status_code,
        "request_2_cache_header": r2_cache,
        "request_2_body": r2_json,
        "db_recorded_event": recorded_event
    }

    # -------------------------------------------------------------
    # 2. Quotas: Exact boundary and 429 Too Many Requests
    # -------------------------------------------------------------
    print("\n--- [EVIDENCE 2] Testing Quota Boundary (At 1,000 vs 1,001) ---")
    # Call 1000 for tenant_near_limit (who has 999 used)
    r_boundary_allow = client.post(
        "/api/v1/generate",
        json={"tenant_id": "tenant_near_limit", "prompt": "Boundary call 1,000", "prompt_tokens": 15},
        headers={"Idempotency-Key": "idemp_call_1000"}
    )
    
    # Call 1001 for tenant_near_limit (now at 1000 used)
    r_boundary_reject = client.post(
        "/api/v1/generate",
        json={"tenant_id": "tenant_near_limit", "prompt": "Boundary call 1,001 (must fail)", "prompt_tokens": 15},
        headers={"Idempotency-Key": "idemp_call_1001"}
    )

    evidence_records["quota_boundary"] = {
        "call_1000_status": r_boundary_allow.status_code,
        "call_1000_quota_status": r_boundary_allow.json().get("quota_status"),
        "call_1001_status": r_boundary_reject.status_code,
        "call_1001_headers": {
            "Retry-After": r_boundary_reject.headers.get("Retry-After")
        },
        "call_1001_body": r_boundary_reject.json()
    }

    # -------------------------------------------------------------
    # 3. Cost Calculation: Pinned pricing & Token categories
    # -------------------------------------------------------------
    print("\n--- [EVIDENCE 3] Testing Pinned Token Pricing Calculations ---")
    r_cost = client.post(
        "/api/v1/generate",
        json={
            "tenant_id": "tenant_pro",
            "prompt": "Compute high dimensional tensor decomposition",
            "prompt_tokens": 100_000,          # 100k fresh input: $0.015000 (15,000 micros)
            "cached_prompt_tokens": 400_000,   # 400k cached input (75% off): $0.015000 (15,000 micros)
            "completion_tokens": 50_000,       # 50k output: $0.030000 (30,000 micros)
            "reasoning_tokens": 20_000         # 20k reasoning (output rate): $0.012000 (12,000 micros)
        },
        headers={"Idempotency-Key": "idemp_cost_breakdown_001"}
    )
    r_cost_json = r_cost.json()
    r_rollup = client.get("/api/v1/usage?tenant_id=tenant_pro").json()

    evidence_records["cost_calculation"] = {
        "generation_cost": r_cost_json["cost"],
        "rollup_totals": r_rollup["cost"],
        "rollup_usage": r_rollup["used"]
    }

    # -------------------------------------------------------------
    # 4. Stripe Integration: Test Checkout & Webhooks
    # -------------------------------------------------------------
    print("\n--- [EVIDENCE 4] Testing Stripe Checkout & Verified Webhook ---")
    # Create Checkout Session
    r_checkout = client.post("/api/v1/billing/checkout", json={"tenant_id": "tenant_upgrade_test", "plan_id": "pro"})
    checkout_data = r_checkout.json()

    # Pre-webhook rollup
    u_before = client.get("/api/v1/usage?tenant_id=tenant_upgrade_test").json()

    # Create signed Stripe webhook payload
    evt_id = f"evt_live_test_{int(time.time())}"
    wh_payload_dict = {
        "id": evt_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_evidence_session_999",
                "client_reference_id": "tenant_upgrade_test",
                "subscription": "sub_stripe_pro_evidence_verified",
                "metadata": {"tenant_id": "tenant_upgrade_test", "plan_id": "pro"}
            }
        }
    }
    raw_wh = json.dumps(wh_payload_dict).encode("utf-8")
    t_str = str(int(time.time()))
    signed_bytes = f"{t_str}.".encode("utf-8") + raw_wh
    sig_hex = hmac.new(STRIPE_WEBHOOK_SECRET.encode("utf-8"), signed_bytes, hashlib.sha256).hexdigest()
    sig_header = f"t={t_str},v1={sig_hex}"

    # Forged signature test
    r_forged = client.post(
        "/api/v1/webhooks/stripe",
        content=raw_wh,
        headers={"Stripe-Signature": f"t={t_str},v1=forged_bad_signature_0000000000", "Content-Type": "application/json"}
    )

    # Valid signature test
    r_valid = client.post(
        "/api/v1/webhooks/stripe",
        content=raw_wh,
        headers={"Stripe-Signature": sig_header, "Content-Type": "application/json"}
    )

    # Replay test (same event sent twice)
    r_replay = client.post(
        "/api/v1/webhooks/stripe",
        content=raw_wh,
        headers={"Stripe-Signature": sig_header, "Content-Type": "application/json"}
    )

    # Post-webhook rollup
    u_after = client.get("/api/v1/usage?tenant_id=tenant_upgrade_test").json()

    evidence_records["stripe_integration"] = {
        "checkout_session": checkout_data,
        "forged_webhook_status": r_forged.status_code,
        "forged_webhook_body": r_forged.json(),
        "valid_webhook_status": r_valid.status_code,
        "valid_webhook_body": r_valid.json(),
        "replay_webhook_status": r_replay.status_code,
        "replay_webhook_body": r_replay.json(),
        "plan_before_webhook": u_before["plan_id"],
        "plan_after_webhook": u_after["plan_id"],
        "limits_before": u_before["limits"],
        "limits_after": u_after["limits"]
    }

    # Save evidence json
    with open("evidence_data.json", "w") as f:
        json.dump(evidence_records, f, indent=2)

    print("\n[SUCCESS] Live evidence generated and saved to evidence_data.json")
    return evidence_records

if __name__ == "__main__":
    run_and_capture_evidence()
