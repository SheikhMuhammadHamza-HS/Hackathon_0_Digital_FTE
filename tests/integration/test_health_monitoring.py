"""
Integration tests for health monitoring system.

These tests validate that the health monitoring system correctly
tracks system health, generates alerts, and provides accurate reports.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

from ai_employee.utils.health_monitor import (
    HealthMonitor, HealthStatus, HealthCheck, Alert,
    HealthCheckConfig, AlertLevel
)
from ai_employee.core.event_bus import get_event_bus
from ai_employee.core.config import AppConfig


class TestHealthMonitoringIntegration:
    """Integration tests for health monitoring."""

    @pytest.fixture
    async def health_monitor(self):
        """Create health monitor for testing."""
        config = HealthCheckConfig(
            check_interval=1.0,  # Short interval for testing
            metrics_retention_hours=1,
            alert_retention_hours=1
        )
        monitor = HealthMonitor(config)
        await monitor.initialize()
        yield monitor
        await monitor.shutdown()

    @pytest.fixture
    async def event_bus(self):
        """Create event bus for testing."""
        event_bus = get_event_bus()
        await event_bus.start_background_processing()
        yield event_bus
        await event_bus.stop_background_processing()

    @pytest.mark.asyncio
    async def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initializes correctly."""
        assert health_monitor.is_running
        assert len(health_monitor.checks) > 0
        assert health_monitor.get_overall_status() == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_system_resource_checks(self, health_monitor):
        """Test system resource health checks."""
        # Wait for initial checks to run
        await asyncio.sleep(2)

        # Check that system checks exist
        system_checks = [c for c in health_monitor.checks if c.name in ["cpu_usage", "memory_usage", "disk_usage"]]
        assert len(system_checks) >= 3

        # Verify checks have run
        for check in system_checks:
            assert check.last_check is not None
            assert check.status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]

    @pytest.mark.asyncio
    async def test_health_report_generation(self, health_monitor):
        """Test health report generation."""
        # Wait for checks to run
        await asyncio.sleep(2)

        # Generate health report
        report = await health_monitor.generate_health_report()

        # Verify report structure
        assert report.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
        assert len(report.checks) > 0
        assert report.timestamp is not None
        assert report.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_alert_generation(self, health_monitor):
        """Test alert generation for unhealthy checks."""
        # Create a check that will fail
        failing_check = HealthCheck(
            name="test_failing_check",
            check_type="test",
            target="test://fail",
            interval=1.0,
            timeout=1.0
        )

        # Mock the check to always fail
        async def failing_check_func():
            raise Exception("Simulated check failure")

        failing_check.execute_check = failing_check_func
        health_monitor.add_check(failing_check)

        # Wait for check to run and generate alert
        await asyncio.sleep(2)

        # Check for alerts
        alerts = await health_monitor.get_active_alerts()
        failing_alerts = [a for a in alerts if a.check_name == "test_failing_check"]
        assert len(failing_alerts) > 0
        assert failing_alerts[0].level in [AlertLevel.ERROR, AlertLevel.CRITICAL]

    @pytest.mark.asyncio
    async def test_metrics_collection(self, health_monitor):
        """Test metrics collection and history."""
        # Wait for metrics to be collected
        await asyncio.sleep(2)

        # Get current metrics
        metrics = await health_monitor.get_current_metrics()

        # Verify system metrics exist
        assert "cpu_usage" in metrics or "memory_usage" in metrics
        for metric_name, metric in metrics.items():
            assert metric.value is not None
            assert metric.unit is not None
            assert metric.timestamp is not None

    @pytest.mark.asyncio
    async def test_custom_health_check(self, health_monitor):
        """Test adding and running custom health checks."""
        # Create custom check
        custom_check = HealthCheck(
            name="custom_check",
            check_type="test",
            target="test://custom",
            interval=1.0,
            timeout=1.0
        )

        # Mock successful check
        async def custom_check_func():
            return {"status": "healthy", "response_time": 0.1}

        custom_check.execute_check = custom_check_func
        health_monitor.add_check(custom_check)

        # Wait for check to run
        await asyncio.sleep(2)

        # Verify check results
        check = health_monitor.get_check("custom_check")
        assert check is not None
        assert check.status == HealthStatus.HEALTHY
        assert check.last_check is not None

    @pytest.mark.asyncio
    async def test_health_check_removal(self, health_monitor):
        """Test removing health checks."""
        # Add a test check
        test_check = HealthCheck(
            name="removable_check",
            check_type="test",
            target="test://remove",
            interval=1.0,
            timeout=1.0
        )
        health_monitor.add_check(test_check)
        assert health_monitor.get_check("removable_check") is not None

        # Remove the check
        health_monitor.remove_check("removable_check")
        assert health_monitor.get_check("removable_check") is None

    @pytest.mark.asyncio
    async def test_alert_acknowledgement(self, health_monitor):
        """Test alert acknowledgement functionality."""
        # Create an alert
        alert = Alert(
            check_name="test_check",
            level=AlertLevel.WARNING,
            message="Test alert",
            timestamp=datetime.now(timezone.utc)
        )
        health_monitor.add_alert(alert)

        # Get active alerts
        alerts = await health_monitor.get_active_alerts()
        assert len(alerts) > 0
        assert not alerts[0].acknowledged

        # Acknowledge the alert
        await health_monitor.acknowledge_alert(alert.id)

        # Verify alert is acknowledged
        alerts = await health_monitor.get_active_alerts()
        test_alerts = [a for a in alerts if a.check_name == "test_check"]
        if test_alerts:
            assert test_alerts[0].acknowledged

    @pytest.mark.asyncio
    async def test_health_status_changes(self, health_monitor, event_bus):
        """Test health status change events."""
        events_received = []

        async def event_handler(event):
            events_received.append(event)

        # Subscribe to health events
        await event_bus.subscribe("health_status_changed", event_handler)

        # Create a check that changes status
        status_check = HealthCheck(
            name="status_change_check",
            check_type="test",
            target="test://status",
            interval=1.0,
            timeout=1.0
        )

        # Mock check to change status
        call_count = 0
        async def status_check_func():
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return {"status": "healthy", "response_time": 0.1}
            else:
                raise Exception("Status check failure")

        status_check.execute_check = status_check_func
        health_monitor.add_check(status_check)

        # Wait for status changes
        await asyncio.sleep(3)

        # Verify status change events were published
        health_events = [e for e in events_received if e.get("event_type") == "health_status_changed"]
        assert len(health_events) > 0

    @pytest.mark.asyncio
    async def test_component_health_integration(self, health_monitor):
        """Test integration with other system components."""
        # Test that health monitor can check component health
        component_checks = [
            ("event_bus", "Event Bus Health"),
            ("file_monitor", "File Monitor Health"),
            ("workflow_engine", "Workflow Engine Health")
        ]

        for component_name, description in component_checks:
            check = health_monitor.get_check(f"{component_name}_health")
            if check:
                assert check.last_check is not None
                assert check.status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]

    @pytest.mark.asyncio
    async def test_health_monitor_persistence(self, health_monitor):
        """Test health monitor data persistence."""
        # Wait for some data to be collected
        await asyncio.sleep(2)

        # Get metrics history
        history = await health_monitor.get_metrics_history("cpu_usage", hours=1)
        if history:  # Only check if metrics were collected
            assert len(history) > 0
            for metric in history:
                assert metric.value is not None
                assert metric.timestamp is not None

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, health_monitor):
        """Test concurrent execution of health checks."""
        # Add multiple checks with short intervals
        for i in range(5):
            check = HealthCheck(
                name=f"concurrent_check_{i}",
                check_type="test",
                target=f"test://concurrent/{i}",
                interval=0.5,
                timeout=0.5
            )

            async def check_func():
                await asyncio.sleep(0.1)  # Simulate some work
                return {"status": "healthy", "response_time": 0.1}

            check.execute_check = check_func
            health_monitor.add_check(check)

        # Wait for all checks to run
        await asyncio.sleep(2)

        # Verify all checks ran successfully
        for i in range(5):
            check = health_monitor.get_check(f"concurrent_check_{i}")
            assert check is not None
            assert check.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_monitor_error_handling(self, health_monitor):
        """Test health monitor error handling."""
        # Create a check that throws an exception
        error_check = HealthCheck(
            name="error_check",
            check_type="test",
            target="test://error",
            interval=1.0,
            timeout=1.0
        )

        # Mock check to raise an exception
        async def error_check_func():
            raise ValueError("Test error in health check")

        error_check.execute_check = error_check_func
        health_monitor.add_check(error_check)

        # Wait for check to run
        await asyncio.sleep(2)

        # Verify error was handled
        check = health_monitor.get_check("error_check")
        assert check is not None
        assert check.status == HealthStatus.CRITICAL
        assert "error" in check.message.lower()

    @pytest.mark.asyncio
    async def test_health_monitor_shutdown(self, health_monitor):
        """Test health monitor graceful shutdown."""
        # Verify monitor is running
        assert health_monitor.is_running

        # Shutdown monitor
        await health_monitor.shutdown()

        # Verify monitor is stopped
        assert not health_monitor.is_running

        # Verify no background tasks are running
        assert health_monitor._monitor_task is None or health_monitor._monitor_task.done()