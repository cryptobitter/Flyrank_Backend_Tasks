"""
Base Platform Adapter Interface:
Defines the uniform publishing contract for all social media platforms (Mock, Discord, Telegram, Mastodon).
"""

from abc import ABC, abstractmethod
from typing import Optional

from schemas import (
    PlatformPublishResult,
    PlatformType,
    PostContent,
    PublishStatus,
)


class BasePlatformAdapter(ABC):
    def __init__(self, platform_type: PlatformType):
        self.platform_type = platform_type

    @abstractmethod
    async def publish(
        self,
        content: PostContent,
        idempotency_key: str,
        callback_url: Optional[str] = None,
        simulate_rate_limit: bool = False,
    ) -> PlatformPublishResult:
        """Publishes post content to the destination platform."""
        pass
