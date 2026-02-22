#!/usr/bin/env python
"""Minimal test to verify health monitor works."""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the project root to sys.path
sys.path.insert(0, '.')

# Set test environment
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key')

async def test_health_monitor():
    """Test health monitor."""
    print("Testing Health Monitor...")

    try:
        from ai_employee.utils.health_monitor import HealthMonitor, HealthStatus
        from ai_employee.core.config import AppConfig

        # Create minimal config
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

        # Initialize
        await monitor.initialize()
        print("  [OK] Initialized")

        # Wait a bit
        await asyncio.sleep(1)

        # Get status
        status = monitor.get_overall_status()
        print(f"  [OK] Status: {status}")

        # Get metrics
        metrics = monitor.get_metrics()
        print(f"  [OK] Metrics: {len(metrics)} collected")

        # Generate report
        report = await monitor.generate_health_report()
        print(f"  [OK] Report: {len(report.checks)} checks")

        # Shutdown
        await monitor.shutdown()
        print("  [OK] Shutdown")

        print("\n[SUCCESS] Health monitor works!")

    except Exception as e:
        print(f"\n[FAILED] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_health_monitor())