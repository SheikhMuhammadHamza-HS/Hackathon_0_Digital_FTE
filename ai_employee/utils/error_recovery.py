"""
Error recovery service for AI Employee system.

Handles different error types with appropriate recovery strategies,
rollback mechanisms, and integration with circuit breaker and workflow engine.
"""

import asyncio
import logging
import os
import shutil
import time
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
import json
import uuid
import traceback

from ..core.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitState
from ..core.event_bus import get_event_bus, Event, EventPriority
from ..core.workflow_engine import get_workflow_engine, WorkflowStatus
from ..core.config import get_config, AppConfig
from ..utils.logging_config import get_logger
from ..utils.file_monitor import get_file_monitor
from ..utils.approval_system import get_approval_system
from ..utils.health_monitor import get_health_monitor, HealthStatus, HealthEvent

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    AUTH = "auth"
    LOGIC = "logic"
    SYSTEM = "system"
    DATA_CORRUPTION = "data_corruption"
    PROCESS_CRASH = "process_crash"
    APPROVAL_SYSTEM = "approval_system"
    FILE_SYSTEM = "file_system"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Recovery action types."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    NO_RETRY_HUMAN = "no_retry_human"
    QUEUE_FOR_REVIEW = "queue_for_review"
    AUTO_RESTART = "auto_restart"
    QUARANTINE_FILE = "quarantine_file"
    FALLBACK = "fallback"
    ESCALATE = "escalate"


@dataclass
class ErrorEvent(Event):
    """Event published when an error occurs."""
    operation: str = field(default_factory="")
    error_category: ErrorCategory = field(default_factory=ErrorCategory.NETWORK)
    error_severity: ErrorSeverity = field(default_factory=ErrorSeverity.MEDIUM)
    error_message: str = field(default_factory="")
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_strategy: Optional[Dict[str, Any]] = field(default_factory=lambda: None)
    retry_count: int = field(default_factory=0)
    resolved: bool = field(default_factory=False)


@dataclass
class RollbackInfo:
    """Information for rolling back failed operations."""
    operation_id: str = field(default_factory="")
    operation_type: str = field(default_factory="")
    rollback_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: str = field(default_factory="pending")  # pending, in_progress, completed, failed


@dataclass
class RecoveryStrategy:
    """Recovery strategy configuration."""
    action: RecoveryAction
    max_retries: int = 3
    backoff_factor: float = 2.0
    base_delay: float = 1.0
    escalation_level: str = "medium"
    requires_approval: bool = False
    rollback_supported: bool = True


# Custom exceptions
class DataCorruptionError(Exception):
    """Data corruption detected."""
    pass


class ProcessCrashedError(Exception):
    """Process crashed unexpectedly."""
    pass


class ApprovalSystemError(Exception):
    """Approval system failure."""
    pass


class FileSystemError(Exception):
    """File system operation failed."""
    pass


class ErrorRecoveryService:
    """Service for handling error recovery with different strategies."""

    def __init__(
        self,
        circuit_breaker: CircuitBreaker,
        file_monitor=None,
        approval_system=None,
        config=None
    ):
        """Initialize error recovery service.

        Args:
            circuit_breaker: Circuit breaker instance
            file_monitor: File monitor instance
            approval_system: Approval system instance
            config: Application configuration
        """
        self.circuit_breaker = circuit_breaker
        self.file_monitor = file_monitor or get_file_monitor()
        self.approval_system = approval_system or get_approval_system()
        self.config = config or get_config()
        self.event_bus = get_event_bus()
        self.workflow_engine = get_workflow_engine()
        self.health_monitor = get_health_monitor()

        # Error tracking
        self._error_history: List[Dict[str, Any]] = []
        self._active_rollbacks: Dict[str, RollbackInfo] = {}
        self._rollback_failures: Dict[str, bool] = {}
        self._retry_queue: asyncio.Queue = asyncio.Queue()
        self._approval_queue: asyncio.Queue = asyncio.Queue()
        self._review_queue: asyncio.Queue = asyncio.Queue()

        # Recovery strategies by error category
        self._recovery_strategies = {
            ErrorCategory.NETWORK: RecoveryStrategy(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                max_retries=5,
                backoff_factor=2.0,
                base_delay=1.0,
                escalation_level="medium"
            ),
            ErrorCategory.AUTH: RecoveryStrategy(
                action=RecoveryAction.NO_RETRY_HUMAN,
                max_retries=0,
                escalation_level="high",
                requires_approval=True,
                rollback_supported=False
            ),
            ErrorCategory.LOGIC: RecoveryStrategy(
                action=RecoveryAction.QUEUE_FOR_REVIEW,
                max_retries=2,
                backoff_factor=1.5,
                base_delay=0.5,
                escalation_level="low"
            ),
            ErrorCategory.SYSTEM: RecoveryStrategy(
                action=RecoveryAction.AUTO_RESTART,
                max_retries=1,
                escalation_level="critical",
                rollback_supported=True
            ),
            ErrorCategory.DATA_CORRUPTION: RecoveryStrategy(
                action=RecoveryAction.QUARANTINE_FILE,
                max_retries=0,
                escalation_level="high",
                rollback_supported=False
            ),
            ErrorCategory.PROCESS_CRASH: RecoveryStrategy(
                action=RecoveryAction.AUTO_RESTART,
                max_retries=3,
                escalation_level="critical",
                rollback_supported=True
            ),
            ErrorCategory.APPROVAL_SYSTEM: RecoveryStrategy(
                action=RecoveryAction.ESCALATE,
                max_retries=0,
                escalation_level="high",
                requires_approval=True,
                rollback_supported=False
            ),
            ErrorCategory.FILE_SYSTEM: RecoveryStrategy(
                action=RecoveryAction.FALLBACK,
                max_retries=2,
                backoff_factor=1.5,
                base_delay=2.0,
                escalation_level="medium"
            )
        }

        # Background tasks
        self._retry_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize the error recovery service."""
        logger.info("Initializing Error Recovery Service")

        # Start background tasks
        self._retry_task = asyncio.create_task(self._retry_worker())
        self._monitoring_task = asyncio.create_task(self._monitor_resources())
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())

        # Subscribe to event bus for error events
        self.event_bus.subscribe(ErrorEvent, self._handle_error_event)

        # Register error recovery health checks
        await self._register_health_checks()

        logger.info("Error Recovery Service initialized successfully")

    async def shutdown(self):
        """Shutdown the error recovery service."""
        logger.info("Shutting down Error Recovery Service")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for background tasks to complete
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Error Recovery Service shutdown complete")

    async def handle_service_failure(
        self,
        service_name: str,
        context: Dict[str, Any],
        use_fallback: bool = False
    ) -> None:
        """Handle service failure.

        Args:
            service_name: Name of the failed service
            context: Error context information
            use_fallback: Whether to use fallback mechanism

        Raises:
            Exception: When service is unavailable
        """
        error_message = f"Service {service_name} failure"

        # Check circuit breaker state
        if not use_fallback and not self.circuit_breaker.can_execute():
            raise Exception("Service unavailable - circuit breaker open")

        # Log error and apply recovery strategy
        logger.error(f"Service failure: {service_name} - {context}")

        # Create error event
        error_event = ErrorEvent(
            operation=f"{service_name}_failure",
            error_category=ErrorCategory.SYSTEM,
            error_severity=ErrorSeverity.HIGH if context.get("priority") == "high" else ErrorSeverity.MEDIUM,
            error_message=error_message,
            context=context,
            source="error_recovery_service"
        )

        await self.event_bus.publish(error_event)

        # If circuit is open and fallback is requested, use fallback strategy
        if self.circuit_breaker.state == CircuitState.OPEN and use_fallback:
            await self._execute_fallback(service_name, context)

    async def handle_network_timeout(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle network timeout.

        Args:
            operation: Operation that timed out
            context: Operation context

        Raises:
            Exception: When timeout occurs
        """
        error_message = f"Network timeout for operation: {operation}"

        logger.warning(f"Network timeout: {operation}")

        # Apply recovery strategy
        strategy = self._recovery_strategies[ErrorCategory.NETWORK]
        await self._apply_recovery_strategy(
            operation,
            ErrorCategory.NETWORK,
            error_message,
            context,
            strategy
        )

        # Raise exception to propagate error
        raise Exception(error_message)

    async def handle_auth_error(
        self,
        service_name: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle authentication error.

        Args:
            service_name: Service requiring authentication
            context: Authentication context

        Raises:
            Exception: When authentication fails
        """
        error_message = f"Authentication failed for service: {service_name}"

        logger.error(f"Auth error: {service_name}")

        # Apply recovery strategy
        strategy = self._recovery_strategies[ErrorCategory.AUTH]
        await self._apply_recovery_strategy(
            f"{service_name}_auth",
            ErrorCategory.AUTH,
            error_message,
            context,
            strategy
        )

        # Mark that new authentication is required
        self._mark_auth_required(service_name)

        raise Exception(error_message)

    async def handle_logic_error(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle business logic error.

        Args:
            operation: Operation with logic error
            context: Error context

        Raises:
            Exception: When logic error occurs
        """
        error_message = context.get("error", f"Logic error in operation: {operation}")

        logger.warning(f"Logic error: {operation} - {error_message}")

        # Apply recovery strategy
        strategy = self._recovery_strategies[ErrorCategory.LOGIC]
        await self._apply_recovery_strategy(
            operation,
            ErrorCategory.LOGIC,
            error_message,
            context,
            strategy
        )

        # Queue for manual review
        await self._queue_for_review(operation, context)

        raise Exception(error_message)

    async def handle_data_corruption(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle data corruption error.

        Args:
            operation: Operation with corrupted data
            context: Error context

        Raises:
            Exception: When data corruption is detected
        """
        error_message = f"Data corruption detected in operation: {operation}"
        file_path = context.get("file")

        logger.error(f"Data corruption: {operation} - {context}")

        # Quarantine corrupted file if specified
        if file_path and await self._quarantine_file(file_path):
            logger.info(f"Quarantined corrupted file: {file_path}")

        # Apply recovery strategy
        strategy = self._recovery_strategies[ErrorCategory.DATA_CORRUPTION]
        await self._apply_recovery_strategy(
            operation,
            ErrorCategory.DATA_CORRUPTION,
            error_message,
            context,
            strategy
        )

        raise Exception(error_message)

    async def handle_system_crash(
        self,
        process_name: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle system crash.

        Args:
            process_name: Name of crashed process
            context: Crash context

        Raises:
            Exception: When process crash occurs
        """
        error_message = f"Process crash: {process_name}"
        pid = context.get("pid")

        logger.critical(f"System crash: {process_name} (pid: {pid})")

        # Schedule restart if possible
        if await self._schedule_restart(process_name, pid):
            logger.info(f"Scheduled restart for process: {process_name}")

        # Apply recovery strategy
        strategy = self._recovery_strategies[ErrorCategory.PROCESS_CRASH]
        await self._apply_recovery_strategy(
            f"{process_name}_crash",
            ErrorCategory.PROCESS_CRASH,
            error_message,
            context,
            strategy
        )

        raise Exception(error_message)

    async def handle_approval_failure(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle approval system failure.

        Args:
            operation: Operation requiring approval
            context: Error context
        """
        error_message = f"Approval system failure for operation: {operation}"

        logger.error(f"Approval failure: {operation} - {context}")

        # Queue operation for manual review
        payment_id = context.get("payment_id")
        if payment_id:
            await self._queue_for_approval(operation, {"payment_id": payment_id})

        # Apply recovery strategy
        strategy = self._recovery_strategies[ErrorCategory.APPROVAL_SYSTEM]
        await self._apply_recovery_strategy(
            operation,
            ErrorCategory.APPROVAL_SYSTEM,
            error_message,
            context,
            strategy
        )

        raise Exception(error_message)

    async def handle_approval_timeout(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle approval timeout.

        Args:
            operation: Operation with expired approval
            context: Timeout context
        """
        error_message = f"Approval timeout for operation: {operation}"

        logger.warning(f"Approval timeout: {operation} - {context}")

        # Schedule new approval request
        payment_id = context.get("payment_id")
        if payment_id:
            await self._schedule_approval_retry(operation, payment_id)

        raise Exception(error_message)

    async def handle_file_system_issue(
        self,
        issue_type: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle file system issues.

        Args:
            issue_type: Type of file system issue
            context: Issue context
        """
        error_message = f"File system issue: {issue_type}"

        logger.error(f"File system issue: {issue_type} - {context}")

        # Handle disk space issues
        if issue_type == "disk_space":
            path = context.get("path")
            if path:
                await self._cleanup_old_files(Path(path))

        # Apply recovery strategy
        strategy = self._recovery_strategies[ErrorCategory.FILE_SYSTEM]
        await self._apply_recovery_strategy(
            f"filesystem_{issue_type}",
            ErrorCategory.FILE_SYSTEM,
            error_message,
            context,
            strategy
        )

    async def handle_critical_error(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle critical system errors.

        Args:
            operation: Operation with critical error
            context: Error context
        """
        error_message = context.get("error", f"Critical error in operation: {operation}")

        logger.critical(f"Critical error: {operation} - {error_message}")

        # Send email notification
        await self._send_critical_notification(operation, error_message, context)

        # Create error event with critical priority
        error_event = ErrorEvent(
            operation=operation,
            error_category=ErrorCategory.SYSTEM,
            error_severity=ErrorSeverity.CRITICAL,
            error_message=error_message,
            context=context,
            priority=EventPriority.CRITICAL,
            source="error_recovery_service"
        )

        await self.event_bus.publish(error_event)

    def _get_escalation_level(self, error: Exception) -> str:
        """Determine escalation level based on error.

        Args:
            error: Exception to evaluate

        Returns:
            Escalation level string
        """
        error_msg = str(error).lower()

        # Critical errors
        critical_keywords = ["database connection", "system crash", "security", "authentication"]
        if any(keyword in error_msg for keyword in critical_keywords):
            return "critical"

        # High priority errors
        high_keywords = ["payment", "invoice", "approval", "data corruption"]
        if any(keyword in error_msg for keyword in high_keywords):
            return "high"

        # Low priority errors
        low_keywords = ["warning", "retry", "timeout"]
        if any(keyword in error_msg for keyword in low_keywords):
            return "low"

        # Default to medium
        return "medium"

    def _get_recovery_strategy(self, error: Exception) -> Dict[str, Any]:
        """Get recovery strategy for error type.

        Args:
            error: Exception to get strategy for

        Returns:
            Recovery strategy dictionary
        """
        error_msg = str(error).lower()

        # Network timeout
        if "timeout" in error_msg or "network" in error_msg:
            return {
                "action": "queue_and_retry",
                "retry_after": 60.0,
                "max_retries": 5
            }

        # Authentication error
        if "auth" in error_msg or "credential" in error_msg:
            return {
                "action": "require_approval",
                "escalation": "immediate"
            }

        # Logic error
        if "logic" in error_msg or "validation" in error_msg:
            return {
                "action": "queue_for_review",
                "escalation": "low"
            }

        # System crash
        if "crash" in error_msg or "system" in error_msg:
            return {
                "action": "auto_restart",
                "escalation": "critical"
            }

        # Default strategy
        return {
            "action": "retry",
            "escalation": "medium"
        }

    def _start_rollback(self, operation_id: str, rollback_data: Dict[str, Any]) -> None:
        """Start rollback for failed operation.

        Args:
            operation_id: ID of operation to rollback
            rollback_data: Data needed for rollback
        """
        rollback_info = RollbackInfo(
            operation_id=operation_id,
            operation_type="rollback",
            rollback_data=rollback_data,
            status="pending"
        )

        self._active_rollbacks[operation_id] = rollback_info
        logger.info(f"Started rollback for operation: {operation_id}")

    def _mark_rollback_failed(self, operation_id: str, reason: str) -> None:
        """Mark rollback as failed.

        Args:
            operation_id: ID of failed rollback
            reason: Reason for failure
        """
        self._rollback_failures[operation_id] = True

        if operation_id in self._active_rollbacks:
            self._active_rollbacks[operation_id].status = "failed"

        logger.error(f"Rollback failed for operation {operation_id}: {reason}")

    def _schedule_retry(self, operation: str) -> bool:
        """Schedule operation for retry.

        Args:
            operation: Operation to retry

        Returns:
            True if scheduled successfully
        """
        try:
            retry_info = {
                "operation": operation,
                "timestamp": datetime.now(timezone.utc),
                "retry_count": 0
            }
            asyncio.create_task(self._retry_queue.put(retry_info))
            return True
        except Exception as e:
            logger.error(f"Failed to schedule retry for {operation}: {e}")
            return False

    def _requires_new_auth(self, service_name: str) -> bool:
        """Check if service requires new authentication.

        Args:
            service_name: Service to check

        Returns:
            True if new auth required
        """
        # Mark service as requiring re-authentication
        return True

    def _queue_for_review(self, operation: str, context: Dict[str, Any]) -> bool:
        """Queue operation for manual review.

        Args:
            operation: Operation to review
            context: Review context

        Returns:
            True if queued successfully
        """
        try:
            review_info = {
                "operation": operation,
                "context": context,
                "timestamp": datetime.now(timezone.utc),
                "status": "pending_review"
            }
            asyncio.create_task(self._review_queue.put(review_info))
            return True
        except Exception as e:
            logger.error(f"Failed to queue {operation} for review: {e}")
            return False

    async def _quarantine_file(self, file_path: str) -> bool:
        """Quarantine corrupted file.

        Args:
            file_path: Path to file to quarantine

        Returns:
            True if quarantined successfully
        """
        try:
            source = Path(file_path)
            if not source.exists():
                return False

            # Create quarantine directory
            quarantine_dir = Path(self.config.paths.archive_path) / "quarantine"
            quarantine_dir.mkdir(parents=True, exist_ok=True)

            # Move file to quarantine
            quarantine_path = quarantine_dir / f"{source.name}.{datetime.now(timezone.utc).isoformat()}"
            shutil.move(str(source), str(quarantine_path))

            logger.info(f"Quarantined file: {source} -> {quarantine_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to quarantine file {file_path}: {e}")
            return False

    def _schedule_restart(self, process_name: str, pid: Optional[int]) -> bool:
        """Schedule process restart.

        Args:
            process_name: Name of process to restart
            pid: Process ID (optional)

        Returns:
            True if restart scheduled
        """
        # In a real implementation, this would interface with process manager
        logger.info(f"Scheduling restart for process: {process_name} (pid: {pid})")
        return True

    async def _generate_error_report(
        self,
        operation: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Generate error report.

        Args:
            operation: Failed operation
            error: Exception that occurred
            context: Error context
        """
        report_data = {
            "operation": operation,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": self._get_escalation_level(error)
        }

        # In a real implementation, this would save to database or file
        logger.info(f"Generated error report for {operation}")

    async def create_error_recovery_workflow(
        self,
        workflow_name: str,
        failing_operation: str,
        context: Dict[str, Any]
    ) -> Any:
        """Create workflow for error recovery.

        Args:
            workflow_name: Name of workflow
            failing_operation: Operation that failed
            context: Error context

        Returns:
            Created workflow
        """
        # Create workflow definition
        workflow_def = {
            "name": workflow_name,
            "description": f"Error recovery workflow for {failing_operation}",
            "steps": [
                {
                    "name": "detect_error",
                    "action": "categorize_error",
                    "input": {"error": failing_operation, "context": context}
                },
                {
                    "name": "apply_recovery",
                    "action": "execute_recovery_strategy",
                    "depends_on": ["detect_error"]
                },
                {
                    "name": "verify_recovery",
                    "action": "check_system_health",
                    "depends_on": ["apply_recovery"]
                }
            ]
        }

        # Create workflow using engine
        workflow = await self.workflow_engine.create_workflow(workflow_def)
        return workflow

    def _handle_workflow_failure(
        self,
        workflow_name: str,
        context: Dict[str, Any]
    ) -> bool:
        """Handle workflow failure.

        Args:
            workflow_name: Name of failed workflow
            context: Failure context

        Returns:
            True if handled successfully
        """
        logger.error(f"Workflow {workflow_name} failed: {context.get('error')}")
        return True

    def _update_dashboard_status(self) -> None:
        """Update dashboard with error status."""
        # In a real implementation, this would update dashboard service
        status_data = {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_errors": len(self._error_history),
            "active_rollbacks": len(self._active_rollbacks)
        }
        logger.info(f"Dashboard status updated: {status_data}")

    def _clear_resolved_errors(self) -> None:
        """Clear resolved errors from history."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self._error_history = [
            error for error in self._error_history
            if error["timestamp"] > cutoff and not error.get("resolved", False)
        ]
        logger.info("Cleared resolved errors from history")

    async def _queue_for_approval(
        self,
        operation: str,
        payment_data: Dict[str, Any]
    ) -> str:
        """Queue payment for manual approval.

        Args:
            operation: Operation requiring approval
            payment_data: Payment information

        Returns:
            Approval request ID
        """
        approval_request = {
            "operation": operation,
            "payment_data": payment_data,
            "timestamp": datetime.now(timezone.utc),
            "status": "pending"
        }

        request_id = str(uuid.uuid4())
        await self._approval_queue.put((request_id, approval_request))
        return request_id

    async def _schedule_approval_retry(
        self,
        operation: str,
        payment_id: str
    ) -> bool:
        """Schedule approval retry.

        Args:
            operation: Operation requiring approval
            payment_id: Payment ID

        Returns:
            True if scheduled successfully
        """
        retry_info = {
            "operation": operation,
            "payment_id": payment_id,
            "retry_after": datetime.now(timezone.utc) + timedelta(hours=1)
        }

        # Schedule retry
        asyncio.create_task(self._retry_queue.put(retry_info))
        return True

    async def _apply_recovery_strategy(
        self,
        operation: str,
        category: ErrorCategory,
        error_message: str,
        context: Dict[str, Any],
        strategy: RecoveryStrategy
    ) -> None:
        """Apply recovery strategy to error.

        Args:
            operation: Failed operation
            category: Error category
            error_message: Error message
            context: Error context
            strategy: Recovery strategy to apply
        """
        # Add to error history
        error_record = {
            "timestamp": datetime.now(timezone.utc),
            "operation": operation,
            "category": category.value,
            "message": error_message,
            "context": context,
            "strategy": strategy.action.value,
            "resolved": False,
            "retry_count": 0
        }
        self._error_history.append(error_record)

        # Execute strategy
        if strategy.action == RecoveryAction.RETRY_WITH_BACKOFF:
            await self._schedule_retry_with_backoff(operation, strategy)
        elif strategy.action == RecoveryAction.QUEUE_FOR_REVIEW:
            await self._queue_for_review(operation, context)
        elif strategy.action == RecoveryAction.AUTO_RESTART:
            await self._execute_auto_restart(operation, context)
        elif strategy.action == RecoveryAction.QUARANTINE_FILE:
            if "file" in context:
                await self._quarantine_file(context["file"])
        elif strategy.action == RecoveryAction.FALLBACK:
            await self._execute_fallback(operation, context)
        elif strategy.action == RecoveryAction.ESCALATE:
            await self._escalate_error(operation, error_message, context)

    async def _schedule_retry_with_backoff(
        self,
        operation: str,
        strategy: RecoveryStrategy
    ) -> None:
        """Schedule retry with exponential backoff.

        Args:
            operation: Operation to retry
            strategy: Recovery strategy with backoff configuration
        """
        retry_delay = strategy.base_delay * (strategy.backoff_factor ** 0)

        retry_info = {
            "operation": operation,
            "timestamp": datetime.now(timezone.utc),
            "retry_count": 0,
            "max_retries": strategy.max_retries,
            "next_retry": datetime.now(timezone.utc) + timedelta(seconds=retry_delay),
            "backoff_factor": strategy.backoff_factor,
            "base_delay": strategy.base_delay
        }

        await self._retry_queue.put(retry_info)
        logger.info(f"Scheduled retry for {operation} in {retry_delay:.1f}s")

    async def _execute_auto_restart(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Execute automatic restart.

        Args:
            operation: Operation to restart
            context: Restart context
        """
        logger.info(f"Executing auto-restart for {operation}")
        # In real implementation, would restart the process/service

    async def _execute_fallback(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Execute fallback mechanism.

        Args:
            operation: Operation with fallback
            context: Fallback context
        """
        logger.info(f"Executing fallback for {operation}")
        # In real implementation, would execute fallback logic

    async def _escalate_error(
        self,
        operation: str,
        error_message: str,
        context: Dict[str, Any]
    ) -> None:
        """Escalate error to higher level.

        Args:
            operation: Operation with error
            error_message: Error to escalate
            context: Error context
        """
        logger.critical(f"Escalating error: {operation} - {error_message}")
        # In real implementation, would notify administrators/ops team

    def _mark_auth_required(self, service_name: str) -> None:
        """Mark service as requiring new authentication.

        Args:
            service_name: Service requiring re-auth
        """
        # Store auth requirement
        logger.warning(f"Service {service_name} requires re-authentication")

    async def _cleanup_old_files(self, directory: Path) -> bool:
        """Clean up old files to free space.

        Args:
            directory: Directory to clean

        Returns:
            True if cleanup executed
        """
        if not directory.exists():
            return False

        # Clean files older than 7 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        cleaned = 0

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff:
                    try:
                        file_path.unlink()
                        cleaned += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")

        logger.info(f"Cleaned up {cleaned} old files in {directory}")
        return True

    async def _send_critical_notification(
        self,
        operation: str,
        error_message: str,
        context: Dict[str, Any]
    ) -> None:
        """Send critical error notification.

        Args:
            operation: Operation with critical error
            error_message: Critical error message
            context: Error context
        """
        # In real implementation, would send email/SMS notification
        logger.critical(f"CRITICAL NOTIFICATION: {operation} - {error_message}")

    async def _retry_worker(self) -> None:
        """Background worker for processing retry queue."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for retry item with timeout
                try:
                    retry_info = await asyncio.wait_for(
                        self._retry_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Check retry time
                now = datetime.now(timezone.utc)
                retry_time = retry_info.get("next_retry", now)

                if now < retry_time:
                    # Not time yet, put back and wait
                    await asyncio.sleep(0.1)
                    await self._retry_queue.put(retry_info)
                    continue

                # Execute retry
                operation = retry_info.get("operation")
                retry_count = retry_info.get("retry_count", 0)
                max_retries = retry_info.get("max_retries", 3)

                if retry_count >= max_retries:
                    logger.error(f"Max retries exceeded for {operation}")
                    continue

                # Update retry count
                retry_info["retry_count"] += 1

                # Calculate next backoff
                backoff_factor = retry_info.get("backoff_factor", 2.0)
                base_delay = retry_info.get("base_delay", 1.0)
                next_delay = base_delay * (backoff_factor ** retry_info["retry_count"])
                retry_info["next_retry"] = now + timedelta(seconds=next_delay)

                # Log retry attempt
                logger.info(f"Retrying {operation} (attempt {retry_count + 1}/{max_retries})")

                # In real implementation, would execute the actual retry
                # For now, just reschedule
                if retry_count < max_retries:
                    await self._retry_queue.put(retry_info)

            except Exception as e:
                logger.error(f"Error in retry worker: {e}")
                await asyncio.sleep(1.0)

    async def _monitor_resources(self) -> None:
        """Background worker for resource monitoring."""
        while not self._shutdown_event.is_set():
            try:
                # Monitor system resources
                # In real implementation, would check CPU, memory, disk

                # Check circuit breaker state
                if self.circuit_breaker.state == CircuitState.OPEN:
                    logger.warning(f"Circuit breaker is open for {self.circuit_breaker.name}")

                # Monitor error rates
                recent_errors = [
                    e for e in self._error_history
                    if e["timestamp"] > datetime.now(timezone.utc) - timedelta(minutes=5)
                ]

                if len(recent_errors) > 10:
                    logger.error(f"High error rate detected: {len(recent_errors)} errors in 5 minutes")

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(10)

    async def _cleanup_worker(self) -> None:
        """Background worker for cleanup operations."""
        while not self._shutdown_event.is_set():
            try:
                # Clean up resolved errors
                self._clear_resolved_errors()

                # Clean up old rollbacks
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                old_rollbacks = [
                    op_id for op_id, info in self._active_rollbacks.items()
                    if info.timestamp < cutoff
                ]

                for op_id in old_rollbacks:
                    del self._active_rollbacks[op_id]

                # Run cleanup every hour
                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                await asyncio.sleep(60)

    async def _register_health_checks(self) -> None:
        """Register error recovery related health checks."""
        # Error rate health check
        async def check_error_rate(check) -> List[Dict[str, Any]]:
            """Check error rate over last 5 minutes."""
            recent_errors = [
                e for e in self._error_history
                if e["timestamp"] > datetime.now(timezone.utc) - timedelta(minutes=5)
            ]

            error_rate = len(recent_errors) / 5.0  # errors per minute

            return [
                {
                    "name": "error_rate_per_minute",
                    "value": error_rate,
                    "unit": "errors/min",
                    "threshold_warning": 2.0,
                    "threshold_critical": 5.0
                }
            ]

        # Circuit breaker health check
        async def check_circuit_breaker(check) -> List[Dict[str, Any]]:
            """Check circuit breaker state."""
            state_score = {
                "CLOSED": 1.0,
                "HALF_OPEN": 0.5,
                "OPEN": 0.0
            }

            score = state_score.get(self.circuit_breaker.state.name, 0.0)
            failures = self.circuit_breaker.failure_count

            return [
                {
                    "name": "circuit_breaker_health",
                    "value": score,
                    "unit": "score",
                    "threshold_warning": 0.5,
                    "threshold_critical": 0.0
                },
                {
                    "name": "circuit_breaker_failures",
                    "value": failures,
                    "unit": "count",
                    "threshold_warning": 3.0,
                    "threshold_critical": 5.0
                }
            ]

        # Queue depth health check
        async def check_queue_depth(check) -> List[Dict[str, Any]]:
            """Check queue depths."""
            retry_depth = self._retry_queue.qsize()
            approval_depth = self._approval_queue.qsize()
            review_depth = self._review_queue.qsize()

            total_depth = retry_depth + approval_depth + review_depth

            return [
                {
                    "name": "total_queue_depth",
                    "value": total_depth,
                    "unit": "items",
                    "threshold_warning": 10.0,
                    "threshold_critical": 50.0
                },
                {
                    "name": "retry_queue_depth",
                    "value": retry_depth,
                    "unit": "items"
                },
                {
                    "name": "approval_queue_depth",
                    "value": approval_depth,
                    "unit": "items"
                },
                {
                    "name": "review_queue_depth",
                    "value": review_depth,
                    "unit": "items"
                }
            ]

        # Register checks with health monitor
        self.health_monitor.register_check(
            name="error_recovery_rate",
            check_type="custom",
            description="Monitor error rate",
            interval=60,
            check_function=check_error_rate
        )

        self.health_monitor.register_check(
            name="circuit_breaker_status",
            check_type="custom",
            description="Monitor circuit breaker state",
            interval=30,
            check_function=check_circuit_breaker
        )

        self.health_monitor.register_check(
            name="error_recovery_queues",
            check_type="custom",
            description="Monitor error queue depths",
            interval=30,
            check_function=check_queue_depth
        )

    async def _handle_error_event(self, event: ErrorEvent) -> None:
        """Handle error events from event bus.

        Args:
            event: Error event to handle
        """
        logger.debug(f"Handling error event: {event.error_message}")

        # Update error history
        for error in self._error_history:
            if error["timestamp"].isoformat() == event.timestamp.isoformat():
                error["resolved"] = event.resolved
                break

        # Trigger health check if error is critical
        if event.error_severity == ErrorSeverity.CRITICAL:
            logger.warning(f"Critical error detected, triggering health check")
            try:
                await self.health_monitor.run_check("error_recovery_rate")
            except Exception as e:
                logger.error(f"Failed to run health check: {e}")