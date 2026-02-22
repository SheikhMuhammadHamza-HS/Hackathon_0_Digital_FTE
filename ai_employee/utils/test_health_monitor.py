"""
Test and demonstration of the health monitoring system.
"""

import asyncio
import time
from datetime import datetime, timedelta
from ai_employee.utils.health_monitor import (
    HealthMonitor,
    HealthStatus,
    CheckType,
    AlertSeverity,
    health_check
)
from ai_employee.core.config import get_config


async def demonstrate_health_monitoring():
    """Demonstrate the health monitoring system capabilities."""
    print("=== Health Monitoring System Demo ===\n")

    # Initialize configuration
    config = get_config()

    # Create and initialize health monitor
    monitor = HealthMonitor(config=config)
    await monitor.initialize()

    print("✓ Health Monitor initialized")
    print(f"  Registered checks: {len(monitor._checks)}")

    # List all registered checks
    print("\nRegistered Health Checks:")
    for name, check in monitor._checks.items():
        print(f"  - {name}: {check.check_type.value} ({check.description})")

    # Run a few checks manually
    print("\nRunning health checks...")
    checks_to_run = ["cpu_usage", "memory_usage", "disk_usage"]

    for check_name in checks_to_run:
        if check_name in monitor._checks:
            print(f"\n  Running {check_name}...")
            result = await monitor.run_check(check_name)
            print(f"    Status: {result.status.value}")
            print(f"    Last check: {result.last_check}")

            if result.metrics:
                print("    Metrics:")
                for metric in result.metrics:
                    print(f"      - {metric.name}: {metric.value:.1f}{metric.unit} ({metric.status.value})")

    # Wait a bit for more data
    print("\nWaiting for 30 seconds to collect more data...")
    await asyncio.sleep(30)

    # Generate health report
    print("\nGenerating Health Report...")
    report = await monitor.generate_health_report()

    print(f"  Overall Status: {report.overall_status.value}")
    print(f"  System Uptime: {report.uptime_percentage:.1f}%")
    print(f"  Total Checks: {len(report.checks)}")
    print(f"  Active Alerts: {len(report.alerts)}")
    print(f"  Response Time: {report.response_time_ms:.1f}ms")

    # Add a custom health check
    print("\n\nAdding custom health check...")

    @health_check(
        name="custom_time_check",
        check_type=CheckType.CUSTOM,
        interval=10,
        threshold_warning=50.0,
        threshold_critical=100.0
    )
    async def check_time_metrics(check):
        """Custom check for time-based metrics."""
        # Simulate a metric that changes over time
        current_time = time.time()
        seconds_past_minute = current_time % 60

        # Simulate varying load based on time
        load_factor = abs(seconds_past_minute - 30) / 30.0 * 100

        return [
            {
                "name": "simulated_load",
                "value": load_factor,
                "unit": "percent",
                "threshold_warning": check.metadata.get("threshold_warning", 70.0),
                "threshold_critical": check.metadata.get("threshold_critical", 90.0)
            }
        ]

    # Enable the custom check
    await monitor.enable_check("custom_time_check")
    print("✓ Custom check enabled")

    # Wait and run the custom check
    print("\nRunning custom check...")
    await asyncio.sleep(15)

    custom_result = await monitor.run_check("custom_time_check")
    print(f"  Custom check status: {custom_result.status.value}")
    for metric in custom_result.metrics:
        print(f"    {metric.name}: {metric.value:.1f}{metric.unit}")

    # Demonstrate alerts
    print("\n\nAlert Management Demo...")

    # Create an alert manually by simulating a failure
    if "test_service" not in monitor._checks:
        monitor.register_check(
            name="test_service",
            check_type=CheckType.SERVICE_AVAILABILITY,
            description="Test service for alert demo",
            interval=5,
            service_config={"host": "nonexistent.service.local", "port": 9999}
        )

    # Run the check to generate an alert
    await monitor.enable_check("test_service")
    await asyncio.sleep(2)
    await monitor.run_check("test_service")

    # Check for alerts
    if monitor._active_alerts:
        print(f"  Active alerts: {len(monitor._active_alerts)}")
        for alert_id, alert in list(monitor._active_alerts.items())[:3]:
            print(f"    - {alert_id}: {alert.severity.value} - {alert.message}")

            # Acknowledge the alert
            await monitor.acknowledge_alert(alert_id, "demo_user")
            print(f"      ✓ Acknowledged by demo_user")

    # Get uptime statistics
    print("\n\nUptime Statistics:")
    for check_name in list(monitor._checks.keys())[:5]:
        uptime = monitor.calculate_uptime(check_name, hours=1)
        print(f"  {check_name}: {uptime:.1f}% (last hour)")

    # Get metrics history
    print("\n\nMetrics History Sample:")
    if "cpu_usage_cpu_percent" in monitor._metrics_history:
        history = await monitor.get_metrics_history("cpu_usage_cpu_percent", limit=5)
        print("  CPU Usage (last 5 readings):")
        for timestamp, value in history:
            print(f"    {timestamp.strftime('%H:%M:%S')}: {value:.1f}%")

    # Cleanup
    print("\n\nShutting down health monitor...")
    await monitor.shutdown()
    print("✓ Shutdown complete")


if __name__ == "__main__":
    asyncio.run(demonstrate_health_monitoring())