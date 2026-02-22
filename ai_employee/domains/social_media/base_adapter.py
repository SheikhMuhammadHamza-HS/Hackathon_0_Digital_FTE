"""Base social media adapter interface."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import SocialPost, BrandMention, Platform


class SocialMediaAdapter(ABC):
    """Abstract base class for social media platform adapters."""

    def __init__(self, platform: Platform):
        """Initialize adapter with platform configuration."""
        self.platform = platform
        self._client = None

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with the social media platform."""
        pass

    @abstractmethod
    async def post_content(self, post: SocialPost) -> str:
        """Post content to the platform. Returns post ID."""
        pass

    @abstractmethod
    async def get_post(self, post_id: str) -> Optional[SocialPost]:
        """Retrieve a post by ID."""
        pass

    @abstractmethod
    async def delete_post(self, post_id: str) -> bool:
        """Delete a post by ID."""
        pass

    @abstractmethod
    async def get_mentions(self, since: Optional[datetime] = None) -> List[BrandMention]:
        """Get brand mentions."""
        pass

    @abstractmethod
    async def get_engagement_stats(self, post_id: str) -> Dict[str, Any]:
        """Get engagement statistics for a post."""
        pass

    @abstractmethod
    def supports_content_type(self, content_type: str) -> bool:
        """Check if platform supports given content type."""
        pass
