"""
Circuit breaker pattern implementation for AI Employee system.

Provides fault tolerance by preventing cascade failures when external
services are experiencing issues.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import functools
import weakref

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail immediately
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: float = 60.0      # Seconds to wait before trying again
    expected_exception: type = Exception  # Exception type that counts as failure
    success_threshold: int = 2          # Success count to close circuit in half-open
    timeout: float = 30.0               # Call timeout in seconds
    max_retries: int = 3                # Maximum retry attempts
    backoff_factor: float = 2.0         # Exponential backoff factor


@dataclass
class CallResult:
    """Result of a circuit breaker protected call."""
    success: bool
    result: Any = None
    exception: Optional[Exception] = None
    duration: float = 0.0
    retries: int = 0
    circuit_state: CircuitState = CircuitState.CLOSED


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker errors."""
    pass


class CircuitOpenError(CircuitBreakerError):
    """Raised when circuit is open and calls are blocked."""
    pass


class CallTimeoutError(CircuitBreakerError):
    """Raised when call times out."""
    pass


class MaxRetriesExceededError(CircuitBreakerError):
    """Raised when maximum retries are exceeded."""
    pass


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0
    circuit_opens: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name for identification
            config: Configuration options
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._success_count = 0
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == CircuitState.OPEN

    @property
    def can_execute(self) -> bool:
        """Check if calls can be executed."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    return True
            return False

        # HALF_OPEN state allows limited calls
        return True

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: Various circuit breaker errors
        """
        async with self._lock:
            if not self.can_execute:
                self._stats.total_calls += 1
                raise CircuitOpenError(f"Circuit '{self.name}' is open")

            # Transition to HALF_OPEN if we were OPEN and timeout passed
            if self._state == CircuitState.OPEN and self._last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info(f"Circuit '{self.name}' transitioning to HALF_OPEN")

        # Execute the call with retries
        result = await self._execute_with_retry(func, *args, **kwargs)

        # Update statistics
        async with self._lock:
            self._stats.total_calls += 1
            if result.success:
                self._handle_success()
            else:
                self._handle_failure(result.exception)

        return result.result if result.success else result.exception

    async def _execute_with_retry(self, func: Callable, *args, **kwargs) -> CallResult:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Call result
        """
        last_exception = None
        start_time = time.time()

        for attempt in range(self.config.max_retries + 1):
            try:
                # Execute with timeout
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
                else:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs),
                        timeout=self.config.timeout
                    )

                duration = time.time() - start_time
                return CallResult(
                    success=True,
                    result=result,
                    duration=duration,
                    retries=attempt,
                    circuit_state=self._state
                )

            except asyncio.TimeoutError as e:
                last_exception = CallTimeoutError(f"Call to {func.__name__} timed out after {self.config.timeout}s")
                logger.warning(f"Circuit '{self.name}': Call timeout (attempt {attempt + 1})")

            except Exception as e:
                last_exception = e
                if isinstance(e, self.config.expected_exception):
                    logger.warning(f"Circuit '{self.name}': Expected exception (attempt {attempt + 1}): {e}")
                else:
                    logger.error(f"Circuit '{self.name}': Unexpected exception (attempt {attempt + 1}): {e}")

            # Backoff before retry
            if attempt < self.config.max_retries:
                backoff_time = self.config.backoff_factor ** attempt
                await asyncio.sleep(backoff_time)

        duration = time.time() - start_time
        return CallResult(
            success=False,
            exception=last_exception,
            duration=duration,
            retries=self.config.max_retries,
            circuit_state=self._state
        )

    def _handle_success(self) -> None:
        """Handle successful call."""
        self._stats.successful_calls += 1
        self._stats.last_success_time = datetime.now(timezone.utc)
        self._stats.consecutive_failures = 0
        self._stats.consecutive_successes += 1

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._stats.circuit_opens = 0  # Reset counter
                logger.info(f"Circuit '{self.name}' closed after {self._success_count} successful calls")

    def _handle_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        self._stats.failed_calls += 1
        self._stats.last_failure_time = datetime.now(timezone.utc)
        self._stats.consecutive_failures += 1
        self._stats.consecutive_successes = 0

        if isinstance(exception, self.config.expected_exception):
            self._failure_count += 1

            # Check if we should open the circuit
            if (self._state == CircuitState.CLOSED and
                self._failure_count >= self.config.failure_threshold):
                self._state = CircuitState.OPEN
                self._stats.circuit_opens += 1
                logger.error(f"Circuit '{self.name}' opened after {self._failure_count} failures")

            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._stats.circuit_opens += 1
                logger.error(f"Circuit '{self.name}' re-opened from HALF_OPEN state")

    def force_open(self) -> None:
        """Force the circuit to open."""
        self._state = CircuitState.OPEN
        self._last_failure_time = datetime.now(timezone.utc)
        logger.warning(f"Circuit '{self.name}' forced open")

    def force_close(self) -> None:
        """Force the circuit to close."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info(f"Circuit '{self.name}' forced closed")

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._stats = CircuitBreakerStats()
        logger.info(f"Circuit '{self.name}' reset")

    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics.

        Returns:
            Current statistics
        """
        self._stats.current_state = self._state
        self._stats.consecutive_failures = self._failure_count if self._state == CircuitState.OPEN else 0
        self._stats.consecutive_successes = self._success_count if self._state == CircuitState.HALF_OPEN else 0
        return self._stats


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        """Initialize registry."""
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker.

        Args:
            name: Circuit breaker name
            config: Configuration for new circuit breaker

        Returns:
            Circuit breaker instance
        """
        async with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(name, config)
                logger.info(f"Created circuit breaker '{name}'")
            return self._circuit_breakers[name]

    async def remove_circuit_breaker(self, name: str) -> None:
        """Remove a circuit breaker.

        Args:
            name: Circuit breaker name
        """
        async with self._lock:
            if name in self._circuit_breakers:
                del self._circuit_breakers[name]
                logger.info(f"Removed circuit breaker '{name}'")

    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers.

        Returns:
            Dictionary of circuit breaker statistics
        """
        return {name: cb.get_stats() for name, cb in self._circuit_breakers.items()}

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        async with self._lock:
            for cb in self._circuit_breakers.values():
                cb.reset()
        logger.info("All circuit breakers reset")

    async def close_all(self) -> None:
        """Force all circuit breakers to closed state."""
        async with self._lock:
            for cb in self._circuit_breakers.values():
                cb.force_close()
        logger.info("All circuit breakers forced closed")


# Global registry instance
circuit_registry = CircuitBreakerRegistry()


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type = Exception,
    success_threshold: int = 2,
    timeout: float = 30.0,
    max_retries: int = 3,
    backoff_factor: float = 2.0
):
    """Decorator to apply circuit breaker to a function.

    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds to wait before trying again
        expected_exception: Exception type that counts as failure
        success_threshold: Success count to close circuit in half-open
        timeout: Call timeout in seconds
        max_retries: Maximum retry attempts
        backoff_factor: Exponential backoff factor

    Returns:
        Decorated function
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
        success_threshold=success_threshold,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cb = await circuit_registry.get_circuit_breaker(name, config)
            return await cb.call(func, *args, **kwargs)

        return wrapper

    return decorator


class CircuitBreakerMiddleware:
    """Middleware for integrating circuit breaker with web frameworks."""

    def __init__(self, registry: CircuitBreakerRegistry):
        """Initialize middleware.

        Args:
            registry: Circuit breaker registry
        """
        self.registry = registry

    async def __call__(self, request, call_next):
        """Middleware call for web frameworks.

        Args:
            request: Web request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Extract service name from request or use default
        service_name = getattr(request, 'service_name', 'default')

        cb = await self.registry.get_circuit_breaker(service_name)

        try:
            return await cb.call(call_next, request)
        except CircuitBreakerError as e:
            # Return appropriate error response
            return self._create_error_response(e)

    def _create_error_response(self, error: CircuitBreakerError):
        """Create error response for circuit breaker failures.

        Args:
            error: Circuit breaker error

        Returns:
            Error response
        """
        if isinstance(error, CircuitOpenError):
            return {
                'error': 'Service temporarily unavailable',
                'code': 'SERVICE_UNAVAILABLE',
                'retry_after': 60
            }
        elif isinstance(error, CallTimeoutError):
            return {
                'error': 'Request timeout',
                'code': 'TIMEOUT'
            }
        else:
            return {
                'error': 'Service error',
                'code': 'INTERNAL_ERROR'
            }


# Global circuit breaker registry instance
get_circuit_breaker = circuit_registry.get_circuit_breaker