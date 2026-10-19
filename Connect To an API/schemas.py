"""
Pydantic schemas for the AI Message Triage & Judgment Engine.
Guarantees a strict, typed contract for both incoming requests and model judgements.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class CategoryEnum(str, Enum):
    """Business categories for incoming customer inquiries."""
    BILLING = "billing"
    TECHNICAL_ISSUE = "technical_issue"
    SECURITY_INCIDENT = "security_incident"
    FEATURE_REQUEST = "feature_request"
    CHURN_RISK = "churn_risk"
    GENERAL_INQUIRY = "general_inquiry"


class SentimentEnum(str, Enum):
    """Customer emotional tone detected in the message."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    HOSTILE = "hostile"


class ActionEnum(str, Enum):
    """Deterministic automated action downstream systems should execute."""
    AUTO_REFUND_REVIEW = "auto_refund_review"
    ESCALATE_TO_SECURITY = "escalate_to_security"
    ROUTE_TO_TIER3_ENG = "route_to_tier3_eng"
    STANDARD_SUPPORT_QUEUE = "standard_support_queue"
    CHURN_RETENTION_CONTACT = "churn_retention_contact"
    SEND_KNOWLEDGE_BASE = "send_knowledge_base"


class CustomerTierEnum(str, Enum):
    """Customer account tier for service level agreement (SLA) context."""
    STANDARD = "standard"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------

class TriageRequest(BaseModel):
    """Incoming payload sent to the /api/v1/triage/judge endpoint."""
    message_id: str = Field(..., description="Unique UUID or ticket ID for the message")
    message_body: str = Field(
        ...,
        min_length=3,
        max_length=5000,
        description="Raw, unformatted customer message text to judge",
        examples=["My production cluster is returning 500 errors and our users cannot login! Urgent help needed!"]
    )
    customer_tier: CustomerTierEnum = Field(
        default=CustomerTierEnum.STANDARD,
        description="Account SLA tier affecting triage urgency weighting"
    )
    sender_email: Optional[str] = Field(
        default=None,
        description="Optional customer email address"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "msg-89472",
                "message_body": "I was charged $49.99 twice for invoice #INV-2024-88. Please refund the duplicate transaction immediately.",
                "customer_tier": "pro",
                "sender_email": "finance@clientcorp.io"
            }
        }
    )


# ------------------------------------------------------------------------------
# Response / Judgment Schemas (Trustworthy Contract)
# ------------------------------------------------------------------------------

class TriageJudgment(BaseModel):
    """
    Strictly validated AI judgment output that downstream code can 100% trust.
    Any violation of types, bounds, or missing fields fails instantly.
    """
    message_id: str = Field(..., description="ID matching the incoming message")
    category: CategoryEnum = Field(..., description="Classified business domain")
    urgency_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Severity score: 1 (cosmetic/info) to 5 (critical security/outage emergency)"
    )
    sentiment: SentimentEnum = Field(..., description="Assessed customer tone")
    recommended_action: ActionEnum = Field(..., description="Prescribed programmatic next step")
    requires_human_escalation: bool = Field(..., description="True if human supervisor must immediately inspect")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model self-confidence calibration between 0.0 and 1.0"
    )
    reasoning: str = Field(
        ...,
        min_length=5,
        max_length=350,
        description="Concise rationale explaining the judgment"
    )
    extracted_entities: List[str] = Field(
        default_factory=list,
        description="Key extracted identifiers (e.g., invoice numbers, order IDs, error codes)"
    )
    model_used: str = Field(..., description="Model identifier that produced this judgment")
    processing_time_ms: int = Field(..., ge=0, description="End-to-end execution latency in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "msg-89472",
                "category": "billing",
                "urgency_score": 4,
                "sentiment": "frustrated",
                "recommended_action": "auto_refund_review",
                "requires_human_escalation": False,
                "confidence_score": 0.98,
                "reasoning": "Duplicate charge inquiry with specific invoice number identified. Financial impact warrants high urgency.",
                "extracted_entities": ["INV-2024-88", "$49.99"],
                "model_used": "llama-3.3-70b-versatile",
                "processing_time_ms": 412
            }
        }
    )


# ------------------------------------------------------------------------------
# Error Schemas
# ------------------------------------------------------------------------------

class ApiErrorResponse(BaseModel):
    """Structured error payload returned on unhandled or upstream failures."""
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable explanation of failure")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed diagnostic context")
    is_retryable: bool = Field(..., description="Whether client should consider retrying later")
    attempts_made: int = Field(default=1, description="Number of attempts executed by server")
