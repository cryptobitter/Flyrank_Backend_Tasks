"""
Pydantic Schemas & Boundary Validation Models.

Guarantees:
- Boundary validation: bad input -> clean 4xx, never 500
- Payload size boundaries: rejects oversized payloads with 413 / 422
- Spam & Honeypot detection
"""

import json
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# =====================================================================
# Auth & Tenant Schemas
# =====================================================================

class TenantRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TenantLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    name: str
    email: str


# =====================================================================
# Widget Schemas
# =====================================================================

class FormFieldConfig(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=100)
    type: Literal["text", "email", "textarea", "tel"] = "text"
    required: bool = True
    placeholder: Optional[str] = ""


class WidgetCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    widget_type: Literal["signup_form", "contact_modal", "cta_popover"] = "signup_form"
    button_text: str = Field(default="Submit", min_length=1, max_length=50)
    form_fields: List[FormFieldConfig] = Field(
        default_factory=lambda: [
            FormFieldConfig(name="name", label="Your Name", type="text", required=True),
            FormFieldConfig(name="email", label="Work Email", type="email", required=True),
        ]
    )
    theme_color: str = Field(default="#0D9488", max_length=20)
    allowed_domains: str = Field(default="*", max_length=500)

    @field_validator("theme_color")
    @classmethod
    def validate_theme_color(cls, v: str) -> str:
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", v):
            raise ValueError("Theme color must be a valid hex color code (e.g. #0D9488)")
        return v


class WidgetUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    button_text: Optional[str] = Field(default=None, min_length=1, max_length=50)
    theme_color: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None
    allowed_domains: Optional[str] = Field(default=None, max_length=500)


# =====================================================================
# Public Submission Schemas (Internet Boundary)
# =====================================================================

class PublicSubmissionRequest(BaseModel):
    model_config = {"populate_by_name": True}

    data: Dict[str, Any] = Field(..., description="Key-value dictionary of form submission inputs")
    # Honeypot field: hidden in UI; if populated by bots, submission is rejected or tagged as spam
    hp_website: Optional[str] = Field(default=None, alias="_hp_website", max_length=100)

    @field_validator("data")
    @classmethod
    def validate_data_payload(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not v or not isinstance(v, dict):
            raise ValueError("Form submission data dictionary cannot be empty.")
        if len(v) > 25:
            raise ValueError("Too many form fields submitted (maximum 25 fields allowed).")

        # Check total string size to block oversized JSON payloads (100KB boundary)
        serialized_len = len(json.dumps(v))
        if serialized_len > 102400:
            raise ValueError(f"Payload size ({serialized_len} bytes) exceeds maximum limit of 100KB.")

        # Sanitize and validate email if provided
        if "email" in v:
            email_val = str(v["email"]).strip()
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email_val):
                raise ValueError("Invalid email address format provided in form data.")

        return v


class PublicSubmissionResponse(BaseModel):
    status: Literal["success", "spam_blocked"]
    submission_id: str
    message: str
    geo: Optional[Dict[str, str]] = None


# =====================================================================
# Public Widget Config Schema (Cached Delivery)
# =====================================================================

class PublicWidgetConfigResponse(BaseModel):
    id: str
    title: str
    description: str
    widget_type: str
    button_text: str
    theme_color: str
    form_fields: List[FormFieldConfig]
    submit_url: str
