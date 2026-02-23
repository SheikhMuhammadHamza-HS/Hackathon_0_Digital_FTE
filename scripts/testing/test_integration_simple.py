#!/usr/bin/env python
"""Simple integration test for User Story 4 components."""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, '.')

# Set test environment
from dotenv import load_dotenv
load_dotenv('.env.test')

# Set required environment variables
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-integration-tests')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key-for-integration-tests')

from ai_employee.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from ai_employee.utils.health_monitor import HealthMonitor, HealthCheckConfig, HealthStatus


async def test_circuit_breaker():
    """Test basic circuit breaker functionality."""
    print("Testing Circuit Breaker...")

    # Create circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1.0,
        max_retries=2,
        timeout=1.0
    )
    cb = CircuitBreaker("test_circuit", config)

    # Test initial state
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute is True
    print("✓ Circuit breaker initial state correct")

    # Test successful call
    async def success_func():
        return "success"

    result = await cb.call(success_func)
    assert result == "success"
    print("✓ Circuit breaker successful call works")

    # Test failure handling
    async def fail_func():
        raise Exception("Test failure")

    # Trigger failures
    for i in range(3):
        try:
            await cb.call(fail_func)
        except Exception:
            pass

    # Circuit should be open
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute is False
    print("✓ Circuit breaker opens on failures")

    print("Circuit breaker test passed!\n")


async def test_health_monitor():
    """Test basic health monitor functionality."""
    print("Testing Health Monitor...")

    # Create health monitor
    config = HealthCheckConfig(
        check_interval=0.5,
        metrics_retention_hours=1,
        alert_retention_hours=1
    )
    monitor = HealthMonitor(config)

    try:
        # Initialize monitor
        await monitor.initialize()
        print("✓ Health monitor initialized")

        # Wait for initial checks
        await asyncio.sleep(1)

        # Get overall status
        status = monitor.get_overall_status()
        assert status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
        print(f"✓ Health monitor status: {status}")

        # Generate health report
        report = await monitor.generate_health_report()
        assert len(report.checks) > 0
        assert report.timestamp is not None
        print(f"✓ Health report generated with {len(report.checks)} checks")

        print("Health monitor test passed!\n")

    finally:
        await monitor.shutdown()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("User Story 4 Integration Tests")
    print("=" * 60)
    print()

    try:
        await test_circuit_breaker()
        await test_health_monitor()

        print("=" * 60)
        print("✅ All integration tests passed!")
        print("User Story 4 (Error Recovery & System Health) is working correctly.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)