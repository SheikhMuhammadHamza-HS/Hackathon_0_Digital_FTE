#!/usr/bin/env python
"""Simple test for health monitor only."""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, '.')

# Set test environment
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key')

# Import only what we need
from ai_employee.core.config import AppConfig
from ai_employee.core.event_bus import get_event_bus
# Import health monitor directly to avoid import issues
sys.path.insert(0, './ai_employee/utils')
from health_monitor import HealthMonitor, HealthCheckConfig, HealthStatus


async def test_health_monitor():
    """Test basic health monitor functionality."""
    print("Testing Health Monitor...")

    # Create a minimal config
    class Paths:
        logs_path = "./test_logs"

    config = AppConfig(
        environment="test",
        paths=Paths()
    )

    # Create event bus
    event_bus = get_event_bus()
    await event_bus.start_background_processing()

    try:
        # Create health monitor
        health_config = HealthCheckConfig(
            check_interval=0.5,
            metrics_retention_hours=1,
            alert_retention_hours=1
        )
        monitor = HealthMonitor(health_config)

        # Initialize monitor
        await monitor.initialize()
        print("[OK] Health monitor initialized")

        # Wait for initial checks
        await asyncio.sleep(1)

        # Get overall status
        status = monitor.get_overall_status()
        assert status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
        print(f"[OK] Health monitor status: {status}")

        # Get current metrics
        metrics = await monitor.get_current_metrics()
        print(f"[OK] Retrieved {len(metrics)} metrics")

        # Generate health report
        report = await monitor.generate_health_report()
        assert len(report.checks) > 0
        assert report.timestamp is not None
        print(f"[OK] Health report generated with {len(report.checks)} checks")

        # Check for alerts
        alerts = await monitor.get_active_alerts()
        print(f"[OK] Retrieved {len(alerts)} active alerts")

        # Shutdown monitor
        await monitor.shutdown()
        print("[OK] Health monitor shutdown successfully")

        print("\n[SUCCESS] Health monitor test passed!")
        print("User Story 4 Health Monitoring component is working correctly.")

    finally:
        await event_bus.stop_background_processing()


if __name__ == "__main__":
    try:
        asyncio.run(test_health_monitor())
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)