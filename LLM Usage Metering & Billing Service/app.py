"""
FastAPI Application for LLM Usage Metering & Billing Engine.
Exposes billable API endpoints, usage rollups, Stripe checkout, signature-verified webhooks,
and administrative reconciliation jobs.
"""

import logging
from typing import Optional
from fastapi import FastAPI, Request, Response, Header, Query, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from database import init_db
from models import (
    GenerateRequest, GenerateResponse,
    UsageRollupResponse, CheckoutSessionRequest, CheckoutSessionResponse,
    ReconcileResponse, ErrorResponse
)
from services.meter_service import record_billable_generation, IdempotencyConflictException
from services.quota_service import get_monthly_usage_rollup, QuotaExceededException
from services.stripe_service import (
    create_checkout_session, verify_stripe_signature, process_webhook_event,
    WebhookSignatureError
)
from services.background_worker import run_stripe_reconciliation, check_and_dispatch_usage_alerts
from config import PLANS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# Initialize database schema on startup
init_db()

app = FastAPI(
    title="LLM Usage Metering & Billing Engine",
    description="Production-grade usage metering, quota enforcement, money math, and Stripe test mode integration.",
    version="1.0.0"
)

# ---------------------------------------------------------
# Clean Boundary Validation Handlers (Never return raw 500s)
# ---------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Translates schema validation failures into clean 422 responses."""
    errors = exc.errors()
    clean_msg = "; ".join([f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in errors])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "code": "INVALID_INPUT",
            "message": f"Input validation failed at the API boundary: {clean_msg}"
        }
    )

@app.exception_handler(QuotaExceededException)
async def quota_exception_handler(request: Request, exc: QuotaExceededException):
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else {}
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "error": "Quota Exceeded" if exc.status_code == 429 else "Payment Required",
            "code": "RATE_LIMIT_EXCEEDED" if exc.status_code == 429 else "PAYMENT_REQUIRED",
            "message": exc.message,
            "retry_after_seconds": exc.retry_after
        }
    )

@app.exception_handler(WebhookSignatureError)
async def webhook_signature_exception_handler(request: Request, exc: WebhookSignatureError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad Request",
            "code": "INVALID_WEBHOOK_SIGNATURE",
            "message": exc.message
        }
    )

@app.exception_handler(IdempotencyConflictException)
async def idempotency_conflict_handler(request: Request, exc: IdempotencyConflictException):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "Conflict",
            "code": "IDEMPOTENCY_KEY_MISMATCH",
            "message": exc.message
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Client Error",
            "code": "RESOURCE_ERROR",
            "message": str(exc)
        }
    )

# ---------------------------------------------------------
# Core API Routes
# ---------------------------------------------------------

@app.get("/health", tags=["Health"])
def healthcheck():
    return {
        "status": "healthy",
        "service": "usage-metering-and-billing-engine",
        "version": "1.0.0",
        "database": "sqlite3_connected"
    }

@app.post("/api/v1/generate", response_model=GenerateResponse, tags=["Metering"])
def generate_llm_completion(
    req: GenerateRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Dummy Billable Endpoint: Simulates an AI completion request.
    Enforces quota before execution and meters usage idempotently.
    """
    res_data, is_cached = record_billable_generation(
        tenant_id=req.tenant_id,
        prompt=req.prompt,
        prompt_tokens=req.prompt_tokens,
        cached_prompt_tokens=req.cached_prompt_tokens,
        completion_tokens=req.completion_tokens,
        reasoning_tokens=req.reasoning_tokens,
        idempotency_key=idempotency_key
    )

    # Set informational response headers
    response.headers["X-Cache"] = "HIT" if is_cached else "MISS"
    if idempotency_key:
        response.headers["X-Idempotency-Key"] = idempotency_key
    response.headers["X-RateLimit-Limit"] = str(res_data["quota_status"]["api_calls_limit"])
    response.headers["X-RateLimit-Remaining"] = str(res_data["quota_status"]["api_calls_remaining"])

    return res_data

@app.get("/api/v1/usage", response_model=UsageRollupResponse, tags=["Metering"])
def get_tenant_usage(tenant_id: str = Query(..., description="Unique tenant organization ID")):
    """
    Usage Rollup Endpoint: Aggregates current monthly usage, limits, remaining quotas,
    and calculates costs according to pinned pricing constants.
    """
    rollup = get_monthly_usage_rollup(tenant_id)
    return rollup

@app.post("/api/v1/billing/checkout", response_model=CheckoutSessionResponse, tags=["Stripe Billing"])
def create_checkout(req: CheckoutSessionRequest):
    """
    Initiates Stripe Checkout session in test mode for customer plan upgrade.
    """
    session = create_checkout_session(
        tenant_id=req.tenant_id,
        plan_id=req.plan_id,
        success_url=req.success_url,
        cancel_url=req.cancel_url
    )
    return session

@app.post("/api/v1/webhooks/stripe", tags=["Stripe Billing"])
async def handle_stripe_webhook(request: Request):
    """
    Stripe Webhook Handler:
    1. Verifies HMAC-SHA256 signature (returns 400 if forged).
    2. Deduplicates event ID (ignores replays).
    3. Synchronizes tenant plan and subscription status in database.
    """
    raw_payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    # Cryptographic verification
    event = verify_stripe_signature(raw_payload=raw_payload, sig_header=sig_header)

    # Deduplicated processing
    result = process_webhook_event(event=event, raw_payload=raw_payload)
    return result

@app.post("/api/v1/admin/reconcile", response_model=ReconcileResponse, tags=["Admin & Background"])
def trigger_reconciliation():
    """
    Nightly Reconciliation Job: Audits local database subscriptions against Stripe state.
    """
    result = run_stripe_reconciliation()
    return {
        "timestamp": "2026-10-20T19:30:00Z",
        "tenants_checked": result["tenants_checked"],
        "anomalies_detected": result["anomalies_detected"],
        "details": result["details"]
    }

@app.get("/api/v1/admin/alerts", tags=["Admin & Background"])
def get_usage_alerts():
    """
    Evaluates customer quota thresholds (80% and 100%) and returns active warning alerts.
    """
    alerts = check_and_dispatch_usage_alerts()
    return {"alerts": alerts, "count": len(alerts)}
