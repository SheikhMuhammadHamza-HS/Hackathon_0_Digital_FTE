"""
Workflow engine for AI Employee system.

Orchestrates business processes with state management,
rollback capabilities, and human approval integration.
"""

import asyncio
import logging
from typing import (
    Dict, List, Optional, Any, Callable, Type, Union,
    get_type_hints
)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid
from abc import ABC, abstractmethod

from .event_bus import get_event_bus, Event
from .circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class StepStatus(Enum):
    """Individual step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class WorkflowContext:
    """Context data passed between workflow steps."""
    workflow_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def set(self, key: str, value: Any) -> None:
        """Set a value in context.

        Args:
            key: Context key
            value: Value to set
        """
        self.data[key] = value
        self.updated_at = datetime.utcnow()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from context.

        Args:
            key: Context key
            default: Default value if key not found

        Returns:
            Context value
        """
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """Check if key exists in context.

        Args:
            key: Context key

        Returns:
            True if key exists
        """
        return key in self.data

    def update(self, updates: Dict[str, Any]) -> None:
        """Update context with multiple values.

        Args:
            updates: Dictionary of updates
        """
        self.data.update(updates)
        self.updated_at = datetime.utcnow()


@dataclass
class StepResult:
    """Result of a workflow step execution."""
    step_id: str
    status: StepStatus
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    rollback_data: Optional[Dict[str, Any]] = None


class WorkflowStep(ABC):
    """Base class for workflow steps."""

    def __init__(self, step_id: str, name: str, description: str = ""):
        """Initialize workflow step.

        Args:
            step_id: Unique step identifier
            name: Human-readable step name
            description: Step description
        """
        self.step_id = step_id
        self.name = name
        self.description = description
        self.requires_approval = False
        self.timeout_seconds = 300
        self.retry_count = 3
        self.can_rollback = True

    @abstractmethod
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the step.

        Args:
            context: Workflow context

        Returns:
            Step execution result
        """
        pass

    async def rollback(self, context: WorkflowContext, step_result: StepResult) -> bool:
        """Rollback the step execution.

        Args:
            context: Workflow context
            step_result: Original step result

        Returns:
            True if rollback successful
        """
        if not self.can_rollback:
            logger.warning(f"Step {self.step_id} does not support rollback")
            return False

        # Default rollback implementation - can be overridden
        if step_result.rollback_data:
            try:
                await self._perform_rollback(context, step_result.rollback_data)
                return True
            except Exception as e:
                logger.error(f"Rollback failed for step {self.step_id}: {e}")
                return False

        return True

    async def _perform_rollback(self, context: WorkflowContext, rollback_data: Dict[str, Any]) -> None:
        """Perform the actual rollback. Override in subclasses.

        Args:
            context: Workflow context
            rollback_data: Data needed for rollback
        """
        pass

    def validate_context(self, context: WorkflowContext) -> List[str]:
        """Validate context before execution.

        Args:
            context: Workflow context

        Returns:
            List of validation errors
        """
        return []


class ApprovalStep(WorkflowStep):
    """Step that requires human approval."""

    def __init__(self, step_id: str, name: str, approval_item: str, approval_reason: str = ""):
        """Initialize approval step.

        Args:
            step_id: Unique step identifier
            name: Human-readable step name
            approval_item: Item being approved
            approval_reason: Reason for approval
        """
        super().__init__(step_id, name, f"Requires approval: {approval_reason}")
        self.requires_approval = True
        self.approval_item = approval_item
        self.approval_reason = approval_reason
        self.can_rollback = False  # Approval steps can't be rolled back

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute approval step.

        Args:
            context: Workflow context

        Returns:
            Step result with approval status
        """
        from ..utils.approval_system import create_approval_request

        # Create approval request
        approval_id = await create_approval_request(
            item_type=self.approval_item,
            item_id=context.workflow_id,
            reason=self.approval_reason,
            metadata=context.data
        )

        context.set('approval_id', approval_id)

        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            data={'approval_id': approval_id, 'requires_approval': True}
        )


class Workflow:
    """Workflow definition and execution."""

    def __init__(self, workflow_id: str, name: str, description: str = ""):
        """Initialize workflow.

        Args:
            workflow_id: Unique workflow identifier
            name: Human-readable workflow name
            description: Workflow description
        """
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.context = WorkflowContext(workflow_id=workflow_id)
        self.status = WorkflowStatus.PENDING
        self.current_step_index = -1
        self.step_results: List[StepResult] = []
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None

    def add_step(self, step: WorkflowStep) -> 'Workflow':
        """Add a step to the workflow.

        Args:
            step: Step to add

        Returns:
            Self for method chaining
        """
        self.steps.append(step)
        return self

    def add_steps(self, *steps: WorkflowStep) -> 'Workflow':
        """Add multiple steps to the workflow.

        Args:
            *steps: Steps to add

        Returns:
            Self for method chaining
        """
        self.steps.extend(steps)
        return self

    async def execute(self) -> bool:
        """Execute the workflow.

        Returns:
            True if workflow completed successfully
        """
        if self.status != WorkflowStatus.PENDING:
            logger.warning(f"Workflow {self.workflow_id} is not in pending state: {self.status}")
            return False

        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.utcnow()

        logger.info(f"Starting workflow {self.workflow_id}: {self.name}")

        try:
            for i, step in enumerate(self.steps):
                self.current_step_index = i

                # Validate context before step execution
                validation_errors = step.validate_context(self.context)
                if validation_errors:
                    error_msg = f"Context validation failed for step {step.step_id}: {validation_errors}"
                    logger.error(error_msg)
                    await self._handle_failure(step, error_msg)
                    return False

                # Execute step
                result = await self._execute_step(step)
                self.step_results.append(result)

                if result.status == StepStatus.FAILED:
                    await self._handle_failure(step, result.error or "Step failed")
                    return False

                # Update context with step result data
                self.context.update(result.data)

                # Check if step requires approval
                if step.requires_approval:
                    self.status = WorkflowStatus.WAITING_APPROVAL
                    logger.info(f"Workflow {self.workflow_id} waiting for approval")
                    return True  # Pause workflow for approval

            # All steps completed successfully
            self.status = WorkflowStatus.COMPLETED
            self.completed_at = datetime.utcnow()

            logger.info(f"Workflow {self.workflow_id} completed successfully")
            return True

        except Exception as e:
            error_msg = f"Workflow execution failed: {e}"
            logger.error(error_msg, exc_info=True)
            await self._handle_failure(None, error_msg)
            return False

    async def _execute_step(self, step: WorkflowStep) -> StepResult:
        """Execute a single step.

        Args:
            step: Step to execute

        Returns:
            Step execution result
        """
        logger.info(f"Executing step {step.step_id}: {step.name}")

        start_time = datetime.utcnow()

        try:
            # Execute step with timeout and retries
            result = await asyncio.wait_for(
                self._execute_with_retry(step),
                timeout=step.timeout_seconds
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            result.execution_time = duration

            if result.status == StepStatus.COMPLETED:
                logger.info(f"Step {step.step_id} completed in {duration:.2f}s")
            else:
                logger.warning(f"Step {step.step_id} failed: {result.error}")

            return result

        except asyncio.TimeoutError:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Step {step.step_id} timed out after {step.timeout_seconds}s"
            logger.error(error_msg)

            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error=error_msg,
                execution_time=duration
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Unexpected error in step {step.step_id}: {e}"
            logger.error(error_msg, exc_info=True)

            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error=error_msg,
                execution_time=duration
            )

    async def _execute_with_retry(self, step: WorkflowStep) -> StepResult:
        """Execute step with retry logic.

        Args:
            step: Step to execute

        Returns:
            Step execution result
        """
        last_result = None

        for attempt in range(step.retry_count + 1):
            try:
                result = await step.execute(self.context)

                if result.status == StepStatus.COMPLETED:
                    return result

                last_result = result

                if attempt < step.retry_count:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Step {step.step_id} failed (attempt {attempt + 1}), retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_result = StepResult(
                    step_id=step.step_id,
                    status=StepStatus.FAILED,
                    error=str(e)
                )

                if attempt < step.retry_count:
                    wait_time = 2 ** attempt
                    logger.warning(f"Step {step.step_id} exception (attempt {attempt + 1}), retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)

        return last_result or StepResult(
            step_id=step.step_id,
            status=StepStatus.FAILED,
            error="All retry attempts failed"
        )

    async def _handle_failure(self, failed_step: Optional[WorkflowStep], error: str) -> None:
        """Handle workflow failure.

        Args:
            failed_step: Step that failed (if any)
            error: Error message
        """
        self.error = error
        self.status = WorkflowStatus.FAILED
        self.completed_at = datetime.utcnow()

        # Attempt rollback of completed steps
        await self.rollback()

    async def rollback(self) -> bool:
        """Rollback all completed steps.

        Returns:
            True if rollback successful
        """
        logger.info(f"Rolling back workflow {self.workflow_id}")

        rollback_success = True

        # Rollback steps in reverse order
        for result in reversed(self.step_results):
            if result.status == StepStatus.COMPLETED:
                step = next((s for s in self.steps if s.step_id == result.step_id), None)
                if step and step.can_rollback:
                    try:
                        success = await step.rollback(self.context, result)
                        if success:
                            result.status = StepStatus.ROLLED_BACK
                            logger.info(f"Rolled back step {step.step_id}")
                        else:
                            rollback_success = False
                            logger.error(f"Failed to rollback step {step.step_id}")
                    except Exception as e:
                        rollback_success = False
                        logger.error(f"Exception during rollback of step {step.step_id}: {e}")

        self.status = WorkflowStatus.ROLLED_BACK if rollback_success else WorkflowStatus.FAILED
        return rollback_success

    async def resume_from_approval(self, approved: bool, notes: str = "") -> bool:
        """Resume workflow after approval decision.

        Args:
            approved: Whether the request was approved
            notes: Approval notes

        Returns:
            True if workflow resumed successfully
        """
        if self.status != WorkflowStatus.WAITING_APPROVAL:
            logger.warning(f"Workflow {self.workflow_id} is not waiting for approval")
            return False

        if not approved:
            self.status = WorkflowStatus.CANCELLED
            self.completed_at = datetime.utcnow()
            self.error = f"Approval denied: {notes}"
            logger.info(f"Workflow {self.workflow_id} cancelled due to approval denial")
            return False

        # Continue with remaining steps
        self.status = WorkflowStatus.RUNNING
        self.context.set('approval_notes', notes)

        logger.info(f"Resuming workflow {self.workflow_id} after approval")

        # Continue execution from next step
        return await self._continue_execution()

    async def _continue_execution(self) -> bool:
        """Continue workflow execution from current step.

        Returns:
            True if workflow completed successfully
        """
        try:
            # Continue from next step
            for i in range(self.current_step_index + 1, len(self.steps)):
                step = self.steps[i]
                self.current_step_index = i

                result = await self._execute_step(step)
                self.step_results.append(result)

                if result.status == StepStatus.FAILED:
                    await self._handle_failure(step, result.error or "Step failed")
                    return False

                self.context.update(result.data)

                # Check if step requires approval
                if step.requires_approval:
                    self.status = WorkflowStatus.WAITING_APPROVAL
                    logger.info(f"Workflow {self.workflow_id} waiting for approval")
                    return True

            # All steps completed successfully
            self.status = WorkflowStatus.COMPLETED
            self.completed_at = datetime.utcnow()

            logger.info(f"Workflow {self.workflow_id} completed successfully")
            return True

        except Exception as e:
            error_msg = f"Workflow continuation failed: {e}"
            logger.error(error_msg, exc_info=True)
            await self._handle_failure(None, error_msg)
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get workflow status information.

        Returns:
            Status dictionary
        """
        return {
            'workflow_id': self.workflow_id,
            'name': self.name,
            'status': self.status.value,
            'current_step': self.current_step_index,
            'total_steps': len(self.steps),
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'step_results': [
                {
                    'step_id': r.step_id,
                    'status': r.status.value,
                    'execution_time': r.execution_time,
                    'error': r.error
                }
                for r in self.step_results
            ]
        }


class WorkflowEngine:
    """Engine for managing and executing workflows."""

    def __init__(self):
        """Initialize workflow engine."""
        self.workflows: Dict[str, Workflow] = {}
        self.event_bus = get_event_bus()
        self._lock = asyncio.Lock()

    async def create_workflow(
        self,
        workflow_id: str,
        name: str,
        description: str = "",
        initial_data: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """Create a new workflow.

        Args:
            workflow_id: Unique workflow identifier
            name: Human-readable workflow name
            description: Workflow description
            initial_data: Initial context data

        Returns:
            Created workflow
        """
        async with self._lock:
            if workflow_id in self.workflows:
                raise ValueError(f"Workflow {workflow_id} already exists")

            workflow = Workflow(workflow_id, name, description)

            if initial_data:
                workflow.context.update(initial_data)

            self.workflows[workflow_id] = workflow

            logger.info(f"Created workflow {workflow_id}: {name}")
            return workflow

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow or None if not found
        """
        return self.workflows.get(workflow_id)

    async def execute_workflow(self, workflow_id: str) -> bool:
        """Execute a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if execution started successfully
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        return await workflow.execute()

    async def resume_workflow(self, workflow_id: str, approved: bool, notes: str = "") -> bool:
        """Resume a workflow from approval.

        Args:
            workflow_id: Workflow ID
            approved: Approval decision
            notes: Approval notes

        Returns:
            True if resumed successfully
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        return await workflow.resume_from_approval(approved, notes)

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if cancelled successfully
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        if workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED]:
            logger.warning(f"Cannot cancel workflow {workflow_id} in status {workflow.status}")
            return False

        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.utcnow()

        logger.info(f"Cancelled workflow {workflow_id}")
        return True

    async def rollback_workflow(self, workflow_id: str) -> bool:
        """Rollback a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if rollback successful
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        return await workflow.rollback()

    async def cleanup_completed_workflows(self, older_than_hours: int = 24) -> int:
        """Clean up completed workflows.

        Args:
            older_than_hours: Remove workflows completed more than this many hours ago

        Returns:
            Number of workflows removed
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        to_remove = []

        for workflow_id, workflow in self.workflows.items():
            if (workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED] and
                workflow.completed_at and workflow.completed_at < cutoff_time):
                to_remove.append(workflow_id)

        for workflow_id in to_remove:
            del self.workflows[workflow_id]

        logger.info(f"Cleaned up {len(to_remove)} completed workflows")
        return len(to_remove)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all workflows.

        Returns:
            Dictionary of workflow statuses
        """
        return {wid: wf.get_status() for wid, wf in self.workflows.items()}


# Global workflow engine instance
workflow_engine = WorkflowEngine()


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine.

    Returns:
        Global workflow engine
    """
    return workflow_engine