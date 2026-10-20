# LLM Usage Metering & Billing Engine

**Track**: FlyRank Backend Track Capstone  
**Flavor**: Money and Limits  
**Author**: Aditya Rajput (`@cryptobitter`)  
**Repository Directory**: [`LLM Usage Metering & Billing Service/`](./LLM%20Usage%20Metering%20&%20Billing%20Service/)  

---

## Executive Summary

The **LLM Usage Metering & Billing Engine** solves the three foundational questions of every SaaS platform:
1. **How much has this customer used?**
   - Exact token categorization (fresh prompt, cached input, completion, and reasoning tokens).
   - Exactly-once metering via `Idempotency-Key` headers (zero double-counting under network retries).
2. **What does it cost?**
   - Pinned pricing constants with zero floating-point drift.
   - Scaled integer micro-dollars ($1.00 USD = 1,000,000 micro-dollars).
   - Cached input tokens are **75% cheaper** ($0.0375 / 1M tokens vs $0.150 / 1M tokens).
   - Reasoning tokens are **billed as output tokens** ($0.600 / 1M tokens).
3. **Have they reached their plan limits?**
   - Boundary-honest quota enforcement:
     - At 999/1,000 calls: **Allowed**.
     - At exactly 1,000/1,000 calls: **Allowed**.
     - At 1,001 calls: **Rejected with HTTP 429 Too Many Requests**, `Retry-After: 3600`, and explanatory response.
     - Lapsed or unpaid subscriptions return **HTTP 402 Payment Required**.
4. **Stripe Test Mode Integration**:
   - Subscription checkout session generation for customer plan upgrade ($29.00/mo Pro plan).
   - Signature-verified webhooks using cryptographic HMAC-SHA256 (`whsec_...`).
   - Forged signatures return **HTTP 400 Bad Request**.
   - Replay protection via event deduplication table (replays return `HTTP 200 OK` with `status: ignored_duplicate`).
   - Database mirrors Stripe subscription truth (`checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`).
5. **Background Auditing Worker**:
   - Automated usage alerts dispatched at **80% and 100%** of customer quota.
   - Nightly subscription reconciliation audit catching out-of-sync plans or missed webhooks.

---

## Deliverables & Required Submission Files

All artifacts required by Sections 6, 7, 8, 10, and 12 of the Capstone Brief are present:

1. **[Comprehensive README](LLM%20Usage%20Metering%20&%20Billing%20Service/README.md)**:
   - Complete system overview, 4-tier architecture diagram, exact run & seed steps, API reference, and honest limitations.
2. **[Evaluator Manifest (`capstone.yaml`)](LLM%20Usage%20Metering%20&%20Billing%20Service/capstone.yaml)**:
   - Machine-checkable manifest specifying `run:`, `seed:`, `test:`, `base_url:`, and probe endpoints.
3. **[Evidence Dossier (`EVIDENCE.md`)](LLM%20Usage%20Metering%20&%20Billing%20Service/EVIDENCE.md)**:
   - One pasted proof per Requirements checkbox in Section 6 (HTTP request/response transcripts, database row dumps, mathematical breakdown).
4. **[AI Iteration Build Log (`BUILDLOG.md`)](LLM%20Usage%20Metering%20&%20Billing%20Service/BUILDLOG.md)**:
   - Honest documentation of where AI helped, where it made critical mistakes (floats, quota boundary logic, raw webhook body handling), and code explainer guarantee.
5. **[Environment Configuration (`.env.example`)](LLM%20Usage%20Metering%20&%20Billing%20Service/.env.example)**:
   - Safe template containing all required environment variables with non-secret defaults.
6. **[Automated Test Suite (`test_capstone.py`)](LLM%20Usage%20Metering%20&%20Billing%20Service/test_capstone.py)**:
   - 7 automated tests passing in 0.201s proving all 5 Acceptance Probes from Section 12.
7. **[Visual System Architecture Graphic](LLM%20Usage%20Metering%20&%20Billing%20Service/architecture-diagram.png)**:
   - High-resolution visual architecture diagram detailing client boundary, core logic, multi-tenant persistence, and Stripe integration.

---

## Evaluation Probes Verification Matrix

| Probe | Target Requirement | Evaluation Scenario | Expected Status | Actual Result | Status |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **Probe 1** | Idempotent Metering | Send same billable request twice with one `Idempotency-Key` | 200 OK | Exactly 1 event created; 2nd response mirrors 1st with `X-Cache: HIT` | **PASS** |
| **Probe 2** | Boundary Honesty | Call 1,000 (at quota) vs Call 1,001 (exceeded) | 200 then 429 | Call 1,000 allowed; Call 1,001 rejected with 429 & Retry-After | **PASS** |
| **Probe 3** | Stripe Checkout Sync | Complete test Checkout webhook (`checkout.session.completed`) | 200 OK | Tenant flipped Free $\rightarrow$ Pro; `GET /usage` shows 50k calls / 10M tokens | **PASS** |
| **Probe 4** | Webhook Security | Forged signature, then replay valid webhook twice | 400 then 200 | Forged rejected with 400; 1st processed, 2nd ignored duplicate | **PASS** |
| **Probe 5** | Pinned Pricing Math | Cached input tokens (75% off) & reasoning tokens (output rate) | 200 OK | Exact scaled micro-dollar calculations; matches `GET /usage` rollup | **PASS** |
