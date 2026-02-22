"""
Integration tests for circuit breaker functionality.

These tests validate that the circuit breaker correctly
prevents cascade failures and provides automatic recovery.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from ai_employee.core.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState,
    CircuitOpenError, CallTimeoutError, MaxRetriesExceededError
)
from ai_employee.core.event_bus import get_event_bus
from ai_employee.core.config import AppConfig


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""

    @pytest.fixture
    async def circuit_breaker(self):
        """Create circuit breaker for testing."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=2.0,  # Short timeout for testing
            max_retries=2,
            timeout=1.0
        )
        return CircuitBreaker("test_circuit", config)

    @pytest.fixture
    async def event_bus(self):
        """Create event bus for testing."""
        event_bus = get_event_bus()
        await event_bus.start_background_processing()
        yield event_bus
        await event_bus.stop_background_processing()

    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self, circuit_breaker):
        """Test circuit breaker initial state."""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.can_execute is True
        assert circuit_breaker.get_statistics()["total_calls"] == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self, circuit_breaker):
        """Test circuit opens after threshold failures."""
        # Create a failing function
        failing_function = AsyncMock(side_effect=Exception("Service unavailable"))

        # Execute failing function multiple times
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)

        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)

        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)

        # Circuit should now be open
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.can_execute is False

    @pytest.mark.asyncio
    async def test_circuit_blocks_calls_when_open(self, circuit_breaker):
        """Test circuit blocks calls when open."""
        # Open the circuit
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._failure_count = 3

        # Create function that would normally work
        working_function = AsyncMock(return_value="success")

        # Call should be blocked immediately
        with pytest.raises(CircuitOpenError):
            await circuit_breaker.call(working_function)

        assert circuit_breaker.can_execute is False

    @pytest.mark.asyncio
    async def test_circuit_recovers_after_timeout(self, circuit_breaker):
        """Test circuit recovers after timeout."""
        # Open the circuit
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._failure_count = 3
        circuit_breaker._last_failure_time = datetime.utcnow() - timedelta(seconds=3)

        # Wait for recovery timeout
        await asyncio.sleep(2.5)

        # Circuit should be half-open
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        # Should allow one call to test recovery
        working_function = AsyncMock(return_value="recovery_test")
        result = await circuit_breaker.call(working_function)
        assert result == "recovery_test"

        # Should close on success
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_closes_on_success(self, circuit_breaker):
        """Test circuit closes on success after half-open."""
        # Open the circuit
        circuit_breaker._state = CircuitState.HALF_OPEN
        circuit_breaker._failure_count = 3
        circuit_breaker._success_count = 1
        circuit_breaker._max_success_threshold = 2

        # Successful call should close circuit
        working_function = AsyncMock(return_value="success")
        await circuit_breaker.call(working_function)

        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_statistics(self, circuit_breaker):
        """Test circuit breaker statistics tracking."""
        # Execute some operations
        working_function = AsyncMock(return_value="test")
        failing_function = AsyncMock(side_effect=Exception("Test error"))

        # Successful call
        await circuit_breaker.call(working_function)

        # Failed calls
        for _ in range(3):
            try:
                await circuit_breaker.call(failing_function)
            except Exception:
                pass

        # Check statistics
        stats = circuit_breaker.get_statistics()
        assert stats["total_calls"] == 4
        assert stats["failed_calls"] == 3
        assert stats["successful_calls"] == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_different_services(self, circuit_breaker, event_bus):
        """Test multiple circuit breakers for different services."""
        # Create additional circuit breakers
        payment_cb = CircuitBreaker("payment_service", CircuitBreakerConfig(failureThreshold=2))
        email_cb = CircuitBreaker("email_service", CircuitBreakerConfig(failureThreshold=5))

        # Simulate payment service failure
        payment_failing = AsyncMock(side_effect=Exception("Payment service down"))

        # First payment service failure
        await payment_cb.call(payment_failing)

        # Second payment service failure (circuit opens)
        with pytest.raises(Exception):
            await payment_cb.call(payment_failing)

        assert payment_cb.state == CircuitState.OPEN
        assert payment_cb.can_execute is False

        # Email service still works
        email_working = AsyncMock(return_value="email sent")
        result = await email_cb.call(email_working)
        assert result == "email sent"

        # Payment service should open but email service should stay closed
        assert payment_cb.state == CircuitState.OPEN
        assert email_cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_calls(self, circuit_breaker):
        """Test concurrent calls to circuit breaker."""
        async def fast_function():
            return "fast_result"

        async def slow_function():
            time.sleep(0.1)
            return "slow_result"

        # Execute concurrent calls
        tasks = [
            circuit_breaker.call(fast_function),
            circuit_breaker.call(slow_function),
            circuit_breaker.call(fast_function)
        ]

        results = await asyncio.gather(*tasks)
        assert all(result == "fast_result" for result in results)

    @pytest.mark.asyncio
    async def test_circuit_breaker_error_categorization(self, circuit_breaker):
        """Test error categorization in circuit breaker."""
        # Network timeout error
        network_error = Exception("Connection timeout")

        # Should retry network errors
        assert not circuit_breaker._is_permanent_error(network_error)

        # Authentication error
        auth_error = Exception("Invalid credentials")

        # Should not retry auth errors
        assert circuit_breaker._is_permanent_error(auth_error)

        # Logic error
        logic_error = Exception("Invalid data format")

        # Should retry logic errors
        assert not circuit_breaker._is_permanent_error(logic_error)

        # System error
        system_error = Exception("Database connection lost")

        # Should not retry system errors
        assert circuit_breaker._is_permanent_error(system_error)

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_special_rules(self, circuit_breaker):
        """Test special rules for specific error types."""
        # Banking API timeout - should never retry
        banking_error = Exception("Bank API timeout")
        assert circuit_breaker._is_permanent_error(banking_error)

        # Gmail API down - should queue operations
        gmail_error = Exception("Gmail service unavailable")
        assert not circuit_breaker._is_permanent_error(gmail_error)

        # Claude unavailable - should queue operations
        claude_error = Exception("Claude service unavailable")
        assert not circuit_breaker._is_permanent_error(claude_error)

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry_backoff(self, circuit_breaker):
        """Test exponential backoff retry logic."""
        call_count = 0
        retry_delays = []

        async def retry_function():
            nonlocal call_count, retry_delays
            call_count += 1
            retry_delays.append(time.time())

            if call_count <= 3:
                raise Exception(f"Attempt {call_count} failed")

        # Call function with retries
        start_time = time.time()
        try:
            await circuit_breaker.call(retry_function)
        except Exception:
            pass

        end_time = time.time()
        duration = end_time - start_time

        # Check that backoff was applied
        assert duration >= 1.0  # At least 1 second for 3 retries
        assert len(retry_delays) == 3

        # Verify exponential backoff (each delay should be longer than the previous)
        for i in range(1, len(retry_delays)):
            if i > 0:
                assert retry_delays[i] >= retry_delays[i-1] * 0.9  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_circuit_breaker_factory_function(self):
        """Test circuit breaker factory function."""
        from ai_employee.core.circuit_breaker import CircuitBreaker

        # Create circuit breaker using factory
        cb1 = CircuitBreaker("factory_test", CircuitBreakerConfig(failureThreshold=5))
        cb2 = CircuitBreaker("factory_test", CircuitBreakerConfig(failureThreshold=3))

        # Both should have different configurations
        assert cb1.config.failure_threshold == 5
        assert cb2.config.failure_threshold == 3
        assert cb1.name == "factory_test"
        assert cb2.name == "factory_test"

    @pytest.mark.asyncio
    async def test_circuit_breaker_event_publishing(self, circuit_breaker, event_bus):
        """Test circuit breaker publishes events."""
        events_received = []

        async def event_handler(event):
            events_received.append(event)

        # Subscribe to circuit breaker events
        with patch('ai_employee.core.circuit_breaker.CircuitBreaker._publish_event', new=self=event_handler):
            # Simulate failures to trigger events
            failing_function = AsyncMock(side_effect=Exception("Service failure"))

            # First failure - should publish failure event
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)

            # Check that failure event was published
            await asyncio.sleep(0.1)  # Allow async processing
            assert len(events_received) >= 1
            assert "CircuitOpenedEvent" in [type(e).__name__ for e in events_received[-3:]]

            # Second failure - should not publish duplicate events
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)

            # Should not create duplicate events
            failure_events = [e for e in events_received if type(e).__name__ == "CircuitOpenedEvent"]
            assert len(failure_events) == 1  # Only one opening event should be published

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_workflow_integration(self, circuit_breaker, event_bus):
        """Test circuit breaker integration with workflow engine."""
        from ai_employee.core.workflow_engine import get_workflow_engine
        from ai_employee.core.workflow_engine import WorkflowStep

        # Create workflow
        workflow_engine = get_workflow_engine()

        # Create workflow with circuit breaker protected step
        workflow = await workflow_engine.create_workflow(
            workflow_id="cb_test_workflow",
            name="Circuit Breaker Test Workflow",
            description="Test circuit breaker in workflow"
        )

        class FailingStep(WorkflowStep):
            async def execute(self, context):
                with pytest.raises(Exception):
                    await circuit_breaker.call(lambda: raise Exception("Step failed"))

                return None

        class WorkingStep(WorkflowStep):
            async def execute(self, context):
                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.COMPLETED,
                    data={"result": "success"}
                )

        workflow.add_step(FailingStep("failing_step", "Failing Step"))
        workflow.add_step(WorkingStep("working_step", "Working Step"))

        # Execute workflow
        result = await workflow_engine.execute_workflow(workflow.id)

        # Workflow should fail at failing step
        assert result is False

        # Circuit breaker should be open
        assert circuit_breaker.state == CircuitState.OPEN

        # Circuit breaker statistics should reflect failures
        stats = circuit_breaker.get_statistics()
        assert stats["failed_calls"] >= 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_cleanup(self, circuit_breaker):
        """Test circuit breaker cleanup."""
        # Get initial statistics
        initial_stats = circuit_breaker.get_statistics()

        # Cleanup should reset state
        circuit_breaker.reset()

        # Statistics should be reset
        final_stats = circuit_breaker.get_statistics()

        assert final_stats["total_calls"] == 0
        assert final_stats["failed_calls"] == 0
        assert final_stats["successful_calls"] == 0
        assert final_stats["circuit_opens"] == 0

        # Can execute after cleanup
        working_function = AsyncMock(return_value="post-reset")
        result = await circuit_breaker.call(working_function)
        assert result == "post-reset"