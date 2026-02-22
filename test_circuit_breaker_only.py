#!/usr/bin/env python
"""Simple test for circuit breaker only."""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, '.')

# Set test environment
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key')

from ai_employee.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState


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
    print("[OK] Circuit breaker initial state correct")

    # Test successful call
    async def success_func():
        return "success"

    result = await cb.call(success_func)
    assert result == "success"
    print("[OK] Circuit breaker successful call works")

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
    print("[OK] Circuit breaker opens on failures")

    # Test statistics
    stats = cb.get_stats()
    assert stats.total_calls == 4
    assert stats.failed_calls == 3
    assert stats.successful_calls == 1
    print("[OK] Circuit breaker statistics tracking works")

    print("\n[SUCCESS] Circuit breaker test passed!")
    print("User Story 4 Error Recovery component is working correctly.")


if __name__ == "__main__":
    try:
        asyncio.run(test_circuit_breaker())
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)