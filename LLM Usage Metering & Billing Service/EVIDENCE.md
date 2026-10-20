# Capstone Evidence Dossier: LLM Usage Metering & Billing Engine

> **The Contract**: Done = every box below ticked, with one pasted proof per box in `EVIDENCE.md`. Each box is written so a reviewer can verify it in minutes.

---

## 1. Metering

### [x] Requirement 1.1: A billable action creates exactly one usage event, even under retries — deduplicated by idempotency key.
### [x] Requirement 1.2: Proof that double-counting cannot happen: test output or transcript of the same request sent twice.

#### Proof: Live Request Transcript (Request 1 vs Request 2 with same Idempotency-Key)

```http
================================================================================
REQUEST 1 (Initial Call):
POST /api/v1/generate HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Idempotency-Key: idemp_proof_live_run_001

{
  "tenant_id": "tenant_fresh",
  "prompt": "Synthesize a technical post-mortem on database replication lag.",
  "prompt_tokens": 120,
  "cached_prompt_tokens": 30,
  "completion_tokens": 80,
  "reasoning_tokens": 25
}

RESPONSE 1:
HTTP/1.1 200 OK
X-Cache: MISS
X-Idempotency-Key: idemp_proof_live_run_001
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999

{
  "request_id": "req_cbc8210b99c6",
  "tenant_id": "tenant_fresh",
  "content": "Simulated LLM response for tenant 'tenant_fresh': Successfully processed prompt ('Synthesize a technical post-mortem on da...') utilizing 255 total tokens.",
  "usage": {
    "prompt_tokens": 120,
    "cached_prompt_tokens": 30,
    "completion_tokens": 80,
    "reasoning_tokens": 25,
    "total_tokens": 255
  },
  "cost": {
    "total_cost_micros": 182,
    "total_cost_cents": 1,
    "formatted_usd": "$0.000182",
    "token_cost_micros": 82,
    "base_fee_micros": 100,
    "prompt_cost_micros": 18,
    "cached_cost_micros": 1,
    "completion_cost_micros": 48,
    "reasoning_cost_micros": 15
  },
  "quota_status": {
    "api_calls_used": 1,
    "api_calls_limit": 1000,
    "api_calls_remaining": 999,
    "tokens_used": 255,
    "tokens_limit": 100000,
    "tokens_remaining": 99745,
    "percentage_calls_used": 0.1,
    "percentage_tokens_used": 0.26
  },
  "cached_response": false
}

================================================================================
REQUEST 2 (Network Retry - Identical Idempotency-Key):
POST /api/v1/generate HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Idempotency-Key: idemp_proof_live_run_001

{
  "tenant_id": "tenant_fresh",
  "prompt": "Synthesize a technical post-mortem on database replication lag.",
  "prompt_tokens": 120,
  "cached_prompt_tokens": 30,
  "completion_tokens": 80,
  "reasoning_tokens": 25
}

RESPONSE 2 (Served from Idempotency Cache):
HTTP/1.1 200 OK
X-Cache: HIT
X-Idempotency-Key: idemp_proof_live_run_001
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999

{
  "request_id": "req_cbc8210b99c6",
  "tenant_id": "tenant_fresh",
  "content": "Simulated LLM response for tenant 'tenant_fresh': Successfully processed prompt ('Synthesize a technical post-mortem on da...') utilizing 255 total tokens.",
  "usage": {
    "prompt_tokens": 120,
    "cached_prompt_tokens": 30,
    "completion_tokens": 80,
    "reasoning_tokens": 25,
    "total_tokens": 255
  },
  "cost": {
    "total_cost_micros": 182,
    "total_cost_cents": 1,
    "formatted_usd": "$0.000182",
    "token_cost_micros": 82,
    "base_fee_micros": 100,
    "prompt_cost_micros": 18,
    "cached_cost_micros": 1,
    "completion_cost_micros": 48,
    "reasoning_cost_micros": 15
  },
  "quota_status": {
    "api_calls_used": 1,
    "api_calls_limit": 1000,
    "api_calls_remaining": 999,
    "tokens_used": 255,
    "tokens_limit": 100000,
    "tokens_remaining": 99745,
    "percentage_calls_used": 0.1,
    "percentage_tokens_used": 0.26
  },
  "cached_response": true
}
```

#### Database State Verification: Zero Double-Counting

```sql
SELECT id, tenant_id, event_type, api_calls_qty, total_tokens, cost_micros, idempotency_key, timestamp
FROM usage_events
WHERE tenant_id = 'tenant_fresh';
```

| id | tenant_id | event_type | api_calls_qty | total_tokens | cost_micros | idempotency_key | timestamp |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 25 | tenant_fresh | llm_completion | 1 | 255 | 182 | idemp_proof_live_run_001 | 2026-10-20 14:54:44 |

**Verification**: `initial_db_count = 0`, `final_db_count = 1`. Exactly **1** usage event was created across two identical HTTP requests. Double-counting cannot happen.

---

## 2. Quotas

### [x] Requirement 2.1: Usage is checked against the tenant's plan; requests over the limit are rejected.
### [x] Requirement 2.2: Responses carry the correct status codes (429 / 402) and a message explaining why.

#### Proof: Exact Quota Boundary Testing (Call #1,000 vs Call #1,001 on Free Tier)

`tenant_near_limit` is seeded with **999 of 1,000** calls already used:

```http
================================================================================
CALL 1000 (At Quota Boundary - Allowed):
POST /api/v1/generate HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Idempotency-Key: idemp_call_1000

{"tenant_id": "tenant_near_limit", "prompt": "Boundary call 1,000", "prompt_tokens": 15}

RESPONSE:
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0

{
  "request_id": "req_8817a32d",
  "tenant_id": "tenant_near_limit",
  "quota_status": {
    "api_calls_used": 1000,
    "api_calls_limit": 1000,
    "api_calls_remaining": 0,
    "tokens_used": 99743,
    "tokens_limit": 100000,
    "tokens_remaining": 257,
    "percentage_calls_used": 100.0,
    "percentage_tokens_used": 99.74
  },
  "cached_response": false
}

================================================================================
CALL 1001 (Beyond Quota Boundary - Rejected):
POST /api/v1/generate HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Idempotency-Key: idemp_call_1001

{"tenant_id": "tenant_near_limit", "prompt": "Boundary call 1,001 (must fail)", "prompt_tokens": 15}

RESPONSE:
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
Content-Type: application/json

{
  "error": "Quota Exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "API call quota exceeded: 1000/1000 calls used this month. Upgrade to Pro for 50,000 calls/month.",
  "retry_after_seconds": 3600
}
```

---

## 3. Cost Calculation

### [x] Requirement 3.1: Monthly usage rolls up into a cost figure per tenant.
### [x] Requirement 3.2: AI token pricing handles cached input tokens, reasoning tokens, and output pricing correctly.
### [x] Requirement 3.3: Pricing constants are pinned in config, with proof of correct totals.

#### Pinned Pricing Constants in `config.py`

| Token Category | Cost per 1,000,000 Tokens | Scaled Micro-Dollars per Token | Pricing Rule |
| :--- | :---: | :---: | :--- |
| **Fresh Input Tokens** | \$0.150 / 1M | 150,000 micros | Full standard rate |
| **Cached Input Tokens** | \$0.0375 / 1M | 37,500 micros | **75% discount** vs fresh input |
| **Output / Completion** | \$0.600 / 1M | 600,000 micros | Standard generation rate |
| **Reasoning Tokens** | \$0.600 / 1M | 600,000 micros | **Billed identically to output tokens** |
| **API Base Overhead Fee** | \$0.000100 / call | 100 micros | Fixed per-request infrastructure cost |

#### Proof: Multi-Token Category Calculation & Rollup

```http
POST /api/v1/generate HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "tenant_id": "tenant_pro",
  "prompt": "Compute high dimensional tensor decomposition",
  "prompt_tokens": 100000,
  "cached_prompt_tokens": 400000,
  "completion_tokens": 50000,
  "reasoning_tokens": 20000
}

RESPONSE:
HTTP/1.1 200 OK

{
  "usage": {
    "prompt_tokens": 100000,
    "cached_prompt_tokens": 400000,
    "completion_tokens": 50000,
    "reasoning_tokens": 20000,
    "total_tokens": 570000
  },
  "cost": {
    "prompt_cost_micros": 15000,
    "cached_cost_micros": 15000,
    "completion_cost_micros": 30000,
    "reasoning_cost_micros": 12000,
    "token_cost_micros": 72000,
    "base_fee_micros": 100,
    "total_cost_micros": 72100,
    "total_cost_cents": 8,
    "formatted_usd": "$0.072100"
  }
}
```

**Math Verification**:
- Fresh input: $100,000 \times \frac{150,000}{1,000,000} = 15,000\text{ micros}$
- Cached input: $400,000 \times \frac{37,500}{1,000,000} = 15,000\text{ micros}$ *(Notice 400k cached tokens costs the exact same as 100k fresh tokens — exactly 75% cheaper!)*
- Output: $50,000 \times \frac{600,000}{1,000,000} = 30,000\text{ micros}$
- Reasoning: $20,000 \times \frac{600,000}{1,000,000} = 12,000\text{ micros}$
- Base fee: $100\text{ micros}$
- **Total**: $15,000 + 15,000 + 30,000 + 12,000 + 100 = \mathbf{72,100\text{ micros}} = \mathbf{\$0.072100}$.

#### Monthly Rollup (`GET /api/v1/usage?tenant_id=tenant_pro`)

```http
GET /api/v1/usage?tenant_id=tenant_pro HTTP/1.1
Host: localhost:8000

HTTP/1.1 200 OK

{
  "tenant_id": "tenant_pro",
  "tenant_name": "HyperScale AI",
  "plan_id": "pro",
  "plan_name": "Pro Tier",
  "status": "active",
  "used": {
    "api_calls": 12501,
    "tokens": 3370000,
    "prompt_tokens": 1500000,
    "cached_prompt_tokens": 1000000,
    "completion_tokens": 750000,
    "reasoning_tokens": 120000
  },
  "limits": {
    "api_calls": 50000,
    "tokens": 10000000
  },
  "remaining": {
    "api_calls": 37499,
    "tokens": 6630000
  },
  "quota_percentage": {
    "api_calls": 25.0,
    "tokens": 33.7
  },
  "cost": {
    "total_cost_micros": 7572100,
    "total_cost_cents": 758,
    "formatted_usd": "$7.572100"
  }
}
```

---

## 4. Stripe Integration

### [x] Requirement 4.1: Subscription checkout works end-to-end in Stripe test mode.
### [x] Requirement 4.2: Webhooks verify signatures, ignore duplicate events, and update tenant plan/status.

#### Proof: Stripe Checkout Session Creation

```http
POST /api/v1/billing/checkout HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{"tenant_id": "tenant_upgrade_test", "plan_id": "pro"}

RESPONSE:
HTTP/1.1 200 OK

{
  "session_id": "cs_test_4147ec6209aa492280ad95038ee23622",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_4147ec6209aa492280ad95038ee23622",
  "tenant_id": "tenant_upgrade_test",
  "plan_id": "pro",
  "mode": "test"
}
```

#### Proof: Forged Webhook Rejected (HTTP 400)

```http
POST /api/v1/webhooks/stripe HTTP/1.1
Host: localhost:8000
Stripe-Signature: t=1792508084,v1=forged_bad_signature_0000000000
Content-Type: application/json

{"id": "evt_forged_999", "type": "checkout.session.completed", "data": {}}

RESPONSE:
HTTP/1.1 400 Bad Request

{
  "error": "Bad Request",
  "code": "INVALID_WEBHOOK_SIGNATURE",
  "message": "Forged or invalid signature: HMAC-SHA256 verification failed."
}
```

#### Proof: Valid Webhook Processes & Flips Tenant Free -> Pro

```http
POST /api/v1/webhooks/stripe HTTP/1.1
Host: localhost:8000
Stripe-Signature: t=1792508084,v1=984cfb7d346b0d9c490a66d03f0b0ea410cb2e2607e15d8624128509b7c8df0c
Content-Type: application/json

{
  "id": "evt_live_test_1792508084",
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

RESPONSE:
HTTP/1.1 200 OK

{
  "status": "processed",
  "event_id": "evt_live_test_1792508084",
  "event_type": "checkout.session.completed",
  "message": "Successfully processed checkout.session.completed for event evt_live_test_1792508084."
}
```

#### Proof: Webhook Replay Deduplication (Ignored Duplicate)

```http
POST /api/v1/webhooks/stripe HTTP/1.1
Host: localhost:8000
Stripe-Signature: t=1792508084,v1=984cfb7d346b0d9c490a66d03f0b0ea410cb2e2607e15d8624128509b7c8df0c
Content-Type: application/json

{
  "id": "evt_live_test_1792508084",
  "type": "checkout.session.completed",
  "data": { ... }
}

RESPONSE:
HTTP/1.1 200 OK

{
  "status": "ignored_duplicate",
  "event_id": "evt_live_test_1792508084",
  "event_type": "checkout.session.completed",
  "message": "Event 'evt_live_test_1792508084' has already been processed at 2026-10-20 14:54:44."
}
```

#### Post-Webhook Verification (`tenant_upgrade_test` now Pro):

- Plan before webhook: `free` (limits: 1,000 calls / 100,000 tokens)
- Plan after webhook: `pro` (limits: **50,000 calls / 10,000,000 tokens**)

---

## 5. Data Model, Tests & Documentation

### [x] Requirement 5.1: Database includes tenants, plans, subscriptions, and usage events; customer data isolated per tenant.
### [x] Requirement 5.2: README + architecture diagram + setup instructions; required files from Section 10 present.

#### Test Suite Execution Output (`python test_capstone.py`)

```text
Ran 7 tests in 0.201s

OK
[SEED] Cleaned existing records.
[SEED SUCCESS] Successfully seeded 5 tenants, plans, and historical usage.

[BACKGROUND WORKER PASSED] Alerts and reconciliation background job executed successfully.
[VALIDATION PASSED] Boundary validation verified: clean 4xx responses, zero 500 crashes.
[PROBE 1 PASSED] Exactly-once metering verified: same idempotency key resulted in 1 event and cached response.
[PROBE 2 PASSED] Boundary honesty verified: call 1,000 passed, call 1,001 returned 429.
[PROBE 3 PASSED] Stripe test Checkout sync verified: webhook flipped tenant Free -> Pro.
[PROBE 4 PASSED] Webhook security verified: forged signature rejected with 400, replay deduplicated.
[PROBE 5 PASSED] Pinned pricing rules verified: exact micro-dollar pricing for cached and reasoning tokens.
```

#### Submission Pack Verification Checklist

- [x] `README.md` (System overview, architecture diagram, exact run + seed steps, honest limitations).
- [x] `capstone.yaml` (Evaluator manifest with `run:`, `seed:`, `test:`, `base_url:`, probe definitions).
- [x] `EVIDENCE.md` (Every box in Section 6 verified with pasted proof and transcripts).
- [x] `BUILDLOG.md` (Complete AI-usage log: where AI helped, where it was wrong, what was changed).
- [x] `.env.example` (All environment variables with safe placeholder values).
- [x] `architecture-diagram.png` (High-resolution 4-layer system architecture graphic).
