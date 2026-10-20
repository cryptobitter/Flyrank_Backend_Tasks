"""
Pydantic Schemas & Domain Models for AI Image Understanding Engine.

Enforces:
- Schema validation for Vision AI structured outputs
- Mismatch guard decision records and human-readable explanations
- Cost tracking audit entries
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ImageVisionOutput(BaseModel):
    """Structured output expected from Vision Model."""
    subject: str = Field(..., min_length=1, max_length=100, description="Identified primary subject, e.g. red fox")
    category: str = Field(..., min_length=1, max_length=50, description="High-level category, e.g. animal, technology")
    attributes: List[str] = Field(default_factory=list, description="Visual descriptors like orange fur, wild, forest")
    caption: str = Field(..., min_length=5, max_length=300, description="Natural language description of the image")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    flagged_for_review: bool = Field(default=False, description="Flagged if confidence is below safety threshold")

    @field_validator("confidence")
    @classmethod
    def check_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 3)


class ImageRecord(BaseModel):
    """Persisted database record of an analyzed image."""
    id: str
    filename: str
    file_path: str
    subject: str
    category: str
    attributes: List[str]
    caption: str
    confidence: float
    flagged_for_review: bool
    created_at: str


class BlogPostCreate(BaseModel):
    """Schema for registering or querying a blog post."""
    id: Optional[str] = None
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10, max_length=10000)


class CandidateMatch(BaseModel):
    """Individual candidate image evaluated by the Mismatch Guard."""
    image_id: str
    subject: str
    category: str
    caption: str
    confidence: float
    similarity_score: float
    guard_decision: Literal["ACCEPTED", "REJECTED"]
    rejection_reason: Optional[str] = None


class MatchResponse(BaseModel):
    """Response returned when querying an image for a blog post."""
    post_id: str
    post_title: str
    status: Literal["matched", "no_confident_match"]
    recommended_image: Optional[CandidateMatch] = None
    top_candidates: List[CandidateMatch] = []
    explanation: str


class ReviewAction(BaseModel):
    """Human-in-the-loop review workflow payload."""
    post_id: str
    image_id: str
    decision: Literal["approved", "rejected"]
    feedback: Optional[str] = None


class CostLogEntry(BaseModel):
    """Cost ledger entry attributed per AI call."""
    id: str
    operation: Literal["vision_tagging", "embedding_generation"]
    model: str
    input_units: int
    output_units: int
    cost_usd: float
    timestamp: str
