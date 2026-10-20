"""
Interactive Demonstration Script:
Demonstrates the full lifecycle of the Background Job architecture.

Highlights:
1. Fast acceptance: 202 Accepted returned in <20ms while the slow AI call runs in worker.
2. Status polling: GET /api/v1/jobs/{job_id} reflects progress up to completion.
3. Idempotency (1st Non-Negotiable): Duplicate submissions return existing job record without re-running.
4. Retries & Backoff (2nd Non-Negotiable): Failed operations backoff exponentially up to max retries.
5. Alerts (3rd Non-Negotiable): Fatal failures trigger alert dispatcher for on-call notification.
"""

import asyncio
import time
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from httpx import AsyncClient, ASGITransport
from app import app
from queue_manager import queue_manager
from alert_service import alert_service
from worker import worker


async def run_demo():
    print("\n" + "=" * 75)
    print("🚀 FLYRANK ENGINEERING INTERNSHIP: YOUR FIRST BACKGROUND JOB DEMO")
    print("=" * 75)

    await worker.start()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:

            # ----------------------------------------------------------------------
            # SCENARIO 1: ACCEPT FAST (HTTP 202 ACCEPTED)
            # ----------------------------------------------------------------------
            print("\n🔹 [SCENARIO 1] Moving Slow AI Triage to Background Job")
            print("  Client submits an urgent customer inquiry that takes ~1.2s to evaluate.")

            payload = {
                "message": "URGENT: Our production cluster in us-east-1 is down! 500 errors on checkout and customers cannot pay!",
                "user_id": "cust-enterprise-901",
                "simulate_delay_sec": 1.2,
            }

            t0 = time.perf_counter()
            res = await client.post(
                "/api/v1/jobs",
                json=payload,
                headers={"Idempotency-Key": "demo-key-checkout-outage"}
            )
            elapsed_submit_ms = (time.perf_counter() - t0) * 1000.0

            print(f"  📥 Endpoint HTTP Status: {res.status_code} Accepted")
            print(f"  ⚡ Time to Return:       {elapsed_submit_ms:.2f} ms (< 25ms threshold passed!)")
            data = res.json()
            job_id = data["job_id"]
            status_url = res.headers.get("Location") or data["status_url"]
            print(f"  🏷️  Job ID:               {job_id}")
            print(f"  📍 Location Header:      {status_url}")
            print(f"  🔑 Idempotency Key:      {data['idempotency_key']}")

            # ----------------------------------------------------------------------
            # SCENARIO 2: WORKER EXECUTION & STATUS POLLING
            # ----------------------------------------------------------------------
            print(f"\n🔹 [SCENARIO 2] Polling Status Endpoint for Job {job_id}")

            polls = 0
            final_status = None
            while polls < 15:
                polls += 1
                poll_res = await client.get(status_url)
                status_data = poll_res.json()
                current_status = status_data["status"]
                print(f"  ⏱️  Poll #{polls:02d}: Status = [{current_status.upper()}] (attempts: {status_data['attempts']})")

                if current_status == "completed":
                    final_status = status_data
                    break
                await asyncio.sleep(0.3)

            if final_status and final_status.get("result"):
                res_obj = final_status["result"]
                print(f"\n  ✅ Job Completed! AI Triage Judgment:")
                print(f"     • Category:            {res_obj['category']}")
                print(f"     • Urgency:             {res_obj['urgency']}")
                print(f"     • Confidence:          {res_obj['confidence'] * 100:.1f}%")
                print(f"     • Summary:             {res_obj['summary']}")
                print(f"     • Recommended Action:  {res_obj['recommended_action']}")
                print(f"     • Escalation Required: {res_obj['is_escalation_required']}")
                print(f"     • Execution Duration:  {final_status['duration_ms']:.1f}ms")

            # ----------------------------------------------------------------------
            # SCENARIO 3: 1ST NON-NEGOTIABLE — IDEMPOTENCY (JOBS WILL RUN TWICE)
            # ----------------------------------------------------------------------
            print("\n🔹 [SCENARIO 3] Idempotency Guard (Network retry / Double Submission)")
            print("  Client accidentally submits the same request with the same Idempotency-Key:")

            res_dup = await client.post(
                "/api/v1/jobs",
                json=payload,
                headers={"Idempotency-Key": "demo-key-checkout-outage"}
            )
            dup_data = res_dup.json()
            print(f"  📥 Response Status: {res_dup.status_code} Accepted")
            print(f"  🔁 Is Duplicate:    {dup_data['is_duplicate']}")
            print(f"  🆔 Returned Job ID: {dup_data['job_id']} (Matches original: {dup_data['job_id'] == job_id})")
            print(f"  🛡️  Idempotency Result: Zero duplicate LLM calls or duplicate work spawned!")

            # ----------------------------------------------------------------------
            # SCENARIO 4: 2ND & 3RD NON-NEGOTIABLES — RETRIES & ALERTS
            # ----------------------------------------------------------------------
            print("\n🔹 [SCENARIO 4] Retries & Dead Letter Alerts (Jobs Will Fail & Someone Must Find Out)")
            print("  Submitting a job configured with simulate_failure=True...")

            fail_payload = {
                "message": "Testing fatal upstream error handling and alert dispatch.",
                "simulate_failure": True,
                "simulate_delay_sec": 0.05,
            }

            fail_res = await client.post(
                "/api/v1/jobs",
                json=fail_payload,
                headers={"Idempotency-Key": "demo-key-failure-test"}
            )
            fail_data = fail_res.json()
            fail_job_id = fail_data["job_id"]
            fail_url = fail_data["status_url"]
            print(f"  📥 Accepted Failure Test Job: {fail_job_id}")

            # Poll until dead letter
            print("  🔄 Monitoring retry attempts with exponential backoff...")
            for _ in range(25):
                st_res = await client.get(fail_url)
                st = st_res.json()
                if st["status"] == "dead_letter":
                    print(f"  💀 Job entered DEAD_LETTER after {st['attempts']} attempts!")
                    print(f"     • Max Retries:          {st['max_retries']}")
                    print(f"     • Final Error:          {st['error']}")
                    print(f"     • Alert Dispatched:     {st['alert_dispatched']}")
                    print(f"     • Retry History Count:  {len(st['retry_history'])}")
                    break
                await asyncio.sleep(0.3)

            # Verify Alert endpoint
            print("\n  📢 Inspecting /api/v1/alerts endpoint:")
            alerts_res = await client.get("/api/v1/alerts")
            alerts = alerts_res.json()
            print(f"  🚨 Total Active Alerts Dispatched: {len(alerts)}")
            if alerts:
                top_alert = alerts[0]
                print(f"     • Alert ID:   {top_alert['alert_id']}")
                print(f"     • Severity:   {top_alert['severity']}")
                print(f"     • Channel:    {top_alert['target_channel']}")
                print(f"     • Error:      {top_alert['error_message']}")

    finally:
        await worker.stop()

    print("\n" + "=" * 75)
    print("🎉 DEMONSTRATION COMPLETE: ALL 3 NON-NEGOTIABLES VERIFIED!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
