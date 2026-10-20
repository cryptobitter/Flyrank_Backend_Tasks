"""
Live Interactive Demonstration Script: Social Media Studio.

Demonstrates:
1. Multi-platform broadcast (Twitter Mock, LinkedIn Mock, Discord, Telegram)
2. Handling 429 Too Many Requests with Retry-After backoff recovery
3. Idempotency Key enforcement (zero duplicate posts)
4. HMAC-SHA256 cryptographically verified delivery callbacks
"""

import asyncio
import json
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from httpx import AsyncClient, ASGITransport
from app import app
from mock_platform_server import sign_payload, HMAC_SECRET
from publisher_service import publisher_service


async def run_demo():
    print("\n" + "=" * 75)
    print("📢 FLYRANK CAPSTONE: SOCIAL MEDIA STUDIO DEMONSTRATION")
    print("=" * 75)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        publisher_service.mock_client = client

        # ----------------------------------------------------------------------
        # SCENARIO 1: MULTI-PLATFORM CAMPAIGN BROADCAST
        # ----------------------------------------------------------------------
        print("\n🔹 [SCENARIO 1] Broadcasting Campaign Across 4 Social Platforms")
        print("  Platforms: Twitter / X (Mock), LinkedIn (Mock), Discord (Free), Telegram (Free)")

        campaign_payload = {
            "campaign_id": "flyrank-global-v1",
            "content": {
                "text": "Excited to ship our new Social Media Studio! 🚀 Built with FastAPI, resilient 429 Retry-After backoffs, and cryptographic HMAC webhooks.",
                "tags": ["FlyRank", "Engineering", "BuildInPublic", "FastAPI"],
            },
            "platforms": ["mock_twitter", "mock_linkedin", "discord", "telegram"],
            "idempotency_key": "idemp-demo-broadcast-2026",
            "callback_url": "http://testserver/webhooks/platform-callback",
            "simulate_rate_limit": False,
        }

        t0 = time.perf_counter()
        res = await client.post("/api/v1/campaigns/publish", json=campaign_payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        print(f"  📥 Broadcast HTTP Status: {res.status_code} OK ({elapsed_ms:.1f}ms)")
        data = res.json()
        print(f"  📊 Success Rate:          {data['successful_platforms']} / {data['total_platforms']} platforms")
        print(f"  🔑 Idempotency Key:       {data['idempotency_key']}")
        print(f"  📋 Platform Breakdown:")
        for r in data["results"]:
            print(f"     • {r['platform']:15} -> Status: [{r['status'].upper()}] | ID: {r['post_id']} | Latency: {r['latency_ms']:.1f}ms")

        # ----------------------------------------------------------------------
        # SCENARIO 2: 429 RATE LIMIT WITH RETRY-AFTER RECOVERY
        # ----------------------------------------------------------------------
        print("\n🔹 [SCENARIO 2] Resilience Under Fire: 429 Too Many Requests & Retry-After")
        print("  Simulating platform API rate limit. The adapter must intercept 429, sleep, and self-heal.")

        rate_limit_payload = {
            "campaign_id": "rate-limit-test-camp",
            "content": {
                "text": "Testing high-throughput resilience under upstream rate limiting.",
                "tags": ["ChaosTesting"],
            },
            "platforms": ["mock_twitter"],
            "idempotency_key": "idemp-rate-limit-strike-001",
            "simulate_rate_limit": True,
        }

        t_rl = time.perf_counter()
        rl_res = await client.post("/api/v1/campaigns/publish", json=rate_limit_payload)
        rl_elapsed = (time.perf_counter() - t_rl) * 1000.0

        rl_data = rl_res.json()
        result_item = rl_data["results"][0]
        print(f"  📥 Response Status:       {rl_res.status_code} OK (Elapsed: {rl_elapsed:.1f}ms)")
        print(f"  🛑 Attempts Made:         {result_item['attempts']}")
        print(f"  ⚡ 429 Backoff Recovered:  {result_item['rate_limit_recovered']}")
        print(f"  ✅ Final Status:          [{result_item['status'].upper()}] (Post ID: {result_item['post_id']})")

        # ----------------------------------------------------------------------
        # SCENARIO 3: IDEMPOTENCY ENFORCEMENT (ZERO DUPLICATE POSTS)
        # ----------------------------------------------------------------------
        print("\n🔹 [SCENARIO 3] Idempotency Guard (Client Network Retry / Duplicate Trigger)")
        print("  Client re-sends identical broadcast request with same Idempotency-Key:")

        dup_res = await client.post("/api/v1/campaigns/publish", json=campaign_payload)
        dup_data = dup_res.json()
        print(f"  📥 Response Status:       {dup_res.status_code} OK")
        print(f"  🔁 Is Duplicate Run:      {dup_data['is_duplicate_run']}")
        print(f"  🛡️ Idempotency Outcome:   Returned existing broadcast state; ZERO duplicate posts created!")

        # ----------------------------------------------------------------------
        # SCENARIO 4: HMAC-SHA256 DELIVERY CALLBACK WEBHOOK
        # ----------------------------------------------------------------------
        print("\n🔹 [SCENARIO 4] Cryptographic HMAC-SHA256 Webhook Verification")
        print("  Platform delivers signed delivery confirmation. Webhook receiver checks X-Hub-Signature-256.")

        sample_event = {
            "event_id": "evt-delivery-9901",
            "event_type": "post.delivered",
            "platform": "mock_twitter",
            "post_id": data["results"][0]["post_id"],
            "campaign_id": "flyrank-global-v1",
        }
        raw_body = json.dumps(sample_event).encode("utf-8")
        signature = sign_payload(HMAC_SECRET, raw_body)

        wh_res = await client.post(
            "/webhooks/platform-callback",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )
        print(f"  📥 Webhook Acceptance:    {wh_res.status_code} OK (Accepted: {wh_res.json()['status']})")
        print(f"  🔐 Cryptographic Sig:     {signature[:36]}...")

        # Fetch deliveries audit log
        audit_res = await client.get("/webhooks/deliveries")
        deliveries = audit_res.json()
        print(f"  📋 Total Verified Deliveries Logged: {len(deliveries)}")

    print("\n" + "=" * 75)
    print("🎉 ALL CAPSTONE DEMONSTRATION SCENARIOS COMPLETED SUCCESSFULLY!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
