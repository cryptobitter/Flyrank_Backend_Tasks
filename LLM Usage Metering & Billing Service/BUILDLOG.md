# Engineering Build Log: LLM Usage Metering & Billing Engine

> **The Rule (Section 3 & 10)**: *Use AI tools freely, but keep `BUILDLOG.md` honest: where AI helped, where it was wrong, what you changed. You must be able to explain any 2–3 lines of your code that the evaluator picks. Honesty is graded, perfection is not.*

---

## 1. Project Inception & Design Decisions

### The Core Problem
Billing and metering systems look deceptively simple until they face network retries, race conditions, edge quotas, and fractional-cent token math. Double-charging a customer or giving away free unlimited access is unacceptable.

### Where AI Helped
- AI provided the initial schema draft for multi-tenant tables (`tenants`, `plans`, `subscriptions`, `usage_events`).
- AI suggested the standard Pydantic models for request validation and response serialization.

### Where AI Was Wrong & What I Changed
- **Mistake 1: Storing money as floating-point decimals (`DECIMAL(10, 4)` / `float`)**:
  - *What AI did*: Suggested calculating `prompt_tokens * 0.00015` in Python floats.
  - *Why it's fatal*: Floating-point numbers (`0.1 + 0.2 != 0.3`) accumulate rounding drift over millions of events. A customer will see ledger discrepancies between per-request costs and monthly rollups.
  - *What I changed*: Replaced all money calculations with **scaled integer micro-dollars** ($1.00 USD = 1,000,000 micro-dollars). All arithmetic uses integer operations with half-up rounding `(scaled + 500,000) // 1,000,000`. Cents are converted as integer ceil `(micros + 9,999) // 10,000`.

---

## 2. Iteration Log: The Hard Parts

### Iteration 1: Idempotency & Exactly-Once Metering
- **The Challenge**: Client network timeouts cause automatic HTTP retries. The retry must return the original result without inserting a second billable event.
- **AI Recommendation**: Check if an event exists with `idempotency_key` in `usage_events`.
- **Flaw Detected**: If the previous request is still in-flight or if the caller modifies the payload while reusing the key, querying just `usage_events` is insufficient. Furthermore, the response body and status code need to be returned byte-for-byte to the client.
- **My Solution**:
  1. Created a dedicated `idempotency_records` table storing `(key, tenant_id, request_hash, response_status, response_body)`.
  2. If the key exists:
     - Compare SHA-256 hash of incoming payload.
     - If hash matches: deserialize cached JSON and return with `X-Cache: HIT` and `cached_response: true`. Zero rows inserted into `usage_events`.
     - If hash differs: immediately return `HTTP 409 Conflict` (`IDEMPOTENCY_KEY_MISMATCH`).

### Iteration 2: Boundary Honesty (The 999 vs 1,000 vs 1,001 Problem)
- **The Challenge**: At 999 calls on a 1,000-call plan, what happens? At exactly 1,000? At 1,001?
- **AI Mistake**:
  - The AI prompt generated: `if current_usage >= quota: raise QuotaExceeded()`.
  - When a tenant reached 1,000 calls, `current_usage` was 999. Call 1,000 made it 1,000. But on the *subsequent* call, `current_usage >= quota` triggered prematurely if checked after execution, or failed to allow call #1,000 if checked before execution with `used + requested >= limit`.
- **My Correction**:
  - Enforced pre-action boundary evaluation:
    `if current_usage + requested_calls > limit:`
  - At 999 used + 1 requested = 1000 $\le$ 1000 $\rightarrow$ **ALLOWED**.
  - At 1000 used + 1 requested = 1001 $>$ 1000 $\rightarrow$ **REJECTED with HTTP 429 Too Many Requests**.
  - Verified with automated probe in `test_capstone.py` (`test_probe_2_boundary_honesty_quota_exceeded`).

### Iteration 3: Token Pricing Quirks (Cached Input & Reasoning Tokens)
- **The Challenge**:
  - Cached input tokens are 75% cheaper ($0.0375 / 1M vs $0.150 / 1M).
  - Reasoning ("thinking") tokens count as output tokens ($0.600 / 1M), not input tokens or a free category.
  - Categories cannot simply be summed as `total_tokens * flat_rate`.
- **AI Mistake**:
  - The AI initially lumped `prompt_tokens + cached_tokens` and applied a flat discount multiplier `* 0.8`.
- **My Correction**:
  - Separated the formulas in `pricing.py`:
    ```python
    prompt_micros_scaled = prompt_tokens * PRICING.INPUT_TOKEN_RATE_PER_MILLION_MICROS
    cached_micros_scaled = cached_prompt_tokens * PRICING.CACHED_INPUT_TOKEN_RATE_PER_MILLION_MICROS
    completion_micros_scaled = completion_tokens * PRICING.OUTPUT_TOKEN_RATE_PER_MILLION_MICROS
    reasoning_micros_scaled = reasoning_tokens * PRICING.REASONING_TOKEN_RATE_PER_MILLION_MICROS
    ```
  - Proved that 400,000 cached tokens ($15,000 micros) cost identical to 100,000 fresh tokens ($15,000 micros) — exactly 75% savings.

### Iteration 4: Stripe Webhook Signature Verification & Raw-Body Pitfall
- **The Challenge**: Stripe webhooks sign the exact raw byte payload using HMAC-SHA256 with secret `whsec_...`.
- **AI Mistake**:
  - In `app.py`, the AI wrote: `async def handle_stripe_webhook(request: Request, payload: dict = Body(...))`.
  - Then inside the function: `verify_signature(json.dumps(payload).encode(), ...)`.
  - *Why it breaks*: `json.dumps(payload)` re-serializes the dictionary with Python's whitespace and key ordering, altering the cryptographic hash and causing signature verification to fail on 100% of real Stripe webhooks!
- **My Correction**:
  - Replaced with direct raw byte consumption:
    ```python
    raw_payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")
    event = verify_stripe_signature(raw_payload=raw_payload, sig_header=sig_header)
    ```
  - Added timestamp freshness tolerance ($\le 300\text{s}$) and constant-time HMAC comparison (`hmac.compare_digest`).

### Iteration 5: Webhook Replay Deduplication
- **The Challenge**: Stripe retries webhooks up to 72 hours if delivery is delayed or network drops.
- **My Solution**:
  - Dedicated `webhook_events` table tracking `(event_id, event_type, processed_at, payload_hash)`.
  - If `event_id` is replayed: returns `HTTP 200 OK` with `{"status": "ignored_duplicate"}`. Prevents resetting tenant subscriptions or triggering duplicate subscription upgrade hooks.

---

## 3. Code Explainer Guarantee (Any 2–3 Lines)

Below are the 3 lines at the core of the service that I am prepared to explain in any engineering review:

```python
# services/meter_service.py L35-43
if cached_record["request_hash"] != req_hash:
    raise IdempotencyConflictException(f"Idempotency-Key '{idempotency_key}' was previously used with a different request payload.")
saved_response = json.loads(cached_record["response_body"])
saved_response["cached_response"] = True
return saved_response, True
```

**Explanation**:  
When a client sends an `Idempotency-Key`, we don't just look up the key—we compare the SHA-256 hash of the incoming request body against the cached `request_hash`. If an engineer or client buggy retry sends a different prompt under the same key, it raises an explicit `409 Conflict`. If it matches, we immediately deserialize the exact previous JSON and return it with `cached_response = True` and header `X-Cache: HIT`, ensuring zero database mutations and zero double-counting.

---

## 4. Verification & Gate Summary

- [x] **Design Gate**: Multi-tenant database schema, isolated tenants, pinned pricing config committed.
- [x] **Metering Gate**: Same request sent twice creates exactly 1 event; boundary 1,000/1,000 passes, 1,001 returns 429.
- [x] **Stripe Gate**: Test checkout session creates valid URL; signed webhook flips tenant Free $\rightarrow$ Pro; forged webhook returns 400; replay ignored.
- [x] **Cost Gate**: Scaled integer micro-dollar math verified with cached tokens (75% off) and reasoning tokens (output rate).
- [x] **Background Gate**: Asynchronous audit worker scans tenant quotas (80% and 100% alerts) and executes subscription reconciliation.
