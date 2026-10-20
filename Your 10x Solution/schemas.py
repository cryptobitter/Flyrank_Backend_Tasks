"""
Pydantic v2 Schemas for SentinelAI:
Strict data contracts for Auth, Incident Ingestion, AI Triage, and Post-Mortems.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    SRE_ENGINEER = "sre_engineer"
    ADMIN = "admin"
    VIEWER = "viewer"


class IncidentSeverity(str, Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"


# --- AUTH SCHEMAS ---

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password min length 6")
    full_name: Optional[str] = None
    role: UserRole = UserRole.SRE_ENGINEER


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in_minutes: int
    user_id: str
    email: str
    role: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


# --- INCIDENT SCHEMAS ---

class IncidentCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    service_name: str = Field(..., min_length=2, max_length=100)
    severity: IncidentSeverity = IncidentSeverity.P2_HIGH
    raw_logs: str = Field(..., min_length=5, description="Stack trace or monitoring log snippet")
    error_count: int = Field(default=1, ge=1)
    idempotency_key: Optional[str] = Field(None, description="Client idempotency key to prevent duplicate alert ingestion")


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    service_name: str
    severity: str
    status: str
    raw_logs: str
    error_count: int
    ai_analyzed: bool
    root_cause: Optional[str] = None
    mitigation_steps: Optional[str] = None
    confidence_score: Optional[float] = None
    suggested_runbook_url: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class IncidentTriageResult(BaseModel):
    """Structured AI output returned by the Incident Commander LLM."""
    severity: IncidentSeverity
    root_cause: str
    mitigation_steps: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    suggested_runbook_url: str
    executive_summary: str
    estimated_impact_minutes: int = 30


# --- POST-MORTEM SCHEMAS ---

class PostMortemCreateRequest(BaseModel):
    executive_summary: Optional[str] = None
    root_cause_analysis: Optional[str] = None
    impact_duration_minutes: int = 45
    timeline: List[Dict[str, str]] = Field(default_factory=list)
    action_items: List[Dict[str, str]] = Field(default_factory=list)


class PostMortemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str
    executive_summary: str
    root_cause_analysis: str
    impact_duration_minutes: int
    pdf_path: Optional[str]
    generated_at: datetime
