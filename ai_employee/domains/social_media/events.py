"""Social media domain events."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class SocialMediaEventType(str, Enum):
    """Social media event types."""
    POST_CREATED = "post_created"
    POST_PUBLISHED = "post_published"
    POST_SCHEDULED = "post_scheduled"
    POST_FAILED = "post_failed"
    POST_DELETED = "post_deleted"
    MENTION_RECEIVED = "mention_received"
    MENTION_PROCESSED = "mention_processed"
    ENGAGEMENT_UPDATED = "engagement_updated"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMIT_HIT = "rate_limit_hit"
    SENTIMENT_ANALYZED = "sentiment_analyzed"


@dataclass
class SocialMediaEvent:
    """Base event for social media domain."""
    event_type: SocialMediaEventType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PostCreatedEvent(SocialMediaEvent):
    """Event triggered when a social media post is created."""
    post_id: str = ""
    platform: str = ""
    content_type: str = ""
    content_preview: str = ""
    scheduled_time: Optional[datetime] = None

    def __post_init__(self):
        self.event_type = SocialMediaEventType.POST_CREATED


@dataclass
class PostPublishedEvent(SocialMediaEvent):
    """Event triggered when a post is successfully published."""
    post_id: str = ""
    platform: str = ""
    external_post_id: str = ""
    publish_time: Optional[datetime] = None

    def __post_init__(self):
        self.event_type = SocialMediaEventType.POST_PUBLISHED


@dataclass
class PostScheduledEvent(SocialMediaEvent):
    """Event triggered when a post is scheduled for future publishing."""
    schedule_id: str = ""
    platform: str = ""
    content_preview: str = ""
    scheduled_time: Optional[datetime] = None

    def __post_init__(self):
        self.event_type = SocialMediaEventType.POST_SCHEDULED


@dataclass
class PostFailedEvent(SocialMediaEvent):
    """Event triggered when a post fails to publish."""
    post_id: str = ""
    platform: str = ""
    error_message: str = ""
    failure_type: str = ""
    retry_count: int = 0

    def __post_init__(self):
        self.event_type = SocialMediaEventType.POST_FAILED


@dataclass
class PostDeletedEvent(SocialMediaEvent):
    """Event triggered when a post is deleted."""
    post_id: str = ""
    platform: str = ""
    delete_time: Optional[datetime] = None

    def __post_init__(self):
        self.event_type = SocialMediaEventType.POST_DELETED


@dataclass
class MentionReceivedEvent(SocialMediaEvent):
    """Event triggered when a brand mention is detected."""
    mention_id: str = ""
    platform: str = ""
    author: str = ""
    content_preview: str = ""
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        self.event_type = SocialMediaEventType.MENTION_RECEIVED


@dataclass
class MentionProcessedEvent(SocialMediaEvent):
    """Event triggered when a mention is processed with sentiment analysis."""
    mention_id: str = ""
    platform: str = ""
    sentiment_score: float = 0.0
    requires_approval: bool = False
    action_taken: str = ""

    def __post_init__(self):
        self.event_type = SocialMediaEventType.MENTION_PROCESSED


@dataclass
class EngagementUpdatedEvent(SocialMediaEvent):
    """Event triggered when engagement statistics are updated."""
    post_id: str = ""
    platform: str = ""
    likes: int = 0
    comments: int = 0
    shares: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0

    def __post_init__(self):
        self.event_type = SocialMediaEventType.ENGAGEMENT_UPDATED


@dataclass
class AuthenticationSuccessEvent(SocialMediaEvent):
    """Event triggered when platform authentication succeeds."""
    platform: str = ""
    auth_method: str = ""
    user_id: str = ""

    def __post_init__(self):
        self.event_type = SocialMediaEventType.AUTHENTICATION_SUCCESS


@dataclass
class AuthenticationFailedEvent(SocialMediaEvent):
    """Event triggered when platform authentication fails."""
    platform: str = ""
    error_message: str = ""
    attempted_auth_method: str = ""

    def __post_init__(self):
        self.event_type = SocialMediaEventType.AUTHENTICATION_FAILED


@dataclass
class RateLimitHitEvent(SocialMediaEvent):
    """Event triggered when rate limiting is encountered."""
    platform: str = ""
    limit_type: str = ""
    retry_after: Optional[datetime] = None
    affected_operation: str = ""

    def __post_init__(self):
        self.event_type = SocialMediaEventType.RATE_LIMIT_HIT


@dataclass
class SentimentAnalyzedEvent(SocialMediaEvent):
    """Event triggered when sentiment analysis completes."""
    mention_id: str = ""
    platform: str = ""
    sentiment_score: float = 0.0
    sentiment_label: str = ""
    confidence: float = 0.0

    def __post_init__(self):
        self.event_type = SocialMediaEventType.SENTIMENT_ANALYZED
