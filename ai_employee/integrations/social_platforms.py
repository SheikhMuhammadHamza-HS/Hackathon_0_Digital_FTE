"""Unified social media integration client."""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ai_employee.domains.social_media import (
    SocialMediaService, SocialMediaConfig,
    TwitterAdapter, FacebookAdapter, InstagramAdapter, LinkedInAdapter,
    SocialPost, BrandMention, Platform, ContentType, PostStatus
)
from ai_employee.core.event_bus import get_event_bus
from ai_employee.domains.social_media.events import *

logger = logging.getLogger(__name__)


class UnifiedSocialClient:
    """Unified client for managing all social media platforms."""

    def __init__(self, config: Optional[SocialMediaConfig] = None):
        """Initialize unified social client."""
        self.service = SocialMediaService(config)
        self.event_bus = get_event_bus()
        self.platform_configs: Dict[Platform, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> bool:
        """Initialize all configured social media platforms."""
        try:
            await self.service.start_watchdog()

            # Register all adapters
            await self.service.register_adapter(Platform.TWITTER, TwitterAdapter())
            await self.service.register_adapter(Platform.FACEBOOK, FacebookAdapter())
            await self.service.register_adapter(Platform.INSTAGRAM, InstagramAdapter())
            await self.service.register_adapter(Platform.LINKEDIN, LinkedInAdapter())

            self.logger.info("Unified social client initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize social client: {e}")
            return False

    async def configure_platform(
        self,
        platform: Platform,
        credentials: Dict[str, str]
    ) -> bool:
        """Configure and authenticate a social media platform."""
        try:
            success = await self.service.authenticate_platform(platform, credentials)

            if success:
                self.platform_configs[platform] = {
                    'credentials': credentials,
                    'configured_at': datetime.now()
                }

                await self.event_bus.publish(AuthenticationSuccessEvent(
                    platform=platform.value,
                    auth_method="oauth",
                    user_id=credentials.get('user_id', 'unknown')
                ))

                self.logger.info(f"Platform {platform.value} configured successfully")
            else:
                await self.event_bus.publish(AuthenticationFailedEvent(
                    platform=platform.value,
                    error_message="Authentication failed",
                    attempted_auth_method="oauth"
                ))

            return success

        except Exception as e:
            self.logger.error(f"Failed to configure platform {platform.value}: {e}")
            await self.event_bus.publish(AuthenticationFailedEvent(
                platform=platform.value,
                error_message=str(e),
                attempted_auth_method="oauth"
            ))
            return False

    async def create_and_post(
        self,
        platforms: List[Platform],
        content: str,
        content_type: str = "text",
        tags: Optional[List[str]] = None,
        engagement_goals: Optional[Dict[str, Any]] = None
    ) -> Dict[Platform, Optional[str]]:
        """Create a post and publish it to multiple platforms."""
        try:
            post = SocialPost(
                platform=None,  # Will be set per platform
                content=content,
                content_type=content_type,
                tags=tags or [],
                engagement_goals=engagement_goals or {}
            )

            # Publish to platforms
            results = await self.service.post_to_multiple_platforms(platforms, post)

            # Emit events for successful posts
            for platform, post_id in results.items():
                if post_id:
                    await self.event_bus.publish(PostPublishedEvent(
                        post_id=post_id,
                        platform=platform.value,
                        external_post_id=post_id,
                        publish_time=datetime.now()
                    ))
                else:
                    await self.event_bus.publish(PostFailedEvent(
                        post_id="",
                        platform=platform.value,
                        error_message="Failed to publish post",
                        failure_type="publication_failed"
                    ))

            return results

        except Exception as e:
            self.logger.error(f"Failed to create and post: {e}")
            raise

    async def schedule_content(
        self,
        platforms: List[Platform],
        content: str,
        content_type: str,
        scheduled_time: datetime,
        tags: Optional[List[str]] = None,
        engagement_goals: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule content for future publishing."""
        try:
            post = SocialPost(
                platform=None,
                content=content,
                content_type=content_type,
                tags=tags or [],
                engagement_goals=engagement_goals or {}
            )

            schedule_id = await self.service.schedule_post(platforms, post, scheduled_time)

            await self.event_bus.publish(PostScheduledEvent(
                schedule_id=schedule_id,
                platform=",".join([p.value for p in platforms]),
                content_preview=content[:100],
                scheduled_time=scheduled_time
            ))

            self.logger.info(f"Content scheduled with ID: {schedule_id}")
            return schedule_id

        except Exception as e:
            self.logger.error(f"Failed to schedule content: {e}")
            raise

    async def monitor_brand_mentions(self) -> List[BrandMention]:
        """Monitor brand mentions across all configured platforms."""
        try:
            mentions = await self.service.get_mentions()

            for mention in mentions:
                await self.event_bus.publish(MentionReceivedEvent(
                    mention_id=f"{mention.platform.value}_{hash(mention.content)}",
                    platform=mention.platform.value,
                    author=mention.author,
                    content_preview=mention.content[:100],
                    timestamp=mention.timestamp
                ))

                # Process the mention for sentiment
                processed = await self.service.process_mention(mention)

                await self.event_bus.publish(MentionProcessedEvent(
                    mention_id=f"{mention.platform.value}_{hash(mention.content)}",
                    platform=mention.platform.value,
                    sentiment_score=processed['mention'].sentiment_score or 0.5,
                    requires_approval=processed['requires_approval'],
                    action_taken=processed['recommended_action']
                ))

            return mentions

        except Exception as e:
            self.logger.error(f"Failed to monitor mentions: {e}")
            raise

    async def get_platform_status(self) -> Dict[str, Any]:
        """Get status of all configured platforms."""
        try:
            platforms = self.service.get_registered_platforms()
            stats = await self.service.get_engagement_stats(platforms)

            status = {
                'overall_status': 'healthy',
                'platforms': {},
                'total_posts_today': 0,
                'total_engagement_today': 0
            }

            for platform in platforms:
                platform_stats = stats.get(platform, {})
                is_active = platform_stats.get('active', False)

                status['platforms'][platform.value] = {
                    'active': is_active,
                    'stats': platform_stats,
                    'configured': platform in self.platform_configs
                }

                if not is_active:
                    status['overall_status'] = 'degraded'

            return status

        except Exception as e:
            self.logger.error(f"Failed to get platform status: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        await self.service.cleanup()
        self.logger.info("Unified social client cleaned up")
