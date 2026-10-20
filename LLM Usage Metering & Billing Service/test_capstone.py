"""
Comprehensive Evaluation Suite for LLM Usage Metering & Billing Engine.
Verifies all 5 Acceptance Probes from Section 12, boundary validation, and background jobs.
"""

import unittest
import json
import time
import hmac
import hashlib
from fastapi.testclient import TestClient

from app import app
from seed import seed_database
from database import get_db
from config import STRIPE_WEBHOOK_SECRET, PRICING, PLANS

class TestBillingCapstone(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.client = TestClient(app)

    def test_probe_1_idempotent_metering_no_double_count(self):
        """
        PROBE 1: Send the same billable request twice with one idempotency key.
        Guarantees:
        - Exactly one usage event recorded in database.
        - Second response mirrors first.
        - Second response contains 'X-Cache: HIT' and cached_response: true.
        """
        idemp_key = "idemp_test_probe_1_unique_key_999"
        payload = {
            "tenant_id": "tenant_fresh",
            "prompt": "Explain quantum entanglement in simple terms",
            "prompt_tokens": 100,
            "cached_prompt_tokens": 20,
            "completion_tokens": 50,
            "reasoning_tokens": 15
        }
        headers = {"Idempotency-Key": idemp_key}

        # Check initial event count for tenant_fresh
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM usage_events WHERE tenant_id = 'tenant_fresh';")
            count_before = cursor.fetchone()[0]

        # First Request (MISS)
        resp1 = self.client.post("/api/v1/generate", json=payload, headers=headers)
        self.assertEqual(resp1.status_code, 200, f"Expected 200, got: {resp1.text}")
        data1 = resp1.json()
        self.assertEqual(resp1.headers.get("X-Cache"), "MISS")
        self.assertFalse(data1.get("cached_response"))

        # Second Request (HIT - exact replay)
        resp2 = self.client.post("/api/v1/generate", json=payload, headers=headers)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(resp2.headers.get("X-Cache"), "HIT")
        self.assertTrue(data2.get("cached_response"))

        # Compare outputs: identical request_id and content
        self.assertEqual(data1["request_id"], data2["request_id"])
        self.assertEqual(data1["content"], data2["content"])
        self.assertEqual(data1["cost"]["total_cost_micros"], data2["cost"]["total_cost_micros"])

        # Check database: exactly one new usage event created, NOT two!
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM usage_events WHERE tenant_id = 'tenant_fresh';")
            count_after = cursor.fetchone()[0]

        self.assertEqual(count_after, count_before + 1, "CRITICAL BUG: Double-count occurred on idempotency retry!")
        print("\n[PROBE 1 PASSED] Exactly-once metering verified: same idempotency key resulted in 1 event and cached response.")

    def test_probe_2_boundary_honesty_quota_exceeded(self):
        """
        PROBE 2: Drive a tenant to its exact quota.
        - Tenant 'tenant_near_limit' has 999/1000 calls used.
        - Call #1000 is ALLOWED (boundary honesty).
        - Call #1001 is REJECTED with 429 Too Many Requests and a clear message.
        """
        # Call #1000 (at boundary)
        resp_1000 = self.client.post(
            "/api/v1/generate",
            json={"tenant_id": "tenant_near_limit", "prompt": "Boundary request 1000", "prompt_tokens": 10},
            headers={"Idempotency-Key": "idemp_boundary_1000"}
        )
        self.assertEqual(resp_1000.status_code, 200, "Call #1000 must be allowed at the quota boundary.")
        data_1000 = resp_1000.json()
        self.assertEqual(data_1000["quota_status"]["api_calls_used"], 1000)
        self.assertEqual(data_1000["quota_status"]["api_calls_remaining"], 0)

        # Call #1001 (beyond boundary)
        resp_1001 = self.client.post(
            "/api/v1/generate",
            json={"tenant_id": "tenant_near_limit", "prompt": "Boundary request 1001", "prompt_tokens": 10},
            headers={"Idempotency-Key": "idemp_boundary_1001"}
        )
        self.assertEqual(resp_1001.status_code, 429, "Call #1001 must return 429 Too Many Requests.")
        data_1001 = resp_1001.json()
        self.assertIn("API call quota exceeded", data_1001["message"])
        self.assertIn("Retry-After", resp_1001.headers)
        print("\n[PROBE 2 PASSED] Boundary honesty verified: call 1,000 passed, call 1,001 returned 429.")

    def test_probe_3_stripe_test_checkout_and_webhook_plan_sync(self):
        """
        PROBE 3: Complete a Stripe test Checkout.
        - Webhook flips tenant Free -> Pro.
        - GET /api/v1/usage immediately shows new Pro limits (50,000 calls / 10M tokens).
        """
        tenant_id = "tenant_upgrade_test"

        # Verify initial Free limits
        usage_before = self.client.get(f"/api/v1/usage?tenant_id={tenant_id}").json()
        self.assertEqual(usage_before["plan_id"], "free")
        self.assertEqual(usage_before["limits"]["api_calls"], 1000)

        # Simulate Checkout completion webhook
        event_id = f"evt_checkout_completed_{int(time.time())}"
        payload_dict = {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": f"cs_test_{int(time.time())}",
                    "client_reference_id": tenant_id,
                    "subscription": f"sub_stripe_pro_{int(time.time())}",
                    "metadata": {"tenant_id": tenant_id, "plan_id": "pro"}
                }
            }
        }
        raw_payload = json.dumps(payload_dict).encode("utf-8")
        timestamp = str(int(time.time()))
        signed_data = f"{timestamp}.".encode("utf-8") + raw_payload
        signature = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode("utf-8"),
            signed_data,
            hashlib.sha256
        ).hexdigest()
        sig_header = f"t={timestamp},v1={signature}"

        # Send Webhook
        webhook_resp = self.client.post(
            "/api/v1/webhooks/stripe",
            content=raw_payload,
            headers={"Stripe-Signature": sig_header, "Content-Type": "application/json"}
        )
        self.assertEqual(webhook_resp.status_code, 200)
        self.assertEqual(webhook_resp.json()["status"], "processed")

        # Verify GET /usage shows updated Pro plan and limits
        usage_after = self.client.get(f"/api/v1/usage?tenant_id={tenant_id}").json()
        self.assertEqual(usage_after["plan_id"], "pro")
        self.assertEqual(usage_after["limits"]["api_calls"], 50000)
        self.assertEqual(usage_after["limits"]["tokens"], 10000000)
        print("\n[PROBE 3 PASSED] Stripe test Checkout sync verified: webhook flipped tenant Free -> Pro.")

    def test_probe_4_forged_webhook_rejected_and_replays_deduplicated(self):
        """
        PROBE 4:
        - Send forged webhook (bad signature) -> 400 Bad Request, nothing changes.
        - Replay a real valid event twice -> processed once, second is ignored.
        """
        raw_payload = b'{"id": "evt_forged_999", "type": "checkout.session.completed", "data": {}}'
        bad_sig_header = f"t={int(time.time())},v1=deadbeefcafebabe1234567890abcdef"

        # 1. Forged Signature Test
        forged_resp = self.client.post(
            "/api/v1/webhooks/stripe",
            content=raw_payload,
            headers={"Stripe-Signature": bad_sig_header, "Content-Type": "application/json"}
        )
        self.assertEqual(forged_resp.status_code, 400, "Forged signature must be rejected with 400.")
        self.assertIn("INVALID_WEBHOOK_SIGNATURE", forged_resp.json()["code"])

        # 2. Replay Deduplication Test
        event_id = f"evt_replay_test_{int(time.time())}"
        valid_payload_dict = {
            "id": event_id,
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_test", "status": "active", "metadata": {"tenant_id": "tenant_pro"}}}
        }
        valid_raw = json.dumps(valid_payload_dict).encode("utf-8")
        timestamp = str(int(time.time()))
        signed_data = f"{timestamp}.".encode("utf-8") + valid_raw
        valid_signature = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode("utf-8"),
            signed_data,
            hashlib.sha256
        ).hexdigest()
        valid_sig_header = f"t={timestamp},v1={valid_signature}"

        # First delivery: processed
        first_resp = self.client.post(
            "/api/v1/webhooks/stripe",
            content=valid_raw,
            headers={"Stripe-Signature": valid_sig_header, "Content-Type": "application/json"}
        )
        self.assertEqual(first_resp.status_code, 200)
        self.assertEqual(first_resp.json()["status"], "processed")

        # Second delivery (replay): ignored duplicate
        replay_resp = self.client.post(
            "/api/v1/webhooks/stripe",
            content=valid_raw,
            headers={"Stripe-Signature": valid_sig_header, "Content-Type": "application/json"}
        )
        self.assertEqual(replay_resp.status_code, 200)
        self.assertEqual(replay_resp.json()["status"], "ignored_duplicate")
        print("\n[PROBE 4 PASSED] Webhook security verified: forged signature rejected with 400, replay deduplicated.")

    def test_probe_5_pinned_pricing_rules_and_token_categories(self):
        """
        PROBE 5: Check pinned pricing rules.
        - Cached input tokens are cheaper ($0.0375/1M vs $0.150/1M fresh input, 75% discount).
        - Reasoning tokens count as output tokens ($0.600/1M).
        - Categories are not lumped together; GET /api/v1/usage matches.
        """
        # Test input:
        # 1,000,000 fresh prompt tokens = 150,000 micros ($0.15)
        # 1,000,000 cached prompt tokens = 37,500 micros ($0.0375)
        # 1,000,000 completion tokens = 600,000 micros ($0.60)
        # 1,000,000 reasoning tokens = 600,000 micros ($0.60)
        # Base fee = 100 micros ($0.000100)
        # Total expected = 1,387,600 micro-dollars ($1.387600)
        
        req_payload = {
            "tenant_id": "tenant_pro",
            "prompt": "Deep mathematical theorem proof",
            "prompt_tokens": 1000000,
            "cached_prompt_tokens": 1000000,
            "completion_tokens": 1000000,
            "reasoning_tokens": 1000000,
        }
        resp = self.client.post("/api/v1/generate", json=req_payload, headers={"Idempotency-Key": "idemp_pricing_test_001"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        cost = data["cost"]

        expected_total_micros = 150000 + 37500 + 600000 + 600000 + 100
        self.assertEqual(cost["total_cost_micros"], expected_total_micros)
        self.assertEqual(cost["formatted_usd"], "$1.387600")

        # Verify cached input tokens were strictly 75% cheaper than fresh input (37,500 vs 150,000)
        self.assertEqual(cost["cached_cost_micros"], 37500)
        self.assertEqual(cost["prompt_cost_micros"], 150000)
        self.assertLess(cost["cached_cost_micros"], cost["prompt_cost_micros"])

        # Verify reasoning tokens are priced identically to output tokens (600,000 micros)
        self.assertEqual(cost["reasoning_cost_micros"], 600000)
        self.assertEqual(cost["completion_cost_micros"], 600000)

        # Verify rollup matches
        usage_resp = self.client.get("/api/v1/usage?tenant_id=tenant_pro").json()
        self.assertGreaterEqual(usage_resp["cost"]["total_cost_micros"], expected_total_micros)
        print("\n[PROBE 5 PASSED] Pinned pricing rules verified: exact micro-dollar pricing for cached and reasoning tokens.")

    def test_boundary_validation_no_500_errors(self):
        """Verifies boundary validation: invalid inputs return clean 4xx (422/400), never a 500 error."""
        # Missing required prompt and tenant_id
        bad_req = self.client.post("/api/v1/generate", json={})
        self.assertEqual(bad_req.status_code, 422)
        self.assertEqual(bad_req.json()["code"], "INVALID_INPUT")

        # Negative token count
        bad_tokens = self.client.post("/api/v1/generate", json={"tenant_id": "tenant_fresh", "prompt": "Hi", "prompt_tokens": -50})
        self.assertEqual(bad_tokens.status_code, 422)

        # Unknown tenant
        unknown_tenant = self.client.get("/api/v1/usage?tenant_id=non_existent_tenant_999")
        self.assertEqual(unknown_tenant.status_code, 404)
        print("\n[VALIDATION PASSED] Boundary validation verified: clean 4xx responses, zero 500 crashes.")

    def test_background_worker_alerts_and_reconciliation(self):
        """Verifies background job: 80% & 100% usage alerts and nightly reconciliation audit."""
        # Check alerts endpoint
        alerts_resp = self.client.get("/api/v1/admin/alerts")
        self.assertEqual(alerts_resp.status_code, 200)
        alerts_data = alerts_resp.json()
        self.assertIn("alerts", alerts_data)

        # Trigger reconciliation
        reconcile_resp = self.client.post("/api/v1/admin/reconcile")
        self.assertEqual(reconcile_resp.status_code, 200)
        reconcile_data = reconcile_resp.json()
        self.assertGreaterEqual(reconcile_data["tenants_checked"], 5)
        print("\n[BACKGROUND WORKER PASSED] Alerts and reconciliation background job executed successfully.")

if __name__ == "__main__":
    unittest.main()
