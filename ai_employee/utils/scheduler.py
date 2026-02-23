"""
Simple task scheduler for recurring operations
Provides cron-like scheduling for background tasks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import json
from pathlib import Path

from .logger import setup_logger
from .config import config

logger = setup_logger(__name__)

@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    task_id: str
    schedule_type: str  # 'cron', 'interval', 'once'
    schedule_config: str  # cron expression or interval in seconds
    task_data: Dict[str, Any]
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    is_active: bool = True
    run_count: int = 0
    max_runs: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

class TaskScheduler:
    """
    Simple task scheduler for background operations
    """

    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_task = None
        self.task_handlers: Dict[str, Callable] = {}

    def register_handler(self, action: str, handler: Callable):
        """
        Register a handler for a specific action type

        Args:
            action: Action type (e.g., 'create_backup')
            handler: Async function to handle the action
        """
        self.task_handlers[action] = handler
        logger.info(f"Registered handler for action: {action}")

    async def add_task(
        self,
        task_id: str,
        schedule_type: str,
        schedule_config: str,
        task_data: Dict[str, Any],
        max_runs: Optional[int] = None
    ) -> ScheduledTask:
        """
        Add a new scheduled task

        Args:
            task_id: Unique identifier for the task
            schedule_type: Type of schedule ('cron', 'interval', 'once')
            schedule_config: Schedule configuration
            task_data: Data to pass to the task handler
            max_runs: Maximum number of runs (None for unlimited)

        Returns:
            ScheduledTask object
        """
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id} already exists")

        task = ScheduledTask(
            task_id=task_id,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            task_data=task_data,
            max_runs=max_runs
        )

        # Calculate next run time
        task.next_run = self._calculate_next_run(task)

        self.tasks[task_id] = task
        logger.info(f"Added scheduled task: {task_id}, next run: {task.next_run}")

        return task

    async def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """
        Get a scheduled task by ID

        Args:
            task_id: Task identifier

        Returns:
            ScheduledTask or None if not found
        """
        return self.tasks.get(task_id)

    async def update_task(self, task_id: str, **kwargs) -> bool:
        """
        Update an existing task

        Args:
            task_id: Task identifier
            **kwargs: Fields to update

        Returns:
            True if updated, False if not found
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]

        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Recalculate next run if schedule changed
        if 'schedule_type' in kwargs or 'schedule_config' in kwargs:
            task.next_run = self._calculate_next_run(task)

        logger.info(f"Updated scheduled task: {task_id}")
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled, False if not found
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.is_active = False

        logger.info(f"Cancelled scheduled task: {task_id}")
        return True

    async def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task completely

        Args:
            task_id: Task identifier

        Returns:
            True if removed, False if not found
        """
        if task_id not in self.tasks:
            return False

        del self.tasks[task_id]
        logger.info(f"Removed scheduled task: {task_id}")
        return True

    def _calculate_next_run(self, task: ScheduledTask) -> Optional[datetime]:
        """
        Calculate the next run time for a task

        Args:
            task: ScheduledTask object

        Returns:
            Next run datetime or None
        """
        now = datetime.now()

        if task.schedule_type == "once":
            return now + timedelta(seconds=1)

        elif task.schedule_type == "interval":
            try:
                interval_seconds = int(task.schedule_config)
                return now + timedelta(seconds=interval_seconds)
            except ValueError:
                logger.error(f"Invalid interval config for task {task.task_id}: {task.schedule_config}")
                return None

        elif task.schedule_type == "cron":
            return self._parse_cron_expression(task.schedule_config, now)

        else:
            logger.error(f"Unknown schedule type for task {task.task_id}: {task.schedule_type}")
            return None

    def _parse_cron_expression(self, cron_expr: str, from_time: datetime) -> datetime:
        """
        Simple cron expression parser
        Supports basic format: minute hour day month day_of_week

        Args:
            cron_expr: Cron expression
            from_time: Base time to calculate from

        Returns:
            Next run datetime
        """
        # This is a simplified cron parser
        # For production use, consider using a library like croniter
        parts = cron_expr.split()
        if len(parts) != 5:
            logger.error(f"Invalid cron expression: {cron_expr}")
            return from_time + timedelta(days=1)  # Default to tomorrow

        minute, hour, day, month, weekday = parts

        # Handle special cases
        if minute == "*" and hour == "*" and day == "*" and month == "*" and weekday == "*":
            # Run every minute
            return from_time + timedelta(minutes=1)

        # Simple implementation for common cases
        if minute.isdigit() and hour.isdigit() and day == "*" and month == "*" and weekday == "*":
            # Run at specific time every day
            target_hour = int(hour)
            target_minute = int(minute)
            next_run = from_time.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

            if next_run <= from_time:
                next_run += timedelta(days=1)

            return next_run

        # Handle weekly (e.g., "0 3 * * 0" for Sunday 3 AM)
        if minute.isdigit() and hour.isdigit() and day == "*" and month == "*" and weekday.isdigit():
            target_hour = int(hour)
            target_minute = int(minute)
            target_weekday = int(weekday)  # 0 = Sunday

            days_ahead = (target_weekday - from_time.weekday() + 7) % 7
            if days_ahead == 0 and (from_time.hour > target_hour or
                                  (from_time.hour == target_hour and from_time.minute >= target_minute)):
                days_ahead = 7

            next_run = from_time + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

            return next_run

        # Handle monthly (e.g., "0 4 1 * *" for 1st of month 4 AM)
        if minute.isdigit() and hour.isdigit() and day.isdigit() and month == "*" and weekday == "*":
            target_hour = int(hour)
            target_minute = int(minute)
            target_day = int(day)

            next_run = from_time.replace(day=target_day, hour=target_hour, minute=target_minute, second=0, microsecond=0)

            if next_run <= from_time:
                # Move to next month
                if from_time.month == 12:
                    next_run = next_run.replace(year=from_time.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=from_time.month + 1)

            return next_run

        # Default to next day
        return from_time + timedelta(days=1)

    async def start(self):
        """Start the task scheduler"""
        if self.running:
            return

        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")

    async def stop(self):
        """Stop the task scheduler"""
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Task scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")

        while self.running:
            try:
                now = datetime.now()
                tasks_to_run = []

                # Find tasks ready to run
                for task in self.tasks.values():
                    if (task.is_active and
                        task.next_run and
                        task.next_run <= now and
                        (task.max_runs is None or task.run_count < task.max_runs)):
                        tasks_to_run.append(task)

                # Run tasks
                for task in tasks_to_run:
                    await self._execute_task(task)

                # Sleep for a short interval
                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _execute_task(self, task: ScheduledTask):
        """
        Execute a scheduled task

        Args:
            task: ScheduledTask to execute
        """
        try:
            action = task.task_data.get("action")
            if not action:
                logger.error(f"No action specified for task {task.task_id}")
                return

            handler = self.task_handlers.get(action)
            if not handler:
                logger.error(f"No handler registered for action: {action}")
                return

            logger.info(f"Executing task: {task.task_id}")

            # Execute the handler
            result = await handler(task.task_data)

            # Update task
            task.last_run = datetime.now()
            task.run_count += 1

            # Calculate next run
            if task.schedule_type == "once" or (task.max_runs and task.run_count >= task.max_runs):
                task.is_active = False
                logger.info(f"Task {task.task_id} completed")
            else:
                task.next_run = self._calculate_next_run(task)
                logger.info(f"Task {task.task_id} next run: {task.next_run}")

        except Exception as e:
            logger.error(f"Error executing task {task.task_id}: {str(e)}")
            # Still update last run and calculate next run
            task.last_run = datetime.now()
            task.next_run = self._calculate_next_run(task)

    async def get_active_tasks(self) -> List[ScheduledTask]:
        """
        Get all active tasks

        Returns:
            List of active ScheduledTask objects
        """
        return [task for task in self.tasks.values() if task.is_active]

    async def get_task_statistics(self) -> Dict[str, Any]:
        """
        Get scheduler statistics

        Returns:
            Dict containing statistics
        """
        active_tasks = await self.get_active_tasks()
        total_runs = sum(task.run_count for task in self.tasks.values())

        return {
            "total_tasks": len(self.tasks),
            "active_tasks": len(active_tasks),
            "total_runs": total_runs,
            "running": self.running,
            "next_runs": {
                task.task_id: task.next_run.isoformat() if task.next_run else None
                for task in active_tasks
            }
        }

    async def save_tasks(self, file_path: str = "scheduled_tasks.json"):
        """
        Save scheduled tasks to file

        Args:
            file_path: Path to save tasks
        """
        try:
            tasks_data = {}
            for task_id, task in self.tasks.items():
                tasks_data[task_id] = {
                    "task_id": task.task_id,
                    "schedule_type": task.schedule_type,
                    "schedule_config": task.schedule_config,
                    "task_data": task.task_data,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "is_active": task.is_active,
                    "run_count": task.run_count,
                    "max_runs": task.max_runs,
                    "created_at": task.created_at.isoformat()
                }

            with open(file_path, 'w') as f:
                json.dump(tasks_data, f, indent=2)

            logger.info(f"Saved {len(tasks_data)} tasks to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save tasks: {str(e)}")

    async def load_tasks(self, file_path: str = "scheduled_tasks.json"):
        """
        Load scheduled tasks from file

        Args:
            file_path: Path to load tasks from
        """
        try:
            if not Path(file_path).exists():
                logger.info(f"No tasks file found at {file_path}")
                return

            with open(file_path, 'r') as f:
                tasks_data = json.load(f)

            for task_id, task_data in tasks_data.items():
                task = ScheduledTask(
                    task_id=task_data["task_id"],
                    schedule_type=task_data["schedule_type"],
                    schedule_config=task_data["schedule_config"],
                    task_data=task_data["task_data"],
                    next_run=datetime.fromisoformat(task_data["next_run"]) if task_data["next_run"] else None,
                    last_run=datetime.fromisoformat(task_data["last_run"]) if task_data["last_run"] else None,
                    is_active=task_data["is_active"],
                    run_count=task_data["run_count"],
                    max_runs=task_data.get("max_runs"),
                    created_at=datetime.fromisoformat(task_data["created_at"])
                )
                self.tasks[task_id] = task

            logger.info(f"Loaded {len(tasks_data)} tasks from {file_path}")

        except Exception as e:
            logger.error(f"Failed to load tasks: {str(e)}")

# Global scheduler instance
task_scheduler = TaskScheduler()