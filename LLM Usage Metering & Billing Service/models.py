"""
Pydantic Schemas for Requests, Responses, and Boundary Validation.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    tenant_id: str = Field(..., description="Unique tenant organization ID")
    prompt: str = Field(..., description="User prompt or instruction")
    prompt_tokens: Optional[int] = Field(None, ge=0, description="Optional simulated fresh input token count")
    cached_prompt_tokens: Optional[int] = Field(None, ge=0, description="Optional simulated cached input token count")
    completion_tokens: Optional[int] = Field(None, ge=0, description="Optional simulated output token count")
    reasoning_tokens: Optional[int] = Field(None, ge=0, description="Optional simulated reasoning/thinking token count")

class TokenBreakdown(BaseModel):
    prompt_tokens: int
    cached_prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    total_tokens: int

class CostBreakdown(BaseModel):
    total_cost_micros: int
    total_cost_cents: int
    formatted_usd: str
    token_cost_micros: int
    base_fee_micros: int
    prompt_cost_micros: int
    cached_cost_micros: int
    completion_cost_micros: int
    reasoning_cost_micros: int

class QuotaStatus(BaseModel):
    api_calls_used: int
    api_calls_limit: int
    api_calls_remaining: int
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    percentage_calls_used: float
    percentage_tokens_used: float

class GenerateResponse(BaseModel):
    request_id: str
    tenant_id: str
    content: str
    usage: TokenBreakdown
    cost: CostBreakdown
    quota_status: QuotaStatus
    cached_response: bool = False

class UsageRollupResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    plan_id: str
    plan_name: str
    status: str
    used: Dict[str, int]
    limits: Dict[str, int]
    remaining: Dict[str, int]
    cost: Dict[str, Any]
    quota_percentage: Dict[str, float]

class CheckoutSessionRequest(BaseModel):
    tenant_id: str
    plan_id: str = "pro"
    success_url: Optional[str] = "http://localhost:8000/billing/success"
    cancel_url: Optional[str] = "http://localhost:8000/billing/cancel"

class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    tenant_id: str
    plan_id: str
    mode: str = "test"

class ReconcileResponse(BaseModel):
    timestamp: str
    tenants_checked: int
    anomalies_detected: int
    details: str

class ErrorResponse(BaseModel):
    error: str
    code: str
    message: str
    tenant_id: Optional[str] = None
    retry_after_seconds: Optional[int] = None
