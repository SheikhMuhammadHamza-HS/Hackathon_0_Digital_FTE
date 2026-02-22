"""Base adapter classes for social media platforms."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import logging
from aiohttp import web

logger = logging.getLogger(__name__)


class SocialMediaAdapter(ABC):
    """Base class for all social media platform adapters."""

    def __init__(self, platform_name: str, config: Dict[str, Any]):
        """Initialize the adapter.

        Args:
            platform_name: Name of the social media platform
            config: Configuration dictionary with API credentials and settings
        """
        self.platform_name = platform_name
        self.config = config
        self.is_connected = False
        self.rate_limits = {}
        self._session = None
        self._webhook_server = None

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the social media platform.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        pass

    @abstractmethod
    async def create_post(self, content: str, media_urls: Optional[List[str]] = None,
                         **kwargs) -> Dict[str, Any]:
        """Create a new post on the platform.

        Args:
            content: Post content/text
            media_urls: Optional list of media URLs to attach
            **kwargs: Platform-specific parameters

        Returns:
            Post creation response with post_id, status, etc.
        """
        pass

    @abstractmethod
    async def schedule_post(self, content: str, scheduled_time: datetime,
                           media_urls: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Schedule a post for future publication.

        Args:
            content: Post content/text
            scheduled_time: When to publish the post
            media_urls: Optional list of media URLs
            **kwargs: Platform-specific parameters

        Returns:
            Scheduled post details
        """
        pass

    @abstractmethod
    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get post details and metrics.

        Args:
            post_id: Platform post ID

        Returns:
            Post details with metrics
        """
        pass

    @abstractmethod
    async def delete_post(self, post_id: str) -> Dict[str, Any]:
        """Delete a post.

        Args:
            post_id: Platform post ID

        Returns:
            Deletion confirmation
        """
        pass

    @abstractmethod
    async def search_mentions(self, keywords: List[str], since: datetime,
                            **kwargs) -> Dict[str, Any]:
        """Search for brand mentions.

        Args:
            keywords: List of keywords/hashtags to search for
            since: Search from this timestamp
            **kwargs: Platform-specific search parameters

        Returns:
            Mentions found with details
        """
        pass

    @abstractmethod
    async def reply_to_mention(self, mention_id: str, response_content: str,
                             **kwargs) -> Dict[str, Any]:
        """Reply to a mention/comment.

        Args:
            mention_id: Platform mention ID
            response_content: Response text
            **kwargs: Platform-specific parameters

        Returns:
            Reply confirmation
        """
        pass

    @abstractmethod
    async def get_rate_limit_status(self, endpoint: str = None) -> Dict[str, Any]:
        """Get current rate limit status.

        Args:
            endpoint: Specific endpoint to check (optional)

        Returns:
            Rate limit information
        """
        pass

    async def start_webhook_server(self, host: str = "localhost", port: int = 8080) -> None:
        """Start webhook server for real-time events.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        app = web.Application()
        app.router.add_post(f"/webhook/{self.platform_name}", self._handle_webhook)

        runner = web.AppRunner(app)
        await runner.setup()

        self._webhook_server = web.TCPSite(runner, host, port)
        await self._webhook_server.start()

        logger.info(f"Webhook server started for {self.platform_name} at {host}:{port}")

    async def stop_webhook_server(self) -> None:
        """Stop the webhook server."""
        if self._webhook_server:
            await self._webhook_server.stop()
            self._webhook_server = None
            logger.info(f"Webhook server stopped for {self.platform_name}")

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook requests.

        Args:
            request: Incoming webhook request

        Returns:
            Webhook response
        """
        try:
            payload = await request.json()
            event_data = self._parse_webhook_payload(payload)

            # Process the event (would emit to event bus in real implementation)
            await self._process_webhook_event(event_data)

            return web.json_response({"status": "received"})

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.json_response({"error": str(e)}, status=400)

    @abstractmethod
    def _parse_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse platform-specific webhook payload.

        Args:
            payload: Raw webhook payload

        Returns:
            Standardized event data
        """
        pass

    async def _process_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """Process webhook event.

        Args:
            event_data: Standardized event data
        """
        # In real implementation, this would emit events to the event bus
        logger.info(f"Processing webhook event: {event_data}")

    def _check_rate_limit(self, endpoint: str) -> bool:
        """Check if rate limit allows the request.

        Args:
            endpoint: API endpoint being called

        Returns:
            True if request can proceed
        """
        if endpoint not in self.rate_limits:
            return True

        limit_info = self.rate_limits[endpoint]
        current_time = datetime.utcnow()

        # Check if we're within the rate limit window
        if current_time < limit_info.get("reset_time", current_time):
            remaining = limit_info.get("remaining", 0)
            return remaining > 0

        return True

    def _update_rate_limit(self, endpoint: str, headers: Dict[str, Any]) -> None:
        """Update rate limit info from response headers.

        Args:
            endpoint: API endpoint
            headers: Response headers
        """
        # Common rate limit header names
        rate_limit_headers = {
            "x-rate-limit-limit": "limit",
            "x-rate-limit-remaining": "remaining",
            "x-rate-limit-reset": "reset_time"
        }

        limit_info = {}
        for header, key in rate_limit_headers.items():
            if header in headers:
                if key == "reset_time":
                    # Convert timestamp to datetime
                    limit_info[key] = datetime.utcfromtimestamp(int(headers[header]))
                else:
                    limit_info[key] = int(headers[header])

        if limit_info:
            self.rate_limits[endpoint] = limit_info

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    def _handle_api_error(self, error: Exception) -> Dict[str, Any]:
        """Handle API errors and return standardized error response.

        Args:
            error: Exception from API call

        Returns:
            Standardized error dictionary
        """
        error_message = str(error).lower()

        if "rate limit" in error_message or "429" in error_message:
            return {
                "error": "rate_limit_exceeded",
                "error_code": "RATE_LIMIT",
                "message": str(error),
                "action_required": "wait_and_retry",
                "retry_after": self.rate_limits.get("reset_time")
            }
        elif "auth" in error_message or "401" in error_message or "403" in error_message:
            return {
                "error": "authentication_failed",
                "error_code": "AUTH_ERROR",
                "message": str(error),
                "action_required": "renew_token"
            }
        elif "network" in error_message or "timeout" in error_message:
            return {
                "error": "network_error",
                "error_code": "NETWORK_ERROR",
                "message": str(error),
                "action_required": "retry"
            }
        elif "invalid" in error_message or "400" in error_message:
            return {
                "error": "validation_error",
                "error_code": "VALIDATION_ERROR",
                "message": str(error),
                "action_required": "fix_request"
            }
        else:
            return {
                "error": "unknown_error",
                "error_code": "UNKNOWN_ERROR",
                "message": str(error),
                "action_required": "investigate"
            }


class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(self, calls_per_window: int, window_seconds: int):
        """Initialize rate limiter.

        Args:
            calls_per_window: Number of calls allowed
            window_seconds: Time window in seconds
        """
        self.calls_per_window = calls_per_window
        self.window_seconds = window_seconds
        self.calls = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> tuple[bool, float]:
        """Acquire permission to make a call.

        Returns:
            Tuple of (allowed, wait_time)
        """
        async with self._lock:
            now = datetime.utcnow().timestamp()

            # Remove old calls outside the window
            self.calls = [call_time for call_time in self.calls
                         if now - call_time < self.window_seconds]

            if len(self.calls) >= self.calls_per_window:
                # Calculate wait time until oldest call expires
                oldest_call = min(self.calls)
                wait_time = self.window_seconds - (now - oldest_call)
                return False, wait_time

            self.calls.append(now)
            return True, 0

    def get_wait_time(self) -> float:
        """Get time to wait until next call is available.

        Returns:
            Seconds to wait
        """
        if not self.calls:
            return 0

        now = datetime.utcnow().timestamp()
        oldest_call = min(self.calls)
        wait_time = self.window_seconds - (now - oldest_call)
        return max(0, wait_time)


# Platform-specific rate limits
PLATFORM_RATE_LIMITS = {
    "twitter": {
        "standard": RateLimiter(300, 900),  # 300 calls per 15 minutes
        "post_create": RateLimiter(50, 1800),  # 50 posts per 30 minutes
    },
    "facebook": {
        "standard": RateLimiter(200, 3600),  # 200 calls per hour
        "post_create": RateLimiter(25, 3600),  # 25 posts per hour
    },
    "instagram": {
        "standard": RateLimiter(200, 3600),  # 200 calls per hour
        "post_create": RateLimiter(25, 86400),  # 25 posts per day
    },
    "linkedin": {
        "standard": RateLimiter(100, 3600),  # 100 calls per hour
        "post_create": RateLimiter(10, 3600),  # 10 posts per hour
    }
}
