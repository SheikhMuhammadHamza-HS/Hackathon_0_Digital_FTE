"""Social media service for multi-platform management."""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass, field

from .base_adapter import SocialMediaAdapter
from .models import SocialPost, BrandMention, Platform, PostStatus
from .rate_limiter import AdaptiveRateLimiter
from .content_adapter import ContentAdapter

logger = logging.getLogger(__name__)


@dataclass
class SocialMediaConfig:
    """Configuration for social media service."""
    max_retries: int = 3
    retry_delay: float = 1.0
    max_concurrent_posts: int = 5
    rate_limit_delay: float = 1.0
    auto_approve_threshold: float = 0.8  # Sentiment threshold for auto-approval


class SocialMediaService:
    """Unified social media management service."""

    def __init__(self, config: Optional[SocialMediaConfig] = None):
        """Initialize social media service."""
        self.config = config or SocialMediaConfig()
        self._adapters: Dict[Platform, SocialMediaAdapter] = {}
        self._posting_semaphore = asyncio.Semaphore(self.config.max_concurrent_posts)
        self._rate_limiter = asyncio.Lock()
        self._scheduled_posts: Dict[str, SocialPost] = {}
        self._watchdog_task: Optional[asyncio.Task] = None

    async def register_adapter(self, platform: Platform, adapter: SocialMediaAdapter) -> None:
        """Register a platform adapter."""
        self._adapters[platform] = adapter
        logger.info(f"Registered adapter for {platform.value}")

    async def authenticate_platform(
        self,
        platform: Platform,
        credentials: Dict[str, str]
    ) -> bool:
        """Authenticate with a specific platform."""
        if platform not in self._adapters:
            logger.error(f"No adapter registered for {platform.value}")
            return False

        try:
            adapter = self._adapters[platform]
            return await adapter.authenticate(credentials)
        except Exception as e:
            logger.error(f"Authentication failed for {platform.value}: {e}")
            return False

    async def post_to_platform(
        self,
        platform: Platform,
        post: SocialPost
    ) -> Optional[str]:
        """Post content to a specific platform with retry logic."""
        if platform not in self._adapters:
            logger.error(f"No adapter registered for {platform.value}")
            return None

        async with self._posting_semaphore:
            for attempt in range(self.config.max_retries):
                try:
                    # Apply rate limiting
                    async with self._rate_limiter:
                        await asyncio.sleep(self.config.rate_limit_delay)

                    # Post content
                    adapter = self._adapters[platform]
                    post_id = await adapter.post_content(post)

                    if post_id:
                        logger.info(f"Successfully posted to {platform.value}: {post_id}")
                        return post_id

                except Exception as e:
                    logger.warning(
                        f"Post attempt {attempt + 1} failed for {platform.value}: {e}"
                    )
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))

            logger.error(f"Failed to post to {platform.value} after {self.config.max_retries} attempts")
            return None

    async def post_to_multiple_platforms(
        self,
        platforms: List[Platform],
        post: SocialPost
    ) -> Dict[Platform, Optional[str]]:
        """Post content to multiple platforms concurrently."""
        tasks = []
        for platform in platforms:
            # Create platform-specific post copy
            platform_post = SocialPost(
                platform=platform,
                content=post.content,
                content_type=post.content_type,
                scheduled_time=post.scheduled_time,
                tags=post.tags,
                engagement_goals=post.engagement_goals
            )
            task = self.post_to_platform(platform, platform_post)
            tasks.append((platform, task))

        # Execute all tasks concurrently
        results = {}
        for platform, task in tasks:
            try:
                post_id = await task
                results[platform] = post_id
            except Exception as e:
                logger.error(f"Failed to post to {platform.value}: {e}")
                results[platform] = None

        return results

    async def schedule_post(
        self,
        platforms: List[Platform],
        post: SocialPost,
        scheduled_time: datetime
    ) -> str:
        """Schedule a post for future publishing."""
        schedule_id = f"schedule_{hash(f'{platforms}_{post.content}') % 1000000}"

        scheduled_post = SocialPost(
            platform=post.platform,
            content=post.content,
            content_type=post.content_type,
            scheduled_time=scheduled_time,
            tags=post.tags,
            engagement_goals=post.engagement_goals,
            external_id=schedule_id
        )

        self._scheduled_posts[schedule_id] = scheduled_post
        logger.info(f"Scheduled post {schedule_id} for {scheduled_time}")

        return schedule_id

    async def monitor_scheduled_posts(self) -> None:
        """Background task to monitor and publish scheduled posts."""
        while True:
            try:
                now = datetime.now()
                posts_to_publish = []

                # Find posts ready to publish
                for schedule_id, post in list(self._scheduled_posts.items()):
                    if post.scheduled_time and post.scheduled_time <= now:
                        posts_to_publish.append((schedule_id, post))

                # Publish ready posts
                for schedule_id, post in posts_to_publish:
                    logger.info(f"Publishing scheduled post {schedule_id}")

                    # Post to the specified platforms
                    if post.platform:
                        platforms = [post.platform]
                    else:
                        platforms = list(self._adapters.keys())

                    results = await self.post_to_multiple_platforms(platforms, post)

                    # Remove from scheduled posts
                    del self._scheduled_posts[schedule_id]

                    # Notify about results
                    for platform, post_id in results.items():
                        if post_id:
                            logger.info(f"Scheduled post published to {platform.value}: {post_id}")

            except Exception as e:
                logger.error(f"Error in scheduled post monitor: {e}")

            # Check every minute
            await asyncio.sleep(60)

    async def get_mentions(self, platforms: Optional[List[Platform]] = None) -> List[BrandMention]:
        """Get brand mentions from specified platforms."""
        if platforms is None:
            platforms = list(self._adapters.keys())

        all_mentions = []

        for platform in platforms:
            if platform not in self._adapters:
                continue

            try:
                async with self._rate_limiter:
                    await asyncio.sleep(self.config.rate_limit_delay)

                adapter = self._adapters[platform]
                mentions = await adapter.get_mentions()
                all_mentions.extend(mentions)

            except Exception as e:
                logger.error(f"Failed to get mentions from {platform.value}: {e}")

        return all_mentions

    async def analyze_sentiment(self, mention: BrandMention) -> float:
        """Analyze sentiment of a brand mention (placeholder implementation)."""
        # In the real implementation, would use NLP/ML service
        # For now, return a mock sentiment score based on keywords
        positive_words = ['great', 'amazing', 'love', 'excellent', 'fantastic', 'good', 'awesome']
        negative_words = ['bad', 'terrible', 'hate', 'awful', 'poor', 'horrible', 'issue', 'problem']

        content_lower = mention.content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            return 0.8  # Positive
        elif negative_count > positive_count:
            return 0.2  # Negative
        else:
            return 0.5  # Neutral

    async def process_mention(self, mention: BrandMention) -> Dict[str, Any]:
        """Process a brand mention with sentiment analysis and HITL decision."""
        sentiment = await self.analyze_sentiment(mention)
        mention.sentiment_score = sentiment

        result = {
            'mention': mention,
            'sentiment': sentiment,
            'requires_approval': False,
            'recommended_action': None
        }

        # High-negative sentiment requires human approval
        if sentiment < 0.3:
            result['requires_approval'] = True
            result['recommended_action'] = 'Respond professionally to address concerns'
        # High-positive sentiment with low engagement
        elif sentiment > 0.7 and mention.engagement_score < 2.0:
            result['recommended_action'] = 'Engage to boost visibility'
        # Neutral or positive - auto-approve
        else:
            result['recommended_action'] = 'Monitor for follow-up'

        return result

    async def get_engagement_stats(
        self,
        platforms: Optional[List[Platform]] = None
    ) -> Dict[Platform, Dict[str, Any]]:
        """Get engagement statistics across platforms."""
        if platforms is None:
            platforms = list(self._adapters.keys())

        stats = {}

        for platform in platforms:
            if platform not in self._adapters:
                continue

            try:
                async with self._rate_limiter:
                    await asyncio.sleep(self.config.rate_limit_delay)

                adapter = self._adapters[platform]
                # In real implementation, would fetch recent posts and get their stats
                stats[platform] = {'active': True}

            except Exception as e:
                logger.error(f"Failed to get stats from {platform.value}: {e}")
                stats[platform] = {'active': False, 'error': str(e)}

        return stats

    async def start_watchdog(self) -> None:
        """Start the scheduled post watchdog."""
        if self._watchdog_task is None:
            self._watchdog_task = asyncio.create_task(self.monitor_scheduled_posts())
            logger.info("Started social media watchdog")

    async def stop_watchdog(self) -> None:
        """Stop the scheduled post watchdog."""
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
            self._watchdog_task = None
            logger.info("Stopped social media watchdog")

    def get_registered_platforms(self) -> List[Platform]:
        """Get list of registered platforms."""
        return list(self._adapters.keys())

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.stop_watchdog()
        logger.info("Social media service cleanup completed")
