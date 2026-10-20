"""
Pydantic Schemas for Social Media Studio:
Data contracts for campaign composition, multi-platform publishing,
rate-limit resilience, and HMAC-signed webhook delivery callbacks.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class PlatformType(str, Enum):
    MOCK_TWITTER = "mock_twitter"
    MOCK_LINKEDIN = "mock_linkedin"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    MASTODON = "mastodon"


class PublishStatus(str, Enum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    RATE_LIMITED = "rate_limited"
    FAILED = "failed"


class PostContent(BaseModel):
    """Normalized content payload adapted across various platform constraints."""
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Text body of the social media post"
    )
    media_urls: List[str] = Field(
        default_factory=list,
        description="Optional list of image or video URLs to attach"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Hashtags or classification tags without '#'"
    )


class CampaignPublishRequest(BaseModel):
    """Multi-platform broadcast request payload."""
    campaign_id: str = Field(
        ...,
        description="Unique identifier for the marketing or announcement campaign"
    )
    content: PostContent
    platforms: List[PlatformType] = Field(
        ...,
        min_length=1,
        description="Target social platforms to broadcast the post"
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Client idempotency key. Prevents double-posting on network retry."
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="Webhook endpoint URL to receive HMAC-signed delivery callbacks"
    )
    simulate_rate_limit: bool = Field(
        default=False,
        description="Test flag: Force mock platforms to return 429 Too Many Requests with Retry-After"
    )


class PlatformPublishResult(BaseModel):
    """Result of publishing to an individual platform."""
    platform: PlatformType
    status: PublishStatus
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    attempts: int = 1
    latency_ms: float = 0.0
    rate_limit_recovered: bool = False
    error: Optional[str] = None


class CampaignPublishResponse(BaseModel):
    """Aggregated campaign broadcast response."""
    campaign_id: str
    idempotency_key: str
    total_platforms: int
    successful_platforms: int
    failed_platforms: int
    results: List[PlatformPublishResult]
    is_duplicate_run: bool = False
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MockTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


class WebhookDeliveryPayload(BaseModel):
    """Payload sent by platform callback webhooks."""
    event_id: str
    event_type: str = "post.delivered"
    platform: str
    post_id: str
    campaign_id: str
    delivered_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, str] = Field(default_factory=dict)
