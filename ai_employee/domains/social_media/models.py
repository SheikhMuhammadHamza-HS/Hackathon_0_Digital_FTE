"""Models for social media domain."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from ai_employee.domains import BaseEntity


class Platform(Enum):
    """Supported social media platforms."""

    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"


class PostStatus(Enum):
    """Status of a social media post."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ContentType(str, Enum):
    """Content types for social media posts."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"
    ARTICLE = "article"
    STORY = "story"
    REEL = "reel"


class Sentiment(Enum):
    """Sentiment analysis results."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SocialPost(BaseEntity):
    """Represents a social media post."""

    # Platform identification
    platform: Platform = field(default=None)  # type: ignore
    author_id: str = field(default="")  # Account/handle that posted

    # Content
    content: str = field(default="")
    content_type: ContentType = field(default=ContentType.TEXT)
    media_urls: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Status and timing
    status: PostStatus = field(default=PostStatus.DRAFT)
    scheduled_time: Optional[datetime] = field(default=None)
    published_at: Optional[datetime] = field(default=None)

    # Engagement metrics (after posting)
    metrics: Dict[str, Any] = field(default_factory=dict)
    engagement_goals: Dict[str, Any] = field(default_factory=dict)

    # Platform-specific data
    platform_post_id: Optional[str] = field(default=None)
    platform_url: Optional[str] = field(default=None)

    # Approval workflow
    requires_approval: bool = field(default=False)
    approved_by: Optional[str] = field(default=None)
    approved_at: Optional[datetime] = field(default=None)

    def __post_init__(self):
        """Validate post after initialization."""
        self._validate_status_transition()
        self._validate_content_length()

    def _validate_status_transition(self):
        """Validate status transitions."""
        # This will be enhanced when we add status history
        pass

    def _validate_content_length(self):
        """Validate content length based on platform."""
        if self.platform == Platform.TWITTER and len(self.content) > 280:
            # Twitter character limit
            pass  # Will be handled by content adaptation

    def schedule(self, schedule_time: datetime) -> None:
        """Schedule the post for future publication."""
        if self.status != PostStatus.DRAFT:
            raise ValueError(f"Cannot schedule post in {self.status} status")

        self.status = PostStatus.SCHEDULED
        self.scheduled_time = schedule_time
        self.update_timestamp()

    def publish(self) -> None:
        """Mark post as published."""
        if self.status not in [PostStatus.DRAFT, PostStatus.SCHEDULED]:
            raise ValueError(f"Cannot publish post in {self.status} status")

        self.status = PostStatus.POSTED
        self.published_at = datetime.utcnow()
        self.update_timestamp()

    def cancel(self) -> None:
        """Cancel a scheduled post."""
        if self.status != PostStatus.SCHEDULED:
            raise ValueError(f"Cannot cancel post in {self.status} status")

        self.status = PostStatus.CANCELLED
        self.update_timestamp()

    def mark_failed(self, error: str) -> None:
        """Mark post as failed."""
        self.status = PostStatus.FAILED
        self.add_metadata("failure_reason", error)
        self.update_timestamp()


@dataclass
class BrandMention(BaseEntity):
    """Represents a brand mention on social media."""

    # Platform identification
    platform: Platform = field(default=None)  # type: ignore
    mention_id: str = field(default="")  # Platform's mention ID

    # Author information
    author: str = field(default="")  # Username/handle
    author_id: Optional[str] = field(default=None)  # Platform user ID
    author_profile_url: Optional[str] = field(default=None)

    # Content
    content: str = field(default="")
    url: Optional[str] = field(default=None)  # Link to original mention
    engagement_score: float = field(default=0.0)

    # Analysis
    sentiment: Sentiment = field(default=Sentiment.NEUTRAL)
    sentiment_confidence: float = field(default=0.5)

    # Response management
    requires_response: bool = field(default=False)
    response_priority: str = field(default="low")  # low, medium, high
    response_status: str = field(default="unresponded")  # unresponded, pending, responded, escalated

    # Timing
    mention_timestamp: datetime = field(default_factory=datetime.utcnow)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = field(default=None)

    # Related posts
    post_id: Optional[str] = field(default=None)  # If mention is on one of our posts
    conversation_id: Optional[str] = field(default=None)  # For threaded conversations

    # Sentiment analysis details
    sentiment_scores: Dict[str, float] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)

    # Response tracking
    response_id: Optional[str] = field(default=None)  # ID of our response
    response_content: Optional[str] = field(default=None)  # Our response content

    def __post_init__(self):
        """Validate mention after initialization."""
        self._validate_sentiment_confidence()
        self._determine_response_requirements()

    def _validate_sentiment_confidence(self):
        """Validate sentiment confidence range."""
        if not (0 <= self.sentiment_confidence <= 1):
            raise ValueError("Sentiment confidence must be between 0 and 1")

    def _determine_response_requirements(self):
        """Determine if a response is required based on content and sentiment."""
        # Check for questions
        contains_question = "?" in self.content or any(
            phrase in self.content.lower() for phrase in [
                "how", "what", "when", "where", "why", "can you", "help"
            ]
        )

        # Sentiment-based rules
        if self.sentiment == Sentiment.NEGATIVE:
            if self.sentiment_confidence > 0.8:
                self.requires_response = True
                self.response_priority = "high"
            elif self.sentiment_confidence > 0.6:
                self.requires_response = True
                self.response_priority = "medium"
        elif self.sentiment == Sentiment.NEUTRAL and contains_question:
            self.requires_response = True
            self.response_priority = "medium"

    def mark_responded(self, response_id: str, response_content: str) -> None:
        """Mark mention as responded to."""
        self.response_id = response_id
        self.response_content = response_content
        self.response_status = "responded"
        self.responded_at = datetime.utcnow()
        self.update_timestamp()

    def escalate(self) -> None:
        """Escalate mention for human review."""
        self.response_status = "escalated"
        self.requires_response = True
        self.response_priority = "high"
        self.update_timestamp()

    def get_sentiment_summary(self) -> Dict[str, Any]:
        """Get a summary of sentiment analysis."""
        return {
            "sentiment": self.sentiment.value,
            "confidence": self.sentiment_confidence,
            "scores": self.sentiment_scores,
            "requires_action": self.requires_response,
            "priority": self.response_priority
        }


# Type aliases for convenience
PostSchedule = Dict[str, Any]
MentionFilter = Dict[str, Any]
