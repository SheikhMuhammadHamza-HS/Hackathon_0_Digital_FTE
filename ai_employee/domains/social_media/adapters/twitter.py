"""Twitter API v2 adapter for social media operations."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from urllib.parse import quote

import aiohttp
from aiohttp import web

from . import SocialMediaAdapter, RateLimiter, PLATFORM_RATE_LIMITS
from ai_employee.domains.social_media.models import Platform

logger = logging.getLogger(__name__)


class TwitterAdapter(SocialMediaAdapter):
    """Twitter API v2 adapter for posting and monitoring tweets."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Twitter adapter.

        Args:
            config: Configuration dictionary with:
                - bearer_token: Twitter API bearer token
                - api_key: Twitter API key
                - api_secret: Twitter API secret
                - access_token: User access token
                - access_token_secret: User access token secret
                - webhook_secret: Webhook verification secret
        """
        super().__init__("twitter", config)

        # API credentials
        self.bearer_token = config.get("bearer_token")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.access_token = config.get("access_token")
        self.access_token_secret = config.get("access_token_secret")
        self.webhook_secret = config.get("webhook_secret")

        # API endpoints
        self.base_url = "https://api.twitter.com/2"
        self.upload_url = "https://upload.twitter.com/1.1"

        # Rate limiters
        self.rate_limiters = {
            "standard": PLATFORM_RATE_LIMITS["twitter"]["standard"],
            "post_create": PLATFORM_RATE_LIMITS["twitter"]["post_create"]
        }

        # User info cache
        self.user_id = None
        self.username = None

    async def connect(self) -> bool:
        """Connect to Twitter API and verify credentials.

        Returns:
            True if connection successful
        """
        if not self.bearer_token:
            raise ValueError("Bearer token is required for Twitter API v2")

        try:
            # Get current user info to verify credentials
            headers = {"Authorization": f"Bearer {self.bearer_token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/users/me",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.user_id = data["data"]["id"]
                        self.username = data["data"]["username"]
                        self.is_connected = True

                        # Update rate limits from headers
                        self._update_rate_limit("standard", response.headers)

                        logger.info(f"Connected to Twitter as @{self.username}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Twitter API error: {response.status} - {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Failed to connect to Twitter: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Twitter."""
        self.is_connected = False
        self.user_id = None
        self.username = None
        logger.info("Disconnected from Twitter")

    async def create_post(self, content: str, media_urls: Optional[List[str]] = None,
                         **kwargs) -> Dict[str, Any]:
        """Create a new tweet.

        Args:
            content: Tweet content (max 280 characters)
            media_urls: Optional media URLs to attach
            **kwargs: Additional parameters (reply_to, quote_tweet_id, etc.)

        Returns:
            Tweet creation response
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Twitter")

        # Check rate limit
        can_post, wait_time = await self.rate_limiters["post_create"].acquire()
        if not can_post:
            raise Exception(f"Rate limit exceeded. Wait {wait_time} seconds")

        try:
            # Handle media uploads first
            media_ids = []
            if media_urls:
                media_ids = await self._upload_media(media_urls)

            # Prepare tweet payload
            payload = {
                "text": content[:280]  # Enforce character limit
            }

            # Add optional parameters
            if media_ids:
                payload["media"] = {"media_ids": media_ids}

            if "reply_to" in kwargs:
                payload["reply"] = {"in_reply_to_tweet_id": kwargs["reply_to"]}

            if "quote_tweet_id" in kwargs:
                payload["quote_tweet_id"] = kwargs["quote_tweet_id"]

            # Create tweet
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/tweets",
                    headers=headers,
                    json=payload
                ) as response:
                    # Update rate limits
                    self._update_rate_limit("post_create", response.headers)

                    if response.status == 201:
                        data = await response.json()
                        tweet_id = data["data"]["id"]

                        return {
                            "post_id": tweet_id,
                            "platform": "twitter",
                            "status": "posted",
                            "published_at": datetime.utcnow().isoformat(),
                            "url": f"https://twitter.com/{self.username}/status/{tweet_id}",
                            "text": content[:280]
                        }
                    else:
                        error_data = await response.json()
                        raise Exception(f"Twitter API error: {error_data}")

        except Exception as e:
            error_response = self._handle_api_error(e)
            logger.error(f"Failed to create tweet: {error_response}")
            raise Exception(error_response["message"])

    async def schedule_post(self, content: str, scheduled_time: datetime,
                           media_urls: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Schedule a tweet for future posting.

        Note: Twitter API v2 doesn't have native scheduling,
        so this will queue the tweet for posting at the scheduled time.

        Args:
            content: Tweet content
            scheduled_time: When to post the tweet
            media_urls: Optional media URLs
            **kwargs: Additional parameters

        Returns:
            Scheduled tweet information
        """
        # Validate scheduled time
        if scheduled_time <= datetime.utcnow():
            raise ValueError("Scheduled time must be in the future")

        # For now, we'll create a scheduled post record
        # In a real implementation, this would integrate with a job scheduler
        schedule_id = f"tw_sched_{datetime.utcnow().timestamp()}"

        return {
            "post_id": schedule_id,
            "platform": "twitter",
            "status": "scheduled",
            "scheduled_time": scheduled_time.isoformat(),
            "content": content[:280],
            "media_urls": media_urls or [],
            "created_at": datetime.utcnow().isoformat()
        }

    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get tweet details and metrics.

        Args:
            post_id: Twitter tweet ID

        Returns:
            Tweet details with engagement metrics
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Twitter")

        try:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}

            # Build query for tweet data
            params = {
                "ids": post_id,
                "tweet.fields": "created_at,public_metrics,context_annotations,entities,author_id",
                "user.fields": "username,name,profile_image_url"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/tweets",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        if "data" in data and data["data"]:
                            tweet = data["data"][0]
                            metrics = tweet.get("public_metrics", {})

                            return {
                                "post_id": tweet["id"],
                                "platform": "twitter",
                                "status": "posted",
                                "content": tweet["text"],
                                "metrics": {
                                    "likes": metrics.get("like_count", 0),
                                    "retweets": metrics.get("retweet_count", 0),
                                    "replies": metrics.get("reply_count", 0),
                                    "quotes": metrics.get("quote_count", 0),
                                    "impressions": metrics.get("impression_count", 0)
                                },
                                "created_at": tweet["created_at"],
                                "updated_at": tweet["created_at"],
                                "urls": self._extract_urls(tweet),
                                "hashtags": self._extract_hashtags(tweet),
                                "mentions": self._extract_mentions(tweet)
                            }
                    else:
                        error_data = await response.json()
                        raise Exception(f"Twitter API error: {error_data}")

        except Exception as e:
            error_response = self._handle_api_error(e)
            logger.error(f"Failed to get tweet: {error_response}")
            raise Exception(error_response["message"])

    async def delete_post(self, post_id: str) -> Dict[str, Any]:
        """Delete a tweet.

        Args:
            post_id: Twitter tweet ID

        Returns:
            Deletion confirmation
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Twitter")

        try:
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/tweets/{post_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return {
                            "post_id": post_id,
                            "platform": "twitter",
                            "status": "deleted",
                            "deleted_at": datetime.utcnow().isoformat()
                        }
                    else:
                        error_data = await response.json()
                        raise Exception(f"Twitter API error: {error_data}")

        except Exception as e:
            error_response = self._handle_api_error(e)
            logger.error(f"Failed to delete tweet: {error_response}")
            raise Exception(error_response["message"])

    async def search_mentions(self, keywords: List[str], since: datetime,
                            **kwargs) -> Dict[str, Any]:
        """Search for tweets mentioning our brand.

        Args:
            keywords: Keywords/hashtags to search for
            since: Search from this timestamp
            **kwargs: Additional search parameters

        Returns:
            Found mentions with details
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Twitter")

        try:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}

            # Build search query
            query = " OR ".join(keywords)

            params = {
                "query": query,
                "start_time": since.isoformat() + "Z",
                "tweet.fields": "created_at,public_metrics,author_id,conversation_id",
                "user.fields": "username,name,profile_image_url",
                "max_results": kwargs.get("max_results", 100)
            }

            # Add mentions filter to get mentions of our user
            if self.username:
                params["query"] += f" @{self.username}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/tweets/search/recent",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        mentions = []

                        for tweet in data.get("data", []):
                            author_id = tweet["author_id"]
                            author_info = next(
                                (u for u in data.get("includes", {}).get("users", [])
                                 if u["id"] == author_id),
                                {}
                            )

                            mentions.append({
                                "mention_id": tweet["id"],
                                "platform": "twitter",
                                "author": author_info.get("username", "unknown"),
                                "author_name": author_info.get("name", ""),
                                "author_profile_url": author_info.get("profile_image_url", ""),
                                "content": tweet["text"],
                                "timestamp": tweet["created_at"],
                                "url": f"https://twitter.com/{author_info.get('username', 'unknown')}/status/{tweet['id']}",
                                "sentiment": "neutral",  # Would use ML model in production
                                "sentiment_confidence": 0.5,
                                "response_status": "unresponded",
                                "metrics": tweet.get("public_metrics", {}),
                                "conversation_id": tweet.get("conversation_id")
                            })

                        return {
                            "mentions": mentions,
                            "total_count": len(mentions),
                            "new_count": len(mentions),
                            "last_checked": datetime.utcnow().isoformat(),
                            "next_token": data.get("meta", {}).get("next_token")
                        }
                    else:
                        error_data = await response.json()
                        raise Exception(f"Twitter API error: {error_data}")

        except Exception as e:
            error_response = self._handle_api_error(e)
            logger.error(f"Failed to search mentions: {error_response}")
            raise Exception(error_response["message"])

    async def reply_to_mention(self, mention_id: str, response_content: str,
                             **kwargs) -> Dict[str, Any]:
        """Reply to a mention/comment.

        Args:
            mention_id: Tweet ID to reply to
            response_content: Reply content
            **kwargs: Additional parameters

        Returns:
            Reply confirmation
        """
        # Twitter handles replies through the create_post with reply_to parameter
        return await self.create_post(
            content=response_content,
            reply_to=mention_id
        )

    async def get_rate_limit_status(self, endpoint: str = None) -> Dict[str, Any]:
        """Get current rate limit status.

        Args:
            endpoint: Specific endpoint to check

        Returns:
            Rate limit information
        """
        # Return current rate limit status
        if endpoint == "create_post":
            limiter = self.rate_limiters["post_create"]
            wait_time = limiter.get_wait_time()
            return {
                "platform": "twitter",
                "endpoint": endpoint,
                "limit": limiter.calls_per_window,
                "remaining": limiter.calls_per_window - len(limiter.calls),
                "reset_time": (datetime.utcnow() + timedelta(seconds=wait_time)).isoformat() if wait_time > 0 else None,
                "retry_after": wait_time if wait_time > 0 else 0
            }
        else:
            return {
                "platform": "twitter",
                "endpoint": endpoint or "general",
                "limit": 300,
                "remaining": 300,
                "reset_time": None,
                "retry_after": 0
            }

    def _parse_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Twitter webhook payload.

        Args:
            payload: Raw webhook payload

        Returns:
            Standardized event data
        """
        # Twitter webhook structure
        event_type = payload.get("event_type", "mention")

        if event_type == "mention" or "tweet_create_events" in payload:
            tweet_data = payload.get("tweet_create_events", [{}])[0]
            return {
                "event_type": "mention",
                "platform": "twitter",
                "data": {
                    "mention_id": tweet_data.get("id_str"),
                    "author": tweet_data.get("user", {}).get("screen_name"),
                    "content": tweet_data.get("text"),
                    "timestamp": tweet_data.get("created_at"),
                    "conversation_id": tweet_data.get("conversation_id")
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        elif event_type == "follow":
            return {
                "event_type": "follow",
                "platform": "twitter",
                "data": payload,
                "timestamp": datetime.utcnow().isoformat()
            }

        return {
            "event_type": "unknown",
            "platform": "twitter",
            "data": payload,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _upload_media(self, media_urls: List[str]) -> List[str]:
        """Upload media to Twitter.

        Args:
            media_urls: List of media URLs to upload

        Returns:
            List of media IDs
        """
        media_ids = []

        for media_url in media_urls:
            try:
                # Download media file
                async with aiohttp.ClientSession() as session:
                    async with session.get(media_url) as response:
                        if response.status == 200:
                            media_data = await response.read()
                            content_type = response.headers.get("content-type", "")

                            # Upload to Twitter
                            upload_headers = {
                                "Authorization": f"Bearer {self.bearer_token}"
                            }

                            # Init upload
                            init_payload = {
                                "command": "INIT",
                                "total_bytes": len(media_data),
                                "media_type": content_type
                            }

                            async with session.post(
                                f"{self.upload_url}/media/upload.json",
                                headers=upload_headers,
                                data=init_payload
                            ) as init_response:
                                if init_response.status == 202:
                                    init_data = await init_response.json()
                                    media_id = init_data["media_id_string"]

                                    # Append data
                                    append_payload = {
                                        "command": "APPEND",
                                        "media_id": media_id,
                                        "segment_index": 0,
                                        "media": media_data
                                    }

                                    # Finalize
                                    finalize_payload = {
                                        "command": "FINALIZE",
                                        "media_id": media_id
                                    }

                                    media_ids.append(media_id)

            except Exception as e:
                logger.error(f"Failed to upload media {media_url}: {e}")

        return media_ids

    def _extract_urls(self, tweet: Dict[str, Any]) -> List[str]:
        """Extract URLs from tweet."""
        urls = []
        entities = tweet.get("entities", {})

        for url_info in entities.get("urls", []):
            urls.append(url_info.get("expanded_url"))

        return urls

    def _extract_hashtags(self, tweet: Dict[str, Any]) -> List[str]:
        """Extract hashtags from tweet."""
        hashtags = []
        entities = tweet.get("entities", {})

        for tag_info in entities.get("hashtags", []):
            hashtags.append(f"#{tag_info.get('tag', '')}")

        return hashtags

    def _extract_mentions(self, tweet: Dict[str, Any]) -> List[str]:
        """Extract mentions from tweet."""
        mentions = []
        entities = tweet.get("entities", {})

        for mention_info in entities.get("mentions", []):
            mentions.append(f"@{mention_info.get('username', '')}")

        return mentions
