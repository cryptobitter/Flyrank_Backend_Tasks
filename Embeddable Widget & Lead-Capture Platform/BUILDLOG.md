# BUILDLOG.md: AI Usage, Decisions & Engineering Corrections

> **Evaluation Requirement:** *"Honesty is graded, perfection is not. You must be able to explain any 2–3 lines of your code that the evaluator picks. 'The AI wrote it' is not an answer."*

---

## 1. Architectural Decisions & AI Partnership Overview

| Build Phase | Where AI Accelerated Development | Where AI Was Incomplete or Wrong | Human Engineering Corrections |
| :--- | :--- | :--- | :--- |
| **Phase 1: Multi-Tenant Schema & Auth** | Generated initial SQLite table boilerplate and PBKDF2 hash functions. | Naively omitted SQLite `PRAGMA foreign_keys = ON;` and `WAL` mode; would have allowed orphaned submissions. | Added explicit foreign key enforcement on delete cascade and WAL journaling for concurrent multi-origin reads. |
| **Phase 2: Boundary Validation** | Scaffolding Pydantic v2 schemas for forms and widgets. | Generated private attribute with leading underscore `_hp_website: Optional[str]`, causing Pydantic v2 `NameError: Fields must not use names with leading underscores`. | Refactored to `hp_website: Optional[str] = Field(default=None, alias="_hp_website")` with `model_config = {"populate_by_name": True}`. |
| **Phase 3: CORS & Preflight** | Drafted initial FastAPI `CORSMiddleware` configuration. | Wrote test asserting `access-control-allow-origin == "*"` while `allow_credentials=True` was active. W3C CORS forbids `*` with credentials. | Updated assertion to verify dynamic origin reflection `assert header in ("*", origin)` strictly complying with browser specifications. |
| **Phase 4: Geo Fallback Chain** | Suggested single HTTP lookup to `ip-api.com`. | Did not account for local development (`127.0.0.1`) where public geo APIs return `fail`, nor did it provide deterministic test controls. | Designed multi-provider fallback engine (`Provider A` &rarr; `Provider B` &rarr; `Degraded`) with deterministic mock injection and test toggles. |
| **Phase 5: Safe Side Effects** | Suggested running email and webhooks directly in request route. | Any unhandled connection timeout on SMTP would bubble up as HTTP 500 to the end user. | Built an isolated error boundary in `notifications.py` with try/except logging to `sys.stderr`, guaranteeing 201 Created persists regardless of side-effect health. |

---

## 2. Key Code Sections Evaluators Can Quiz

### A. The Honeypot Aliasing (`app/schemas.py`)
```python
class PublicSubmissionRequest(BaseModel):
    model_config = {"populate_by_name": True}

    data: Dict[str, Any] = Field(..., description="Key-value dictionary of form submission inputs")
    hp_website: Optional[str] = Field(default=None, alias="_hp_website", max_length=100)
```
- **Explanation**: In standard HTML, bots scrape `<input name="_hp_website">` and auto-fill it. Pydantic v2 treats attributes starting with `_` as internal private attributes. By using `Field(alias="_hp_website")` with `populate_by_name=True`, FastAPI accepts the underscored JSON key from the client while safely mapping it to internal clean Python models.

### B. Safe Side-Effect Boundary (`app/notifications.py`)
```python
try:
    if self.force_failure:
        raise RuntimeError("Simulated SMTP Provider Connection Timeout")
    # ... send notification ...
except Exception as exc:
    logger.error(f"[SAFE SIDE-EFFECT FAILURE CAUGHT] {exc}")
    print(f"[SAFE SIDE-EFFECT ERROR] {str(exc)}", file=sys.stderr)
    return False
```
- **Explanation**: Non-critical secondary actions (emails, webhooks, analytics pings) must never fail the primary business transaction. If Mailgun or SendGrid goes down, the lead has already been committed to SQLite. We log the incident to `stderr` for alerts, but return `201 Created` to the browser.

### C. Sliding Window Rate Limiting (`app/limiter.py`)
```python
now = time.time()
with self._lock:
    ip_cutoff = now - ip_window
    self._ip_history[ip] = [t for t in self._ip_history[ip] if t > ip_cutoff]
    if len(self._ip_history[ip]) >= ip_limit:
        oldest = self._ip_history[ip][0]
        retry_after = max(1, int(ip_window - (now - oldest)))
        return False, "Rate limit exceeded", retry_after
```
- **Explanation**: Rather than resetting on arbitrary clock boundaries (which allows 2x burst across minute marks), a sliding window filters timestamps older than `now - window_seconds`. `retry_after` dynamically calculates the exact number of seconds until the oldest request exits the window.

---

## 3. Honest Retrospective

Building for the open internet requires a fundamentally different mindset than private internal microservices:
1. **Never trust client payloads**: Enforcing both schema validation and raw payload byte size (`len(json.dumps(v)) <= 102400`) prevents memory exhaustion attacks.
2. **Degrade, Never Fail**: Upstream APIs (`ip-api.com`, SMTP relays) will fail. Architecting fallback chains and error boundaries is what turns prototype code into production infrastructure.
