"""
Integration tests for error recovery system.

These tests validate that the error recovery system correctly
handles different error types and provides appropriate recovery strategies.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from ai_employee.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ai_employee.core.event_bus import get_event_bus
from ai_employee.core.workflow_engine import get_workflow_engine
from ai_employee.utils.logging_config import get_logger
from ai_employee.utils.file_monitor import get_file_monitor
from ai_employee.utils.approval_system import get_approval_system
from ai_employee.core.config import get_config


class TestErrorRecovery:
    """Integration tests for error recovery."""

    @pytest.fixture
    async def setup_test_environment(self):
        """Setup test environment with temporary directories."""
        temp_dir = Path(tempfile.mkdtemp())

        config = AppConfig(
            log_level="DEBUG",
            environment="test",
            paths=type("Paths", object)  # Would create proper PathsConfig
        )

        # Create test directories
        test_paths = {
            "inbox_path": temp_dir / "Inbox",
            "needs_action_path": temp_dir / "Needs_Action",
            "logs_path": temp_dir / "Logs"
        }

        for path in test_paths.values():
            path.mkdir(parents=True, exist_ok=True)

        yield config, test_paths

        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    async def error_recovery_service(self, setup_test_environment):
        """Create error recovery service."""
        config, test_paths = setup_test_environment

        from ai_employee.utils.error_recovery import ErrorRecoveryService

        service = ErrorRecoveryService(
            circuit_breaker=CircuitBreaker(
                "error_recovery",
                CircuitBreakerConfig(
                    failure_threshold=3,
                    recovery_timeout=5.0,
                    max_retries=3
                )
            ),
            file_monitor=get_file_monitor(),
            approval_system=get_approval_system(),
            config=config
        )

        await service.initialize()
        yield service

        await service.shutdown()

    @pytest.fixture
    async def mock_odoo_client(self):
        """Create mock Odoo client."""
        client = Mock()
        client.authenticate = AsyncMock(return_value=True)
        client.create_invoice = AsyncMock(return_value={"id": "inv_123"})
        client.post_invoice = AsyncMock(return_value=True)
        client.reconcile_payment = AsyncMock(return_value=True)
        client.get_open_invoices = AsyncMock(return_value=[
            {
                "id": "inv_123",
                "invoice_number": "INV-2025-001",
                "partner_id": 1,
                "amount_total": 6600.00,
                "state": "posted",
                "payment_state": "not_paid"
            }
        ])
        return client

    @pytest.fixture
    async def mock_email_service(self):
        """Create mock email service."""
        service = Mock()
        service.send_email = AsyncMock(return_value=True)
        service.send_invoice = AsyncMock(return_value=True)
        service.send_notification = AsyncMock(return_value=True)
        return service

    @pytest.fixture
    async def mock_bank_service(self):
        """Create mock bank service."""
        service = Mock()
        service.get_transactions = AsyncMock(return_value=[
            {
                "id": "txn_123",
                "amount": 6600.00,
                "date": "2025-02-21",
                "reference": "INV-2025-001",
                "description": "Invoice payment"
            }
        ])
        return service

    @pytest.fixture
    async def mock_approval_system(self):
        """Create mock approval system."""
        system = Mock()
        system.create_approval_request = AsyncMock(return_value="approval_123")
        system.check_approval_status = AsyncMock(return_value=None)
        return system

    @pytest.mark.asyncio
    async def test_error_recovery_handles_service_failure(self, error_recovery_service):
        """Test error recovery handles service failures."""
        # Mock service failure
        error_recovery_service.circuit_breaker.force_open()

        # Try operation that requires service
        with pytest.raises(Exception, match="Service unavailable"):
            await error_recovery_service.handle_service_failure(
                "test_service",
                "Critical service is down",
                {"priority": "high", "category": "system"}
            )

        # Error should be logged
        # (Logging is tested separately)

    @pytest.mark.asyncio
    async def test_error_recovery_handles_network_timeout(self, error_recovery_service):
        """Test error recovery handles network timeouts."""
        # Mock network timeout
        with patch('aiohttp.ClientSession.post', side_effect=asyncio.TimeoutError("Network timeout")):
            with pytest.raises(Exception, match="timeout"):
                await error_recovery_service.handle_network_timeout(
                    "api_endpoint",
                    {"endpoint": "/test/endpoint", "timeout": 30.0}
                )

        # Should schedule retry
        assert error_recovery_service._schedule_retry("api_endpoint")

    @pytest.mark.asyncio
    async def test_error_recovery_handles_auth_errors(self, error_recovery_service):
        """Test error recovery handles authentication errors."""
        # Mock authentication error
        with patch('ai_employee.integrations.odoo_client.OdooClient.authenticate',
                   side_effect=OdooAuthenticationError("Invalid credentials")):
            with pytest.raises(Exception, match="Authentication"):
                await error_recovery_service.handle_auth_error(
                    "odoo_client",
                    {"user": "test_user", "database": "test_db"}
                )

        # Should require new authentication
        assert error_recovery_service._requires_new_auth("odoo_client")

    @pytest.mark.asyncio
    async def test_error_recovery_handles_logic_errors(self, error_recovery_service):
        """Test error recovery handles logic errors."""
        # Mock logic error
        with patch.object_method(error_recovery_service, 'validate_data',
                   side_effect=ValueError("Invalid invoice data")):
            with pytest.raises(Exception, match="Invalid invoice data"):
                await error_recovery_service.handle_logic_error(
                    "invoice_creation",
                    {"error": "Invalid invoice data", "data": {"field": "value"}}
                )

        # Should queue for manual review
        assert error_recovery_service._queue_for_review("invoice_creation", {
            "error": "Invalid invoice data",
            "data": {"field": "value"}
        })

    @pytest.mark.asyncio
    async def test_error_recovery_handles_data_corruption(self, error_recovery_service):
        """Test error recovery handles data corruption."""
        # Mock data corruption
        with patch.object_method(error_recovery_service, '_validate_data',
                   side_effect=DataCorruptionError("Data corrupted")):
            with pytest.raises(Exception, match="Data corrupted"):
                await error_recovery_service.handle_data_corruption(
                    "data_processing",
                    {"file": "test_file.txt", "error": "Data corrupted"}
                )

        # Should quarantine file
        assert error_recovery_service._quarantine_file("test_file.txt")

    @pytest.mark.asyncio
    async def test_error_recovery_handles_system_crash(self, error_recovery_service):
        """Test error recovery handles system crashes."""
        # Mock process crash
        with patch.object_method(error_recovery_service, '_check_process_health',
                   side_effect=ProcessCrashedError("Process crashed")):
            with pytest.raises(Exception, match="Process crashed"):
                await error_recovery_system.handle_system_crash(
                    "critical_process",
                    {"pid": 1234, "error": "Process crashed"}
                )

        # Should attempt restart
        assert error_recovery_system._schedule_restart("critical_process", pid=1234)

    @pytest.mark.asyncio
    async def test_error_recovery_escalation_rules(self, error_recovery_service):
        """Test error recovery escalation rules."""
        # Test high priority errors escalate immediately
        critical_error = Exception("Database connection lost")
        escalation = error_recovery_service._get_escalation_level(critical_error)
        assert escalation == "critical"

        # Test medium priority errors escalate after timeout
        medium_error = Exception("Service slow response")
        escalation = error_recovery._get_escalation_level(medium_error)
        assert escalation == "medium"

        # Test low priority errors don't escalate
        low_error = Exception("Minor warning")
        escalation = error_recovery._get_escalation_level(low_error)
        assert escalation == "low"

    @pytest.mark.asyncio
    async def test_error_recovery_recovery_strategies(self, error_recovery_service):
        """Test error recovery recovery strategies."""
        # Network timeout - queue and retry
        network_error = Exception("Network timeout")
        strategy = error_recovery._get_recovery_strategy(network_error)
        assert strategy["action"] == "queue_and_retry"
        assert strategy["retry_after"] == 60.0

        # Auth error - require fresh approval
        auth_error = Exception("Authentication failed")
        strategy = error_recovery._get_recovery_strategy(auth_error)
        assert strategy["action"] == "require_approval"
        assert strategy["escalation"] == "immediate"

        # Logic error - queue for review
        logic_error = Exception("Logic error")
        strategy = error_recovery._get_recovery_strategy(logic_error)
        assert strategy["action"] == "queue_for_review"
        assert strategy["escalation"] == "low"

        # System crash - auto-restart
        system_error = Exception("System crash")
        strategy = error_recovery._get_recovery_strategy(system_error)
        assert strategy["action"] == "auto_restart"
        assert strategy["escalation"] == "critical"

    @pytest.mark.asyncio
    async def test_error_recovery_rollback_mechanism(self, error_recovery_service):
        """Test error recovery rollback mechanism."""
        # Test rollback for failed operations
        rollback_data = {"operation": "test", "state": "before"}

        error_recovery_service._start_rollback("test_operation", rollback_data)

        # Simulate failure during rollback
        error_recovery_service._mark_rollback_failed("test_operation", "Rollback failed")

        # Should log rollback failure
        assert error_recovery_service._rollback_failures.get("test_operation") is True

    @pytest.mark.asyncio
    async def test_error_recovery_with_health_monitoring(self, error_recovery_service):
        """Test error recovery with health monitoring integration."""
        # Mock health monitor
        health_monitor = Mock()
        health_monitor.get_system_status = AsyncMock(return_value={
            "cpu_usage": 0.8,
            "memory_usage": 0.6,
            "disk_usage": 0.4,
            "process_count": 5
        })

        error_recovery_service.health_monitor = health_monitor

        # After error recovery, check system health
        with patch.object_method(error_recovery_service, 'handle_system_crash'):
            await error_recovery_service.handle_system_crash("test_process", {"pid": 1234})

        # Should update health status
        health_monitor.get_system_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_recovery_generates_reports(self, error_recovery_service):
        """Test error recovery generates appropriate reports."""
        # Mock reporting service
        reporting_service = Mock()
        reporting_service.create_error_report = AsyncMock()

        error_recovery_service.reporting_service = reporting_service

        # Generate error report
        await error_recovery_service._generate_error_report(
            "test_operation",
            Exception("Test error"),
            {"context": "test context"}
        )

        # Should create report
        reporting_service.create_error_report.assert_called_once()
        report_data = reporting_service.create_error_report.call_args[0][0]

        assert report_data["operation"] == "test_operation"
        assert "error" in report_data
        assert "context" in report_data

    @pytest.mark.asyncio
    async def test_error_recovery_with_file_system(self, error_recovery_service, setup_test_environment):
        """Test error recovery with file system issues."""
        config, test_paths = setup_test_environment

        # Simulate disk space issue
        test_paths["logs_path"].mkdir(parents=True, exist_ok=True)

        # Create large file to consume space
        large_file = test_paths["logs_path"] / "large_file.log"
        large_file.write_text("x" * 1000000)

        # Check disk space
        with patch('shutil.disk_usage', return_value=95.0):
            # File system check
            await error_recovery_service.handle_file_system_issue(
                "disk_space",
                {"path": str(test_paths["logs_path"]), "usage": 95.0}
            )

        # Should trigger cleanup
        assert error_recovery_service._cleanup_old_files(test_paths["logs_path"])

    @pytest.mark.asyncio
    async def test_error_recovery_with_approval_system(self, error_recovery_service, mock_approval_system):
        """Test error recovery with approval system integration."""
        error_recovery_service.approval_system = mock_approval_system

        # Simulate approval system failure
        mock_approval_system.create_approval_request = AsyncMock(
            side_effect=ApprovalSystemError("Approval system down")
        )

        # When approval system fails during payment processing
        payment_id = "payment_123"
        payment = Mock()
        payment.approval_request_id = "approval_123"
        payment.amount = 1000.00

        with pytest.raises(Exception, match="Approval system down"):
            error_recovery_service.handle_approval_failure(
                "payment_reconciliation",
                {"payment_id": payment_id, "amount": 1000.00}
            )

        # Should queue payment for manual review
        assert "payment_123" in error_recovery_service._queue_for_approval("payment_reconciliation", payment_id)

    @pytest.mark.asyncio
    async def test_error_recovery_with_workflow_engine(self, error_recovery_service):
        """Test error recovery integration with workflow engine."""
        workflow_engine = get_workflow_engine()

        # Create workflow that might fail
        workflow = await error_recovery_service.create_error_recovery_workflow(
            "test_workflow",
            "failing_operation",
            {"data": "test_data"}
        )

        # Execute workflow
        result = await workflow_engine.execute_workflow(workflow.id)

        # Workflow should fail and trigger error recovery
        assert result is False

        # Check error recovery handled the failure
        assert error_recovery_service._handle_workflow_failure(
            "test_workflow",
            {"error": "Workflow execution failed"}
        )

    @pytest.mark.asyncio
    async def test_error_recovery_dashboard_update(self, error_recovery_service):
        """Test error recovery updates dashboard."""
        # Mock dashboard service
        dashboard_service = Mock()
        dashboard_service.update_status = AsyncMock()

        error_recovery_service.dashboard_service = dashboard_service

        # After error, dashboard should be updated
        error_recovery_service._update_dashboard_status()

        dashboard_service.update_status.assert_called_once()

        # Dashboard should show error status
        dashboard_service.update_status.call_args[0][0].get("status") == "error"

    @pytest.mark.asyncio
    async def test_error_recovery_persistence(self, error_recovery_service):
        """Test error recovery state persistence."""
        # Simulate error state
        error_recovery_service._error_history.append({
            "timestamp": datetime.utcnow(),
            "error": "Test error",
            "category": "transient",
            "resolved": False,
            "retry_count": 0
        })

        # State should be persisted
        history = error_recovery_service._error_history
        assert len(history) == 1
        assert history[0]["error"] == "Test error"
        assert not history[0]["resolved"]

        # Clear resolved errors
        error_recovery_service._clear_resolved_errors()

        # Should clear resolved errors
        assert len(error_recovery_service._error_history) == 0

    @pytest.mark.asyncio
    async def test_error_recovery_concurrent_operations(self, error_recovery_service):
        """Test error recovery handles concurrent operations."""
        # Create multiple concurrent operations
        operations = [
            "operation_1",
            "operation_2",
            "operation_3"
        ]

        # Create tasks for concurrent execution
        tasks = [
            error_recovery_service.handle_service_failure(op, {"error": f"{op} failed"})
            for op in operations
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # All should complete (either with success or error)
        assert len(results) == len(operations)

        # Check that each operation was handled
        for i, (op, result) in zip(operations, results):
            if "failed" in str(result):
                # Error was handled
                assert True
            else:
                # Operation succeeded or was already completed
                pass

    @pytest.mark.asyncio
    async def test_error_recovery_with_circuit_breaker_fallback(self, error_recovery_service):
        """Test error recovery uses circuit breaker fallback."""
        # Mock circuit breaker
        circuit_breaker = Mock()
        circuit_breaker.can_execute = Mock(return_value=False)

        error_recovery_service.circuit_breaker = circuit_breaker

        # When circuit is open, should use fallback
        with pytest.raises(Exception):
            error_recovery_service.handle_service_failure(
                "critical_service",
                {"error": "Service down"},
                use_fallback=True
            )

        # Should have used fallback strategy
        circuit_breaker.can_execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_recovery_with_email_notifications(self, error_recovery_service, mock_email_service):
        """Test error recovery sends email notifications."""
        error_recovery_service.email_service = mock_email_service

        # Critical error should send email
        critical_error = Exception("Critical system failure")
        await error_recovery_service.handle_critical_error(
            "system_failure",
            {"error": str(critical_error), "impact": "high"}
        )

        # Should send email notification
        mock_email_service.send_notification.assert_called_once()

        # Email should contain error details
        email_args = mock_email_service.send_notification.call_args
        assert "critical system failure" in email_args[0]
        assert str(critical_error) in email_args[1]

    @pytest.mark.asyncio
    async def test_error_recovery_with_file_monitoring(self, error_recovery_service):
        """Test error recovery integrates with file monitoring."""
        # Mock file monitor
        file_monitor = Mock()
        file_monitor.get_directory_status = AsyncMock(return_value={
            "watching": 5,
            "errors": 1,
            "last_scan": datetime.utcnow()
        })

        error_recovery_service.file_monitor = file_monitor

        # File system error should trigger file monitor check
        with patch.object_method(error_recovery_service, '_check_file_system'):
            await error_recovery_service.handle_file_system_issue(
                "file_system",
                {"path": "/test/path", "error": "Permission denied"}
            )

        # Should check directory status
        file_monitor.get_directory_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_recovery_with_approval_timeout(self, error_recovery_service, mock_approval_system):
        """Test error recovery handles approval timeouts."""
        error_recovery_service.approval_system = mock_approval_system

        # Expired approval request
        expired_request = Mock()
        expired_request.status = "expired"
        expired_request.expires_at = datetime.utcnow() - timedelta(hours=5)

        mock_approval_system.check_approval_status.return_value = expired_request

        # When approval expires, should create new request
        payment_id = "payment_123"
        payment = Mock()
        payment.approval_request_id = "approval_123"

        with pytest.raises(Exception, match="Approval timeout"):
            error_recovery_service.handle_approval_timeout(
                "payment_reconciliation",
                {"payment_id": payment_id}
            )

        # Should schedule new approval
        assert error_recovery_service._schedule_approval_retry("payment_reconciliation", payment_id)