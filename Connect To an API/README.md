# Connect To an API: Operational AI Judgment Engine

**Track:** FlyRank Engineering Internship  
**Assignment:** Connect To an API — Add one endpoint that asks an AI model for a judgment your code can trust  
**Author:** Aditya Rajput  
**Language/Framework:** Python 3.12+ • FastAPI • Pydantic v2 • HTTPX • Pytest  

---

## 1. What This Project Is (And Why It Matters)

> *"Integrate an LLM does not mean 'build a chatbot.' It means one step in a workflow where a human reads something and makes a call — classify this message, tidy this job title, pull fields out of this receipt — done in code instead."*

This system builds that exact workflow step: an **Automated Customer Support Inquiry Classifier & Triage Judgment Engine**. 

When an inbound customer ticket arrives, it is messy, angry, or ambiguous. Traditionally, a human support agent must read the message, determine the domain category, assess the urgency, decide if it represents an existential security threat or a simple feature request, and manually route it.

Our API replaces this human bottleneck with a single, production-grade endpoint:
```http
POST /api/v1/triage/judge
```

The model invocation is only thirty lines; **the real engineering is making the result trustworthy**:
1. **A strict schema for every answer** — downstream code never guesses data types or handles malformed JSON.
2. **A real timeout** — explicit connect and read timeouts prevent server thread exhaustion.
3. **Retries that know when to stop** — intelligent exponential backoff with full jitter that retries transient hiccups (429/503), but **immediately halts** on permanent errors (400/401/403).
4. **Eight automated test cases** — proving schema enforcement, timeouts, and stop policies under pressure.
5. **Two free model providers** — complete integrations for **Groq Console** and **Google AI Studio (Gemini)** with zero credit card requirements, plus a deterministic offline mock provider.

---

## 2. The 4 Pillars of Trustworthy AI Integration

```
   [Inbound Message]
          │
          ▼
   POST /api/v1/triage/judge
          │
          ├──► [1. Real Timeout Enforcement: connect=3.0s, read=8.0s]
          │
          ├──► [2. Smart Retry Controller]
          │       ├─► 429 / 503 / Timeout? ──► Retry with Exponential Backoff + Jitter (Max 3)
          │       └─► 400 / 401 / 403?     ──► STOP IMMEDIATELY (Zero Wasted Retries)
          │
          ├──► [3. LLM Provider (Groq / Gemini / Mock)]
          │
          └──► [4. Strict Pydantic Schema Validation]
                  ├─► Valid JSON & Types?  ──► 200 OK (TriageJudgment)
                  └─► Corrupt / Invalid?   ──► 502 Bad Gateway (SchemaValidationException)
```

### Pillar 1: A Schema for Every Answer
Downstream microservices (such as billing refund bots or PagerDuty alert managers) cannot parse unstructured markdown like *"Here is your summary..."*. 

Our endpoint enforces strict bidirectional Pydantic contracts:
- **`TriageRequest`**: Validates input message boundaries (3 to 5,000 characters), unique message ID, customer account tier (`standard`, `pro`, `enterprise`), and optional sender email.
- **`TriageJudgment`**: Guarantees typed enums and bounds:
  - `category`: `billing` | `technical_issue` | `security_incident` | `feature_request` | `churn_risk` | `general_inquiry`
  - `urgency_score`: Integer strictly bounded between `1` (cosmetic/info) and `5` (critical security emergency)
  - `sentiment`: `positive` | `neutral` | `frustrated` | `hostile`
  - `recommended_action`: `auto_refund_review` | `escalate_to_security` | `route_to_tier3_eng` | `standard_support_queue` | `churn_retention_contact` | `send_knowledge_base`
  - `requires_human_escalation`: Boolean flag
  - `confidence_score`: Float between `0.0` and `1.0`
  - `reasoning`: Concise explanation (capped at 350 chars)
  - `extracted_entities`: Array of strings (e.g. `["INV-4921", "$99.00"]`)

If the model outputs malformed JSON or violates an enum value, `SchemaValidationException` catches it immediately, logs the raw output, and returns an HTTP 502 without poisoning databases.

### Pillar 2: A Real Timeout
Default HTTP clients often wait indefinitely or for 60+ seconds if an upstream AI server experiences packet loss or gateway congestion. This causes connection pools to deplete and crashes the host server.

We enforce explicit timeouts using `httpx.Timeout`:
```python
self.http_timeout = httpx.Timeout(
    connect=3.0,  # 3s to establish TCP/TLS connection
    read=8.0,     # 8s max to receive model completion
    write=5.0,
    pool=5.0
)
```
If the model takes longer than 8 seconds, `httpx.ReadTimeout` is raised and mapped cleanly into an **HTTP 504 Gateway Timeout** with `is_retryable=True`.

### Pillar 3: Retries That Know When to Stop
Blind retry loops are dangerous. Retrying an invalid API key or a malformed request wastes network bandwidth, burns API quotas, and creates retry storms.

Our client categorizes errors into two strict buckets:

| Category | HTTP Codes & Exceptions | Policy | Rationale |
|---|---|---|---|
| **Transient (Safe to Retry)** | `429 Too Many Requests`<br>`500 Internal Server Error`<br>`502 Bad Gateway`<br>`503 Service Unavailable`<br>`504 Gateway Timeout`<br>`httpx.TimeoutException`<br>`httpx.NetworkError` | **Retry with Jittered Exponential Backoff** (up to 3 attempts) | The remote server is temporarily overloaded or experienced a dropped packet. Giving it a brief rest (`0.5s * 2^attempt + jitter`) allows it to recover. |
| **Permanent (STOP IMMEDIATELY)** | `400 Bad Request`<br>`401 Unauthorized`<br>`403 Forbidden`<br>`404 Not Found`<br>`SchemaValidationException` | **HALT ON ATTEMPT 1** (Zero Retries) | Retrying an invalid API key (401) or a safety-blocked prompt (400) with identical input will NEVER succeed. Stopping immediately protects system resources. |

**Jittered Exponential Backoff Formula:**
$$\text{delay} = \text{base\_delay} \times 2^{(\text{attempt} - 1)} + \text{random}(0.05, 0.25)$$

### Pillar 4: Two Free Model Providers (No Credit Card Ever)
The client supports two zero-cost inference providers, switchable via environment variables:

1. **Groq Console (Ultra-Fast Llama 3 Inference)**
   - **Endpoint:** `https://api.groq.com/openai/v1/chat/completions`
   - **Model:** `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`
   - **Features:** Hardware-accelerated LPUs with sub-500ms latency, native JSON object response format.
   - **Free Key:** [console.groq.com/keys](https://console.groq.com/keys) (No card needed).
2. **Google AI Studio (Gemini 1.5 & 2.0 Flash)**
   - **Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent`
   - **Model:** `gemini-1.5-flash`
   - **Features:** Generous free tier token limits, native `response_mime_type: "application/json"`.
   - **Free Key:** [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) (No card needed).
3. **Deterministic Mock Provider**
   - Built-in zero-dependency testing engine that operates offline for CI/CD and unit testing without network calls or API keys.

---

## 3. The 8 Automated Test Cases (Pass Proof)

Our test suite ([`test_triage.py`](test_triage.py)) covers 8 comprehensive scenarios plus end-to-end integration:

| Test ID | Scenario | Verified Behavior | Status |
|---|---|---|---|
| **Test 1** | Critical Security Incident (`sec-001`) | Parses into `CategoryEnum.SECURITY_INCIDENT`, assigns `urgency_score=5`, sets `recommended_action=escalate_to_security`, triggers `requires_human_escalation=True`. | **PASSED** |
| **Test 2** | Low-Urgency Feature Request (`feat-772`) | Parses into `CategoryEnum.FEATURE_REQUEST`, assigns `urgency_score=1`, detects `sentiment=positive`, routes to `standard_support_queue`. | **PASSED** |
| **Test 3** | Strict Schema Validation Rejection | Corrupt/malformed JSON or out-of-range urgency score (`urgency_score=99`) is rejected instantly with `SchemaValidationException` (HTTP 502). | **PASSED** |
| **Test 4** | Real Timeout Enforcement | Upstream network latency exceeding configured `timeout_seconds` triggers `UpstreamTimeoutException` (HTTP 504), preventing worker hang. | **PASSED** |
| **Test 5** | Transient 429 Rate Limit Recovery | Upstream returns HTTP 429 on Attempt 1; client executes backoff and successfully triages on Attempt 2 (`call_count=2`). | **PASSED** |
| **Test 6** | Permanent 401 Unauthorized Stop Policy | Bad or missing API key immediately halts on Attempt 1 (`call_count=1`). Proves client does NOT burn useless retries. | **PASSED** |
| **Test 7** | Permanent 400 Bad Request Stop Policy | Disallowed prompt or content safety violation halts on Attempt 1 (`call_count=1`). | **PASSED** |
| **Test 8** | Persistent 503 Retry Exhaustion | Upstream outage returning continuous HTTP 503 retries exactly `max_retries` (3) times before cleanly returning 503 with `attempts_made=3`. | **PASSED** |
| **Bonus 9** | End-to-End FastAPI Integration | Submits payload to `/api/v1/triage/judge` through `TestClient`, validating HTTP 200 and OpenAPI schema compliance. | **PASSED** |

### Test Execution Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\2k24c\OneDrive\Desktop\projects\Flyrank_Internship
collected 9 items

Connect To an API/test_triage.py::test_urgent_security_incident_judgment_success PASSED   [ 11%]
Connect To an API/test_triage.py::test_feature_request_judgment_success PASSED             [ 22%]
Connect To an API/test_triage.py::test_strict_schema_validation_failure_on_corrupt_llm_output PASSED [ 33%]
Connect To an API/test_triage.py::test_real_timeout_triggers_gateway_timeout PASSED       [ 44%]
Connect To an API/test_triage.py::test_transient_429_rate_limit_retries_and_succeeds PASSED [ 55%]
Connect To an API/test_triage.py::test_permanent_401_unauthorized_stops_immediately_without_retrying PASSED [ 66%]
Connect To an API/test_triage.py::test_permanent_400_bad_request_stops_immediately_without_retrying PASSED [ 77%]
Connect To an API/test_triage.py::test_retry_exhaustion_on_persistent_503_service_unavailable PASSED [ 88%]
Connect To an API/test_triage.py::test_fastapi_endpoint_e2e_integration PASSED            [100%]

======================== 9 passed in 3.76s =========================
```

---

## 4. Quickstart: Run Locally

### 1. Install Dependencies
```bash
cd "Connect To an API"
pip install -r requirements.txt
```

### 2. Run the Automated Test Suite
```bash
python -m pytest test_triage.py -v
```

### 3. Run the Interactive 5-Case Demo
```bash
python demo_judgment.py
```

### 4. Start the FastAPI Production Server
```bash
uvicorn main:app --reload --port 8000
```
Open **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** in your browser to interact with the live Swagger UI.

### 5. Example API Call via cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/triage/judge" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "TICKET-1049",
    "message_body": "CRITICAL: Our database cluster in us-east-1 is throwing repeated authentication breach alerts. Lock the API keys right now!",
    "customer_tier": "enterprise",
    "sender_email": "security@corp.io"
  }'
```

**Example Response:**
```json
{
  "message_id": "TICKET-1049",
  "category": "security_incident",
  "urgency_score": 5,
  "sentiment": "hostile",
  "recommended_action": "escalate_to_security",
  "requires_human_escalation": true,
  "confidence_score": 0.99,
  "reasoning": "Detected security breach or unauthorized access indicators. Requires immediate supervisor intervention.",
  "extracted_entities": ["unauthorized"],
  "model_used": "mock-triage-v1",
  "processing_time_ms": 12
}
```

---

## 5. File Manifest

| File | Purpose |
|---|---|
| [`main.py`](main.py) | FastAPI application exposing `POST /api/v1/triage/judge` and `GET /health` with structured exception handlers. |
| [`schemas.py`](schemas.py) | Strict Pydantic v2 schemas: `TriageRequest`, `TriageJudgment`, and `ApiErrorResponse`. |
| [`llm_client.py`](llm_client.py) | Trustworthy client with real timeouts, intelligent retry controller, schema validation, and multi-provider connectors (Groq, Gemini, Mock). |
| [`test_triage.py`](test_triage.py) | Comprehensive 8+ test suite proving schema compliance, timeouts, 429 retries, and 401/400 stop policies. |
| [`demo_judgment.py`](demo_judgment.py) | Interactive runner triaging 5 real-world scenarios across security, billing, tech outages, feature requests, and churn risk. |
| [`.env.example`](.env.example) | Configuration template for Groq and Gemini free API credentials and timeout parameters. |
| [`requirements.txt`](requirements.txt) | Python dependencies: FastAPI, Uvicorn, Pydantic, HTTPX, Pytest. |
| [`README.md`](README.md) | Architectural documentation, evaluation checklist, and run instructions. |
