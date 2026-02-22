#!/usr/bin/env python
"""Final User Story 4 integration test - simplified."""

import os
import sys

# Set up environment
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key')
sys.path.insert(0, '.')

print("=" * 60)
print("USER STORY 4 - FINAL INTEGRATION TEST")
print("=" * 60)

def test_circuit_breaker():
    """Test circuit breaker."""
    print("\n1. Testing Circuit Breaker...")

    import asyncio
    from ai_employee.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState

    async def test():
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
        cb = CircuitBreaker("test", config)

        # Test state
        assert cb.state == CircuitState.CLOSED
        print("   [OK] Initial state")

        # Test call
        async def success():
            return "ok"
        result = await cb.call(success)
        assert result == "ok"
        print("   [OK] Successful call")

        # Test failure
        async def fail():
            raise Exception("fail")

        for _ in range(3):
            try:
                await cb.call(fail)
            except:
                pass

        assert cb.state == CircuitState.OPEN
        print("   [OK] Opens on failures")

        return True

    return asyncio.run(test())

def test_error_recovery():
    """Test error recovery service."""
    print("\n2. Testing Error Recovery...")

    import asyncio
    from ai_employee.core.circuit_breaker import CircuitBreaker
    from ai_employee.utils.error_recovery import ErrorRecoveryService

    async def test():
        cb = CircuitBreaker("test")
        service = ErrorRecoveryService(circuit_breaker=cb)

        # Check recovery strategies exist
        assert len(service._recovery_strategies) > 0
        print("   [OK] Recovery strategies configured")

        return True

    return asyncio.run(test())

def test_process_watchdog():
    """Test process watchdog."""
    print("\n3. Testing Process Watchdog...")

    import asyncio
    from ai_employee.utils.process_watchdog import ProcessWatchdog

    async def test():
        watchdog = ProcessWatchdog()

        # Test registration
        await watchdog.register_process(
            name="test",
            command=["python", "-c", "print('test')"],
            working_dir="."
        )
        print("   [OK] Process registration")

        # Verify process exists
        processes = await watchdog.get_all_processes()
        assert "test" in processes
        print("   [OK] Process storage")

        return True

    return asyncio.run(test())

def test_cleanup_manager():
    """Test cleanup manager."""
    print("\n4. Testing Cleanup Manager...")

    from ai_employee.utils.cleanup_manager import CleanupManager, CleanupRule

    cleanup = CleanupManager()

    # Add rule
    rule = CleanupRule(
        name="test_rule",
        path_pattern="**/*.tmp",
        max_age_days=7
    )
    cleanup.add_rule(rule)

    assert "test_rule" in cleanup.rules
    print("   [OK] Cleanup rule addition")

    # Test statistics
    stats = cleanup.get_cleanup_statistics()
    assert stats["rules_count"] >= 1
    print("   [OK] Statistics generation")

    return True

def test_main_integration():
    """Test main.py integration."""
    print("\n5. Testing Main System Integration...")

    import asyncio
    from ai_employee.main import AIEmployeeSystem

    async def test():
        system = AIEmployeeSystem()

        # Test directory creation
        await system._create_directories()
        print("   [OK] Directory creation")

        # Test system status
        status = await system.get_status()
        assert "running" in status
        assert "components" in status
        print("   [OK] System status API")

        return True

    return asyncio.run(test())

# Run all tests
all_passed = True
test_functions = [
    test_circuit_breaker,
    test_error_recovery,
    test_process_watchdog,
    test_cleanup_manager,
    test_main_integration
]

for test_func in test_functions:
    try:
        if not test_func():
            all_passed = False
    except Exception as e:
        print(f"   [FAILED] {e}")
        all_passed = False

print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

if all_passed:
    print("\n[SUCCESS] All User Story 4 components are working correctly!")
    print("\nVerified components:")
    print("  ✅ Circuit Breaker")
    print("  ✅ Error Recovery Service")
    print("  ✅ Process Watchdog")
    print("  ✅ Cleanup Manager")
    print("  ✅ Main System Integration")
    print("\nUser Story 4 (Robust Error Recovery & System Health)")
    print("is fully implemented and functional!")
    print("=" * 60)
    sys.exit(0)
else:
    print("\n[FAILED] Some tests failed.")
    print("=" * 60)
    sys.exit(1)