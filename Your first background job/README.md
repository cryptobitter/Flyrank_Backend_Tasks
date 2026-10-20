# Your First Background Job: Asynchronous Worker Architecture

**Track:** FlyRank Engineering Internship  
**Assignment:** Your First Background Job — Move a slow operation out of the request into a background job  
**Author:** Aditya Rajput  
**Language/Framework:** Python 3.12+ • FastAPI • Pydantic v2 • Asyncio • HTTPX • Pytest  

---

## 1. Executive Summary & Purpose

> *"The professional pattern for everything slow: accept fast, work in the background, report status. This is where your async foundation and the queue/worker model become real — including the non-negotiables: jobs will run twice (idempotency), they will fail (retries), and someone must find out (alerts)."*

In assignment **A6 ("Connect To an API")**, we built an automated customer triage AI endpoint. While it delivered trustworthy structured judgments, calling an LLM synchronously blocks the HTTP server connection for **1.5 to 5+ seconds**. In production:
- Web threads exhaust under moderate traffic.
- Mobile clients drop connections on unstable networks.
- Upstream rate limits or timeouts cause 504 Gateway Timeouts.

### The Solution: Decoupling Request from Execution
This project transitions the slow AI operation into a **production-grade asynchronous background job system**:
1. **Accept Fast**: `POST /api/v1/jobs` validates input and responds instantly with **HTTP 202 Accepted** (latency: **< 5ms**).
2. **Work in Background**: Autonomous worker instances listen to the queue and execute the slow AI triage operation independently.
3. **Report Status**: `GET /api/v1/jobs/{job_id}` provides real-time state tracking (`queued` → `processing` → `completed` / `dead_letter`).

---

## 2. Architecture & Request Lifecycle

```
[ Client / Frontend ]             [ FastAPI Web Layer ]            [ Queue & Workers ]           [ AI Model & Alerting ]
        │                                  │                                │                              │
        │── 1. POST /api/v1/jobs ─────────►│                                │                              │
        │   (Inquiry + Idempotency-Key)    │                                │                              │
        │                                  ├── 2. Verify Idempotency        │                              │
        │                                  ├── 3. Enqueue Job ─────────────►│                              │
        │◄── 4. 202 Accepted (in 3ms!) ────│                                │                              │
        │   Location: /api/v1/jobs/:id     │                                │                              │
        │                                  │                                ├── 5. Pull Next Job           │
        │                                  │                                │   (Status: PROCESSING)       │
        │                                  │                                │                              │
        │── 6. GET /api/v1/jobs/:id ──────►│                                ├── 6. Execute Slow AI Task ──►│ (1.2s Latency)
        │◄── Status: PROCESSING ───────────│                                │◄── Triage Judgment Returned ─│
        │                                  │                                │                              │
        │                                  │                                ├── 7. Mark COMPLETED          │
        │── 8. GET /api/v1/jobs/:id ──────►│                                │                              │
        │◄── Status: COMPLETED ────────────│                                │                              │
        │    (Full Structured AI Result)   │                                │                              │
```

---

## 3. The Three Non-Negotiables

Distributed queues and background workers introduce real-world failure modes. Professional systems must enforce three mandatory engineering invariants:

### ⚡ Non-Negotiable #1: Idempotency (Jobs Will Run Twice)
Network disconnects, timeouts, and queue redelivery policies guarantee that **jobs will be submitted or pulled more than once**. If an operation has side effects (charging a card, calling an LLM, sending customer emails), running twice creates severe defects.

**How We Solved It:**
1. **Client-Provided or Auto-Hashed Keys**: Clients pass `Idempotency-Key: <unique-token>` in the HTTP header, or the system auto-hashes the request payload `sha256(user_id + message + config)`.
2. **Atomic Idempotency Store**: If an identical key is already registered, the endpoint immediately returns the existing `job_id` and status with `is_duplicate: True`—**zero duplicate LLM calls are made**.
3. **Worker At-Least-Once Delivery Guard**: When a worker pulls a job, `mark_processing()` performs an atomic check. If the job is already `completed` or `dead_letter`, the worker safely no-ops without altering state.

### 🔄 Non-Negotiable #2: Retries & Exponential Backoff (Jobs Will Fail)
Upstream APIs (Groq, OpenAI, Gemini) fail regularly due to rate limits (429), server hiccups (503), or transient network timeouts. Retrying immediately in a tight loop causes "thundering herd" failures that exacerbate downtime.

**How We Solved It:**
- **Exponential Backoff with Full Jitter**:
  $$\text{backoff} = \min(\text{max\_backoff}, \text{base} \times 2^{\text{attempt}-1}) + \text{uniform}(0, 0.2 \times \text{delay})$$
  - Attempt #1: ~0.5s – 0.6s
  - Attempt #2: ~1.0s – 1.2s
  - Attempt #3: ~2.0s – 2.4s
- **Max Retry Threshold**: Jobs are permitted up to 3 retry attempts before transitioning to `dead_letter`.
- **Detailed History**: Every failed attempt records timestamp, exact error message, and backoff delay for debugging.

### 🚨 Non-Negotiable #3: Alerts (Someone Must Find Out)
Silent failures in background queues are fatal. If a job exhausts all retries and silently disappears, customers are left hanging indefinitely.

**How We Solved It:**
- **Dead-Letter Queue (DLQ)**: Once `attempts >= max_retries`, the job status transitions to `dead_letter`.
- **Automated Alert Dispatcher** (`alert_service.py`):
  - Automatically emits a structured alert (`CRITICAL` severity) to log streams and configurable webhooks (`slack-ops-alerts`).
  - Stores alert metadata (job ID, payload, error stack, retry history) in an auditable registry.
  - Exposes `GET /api/v1/alerts` for monitoring dashboards and alerting integrations (PagerDuty/Slack).

---

## 4. API Endpoints

### 1. Submit Job (Fast Acceptance)
```http
POST /api/v1/jobs
Idempotency-Key: cust-pay-48201
Content-Type: application/json

{
  "message": "Urgent: Payment failed twice on invoice #9041 and our users are locked out.",
  "user_id": "cust-819",
  "simulate_delay_sec": 1.2
}
```
**Response: `HTTP 202 Accepted` (Returned in ~2.8 ms)**
```http
HTTP/1.1 202 Accepted
Location: /api/v1/jobs/job-7a5c7d312f39
Content-Type: application/json

{
  "job_id": "job-7a5c7d312f39",
  "status": "queued",
  "status_url": "/api/v1/jobs/job-7a5c7d312f39",
  "idempotency_key": "cust-pay-48201",
  "is_duplicate": false,
  "message": "Job accepted and enqueued for background worker",
  "accepted_at": "2026-10-20T06:44:52.153401+00:00"
}
```

---

### 2. Poll Job Status
```http
GET /api/v1/jobs/job-7a5c7d312f39
```
**Response: `HTTP 200 OK` (Completed)**
```json
{
  "job_id": "job-7a5c7d312f39",
  "status": "completed",
  "idempotency_key": "cust-pay-48201",
  "attempts": 1,
  "max_retries": 3,
  "created_at": "2026-10-20T06:44:52.153401+00:00",
  "started_at": "2026-10-20T06:44:52.156821+00:00",
  "completed_at": "2026-10-20T06:44:53.363198+00:00",
  "duration_ms": 1206.3,
  "result": {
    "category": "billing_refund",
    "urgency": "high",
    "confidence": 0.94,
    "summary": "Customer inquiry regarding payment dispute or refund.",
    "recommended_action": "Cross-reference Stripe transaction ledger and dispatch to Tier-2 Finance.",
    "is_escalation_required": false,
    "tokens_used": 120,
    "execution_time_ms": 1204.8
  },
  "error": null,
  "alert_dispatched": false,
  "retry_history": []
}
```

---

### 3. List Dispatched Alerts (DLQ Inspection)
```http
GET /api/v1/alerts
```
**Response: `HTTP 200 OK`**
```json
[
  {
    "alert_id": "alt-d4161a83",
    "job_id": "job-4dc700c77afb",
    "event": "JOB_DEAD_LETTER_EXHAUSTED",
    "severity": "CRITICAL",
    "attempts_made": 3,
    "error_message": "Simulated upstream model 503 Service Unavailable (attempt #3)",
    "dispatched_at": "2026-10-20T06:44:55.202319+00:00",
    "target_channel": "slack-ops-alerts"
  }
]
```

---

## 5. Verification & Testing

### Running the Live Interactive Demo
```bash
python "Your first background job/demo_background_job.py"
```

**Live Demonstration Output:**
```
===========================================================================
🚀 FLYRANK ENGINEERING INTERNSHIP: YOUR FIRST BACKGROUND JOB DEMO
===========================================================================

🔹 [SCENARIO 1] Moving Slow AI Triage to Background Job
  Client submits an urgent customer inquiry that takes ~1.2s to evaluate.
  📥 Endpoint HTTP Status: 202 Accepted
  ⚡ Time to Return:       2.82 ms (< 25ms threshold passed!)
  🏷️  Job ID:               job-7a5c7d312f39
  📍 Location Header:      /api/v1/jobs/job-7a5c7d312f39
  🔑 Idempotency Key:      demo-key-checkout-outage

🔹 [SCENARIO 2] Polling Status Endpoint for Job job-7a5c7d312f39
  ⏱️  Poll #01: Status = [QUEUED] (attempts: 0)
  ⏱️  Poll #02: Status = [PROCESSING] (attempts: 1)
  ⏱️  Poll #03: Status = [PROCESSING] (attempts: 1)
  ⏱️  Poll #04: Status = [PROCESSING] (attempts: 1)
  ⏱️  Poll #05: Status = [COMPLETED] (attempts: 1)

  ✅ Job Completed! AI Triage Judgment:
     • Category:            support_technical
     • Urgency:             high
     • Confidence:          94.0%
     • Summary:             Technical outage or software error reported.
     • Recommended Action:  Check Datadog APM logs and file bug report in JIRA.
     • Escalation Required: True
     • Execution Duration:  1206.3ms

🔹 [SCENARIO 3] Idempotency Guard (Network retry / Double Submission)
  Client accidentally submits the same request with the same Idempotency-Key:
  📥 Response Status: 202 Accepted
  🔁 Is Duplicate:    True
  🆔 Returned Job ID: job-7a5c7d312f39 (Matches original: True)
  🛡️  Idempotency Result: Zero duplicate LLM calls or duplicate work spawned!

🔹 [SCENARIO 4] Retries & Dead Letter Alerts (Jobs Will Fail & Someone Must Find Out)
  Submitting a job configured with simulate_failure=True...
  📥 Accepted Failure Test Job: job-4dc700c77afb
  🔄 Monitoring retry attempts with exponential backoff...
  💀 Job entered DEAD_LETTER after 3 attempts!
     • Max Retries:          3
     • Final Error:          Simulated upstream model 503 Service Unavailable (attempt #3)
     • Alert Dispatched:     True
     • Retry History Count:  3

  📢 Inspecting /api/v1/alerts endpoint:
  🚨 Total Active Alerts Dispatched: 1
     • Alert ID:   alt-d4161a83
     • Severity:   CRITICAL
     • Channel:    slack-ops-alerts
     • Error:      Simulated upstream model 503 Service Unavailable (attempt #3)

===========================================================================
🎉 DEMONSTRATION COMPLETE: ALL 3 NON-NEGOTIABLES VERIFIED!
===========================================================================
```

---

### Running the Pytest Suite
```bash
python -m pytest "Your first background job/test_background_jobs.py" -v
```

**Test Results:**
```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\2k24c\OneDrive\Desktop\projects\Flyrank_Internship
collected 8 items

Your first background job/test_background_jobs.py::test_accept_fast_returns_202_instantly PASSED         [ 12%]
Your first background job/test_background_jobs.py::test_job_status_lifecycle_to_completed PASSED         [ 25%]
Your first background job/test_background_jobs.py::test_idempotency_header_prevents_duplicate_execution PASSED [ 37%]
Your first background job/test_background_jobs.py::test_worker_at_least_once_delivery_protection PASSED [ 50%]
Your first background job/test_background_jobs.py::test_retries_with_exponential_backoff PASSED         [ 62%]
Your first background job/test_background_jobs.py::test_dead_letter_and_alert_dispatch_on_fatal_failure PASSED [ 75%]
Your first background job/test_background_jobs.py::test_job_not_found_returns_404 PASSED                [ 87%]
Your first background job/test_background_jobs.py::test_health_check_endpoint PASSED                    [100%]

============================== 8 passed in 1.42s ==============================
```
