"""
SQLAlchemy Relational Models:
- User (Auth & RBAC)
- Incident (Operational Incidents & AI Triage)
- PostMortem (Executive Reports & Analytics)
- AuditLog (Security & Traceability)
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="sre_engineer")  # sre_engineer, admin, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    audit_logs = relationship("AuditLog", back_populates="user")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), default="P2_HIGH", index=True)  # P1_CRITICAL, P2_HIGH, P3_MEDIUM, P4_LOW
    status = Column(String(50), default="OPEN", index=True)        # OPEN, INVESTIGATING, MITIGATED, RESOLVED
    raw_logs = Column(Text, nullable=False)
    error_count = Column(Integer, default=1)
    
    # AI Incident Commander Analysis Fields
    ai_analyzed = Column(Boolean, default=False)
    root_cause = Column(Text, nullable=True)
    mitigation_steps = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    suggested_runbook_url = Column(String(255), nullable=True)
    
    idempotency_key = Column(String(64), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    post_mortem = relationship("PostMortem", back_populates="incident", uselist=False)


class PostMortem(Base):
    __tablename__ = "post_mortems"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), unique=True, nullable=False)
    executive_summary = Column(Text, nullable=False)
    root_cause_analysis = Column(Text, nullable=False)
    impact_duration_minutes = Column(Integer, default=45)
    timeline_json = Column(Text, nullable=True)  # JSON array of events
    action_items_json = Column(Text, nullable=True)  # JSON array of prevention steps
    pdf_path = Column(String(512), nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="post_mortem")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="audit_logs")
