"""
Pydantic Schemas for Background Job System:
- Job submission & acceptance (202 Accepted)
- Job polling & status inspection
- Structured A6 AI Triage judgment result
- Alert dispatch payloads
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class TriageCategory(str, Enum):
    SUPPORT_TECHNICAL = "support_technical"
    BILLING_REFUND = "billing_refund"
    SECURITY_INCIDENT = "security_incident"
    FEATURE_REQUEST = "feature_request"
    GENERAL_INQUIRY = "general_inquiry"


class UrgencyLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TriageJudgment(BaseModel):
    """Structured result produced by the slow AI evaluation task."""
    model_config = ConfigDict(extra="forbid")

    category: TriageCategory = Field(
        ...,
        description="Classified operational domain of the inquiry"
    )
    urgency: UrgencyLevel = Field(
        ...,
        description="Assessed urgency level"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence score between 0.0 and 1.0"
    )
    summary: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="One-sentence executive summary of the issue"
    )
    recommended_action: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Concrete next operational step for staff or automation"
    )
    is_escalation_required: bool = Field(
        ...,
        description="Whether an engineering or executive escalation is warranted"
    )
    tokens_used: int = Field(
        default=0,
        description="Inference tokens consumed"
    )
    execution_time_ms: float = Field(
        default=0.0,
        description="Duration of the slow AI task in milliseconds"
    )


class JobSubmissionRequest(BaseModel):
    """Payload submitted to enqueue a slow AI operation."""
    message: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Inbound raw customer inquiry or message to triage"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional customer or organization identifier"
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Optional client-provided idempotency key. If omitted, will be derived from header or payload hash."
    )
    simulate_failure: bool = Field(
        default=False,
        description="Test flag: Force task failure to exercise worker retry and alerting paths"
    )
    simulate_delay_sec: float = Field(
        default=1.0,
        ge=0.0,
        le=15.0,
        description="Simulated latency for the slow operation in seconds"
    )


class JobSubmissionResponse(BaseModel):
    """Immediate response returned with HTTP 202 Accepted (<50ms)."""
    job_id: str = Field(..., description="Unique job tracking identifier")
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Initial job status")
    status_url: str = Field(..., description="Polling endpoint URL to query job status")
    idempotency_key: str = Field(..., description="Unique idempotency key assigned/used for this job")
    is_duplicate: bool = Field(
        default=False,
        description="True if an existing job was returned due to idempotency key reuse"
    )
    message: str = Field(
        default="Request accepted for asynchronous processing",
        description="Human-readable confirmation"
    )
    accepted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp when the job was accepted"
    )


class JobStatusResponse(BaseModel):
    """Full status response returned from GET /api/v1/jobs/{job_id}."""
    job_id: str
    status: JobStatus
    idempotency_key: str
    attempts: int = Field(default=0, description="Number of execution attempts made by workers")
    max_retries: int = Field(default=3, description="Maximum retry threshold before dead-lettering")
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    result: Optional[TriageJudgment] = None
    error: Optional[str] = None
    alert_dispatched: bool = Field(
        default=False,
        description="True if an alert notification was dispatched due to fatal retries"
    )
    retry_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Log of failed attempts with error messages and timestamps"
    )


class AlertRecord(BaseModel):
    """Structured notification dispatched to on-call or alerting systems."""
    alert_id: str
    job_id: str
    event: str = Field(default="job_fatal_failure")
    severity: str = Field(default="CRITICAL")
    attempts_made: int
    error_message: str
    dispatched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target_channel: str = "slack-ops-pager"
    payload: Dict[str, Any] = Field(default_factory=dict)
