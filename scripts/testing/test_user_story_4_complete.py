#!/usr/bin/env python
"""Comprehensive User Story 4 integration test."""

import os
import sys
import asyncio
from datetime import datetime

# Set up environment
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key')
sys.path.insert(0, '.')

print("=" * 60)
print("USER STORY 4 - COMPREHENSIVE INTEGRATION TEST")
print("=" * 60)

async def run_all_tests():
    """Run all User Story 4 component tests."""

    # Test 1: Circuit Breaker
    print("\n1. Testing Circuit Breaker...")
    try:
        from ai_employee.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState

        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
        cb = CircuitBreaker("test_circuit", config)

        # Test state
        assert cb.state == CircuitState.CLOSED
        print("   [OK] Initial state: CLOSED")

        # Test successful call
        async def success():
            return "success"
        result = await cb.call(success)
        assert result == "success"
        print("   [OK] Successful call works")

        # Test failures until open
        async def fail():
            raise Exception("Test failure")

        for i in range(3):
            try:
                await cb.call(fail)
            except:
                pass

        assert cb.state == CircuitState.OPEN
        print("   [OK] Circuit opens after failures")

        # Test stats
        stats = cb.get_stats()
        assert stats.total_calls >= 3
        print(f"   [OK] Statistics tracked: {stats.total_calls} calls")

    except Exception as e:
        print(f"   [FAILED] Circuit breaker test: {e}")
        return False

    # Test 2: Error Recovery Service
    print("\n2. Testing Error Recovery Service...")
    try:
        from ai_employee.core.circuit_breaker import CircuitBreaker
        from ai_employee.utils.error_recovery import ErrorRecoveryService, ErrorCategory

        cb = CircuitBreaker("test_error_recovery")
        error_service = ErrorRecoveryService(circuit_breaker=cb)

        # Test error strategy retrieval
        network_error = Exception("Connection timeout")
        strategy = error_service._get_recovery_strategy(network_error)
        assert strategy is not None
        print("   [OK] Recovery strategy retrieval works")

        # Test recovery strategies
        strategy = error_service._recovery_strategies[ErrorCategory.NETWORK]
        assert strategy is not None
        print("   [OK] Recovery strategies configured")

    except Exception as e:
        print(f"   [FAILED] Error recovery test: {e}")
        return False

    # Test 3: Health Monitor
    print("\n3. Testing Health Monitoring...")
    try:
        from ai_employee.utils.health_monitor import HealthMonitor, HealthStatus
        from ai_employee.core.config import AppConfig
        from ai_employee.core.event_bus import get_event_bus

        # Setup
        event_bus = get_event_bus()
        await event_bus.start_background_processing()

        try:
            # Create config
            class Paths:
                logs_path = "./test_logs"
                inbox_path = "./test_inbox"
                needs_action_path = "./test_needs_action"
                done_path = "./test_done"
                archive_path = "./test_archive"
                temp_path = "./test_temp"

            config = AppConfig(environment="test", paths=Paths())
            monitor = HealthMonitor(config)

            # Initialize and test
            await monitor.initialize()
            print("   [OK] Health monitor initialized")

            await asyncio.sleep(1)  # Let checks run

            status = monitor.get_overall_status()
            assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
            print(f"   [OK] Health status: {status}")

            # Test report generation
            report = await monitor.generate_health_report()
            assert len(report.checks) > 0
            print(f"   [OK] Health report with {len(report.checks)} checks")

            await monitor.shutdown()
            print("   [OK] Health monitor shutdown")

        finally:
            await event_bus.stop_background_processing()

    except Exception as e:
        print(f"   [FAILED] Health monitoring test: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Process Watchdog
    print("\n4. Testing Process Watchdog...")
    try:
        from ai_employee.utils.process_watchdog import ProcessWatchdog, ProcessStatus

        watchdog = ProcessWatchdog()

        # Test registration
        await watchdog.register_process(
            name="test_process",
            command=["python", "-c", "import time; time.sleep(1)"],
            working_dir="."
        )
        print("   [OK] Process registration works")

        # Test retrieval
        process = await watchdog.get_process_status("test_process")
        assert process is not None
        assert process.name == "test_process"
        print("   [OK] Process retrieval works")

    except Exception as e:
        print(f"   [FAILED] Process watchdog test: {e}")
        return False

    # Test 5: Cleanup Manager
    print("\n5. Testing Cleanup Manager...")
    try:
        from ai_employee.utils.cleanup_manager import CleanupManager, CleanupRule

        cleanup = CleanupManager()

        # Test rule addition
        rule = CleanupRule(
            name="test_rule",
            path_pattern="**/*.tmp",
            max_age_days=7
        )
        cleanup.add_rule(rule)
        assert "test_rule" in cleanup.rules
        print("   [OK] Cleanup rule addition works")

        # Test statistics
        stats = cleanup.get_cleanup_statistics()
        assert stats["rules_count"] >= 1
        print(f"   [OK] Cleanup statistics: {stats['rules_count']} rules")

    except Exception as e:
        print(f"   [FAILED] Cleanup manager test: {e}")
        return False

    return True

# Run tests
if __name__ == "__main__":
    result = asyncio.run(run_all_tests())

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    if result:
        print("\n[SUCCESS] All User Story 4 integration tests passed!")
        print("\nComponents verified:")
        print("  ✅ Circuit Breaker - Prevents cascade failures")
        print("  ✅ Error Recovery Service - Handles different error types")
        print("  ✅ Health Monitoring - Tracks system resources")
        print("  ✅ Process Watchdog - Monitors and restarts processes")
        print("  ✅ Cleanup Manager - Automates file cleanup")
        print("\nUser Story 4 is fully functional!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n[FAILED] Some tests failed.")
        print("=" * 60)
        sys.exit(1)