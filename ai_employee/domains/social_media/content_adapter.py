"""Content adaptation for different social media platforms."""

import asyncio
import re
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from .models import SocialPost, Platform, ContentType

logger = logging.getLogger(__name__)


class AdaptationType(Enum):
    """Types of content adaptation."""
    CHARACTER_LIMIT = "character_limit"
    HASHTAG_OPTIMIZATION = "hashtag_optimization"
    MEDIA_SIZING = "media_sizing"
    LINK_FORMATTING = "link_formatting"
    MENTION_FORMATTING = "mention_formatting"


@dataclass
class PlatformConstraints:
    """Constraints for each platform."""

    platform: Platform
    max_chars: int
    recommended_hashtags: range
    supported_content_types: List[ContentType]
    media_specs: Dict[str, str]
    link_preview_support: bool
    mention_style: str  # e.g., "@handle" or "<@user>"


class ContentAdapter:
    """Adapts content for different social media platforms."""

    def __init__(self):
        """Initialize content adapter with platform constraints."""
        self.constraints: Dict[Platform, PlatformConstraints] = {
            Platform.TWITTER: PlatformConstraints(
                platform=Platform.TWITTER,
                max_chars=280,
                recommended_hashtags=range(1, 3),  # 1-2 hashtags
                supported_content_types=[ContentType.TEXT, ContentType.IMAGE, ContentType.LINK, ContentType.VIDEO],
                media_specs={
                    "image_max_size": "5MB",
                    "image_ratio": "16:9 or 1:1",
                    "video_max_size": "512MB",
                    "video_max_duration": "140 seconds"
                },
                link_preview_support=True,
                mention_style="@handle"
            ),
            Platform.FACEBOOK: PlatformConstraints(
                platform=Platform.FACEBOOK,
                max_chars=5000,
                recommended_hashtags=range(1, 6),  # 1-5 hashtags
                supported_content_types=[ContentType.TEXT, ContentType.IMAGE, ContentType.VIDEO, ContentType.LINK, ContentType.ARTICLE],
                media_specs={
                    "image_max_size": "10MB",
                    "image_ratio": "Flexible",
                    "video_max_size": "10GB",
                    "video_max_duration": "240 minutes"
                },
                link_preview_support=True,
                mention_style="@username"
            ),
            Platform.INSTAGRAM: PlatformConstraints(
                platform=Platform.INSTAGRAM,
                max_chars=2200,
                recommended_hashtags=range(5, 11),  # 5-10 hashtags
                supported_content_types=[ContentType.IMAGE, ContentType.VIDEO, ContentType.STORY, ContentType.REEL],
                media_specs={
                    "image_ratio": "1:1 or 4:5",
                    "image_format": "JPG or PNG",
                    "video_ratio": "16:9 to 4:5",
                    "video_max_size": "4GB",
                    "video_max_duration": "60 seconds"  # Reels
                },
                link_preview_support=False,  # Links only in bio for most accounts
                mention_style="@username"
            ),
            Platform.LINKEDIN: PlatformConstraints(
                platform=Platform.LINKEDIN,
                max_chars=3000,
                recommended_hashtags=range(3, 8),  # 3-7 hashtags
                supported_content_types=[ContentType.TEXT, ContentType.IMAGE, ContentType.VIDEO, ContentType.LINK, ContentType.ARTICLE],
                media_specs={
                    "image_max_size": "10MB",
                    "image_ratio": "1.91:1 to 1:1",
                    "video_max_size": "5GB",
                    "video_max_duration": "10 minutes"
                },
                link_preview_support=True,
                mention_style="@First Last"
            )
        }

    async def adapt_for_platform(
        self,
        post: SocialPost,
        platform: Platform,
        preserve_original: bool = False
    ) -> SocialPost:
        """
        Adapt content for a specific platform.

        Args:
            post: Original social post
            platform: Target platform
            preserve_original: If True, return new post without modifying original

        Returns:
            Adapted social post for the platform
        """
        if preserve_original:
            # Create a copy
            adapted_post = SocialPost(
                platform=post.platform,
                content=post.content,
                content_type=post.content_type,
                media_urls=post.media_urls[:],
                tags=post.tags[:],
                engagement_goals=post.engagement_goals
            )
        else:
            adapted_post = post

        # Get platform constraints
        constraints = self.constraints.get(platform)
        if not constraints:
            logger.warning(f"No constraints defined for {platform.value}")
            return adapted_post

        # Apply adaptations based on platform
        adaptations_applied = []

        # 1. Character limit adaptation
        if len(adapted_post.content) > constraints.max_chars:
            original_length = len(adapted_post.content)
            adapted_post.content = self._truncate_content(
                adapted_post.content,
                constraints.max_chars,
                platform=platform
            )
            adaptations_applied.append(
                f"Truncated content from {original_length} to {len(adapted_post.content)} characters"
            )

        # 2. Hashtag optimization
        if adapted_post.tags:
            optimized_tags = self._optimize_hashtags(
                adapted_post.tags,
                platform=platform,
                max_tags=constraints.recommended_hashtags.stop - 1
            )
            if len(optimized_tags) != len(adapted_post.tags):
                adapted_post.tags = optimized_tags
                adaptations_applied.append(
                    f"Optimized hashtags: {len(adapted_post.tags)} tags"
                )

        # 3. Link formatting (if supported)
        if constraints.link_preview_support and "http" in adapted_post.content:
            adapted_post.content = self._format_links(
                adapted_post.content,
                platform=platform
            )
            adaptations_applied.append("Formatted links for platform")

        # 4. Mention formatting
        adapted_post.content = self._format_mentions(
            adapted_post.content,
            mention_style=constraints.mention_style
        )
        adaptations_applied.append("Formatted mentions")

        # 5. Content type validation
        if adapted_post.content_type not in constraints.supported_content_types:
            # Try to find a compatible content type
            new_type = self._find_compatible_content_type(
                adapted_post.content_type,
                constraints.supported_content_types
            )
            if new_type:
                old_type = adapted_post.content_type
                adapted_post.content_type = new_type
                adaptations_applied.append(
                    f"Changed content type from {old_type.value} to {new_type.value}"
                )
            else:
                logger.warning(
                    f"Content type {adapted_post.content_type.value} not supported on {platform.value}"
                )

        # Log adaptations
        if adaptations_applied:
            logger.info(
                f"Content adapted for {platform.value}: {', '.join(adaptations_applied)}"
            )

        return adapted_post

    def _truncate_content(self, content: str, max_chars: int, platform: Platform) -> str:
        """Truncate content to fit platform limits."""
        if len(content) <= max_chars:
            return content

        # For Twitter, keep hashtags and mentions
        if platform == Platform.TWITTER:
            # Extract hashtags and mentions
            hashtags = re.findall(r'#\w+', content)
            mentions = re.findall(r'@\w+', content)

            # Available space for main content
            reserved_space = len(' '.join(hashtags + mentions))
            available = max_chars - reserved_space - 10  # 10 char buffer

            if available > 0:
                # Truncate main content
                main_content = re.sub(r'[#@]\w+', '', content).strip()
                truncated_main = main_content[:available - 3].strip() + "..."
                return f"{truncated_main} {' '.join(hashtags + mentions)}".strip()

        # Default truncation strategy
        return content[:max_chars - 3].strip() + "..."

    def _optimize_hashtags(self, tags: List[str], platform: Platform, max_tags: int) -> List[str]:
        """Optimize hashtags for platform."""
        if not tags:
            return tags

        constraints = self.constraints[platform]

        # For Instagram, allow more hashtags
        if platform == Platform.INSTAGRAM:
            instagram_max = constraints.recommended_hashtags.stop - 1
            if len(tags) > instagram_max:
                # Keep most relevant hashtags (simplified: just take first ones)
                return tags[:instagram_max]
            return tags

        # For other platforms, be more conservative
        if len(tags) > max_tags:
            return tags[:max_tags]

        return tags

    def _format_links(self, content: str, platform: Platform) -> str:
        """Format links for platform compatibility."""
        # Basic URL cleanup
        content = re.sub(
            r'https?://(www\.)?',
            '',
            content
        )

        return content

    def _format_mentions(self, content: str, mention_style: str) -> str:
        """Format mentions according to platform style."""
        # Standardize mentions to platform style
        # This is a simplified version
        if mention_style == "@First Last":
            # LinkedIn style: ensure proper spacing
            content = re.sub(r'@([a-zA-Z0-9_]+)', r'@\1', content)
        elif mention_style == "@handle":
            # Twitter style: lowercase mentions
            content = re.sub(r'@([A-Za-z0-9_]+)', lambda m: f"@{m.group(1).lower()}", content)

        return content

    def _find_compatible_content_type(
        self,
        original_type: ContentType,
        supported_types: List[ContentType]
    ) -> Optional[ContentType]:
        """Find a compatible content type for the platform."""
        # Priority order for fallback
        priority_order = [
            ContentType.TEXT,
            ContentType.LINK,
            ContentType.IMAGE,
            ContentType.VIDEO
        ]

        for content_type in priority_order:
            if content_type in supported_types:
                return content_type

        return None

    async def adapt_bulk(
        self,
        post: SocialPost,
        platforms: List[Platform]
    ) -> Dict[Platform, SocialPost]:
        """
        Adapt content for multiple platforms.

        Args:
            post: Original social post
            platforms: List of target platforms

        Returns:
            Dictionary mapping platforms to adapted posts
        """
        tasks = []
        for platform in platforms:
            # Create a copy for each platform
            post_copy = SocialPost(
                id=post.id if hasattr(post, 'id') else None,
                platform=post.platform,
                content=post.content,
                content_type=post.content_type,
                media_urls=post.media_urls[:],
                tags=post.tags[:],
                engagement_goals=post.engagement_goals
            )
            task = self.adapt_for_platform(post_copy, platform, preserve_original=True)
            tasks.append((platform, task))

        results = {}
        for platform, task in tasks:
            results[platform] = await task

        return results

    def get_platform_constraints(self, platform: Platform) -> Optional[PlatformConstraints]:
        """Get constraints for a specific platform."""
        return self.constraints.get(platform)

    def validate_content(
        self,
        post: SocialPost,
        platform: Platform
    ) -> Tuple[bool, List[str]]:
        """
        Validate content against platform constraints.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        constraints = self.constraints.get(platform)
        if not constraints:
            return False, ["No constraints defined for platform"]

        issues = []

        # Check character limit
        if len(post.content) > constraints.max_chars:
            issues.append(
                f"Content exceeds {constraints.max_chars} character limit "
                f"by {len(post.content) - constraints.max_chars} characters"
            )

        # Check content type
        if post.content_type not in constraints.supported_content_types:
            issues.append(
                f"Content type '{post.content_type.value}' not supported. "
                f"Supported: {[ct.value for ct in constraints.supported_content_types]}"
            )

        # Check hashtag count
        if len(post.tags) > constraints.recommended_hashtags.stop:
            issues.append(
                f"Too many hashtags ({len(post.tags)}). "
                f"Recommended: {constraints.recommended_hashtags.start}-{constraints.recommended_hashtags.stop - 1}"
            )

        # Check links (if not supported)
        if not constraints.link_preview_support and "http" in post.content:
            issues.append("Links not supported on this platform")

        return len(issues) == 0, issues