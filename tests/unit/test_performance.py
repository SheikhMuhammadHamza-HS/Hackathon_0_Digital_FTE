"""Unit tests for performance utilities."""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from ai_employee.utils.performance import (
    PerformanceMonitor,
    PerformanceMetrics,
    ConnectionPool,
    BatchProcessor,
    CacheManager,
    RateLimiter,
    Optimizer,
    monitor_performance,
    cached,
    PerformanceMode
)


class TestPerformanceMetrics:
    """Test PerformanceMetrics class."""

    def test_metrics_creation(self):
        """Test metrics creation."""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=datetime.now()
        )
        assert metrics.operation_name == "test_operation"
        assert metrics.start_time is not None
        assert metrics.end_time is None
        assert metrics.duration_ms is None
        assert not metrics.success
        assert metrics.error is None

    def test_metrics_finish(self):
        """Test marking metrics as finished."""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=datetime.now()
        )

        # Simulate some work
        time.sleep(0.01)
        metrics.finish(success=True)

        assert metrics.end_time is not None
        assert metrics.duration_ms is not None
        assert metrics.duration_ms > 0
        assert metrics.success
        assert metrics.error is None

    def test_metrics_finish_with_error(self):
        """Test marking metrics as finished with error."""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=datetime.now()
        )

        metrics.finish(success=False, error="Test error")

        assert not metrics.success
        assert metrics.error == "Test error"

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        start = datetime.now()
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=start
        )
        metrics.finish(success=True, metadata={"key": "value"})

        metrics_dict = metrics.to_dict()

        assert metrics_dict["operation"] == "test_operation"
        assert metrics_dict["start_time"] == start.isoformat()
        assert metrics_dict["success"] is True
        assert metrics_dict["metadata"] == {"key": "value"}


class TestPerformanceMonitor:
    """Test PerformanceMonitor class."""

    @pytest.mark.asyncio
    async def test_start_operation(self):
        """Test starting an operation."""
        monitor = PerformanceMonitor()
        operation_id = await monitor.start_operation("test_op")

        assert operation_id is not None
        assert "test_op" in operation_id
        assert operation_id in monitor.active_operations

    @pytest.mark.asyncio
    async def test_finish_operation(self):
        """Test finishing an operation."""
        monitor = PerformanceMonitor()
        operation_id = await monitor.start_operation("test_op")

        await monitor.finish_operation(operation_id, success=True)

        assert operation_id not in monitor.active_operations
        assert len(monitor.metrics["test_op"]) == 1
        assert monitor.metrics["test_op"][0].success

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test getting metrics."""
        monitor = PerformanceMonitor()

        # Add some metrics
        op1 = await monitor.start_operation("op1")
        op2 = await monitor.start_operation("op2")

        await monitor.finish_operation(op1, success=True)
        await monitor.finish_operation(op2, success=False)

        # Get all metrics
        all_metrics = monitor.get_metrics()
        assert len(all_metrics) == 2

        # Get filtered metrics
        op1_metrics = monitor.get_metrics("op1")
        assert len(op1_metrics) == 1
        assert op1_metrics[0]["success"] is True

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting statistics."""
        monitor = PerformanceMonitor()

        # Add multiple operations
        for i in range(5):
            op_id = await monitor.start_operation("test_op")
            time.sleep(0.001)  # Small delay
            await monitor.finish_operation(op_id, success=i < 4)  # One failure

        stats = monitor.get_statistics("test_op")

        assert stats["operation"] == "test_op"
        assert stats["total_operations"] == 5
        assert stats["successful"] == 4
        assert stats["failed"] == 1
        assert stats["success_rate"] == 80.0
        assert "avg_duration_ms" in stats


class TestCacheManager:
    """Test CacheManager class."""

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting cache values."""
        cache = CacheManager(default_ttl=1)

        await cache.set("key1", "value1")
        value = await cache.get("key1")

        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_expired(self):
        """Test getting expired value."""
        cache = CacheManager(default_ttl=0.1)  # 100ms

        await cache.set("key1", "value1")
        await asyncio.sleep(0.2)  # Wait for expiration

        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting cache entries."""
        cache = CacheManager()

        await cache.set("key1", "value1")
        await cache.delete("key1")

        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_clear_expired(self):
        """Test clearing expired entries."""
        cache = CacheManager(default_ttl=0.1)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2", ttl=10)  # Longer TTL

        await asyncio.sleep(0.2)  # Wait for first to expire
        await cache.clear_expired()

        value1 = await cache.get("key1")
        value2 = await cache.get("key2")

        assert value1 is None
        assert value2 == "value2"

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting cache statistics."""
        cache = CacheManager(default_ttl=1)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        stats = await cache.get_stats()

        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["expired_entries"] == 0


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(max_requests=3, time_window=1)

        # First 3 should succeed
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True

        # 4th should fail
        assert await limiter.acquire() is False

    @pytest.mark.asyncio
    async def test_time_window_reset(self):
        """Test rate limit resets after time window."""
        limiter = RateLimiter(max_requests=2, time_window=0.1)

        # Use up limit
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        assert await limiter.acquire() is False

        # Wait for time window
        await asyncio.sleep(0.2)

        # Should work again
        assert await limiter.acquire() is True

    @pytest.mark.asyncio
    async def test_different_identifiers(self):
        """Test rate limiting with different identifiers."""
        limiter = RateLimiter(max_requests=2, time_window=1)

        # Each identifier has its own limit
        assert await limiter.acquire("user1") is True
        assert await limiter.acquire("user1") is True
        assert await limiter.acquire("user1") is False

        # user2 should still have full limit
        assert await limiter.acquire("user2") is True
        assert await limiter.acquire("user2") is True


class TestMonitorDecorator:
    """Test monitor_performance decorator."""

    @pytest.mark.asyncio
    async def test_async_function_monitoring(self):
        """Test monitoring async functions."""
        monitor = PerformanceMonitor()

        @monitor_performance("test_function")
        async def test_func():
            await asyncio.sleep(0.01)
            return "result"

        result = await test_func()

        assert result == "result"
        metrics = monitor.get_metrics("test_function")
        assert len(metrics) == 1
        assert metrics[0]["success"] is True
        assert metrics[0]["duration_ms"] > 0

    def test_sync_function_monitoring(self):
        """Test monitoring sync functions."""
        monitor = PerformanceMonitor()

        @monitor_performance("test_sync_function")
        def test_func():
            time.sleep(0.01)
            return "sync_result"

        result = test_func()

        assert result == "sync_result"
        metrics = monitor.get_metrics("test_sync_function")
        assert len(metrics) == 1
        assert metrics[0]["success"] is True


class TestCachedDecorator:
    """Test cached decorator."""

    @pytest.mark.asyncio
    async def test_async_function_caching(self):
        """Test caching async functions."""
        call_count = 0

        @cached(ttl=1)
        async def expensive_func(x):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * 2

        # First call
        result1 = await expensive_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_func(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment

        # Different argument should call function
        result3 = await expensive_func(10)
        assert result3 == 20
        assert call_count == 2

    def test_sync_function_caching(self):
        """Test caching sync functions."""
        call_count = 0

        @cached(ttl=1)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)
            return x * 2

        # First call
        result1 = expensive_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_func(5)
        assert result2 == 10
        assert call_count == 1


class TestOptimizer:
    """Test Optimizer utility class."""

    @pytest.mark.asyncio
    async def test_parallel_map(self):
        """Test parallel map execution."""
        async def process_item(x):
            await asyncio.sleep(0.01)
            return x * 2

        items = [1, 2, 3, 4, 5]
        results = await Optimizer.parallel_map(process_item, items, max_concurrency=3)

        assert results == [2, 4, 6, 8, 10]

    def test_batch_items(self):
        """Test batching items."""
        items = list(range(10))
        batches = Optimizer.batch_items(items, batch_size=3)

        assert batches == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test retry with backoff on success."""
        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Failed")
            return "success"

        result = await Optimizer.retry_with_backoff(
            flaky_func,
            max_retries=3,
            base_delay=0.01
        )

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_backoff_failure(self):
        """Test retry with backoff on failure."""
        async def always_fail():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await Optimizer.retry_with_backoff(
                always_fail,
                max_retries=2,
                base_delay=0.01
            )


class TestBatchProcessor:
    """Test BatchProcessor class."""

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing of items."""
        processed_batches = []

        async def process_batch(items):
            processed_batches.append(items)
            return [item * 2 for item in items]

        processor = BatchProcessor(
            process_batch,
            batch_size=3,
            max_wait_time=0.1,
            max_concurrent_batches=2
        )

        await processor.start()

        # Add items
        results = []
        for i in range(7):
            result = await processor.add_item(i)
            results.append(result)

        # Wait for processing
        await asyncio.sleep(0.2)
        await processor.stop()

        assert results == [0, 2, 4, 6, 8, 10, 12]
        assert len(processed_batches) == 3  # [0,1,2], [3,4,5], [6]