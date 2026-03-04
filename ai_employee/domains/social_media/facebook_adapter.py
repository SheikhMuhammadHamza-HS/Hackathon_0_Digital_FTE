"""Facebook platform adapter."""

import asyncio
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base_adapter import SocialMediaAdapter
from .models import SocialPost, BrandMention, Platform
import logging

logger = logging.getLogger(__name__)


class FacebookAdapter(SocialMediaAdapter):
    """Facebook platform adapter implementation using Meta Graph API."""

    def __init__(self):
        """Initialize Facebook adapter."""
        super().__init__(Platform.FACEBOOK)
        self._access_token = None
        self._page_id = None
        self._base_url = "https://graph.facebook.com/v21.0"

    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with Facebook API."""
        try:
            self._access_token = credentials.get('access_token')
            self._page_id = credentials.get('page_id')

            if not all([self._access_token, self._page_id]):
                logger.error("Missing required Facebook credentials (access_token or page_id)")
                return False

            # Verify token by fetching page info
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/{self._page_id}",
                    params={"access_token": self._access_token}
                )
                if response.status_code == 200:
                    logger.info("Facebook adapter authenticated successfully")
                    return True
                else:
                    logger.error(f"Facebook authentication failed: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Facebook authentication failed: {e}")
            return False

    async def post_content(self, post: SocialPost) -> str:
        """Post content to Facebook Page feed."""
        try:
            if not self.supports_content_type(post.content_type):
                raise ValueError(f"Unsupported content type: {post.content_type}")

            async with httpx.AsyncClient() as client:
                if post.content_type == "image":
                    media_url = getattr(post, 'media_url', None)
                    if not media_url:
                        endpoint = f"{self._base_url}/{self._page_id}/feed"
                        data = {"message": post.content, "access_token": self._access_token}
                    else:
                        endpoint = f"{self._base_url}/{self._page_id}/photos"
                        data = {"url": media_url, "caption": post.content, "access_token": self._access_token}
                else:
                    endpoint = f"{self._base_url}/{self._page_id}/feed"
                    data = {"message": post.content, "access_token": self._access_token}

                response = await client.post(endpoint, data=data)
                response_data = response.json()

                if response.status_code in [200, 201]:
                    post_id = response_data.get("id") or response_data.get("post_id")
                    logger.info(f"Posted to Facebook with ID: {post_id}")
                    return str(post_id)
                else:
                    logger.error(f"Failed to post to Facebook: {response.text}")
                    raise Exception(f"Facebook API error: {response_data.get('error', {}).get('message', response.text)}")

        except Exception as e:
            logger.error(f"Error posting to Facebook: {e}")
            raise

    async def get_post(self, post_id: str) -> Optional[SocialPost]:
        """Retrieve a Facebook post by ID."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/{post_id}",
                    params={"fields": "message,created_time,status_type", "access_token": self._access_token}
                )
                if response.status_code == 200:
                    data = response.json()
                    return SocialPost(
                        platform=Platform.FACEBOOK,
                        content=data.get("message", ""),
                        content_type="text",
                        external_id=post_id
                    )
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve Facebook post: {e}")
            return None

    async def delete_post(self, post_id: str) -> bool:
        """Delete a Facebook post by ID."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self._base_url}/{post_id}",
                    params={"access_token": self._access_token}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete Facebook post: {e}")
            return False

    async def get_mentions(self, since: Optional[datetime] = None) -> List[BrandMention]:
        """Get brand mentions from Facebook."""
        try:
            mentions = []
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/{self._page_id}/tagged",
                    params={"access_token": self._access_token}
                )
                if response.status_code == 200:
                    data = response.json().get("data", [])
                    for item in data:
                        mentions.append(BrandMention(
                            platform=Platform.FACEBOOK,
                            content=item.get("message", ""),
                            author=item.get("from", {}).get("name", "Unknown"),
                            timestamp=datetime.now(),
                            engagement_score=1.0
                        ))
            return mentions
        except Exception as e:
            logger.error(f"Failed to fetch Facebook mentions: {e}")
            return []

    async def get_engagement_stats(self, post_id: str) -> Dict[str, Any]:
        """Get engagement statistics for a Facebook post."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/{post_id}",
                    params={
                        "fields": "reactions.summary(true),comments.summary(true),shares",
                        "access_token": self._access_token
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'likes': data.get('reactions', {}).get('summary', {}).get('total_count', 0),
                        'comments': data.get('comments', {}).get('summary', {}).get('total_count', 0),
                        'shares': data.get('shares', {}).get('count', 0)
                    }
            return {}
        except Exception as e:
            logger.error(f"Failed to get Facebook engagement stats: {e}")
            return {}

    def supports_content_type(self, content_type: str) -> bool:
        """Check if Facebook supports the content type."""
        supported_types = ['text', 'image', 'video', 'link']
        return content_type in supported_types


class InstagramAdapter(SocialMediaAdapter):
    """Instagram platform adapter implementation using Meta Graph API."""

    def __init__(self):
        """Initialize Instagram adapter."""
        super().__init__(Platform.INSTAGRAM)
        self._access_token = None
        self._ig_user_id = None
        self._base_url = "https://graph.facebook.com/v21.0"

    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with Instagram API."""
        try:
            self._access_token = credentials.get('access_token')
            self._ig_user_id = credentials.get('instagram_user_id')

            if not all([self._access_token, self._ig_user_id]):
                logger.error("Missing required Instagram credentials")
                return False

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/{self._ig_user_id}",
                    params={"fields": "username", "access_token": self._access_token}
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Instagram authentication failed: {e}")
            return False

    async def post_content(self, post: SocialPost) -> str:
        """Post content to Instagram."""
        try:
            if not self.supports_content_type(post.content_type):
                raise ValueError(f"Instagram requires visual content (image/video)")

            media_url = getattr(post, 'media_url', None)
            if not media_url:
                raise ValueError("Instagram posting requires a media_url")

            async with httpx.AsyncClient() as client:
                # 1. Create Media Container
                container_response = await client.post(
                    f"{self._base_url}/{self._ig_user_id}/media",
                    data={
                        "image_url": media_url if post.content_type == "image" else None,
                        "video_url": media_url if post.content_type == "video" else None,
                        "caption": post.content,
                        "access_token": self._access_token
                    }
                )
                container_id = container_response.json().get("id")

                if not container_id:
                    raise Exception(f"Failed to create Instagram media container: {container_response.text}")

                # 2. Publish Media
                publish_response = await client.post(
                    f"{self._base_url}/{self._ig_user_id}/media_publish",
                    data={
                        "creation_id": container_id,
                        "access_token": self._access_token
                    }
                )
                post_id = publish_response.json().get("id")

                if post_id:
                    logger.info(f"Posted to Instagram with ID: {post_id}")
                    return str(post_id)
                else:
                    raise Exception(f"Failed to publish Instagram media: {publish_response.text}")

        except Exception as e:
            logger.error(f"Error posting to Instagram: {e}")
            raise

    async def get_post(self, post_id: str) -> Optional[SocialPost]:
        """Retrieve an Instagram post by ID."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/{post_id}",
                    params={"fields": "caption,media_type,timestamp", "access_token": self._access_token}
                )
                if response.status_code == 200:
                    data = response.json()
                    return SocialPost(
                        platform=Platform.INSTAGRAM,
                        content=data.get("caption", ""),
                        content_type="image",
                        external_id=post_id
                    )
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve Instagram post: {e}")
            return None

    async def delete_post(self, post_id: str) -> bool:
        """Delete an Instagram post."""
        return False

    async def get_mentions(self, since: Optional[datetime] = None) -> List[BrandMention]:
        """Get Instagram mentions."""
        return []

    async def get_engagement_stats(self, post_id: str) -> Dict[str, Any]:
        """Get engagement statistics for an Instagram post."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/{post_id}",
                    params={"fields": "like_count,comments_count", "access_token": self._access_token}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'likes': data.get('like_count', 0),
                        'comments': data.get('comments_count', 0)
                    }
            return {}
        except Exception as e:
            logger.error(f"Failed to get Instagram engagement stats: {e}")
            return {}

    def supports_content_type(self, content_type: str) -> bool:
        """Check if Instagram supports the content type."""
        return content_type in ['image', 'video']
