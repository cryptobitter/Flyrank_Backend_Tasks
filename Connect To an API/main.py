"""
FastAPI Application: Automated Message Triage & Operational Judgment Engine.

Exposes a single trustworthy endpoint that queries an LLM for structured judgment,
backed by real timeouts, intelligent retries, and strict schema validation.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from schemas import (
    TriageRequest,
    TriageJudgment,
    ApiErrorResponse,
)
from llm_client import (
    TrustworthyLLMClient,
    LLMClientException,
    PermanentClientException,
    TransientUpstreamException,
    UpstreamTimeoutException,
    SchemaValidationException,
)

# Global client initialized on module load
llm_client: TrustworthyLLMClient = TrustworthyLLMClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI."""
    global llm_client
    if llm_client is None:
        llm_client = TrustworthyLLMClient()
    yield


app = FastAPI(
    title="AI Support Triage & Operational Judgment API",
    description=(
        "Production-grade API endpoint that queries an AI model for an operational decision. "
        "Engineered with strict Pydantic schemas, explicit HTTP timeouts, and retries that know when to stop."
    ),
    version="1.0.0",
    lifespan=lifespan
)


# ------------------------------------------------------------------------------
# Exception Handlers
# ------------------------------------------------------------------------------

@app.exception_handler(LLMClientException)
async def handle_llm_client_exception(request: Request, exc: LLMClientException):
    """Maps custom LLM exceptions into standardized ApiErrorResponse schemas."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiErrorResponse(
            error_code=exc.__class__.__name__,
            message=exc.message,
            is_retryable=exc.is_retryable,
            attempts_made=exc.attempts,
            details={"path": str(request.url)}
        ).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    """Catches incoming client request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiErrorResponse(
            error_code="ClientValidationError",
            message="Incoming request body failed validation.",
            is_retryable=False,
            attempts_made=1,
            details={"errors": exc.errors()}
        ).model_dump()
    )


# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------

@app.get("/health", tags=["Monitoring"], summary="Service Health & Provider Info")
async def health_check():
    """Returns current API health, active provider configuration, and timeout settings."""
    return {
        "status": "healthy",
        "service": "AI Message Triage Engine",
        "provider": llm_client.provider if llm_client else "uninitialized",
        "timeout_seconds": llm_client.timeout_seconds if llm_client else 8.0,
        "max_retries": llm_client.max_retries if llm_client else 3
    }


@app.post(
    "/api/v1/triage/judge",
    response_model=TriageJudgment,
    status_code=status.HTTP_200_OK,
    tags=["Judgment Engine"],
    summary="Ask AI Model for an Operational Triage Judgment",
    responses={
        200: {"description": "Strictly validated operational judgment"},
        400: {"model": ApiErrorResponse, "description": "Permanent client error or prompt violation"},
        502: {"model": ApiErrorResponse, "description": "Upstream model schema violation or unparseable output"},
        503: {"model": ApiErrorResponse, "description": "Upstream model service unavailable after retries"},
        504: {"model": ApiErrorResponse, "description": "Upstream timeout exceeded"},
    }
)
async def judge_support_message(payload: TriageRequest) -> TriageJudgment:
    """
    Submits a raw customer support message to the AI judgment engine.

    Guarantees:
    - Guaranteed schema validation conforming to TriageJudgment.
    - Explicit network timeouts preventing hanging connections.
    - Backoff retries on transient errors (429/503).
    - Immediate halt on permanent client errors (400/401/403).
    """
    try:
        judgment = await llm_client.judge_message(payload)
        return judgment
    except LLMClientException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected server failure: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
