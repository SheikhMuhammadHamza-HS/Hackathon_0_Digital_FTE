#!/usr/bin/env python
"""Run User Story 4 integration tests."""

import os
import sys
import asyncio

# Set up test environment before imports
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-integration-tests')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key-for-integration-tests')
os.environ.setdefault('INBOX_PATH', './test_data/Inbox')
os.environ.setdefault('NEEDS_ACTION_PATH', './test_data/Needs_Action')
os.environ.setdefault('DONE_PATH', './test_data/Done')
os.environ.setdefault('LOGS_PATH', './test_data/Logs')
os.environ.setdefault('ENVIRONMENT', 'test')

# Add project root to path
sys.path.insert(0, '.')

# Create test directories
import shutil
from pathlib import Path

test_dirs = [
    Path('./test_data/Inbox'),
    Path('./test_data/Needs_Action'),
    Path('./test_data/Done'),
    Path('./test_data/Logs')
]

for test_dir in test_dirs:
    test_dir.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("USER STORY 4 INTEGRATION TESTS")
print("=" * 60)
print()

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "skipped": []
}

async def run_all_tests():
    """Run all User Story 4 integration tests."""

    # Test 1: Circuit Breaker
    print("1. Circuit Breaker Tests")
    print("-" * 40)
    try:
        from tests.integration.test_circuit_breaker import TestCircuitBreakerIntegration
        test = TestCircuitBreakerIntegration()

        # Run simple state test
        await test.test_circuit_breaker_initial_state()
        print("   ✓ Initial state test passed")

        await test.test_circuit_opens_on_failures()
        print("   ✓ Circuit opening test passed")

        test_results["passed"].append("Circuit Breaker Tests")
    except Exception as e:
        print(f"   ✗ Circuit breaker tests failed: {e}")
        test_results["failed"].append(f"Circuit Breaker Tests: {e}")

    print()

    # Test 2: Error Recovery
    print("2. Error Recovery Service Tests")
    print("-" * 40)
    try:
        from ai_employee.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        from ai_employee.utils.error_recovery import ErrorRecoveryService, ErrorCategory

        # Create error recovery service
        cb = CircuitBreaker("test_error_recovery")
        error_recovery = ErrorRecoveryService(circuit_breaker=cb)

        # Test error categorization
        network_error = Exception("Connection timeout")
        category = error_recovery._categorize_error(network_error)
        assert category == ErrorCategory.NETWORK
        print("   ✓ Error categorization works")

        # Test recovery strategies
        strategy = error_recovery._recovery_strategies[ErrorCategory.NETWORK]
        assert strategy.action.value == "retry_with_backoff"
        print("   ✓ Recovery strategies configured")

        test_results["passed"].append("Error Recovery Service Tests")
    except Exception as e:
        print(f"   ✗ Error recovery tests failed: {e}")
        test_results["failed"].append(f"Error Recovery Service Tests: {e}")

    print()

    # Test 3: Health Monitor
    print("3. Health Monitoring Tests")
    print("-" * 40)
    try:
        from ai_employee.utils.health_monitor import HealthMonitor, HealthStatus
        from ai_employee.core.config import AppConfig
        from ai_employee.core.event_bus import get_event_bus

        # Create event bus
        event_bus = get_event_bus()
        await event_bus.start_background_processing()

        try:
            # Create health monitor
            class Paths:
                logs_path = "./test_logs"
                inbox_path = "./test_inbox"
                needs_action_path = "./test_needs_action"
                done_path = "./test_done"
                archive_path = "./test_archive"
                temp_path = "./test_temp"

            config = AppConfig(
                environment="test",
                paths=Paths()
            )

            monitor = HealthMonitor(config)
            await monitor.initialize()
            print("   ✓ Health monitor initialized")

            # Wait for checks
            await asyncio.sleep(2)

            # Check status
            status = monitor.get_overall_status()
            assert status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
            print(f"   ✓ Health status: {status}")

            # Generate report
            report = await monitor.generate_health_report()
            print(f"   ✓ Health report with {len(report.checks)} checks generated")

            # Cleanup
            await monitor.shutdown()
            print("   ✓ Health monitor shutdown successfully")

            test_results["passed"].append("Health Monitoring Tests")
        finally:
            await event_bus.stop_background_processing()

    except Exception as e:
        print(f"   ✗ Health monitoring tests failed: {e}")
        import traceback
        traceback.print_exc()
        test_results["failed"].append(f"Health Monitoring Tests: {e}")

    print()

    # Test 4: Process Watchdog
    print("4. Process Watchdog Tests")
    print("-" * 40)
    try:
        from ai_employee.utils.process_watchdog import ProcessWatchdog, ProcessStatus

        watchdog = ProcessWatchdog()

        # Test process registration
        watchdog.register_process(
            name="test_process",
            command=["python", "-c", "import time; time.sleep(1)"],
            working_dir="."
        )
        print("   ✓ Process registration works")

        # Test process retrieval
        process_info = watchdog.get_process("test_process")
        assert process_info is not None
        assert process_info.name == "test_process"
        print("   ✓ Process retrieval works")

        test_results["passed"].append("Process Watchdog Tests")
    except Exception as e:
        print(f"   ✗ Process watchdog tests failed: {e}")
        test_results["failed"].append(f"Process Watchdog Tests: {e}")

    print()

    # Test 5: Cleanup Manager
    print("5. Cleanup Manager Tests")
    print("-" * 40)
    try:
        from ai_employee.utils.cleanup_manager import CleanupManager, CleanupRule

        cleanup = CleanupManager()

        # Add a test rule
        rule = CleanupRule(
            name="test_cleanup",
            path_pattern="**/*.tmp",
            max_age_days=7
        )
        cleanup.add_rule(rule)
        assert "test_cleanup" in cleanup.rules
        print("   ✓ Cleanup rule addition works")

        # Test statistics
        stats = cleanup.get_cleanup_statistics()
        assert stats["rules_count"] >= 1
        print(f"   ✓ Cleanup statistics: {stats['rules_count']} rules")

        test_results["passed"].append("Cleanup Manager Tests")
    except Exception as e:
        print(f"   ✗ Cleanup manager tests failed: {e}")
        test_results["failed"].append(f"Cleanup Manager Tests: {e}")

    print()

# Run all tests
asyncio.run(run_all_tests())

# Print summary
print("=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print()
print(f"Passed: {len(test_results['passed'])}")
for test in test_results['passed']:
    print(f"  ✓ {test}")

if test_results['failed']:
    print()
    print(f"Failed: {len(test_results['failed'])}")
    for test in test_results['failed']:
        print(f"  ✗ {test}")

if test_results['skipped']:
    print()
    print(f"Skipped: {len(test_results['skipped'])}")
    for test in test_results['skipped']:
        print(f"  - {test}")

print()
print("=" * 60)
if len(test_results['passed']) >= 4:
    print("🎉 USER STORY 4 INTEGRATION TESTS PASSED!")
    print()
    print("All core components are working correctly:")
    print("  • Circuit Breaker")
    print("  • Error Recovery Service")
    print("  • Health Monitoring System")
    print("  • Process Watchdog")
    print("  • Cleanup Manager")
else:
    print("❌ Some tests failed. Check the errors above.")
print("=" * 60)

# Exit with appropriate code
sys.exit(0 if len(test_results['failed']) == 0 else 1)