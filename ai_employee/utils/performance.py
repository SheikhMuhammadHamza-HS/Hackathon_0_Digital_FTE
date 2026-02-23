"""Performance optimization utilities for concurrent operations."""

import asyncio
import concurrent.futures
import functools
import inspect
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class PerformanceMode(Enum):
    """Performance optimization modes."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    HIGH_THROUGHPUT = "high_throughput"
    LOW_LATENCY = "low_latency"
    RESOURCE_CONSERVATION = "resource_conservation"


@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self, success: bool = True, error: Optional[str] = None):
        """Mark operation as finished."""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    def __init__(self, max_history: int = 1000):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.active_operations: Dict[str, PerformanceMetrics] = {}
        self.lock = asyncio.Lock()

    async def start_operation(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start monitoring an operation."""
        operation_id = f"{name}_{int(time.time() * 1000000)}"
        metric = PerformanceMetrics(
            operation_name=name,
            start_time=datetime.now(),
            metadata=metadata or {}
        )

        async with self.lock:
            self.active_operations[operation_id] = metric

        return operation_id

    async def finish_operation(
        self,
        operation_id: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Finish monitoring an operation."""
        async with self.lock:
            if operation_id in self.active_operations:
                metric = self.active_operations.pop(operation_id)
                metric.finish(success, error)
                self.metrics[metric.operation_name].append(metric)

    def get_metrics(self, operation_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get performance metrics."""
        if operation_name:
            return [m.to_dict() for m in self.metrics.get(operation_name, [])]

        all_metrics = []
        for metrics_list in self.metrics.values():
            all_metrics.extend(m.to_dict() for m in metrics_list)
        return all_metrics

    def get_statistics(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for an operation."""
        metrics = list(self.metrics.get(operation_name, []))
        if not metrics:
            return {"error": f"No metrics found for {operation_name}"}

        successful = [m for m in metrics if m.success]
        failed = [m for m in metrics if not m.success]
        durations = [m.duration_ms for m in successful if m.duration_ms]

        stats = {
            "operation": operation_name,
            "total_operations": len(metrics),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(metrics) * 100,
        }

        if durations:
            stats.update({
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)],
                "p99_duration_ms": sorted(durations)[int(len(durations) * 0.99)]
            })

        return stats

    def get_slow_operations(self, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """Get operations slower than threshold."""
        slow_ops = []
        for metrics_list in self.metrics.values():
            for metric in metrics_list:
                if metric.duration_ms and metric.duration_ms > threshold_ms:
                    slow_ops.append(metric.to_dict())

        return sorted(slow_ops, key=lambda x: x["duration_ms"], reverse=True)


# Global performance monitor
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: Optional[str] = None):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        name = operation_name or f"{func.__module__}.{func.__qualname__}"

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                op_id = await performance_monitor.start_operation(name)
                try:
                    result = await func(*args, **kwargs)
                    await performance_monitor.finish_operation(op_id, success=True)
                    return result
                except Exception as e:
                    await performance_monitor.finish_operation(op_id, success=False, error=str(e))
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we need to run in an async context
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                async def _monitor():
                    op_id = await performance_monitor.start_operation(name)
                    try:
                        result = func(*args, **kwargs)
                        await performance_monitor.finish_operation(op_id, success=True)
                        return result
                    except Exception as e:
                        await performance_monitor.finish_operation(op_id, success=False, error=str(e))
                        raise

                return loop.run_until_complete(_monitor())
            return sync_wrapper

    return decorator


class ConnectionPool:
    """Generic connection pool for external services."""

    def __init__(
        self,
        create_connection: Callable,
        max_connections: int = 10,
        min_connections: int = 2,
        max_idle_time: int = 300,  # seconds
        health_check_interval: int = 60  # seconds
    ):
        self.create_connection = create_connection
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval

        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self._active_connections: List = []
        self._connection_times: Dict = {}
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the connection pool."""
        # Create minimum connections
        for _ in range(self.min_connections):
            conn = await self._create_connection()
            await self._pool.put(conn)

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _create_connection(self) -> Any:
        """Create a new connection."""
        conn = await self.create_connection()
        self._connection_times[conn] = time.time()
        return conn

    async def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        try:
            # Try to get existing connection
            conn = self._pool.get_nowait()

            # Check if connection is still valid
            if await self._is_connection_healthy(conn):
                self._connection_times[conn] = time.time()
                return conn
            else:
                # Connection is stale, create new one
                await self._close_connection(conn)
                return await self._create_connection()

        except asyncio.QueueEmpty:
            # Pool is empty, try to create new connection if under limit
            async with self.lock:
                if len(self._active_connections) < self.max_connections:
                    conn = await self._create_connection()
                    self._active_connections.append(conn)
                    return conn
                else:
                    # Wait for a connection to be returned
                    conn = await self._pool.get()
                    if await self._is_connection_healthy(conn):
                        self._connection_times[conn] = time.time()
                        return conn
                    else:
                        await self._close_connection(conn)
                        return await self._create_connection()

    async def release(self, conn: Any):
        """Release a connection back to the pool."""
        if conn in self._active_connections:
            self._active_connections.remove(conn)

        if await self._is_connection_healthy(conn):
            try:
                self._pool.put_nowait(conn)
            except asyncio.QueueFull:
                # Pool is full, close the connection
                await self._close_connection(conn)
        else:
            await self._close_connection(conn)

    async def _is_connection_healthy(self, conn: Any) -> bool:
        """Check if a connection is healthy."""
        # This should be implemented based on the connection type
        # For now, just check age
        conn_time = self._connection_times.get(conn, 0)
        return (time.time() - conn_time) < self.max_idle_time

    async def _close_connection(self, conn: Any):
        """Close a connection."""
        # Implementation depends on connection type
        if hasattr(conn, 'close'):
            await conn.close()
        elif conn in self._connection_times:
            del self._connection_times[conn]

    async def _health_check_loop(self):
        """Periodic health check for connections."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                # Check all connections in pool
                connections_to_check = []
                while not self._pool.empty():
                    conn = self._pool.get_nowait()
                    connections_to_check.append(conn)

                for conn in connections_to_check:
                    if await self._is_connection_healthy(conn):
                        await self._pool.put(conn)
                    else:
                        await self._close_connection(conn)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def close(self):
        """Close the connection pool."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        while not self._pool.empty():
            conn = self._pool.get_nowait()
            await self._close_connection(conn)

        for conn in self._active_connections:
            await self._close_connection(conn)
        self._active_connections.clear()


class BatchProcessor(Generic[T]):
    """Process items in batches for better performance."""

    def __init__(
        self,
        process_func: Callable[[List[T]], List[Any]],
        batch_size: int = 10,
        max_wait_time: float = 1.0,
        max_concurrent_batches: int = 5
    ):
        self.process_func = process_func
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.max_concurrent_batches = max_concurrent_batches

        self._queue: asyncio.Queue = asyncio.Queue()
        self._batch_semaphore = asyncio.Semaphore(max_concurrent_batches)
        self._processor_task: Optional[asyncio.Task] = None
        self._pending_batches: Dict[str, asyncio.Future] = {}

    async def start(self):
        """Start the batch processor."""
        self._processor_task = asyncio.create_task(self._process_loop())

    async def stop(self):
        """Stop the batch processor."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

    async def add_item(self, item: T) -> Any:
        """Add an item to be processed."""
        future = asyncio.Future()
        batch_id = f"batch_{int(time.time() * 1000000)}"

        await self._queue.put((item, future, batch_id))
        self._pending_batches[batch_id] = future

        return await future

    async def _process_loop(self):
        """Main processing loop."""
        current_batch: List[Tuple[T, asyncio.Future, str]] = []
        last_batch_time = time.time()

        while True:
            try:
                # Wait for items or timeout
                try:
                    item, future, batch_id = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self.max_wait_time
                    )
                    current_batch.append((item, future, batch_id))
                except asyncio.TimeoutError:
                    pass

                current_time = time.time()

                # Process batch if conditions met
                if (len(current_batch) >= self.batch_size or
                    (current_batch and current_time - last_batch_time >= self.max_wait_time)):

                    # Create a copy and reset current batch
                    batch_to_process = current_batch.copy()
                    current_batch.clear()
                    last_batch_time = current_time

                    # Process batch in background
                    asyncio.create_task(self._process_batch(batch_to_process))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processor error: {e}")

    async def _process_batch(self, batch: List[Tuple[T, asyncio.Future, str]]):
        """Process a batch of items."""
        async with self._batch_semaphore:
            try:
                # Extract items
                items = [item for item, _, _ in batch]

                # Process batch
                results = await self._process_batch_items(items)

                # Set results for futures
                for (_, future, batch_id), result in zip(batch, results):
                    if batch_id in self._pending_batches:
                        del self._pending_batches[batch_id]
                    if not future.done():
                        future.set_result(result)

            except Exception as e:
                # Set exception for all futures in batch
                for _, future, batch_id in batch:
                    if batch_id in self._pending_batches:
                        del self._pending_batches[batch_id]
                    if not future.done():
                        future.set_exception(e)

    async def _process_batch_items(self, items: List[T]) -> List[Any]:
        """Process a batch of items (to be overridden)."""
        if inspect.iscoroutinefunction(self.process_func):
            return await self.process_func(items)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return await loop.run_in_executor(executor, self.process_func, items)


class CacheManager:
    """Simple in-memory cache with TTL."""

    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = None  # Initialize lazily for sync compatibility

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry["expires"]:
                    return entry["value"]
                else:
                    del self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expires": time.time() + (ttl or self.default_ttl)
            }

    async def delete(self, key: str):
        """Delete value from cache."""
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            self._cache.pop(key, None)

    async def clear_expired(self):
        """Clear expired entries."""
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time >= entry["expires"]
            ]
            for key in expired_keys:
                del self._cache[key]

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            total_entries = len(self._cache)
            expired = sum(
                1 for entry in self._cache.values()
                if time.time() >= entry["expires"]
            )

            return {
                "total_entries": total_entries,
                "expired_entries": expired,
                "active_entries": total_entries - expired
            }


# Global cache instance
cache_manager = CacheManager()


def cached(ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Try to get from cache
                cached_result = await cache_manager.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute function and cache result
                result = await func(*args, **kwargs)
                await cache_manager.set(cache_key, result, ttl)
                return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions
                loop = asyncio.get_event_loop()

                async def _cached_call():
                    # Generate cache key
                    if key_func:
                        cache_key = key_func(*args, **kwargs)
                    else:
                        cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                    # Try to get from cache
                    cached_result = await cache_manager.get(cache_key)
                    if cached_result is not None:
                        return cached_result

                    # Execute function and cache result
                    result = func(*args, **kwargs)
                    await cache_manager.set(cache_key, result, ttl)
                    return result

                return loop.run_until_complete(_cached_call())
            return sync_wrapper

    return decorator


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self._requests: Dict[str, deque] = defaultdict(lambda: deque())

    async def acquire(self, identifier: str = "default") -> bool:
        """Check if request is allowed."""
        now = time.time()
        request_times = self._requests[identifier]

        # Remove old requests outside time window
        while request_times and request_times[0] < now - self.time_window:
            request_times.popleft()

        # Check if under limit
        if len(request_times) < self.max_requests:
            request_times.append(now)
            return True

        return False

    async def wait_if_needed(self, identifier: str = "default"):
        """Wait if rate limit is exceeded."""
        while not await self.acquire(identifier):
            await asyncio.sleep(0.1)


# Performance optimization utilities
class Optimizer:
    """Collection of performance optimization utilities."""

    @staticmethod
    async def parallel_map(
        func: Callable,
        items: List[T],
        max_concurrency: int = 10
    ) -> List[R]:
        """Apply function to items in parallel."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_item(item: T) -> R:
            async with semaphore:
                if inspect.iscoroutinefunction(func):
                    return await func(item)
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        return await loop.run_in_executor(executor, func, item)

        tasks = [process_item(item) for item in items]
        return await asyncio.gather(*tasks)

    @staticmethod
    async def gather_with_concurrency(
        *coroutines_or_futures,
        max_concurrency: int = 10
    ) -> List[Any]:
        """Gather coroutines with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _limited_coro(coro):
            async with semaphore:
                return await coro

        limited_coros = [_limited_coro(coro) for coro in coroutines_or_futures]
        return await asyncio.gather(*limited_coros)

    @staticmethod
    def batch_items(items: List[T], batch_size: int) -> List[List[T]]:
        """Split items into batches."""
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

    @staticmethod
    async def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ) -> Any:
        """Retry function with exponential backoff."""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                if inspect.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
            except Exception as e:
                last_exception = e

                if attempt < max_retries:
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {max_retries + 1} attempts failed")

        raise last_exception