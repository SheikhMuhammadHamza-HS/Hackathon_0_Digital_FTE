"""Advanced rate limiting for social media platforms."""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from .models import Platform

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration per platform."""

    # Platform identifier
    platform: Platform

    # Requests per time window
    requests_per_window: int
    window_seconds: int

    # Burst allowance (temporary increase)
    burst_allowance: int = 0

    # Retry configuration
    retry_after_header: str = "Retry-After"
    max_retries: int = 3

    # Cooldown periods for rate limit violations
    cooldown_seconds: int = 300  # 5 minutes default

    def __post_init__(self):
        """Validate configuration."""
        if self.requests_per_window <= 0:
            raise ValueError("requests_per_window must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class UsageBucket:
    """Track API usage within a time window."""

    start_time: float
    request_count: int = 0
    platform: Platform = None  # type: ignore

    def is_expired(self, window_seconds: int) -> bool:
        """Check if this bucket is expired."""
        return time.time() - self.start_time > window_seconds

    def add_request(self) -> None:
        """Increment request count."""
        self.request_count += 1

    def get_wait_time(self, window_seconds: int) -> float:
        """Get remaining time in window."""
        elapsed = time.time() - self.start_time
        return max(0, window_seconds - elapsed)


class RateLimiter:
    """Advanced rate limiter for social media platforms."""

    def __init__(self):
        """Initialize rate limiter."""
        # Platform-specific configurations
        self.configs: Dict[Platform, RateLimitConfig] = {}

        # Usage tracking per platform
        self.usage_history: Dict[Platform, List[UsageBucket]] = {}

        # Current bucket per platform
        self.current_buckets: Dict[Platform, UsageBucket] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

        # Cooldown tracking for rate limit violations
        self.cooldown_until: Dict[Platform, float] = {}

        # Platform-specific rate limits
        self._setup_default_limits()

    def _setup_default_limits(self) -> None:
        """Set up default rate limits for each platform."""
        # Twitter API limits (v2)
        self.set_config(RateLimitConfig(
            platform=Platform.TWITTER,
            requests_per_window=300,  # 300 per 15 minutes for posting
            window_seconds=900,  # 15 minutes
            burst_allowance=50,
            cooldown_seconds=900
        ))

        # Facebook API limits
        self.set_config(RateLimitConfig(
            platform=Platform.FACEBOOK,
            requests_per_window=200,  # 200 calls per user per hour
            window_seconds=3600,  # 1 hour
            burst_allowance=100,
            cooldown_seconds=600
        ))

        # Instagram API limits (via Facebook)
        self.set_config(RateLimitConfig(
            platform=Platform.INSTAGRAM,
            requests_per_window=200,  # Similar to Facebook
            window_seconds=3600,
            burst_allowance=50,
            cooldown_seconds=600
        ))

        # LinkedIn API limits
        self.set_config(RateLimitConfig(
            platform=Platform.LINKEDIN,
            requests_per_window=100,  # 100 requests per user per day
            window_seconds=86400,  # 24 hours
            burst_allowance=10,
            cooldown_seconds=3600
        ))

    def set_config(self, config: RateLimitConfig) -> None:
        """Set or update rate limit configuration for a platform."""
        self.configs[config.platform] = config
        if config.platform not in self.usage_history:
            self.usage_history[config.platform] = []

    async def check_limit(self, platform: Platform) -> Tuple[bool, Optional[str]]:
        """
        Check if a request can be made for the given platform.

        Returns:
            Tuple of (can_proceed, error_message)
        """
        async with self._lock:
            # Check if platform is in cooldown
            if platform in self.cooldown_until:
                if time.time() < self.cooldown_until[platform]:
                    remaining = self.cooldown_until[platform] - time.time()
                    return False, f"Platform {platform.value} is in cooldown for {remaining:.1f} seconds"
                else:
                    del self.cooldown_until[platform]

            # Get or create current bucket
            if platform not in self.current_buckets or self.current_buckets[platform].is_expired(
                self.configs[platform].window_seconds
            ):
                # Create new bucket
                self.current_buckets[platform] = UsageBucket(
                    start_time=time.time(),
                    platform=platform
                )
                # Clean up old buckets
                await self._cleanup_old_buckets(platform)

            bucket = self.current_buckets[platform]
            config = self.configs[platform]

            # Check if we're within rate limits
            total_requests = bucket.request_count

            # Add up requests from recent buckets in the same window
            cutoff_time = time.time() - config.window_seconds
            for hist_bucket in self.usage_history[platform]:
                if hist_bucket.start_time > cutoff_time:
                    total_requests += hist_bucket.request_count

            # Check against limit with burst allowance
            effective_limit = config.requests_per_window + config.burst_allowance
            if total_requests >= effective_limit:
                # Calculate wait time
                wait_time = bucket.get_wait_time(config.window_seconds)
                return False, (
                    f"Rate limit exceeded for {platform.value}. "
                    f"Limit: {config.requests_per_window} requests per {config.window_seconds}s. "
                    f"Try again in {wait_time:.1f} seconds"
                )

            return True, None

    async def record_request(self, platform: Platform) -> None:
        """Record a successful request for rate limiting purposes."""
        async with self._lock:
            if platform not in self.current_buckets:
                self.current_buckets[platform] = UsageBucket(
                    start_time=time.time(),
                    platform=platform
                )

            self.current_buckets[platform].add_request()

    async def handle_rate_limit_error(self, platform: Platform, retry_after: Optional[int] = None) -> None:
        """
        Handle rate limit error from platform API.

        Args:
            platform: Platform that returned rate limit error
            retry_after: Seconds to wait (from API response)
        """
        config = self.configs.get(platform)
        if not config:
            return

        # Start cooldown period
        cooldown_duration = retry_after if retry_after else config.cooldown_seconds
        self.cooldown_until[platform] = time.time() + cooldown_duration

        logger.warning(
            f"Rate limit hit for {platform.value}. "
            f"Cooldown period: {cooldown_duration}s"
        )

    async def _cleanup_old_buckets(self, platform: Platform) -> None:
        """Clean up expired usage buckets."""
        if platform not in self.usage_history:
            return

        config = self.configs[platform]
        cutoff_time = time.time() - config.window_seconds

        # Move current bucket to history if it exists
        if platform in self.current_buckets:
            current_bucket = self.current_buckets[platform]
            if current_bucket.start_time < cutoff_time:
                self.usage_history[platform].append(current_bucket)
                del self.current_buckets[platform]

        # Clean up old history buckets
        self.usage_history[platform] = [
            bucket for bucket in self.usage_history[platform]
            if bucket.start_time > cutoff_time
        ]

    def get_usage_stats(self, platform: Platform) -> Dict[str, Any]:
        """Get usage statistics for a platform."""
        if platform not in self.configs:
            return {"error": "No configuration found"}

        config = self.configs[platform]
        cutoff_time = time.time() - config.window_seconds

        # Count total requests in current window
        total_requests = 0
        current_bucket_reqs = 0

        if platform in self.current_buckets:
            current_bucket = self.current_buckets[platform]
            if not current_bucket.is_expired(config.window_seconds):
                total_requests += current_bucket.request_count
                current_bucket_reqs = current_bucket.request_count

        # Add recent history
        recent_history = []
        for bucket in self.usage_history.get(platform, []):
            if bucket.start_time > cutoff_time:
                total_requests += bucket.request_count
                recent_history.append({
                    "start_time": bucket.start_time,
                    "requests": bucket.request_count
                })

        # Check if in cooldown
        in_cooldown = False
        cooldown_remaining = 0
        if platform in self.cooldown_until:
            if time.time() < self.cooldown_until[platform]:
                in_cooldown = True
                cooldown_remaining = self.cooldown_until[platform] - time.time()

        return {
            "platform": platform.value,
            "requests_in_window": total_requests,
            "window_limit": config.requests_per_window,
            "window_seconds": config.window_seconds,
            "current_bucket_requests": current_bucket_reqs,
            "recent_buckets": recent_history,
            "in_cooldown": in_cooldown,
            "cooldown_remaining": round(cooldown_remaining, 1) if cooldown_remaining > 0 else 0,
            "remaining_capacity": max(0, config.requests_per_window - total_requests)
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get usage statistics for all platforms."""
        return {
            platform.value: self.get_usage_stats(platform)
            for platform in self.configs.keys()
        }


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on platform responses."""

    def __init__(self):
        """Initialize adaptive rate limiter."""
        super().__init__()
        self.success_history: Dict[Platform, List[float]] = {}
        self.error_history: Dict[Platform, List[Tuple[float, str]]] = {}

    async def record_success(self, platform: Platform, response_time: float) -> None:
        """Record successful request for adaptive learning."""
        if platform not in self.success_history:
            self.success_history[platform] = []

        self.success_history[platform].append(response_time)

        # Keep only last 100 successes
        if len(self.success_history[platform]) > 100:
            self.success_history[platform] = self.success_history[platform][-100:]

    async def record_error(self, platform: Platform, error: str) -> None:
        """Record failed request for adaptive learning."""
        if platform not in self.error_history:
            self.error_history[platform] = []

        self.error_history[platform].append((time.time(), error))

        # Keep only last 50 errors
        if len(self.error_history[platform]) > 50:
            self.error_history[platform] = self.error_history[platform][-50:]

    async def get_performance_stats(self, platform: Platform) -> Dict[str, Any]:
        """Get performance statistics for adaptive adjustments."""
        stats = {
            "platform": platform.value,
            "success_count": 0,
            "error_count": 0,
            "avg_response_time": 0,
            "error_rate": 0
        }

        if platform in self.success_history:
            success_times = self.success_history[platform]
            stats["success_count"] = len(success_times)
            if success_times:
                stats["avg_response_time"] = sum(success_times) / len(success_times)

        if platform in self.error_history:
            # Filter errors in the last hour
            cutoff = time.time() - 3600
            recent_errors = [e for e in self.error_history[platform] if e[0] > cutoff]
            stats["error_count"] = len(recent_errors)

            # Calculate error rate
            total_attempts = stats["success_count"] + stats["error_count"]
            if total_attempts > 0:
                stats["error_rate"] = stats["error_count"] / total_attempts

        return stats
