"""
Backup scheduler for automated backup operations
Integrates with the task scheduler to run regular backups
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .backup_manager import backup_manager
from .logger import setup_logger
from .config import config

logger = setup_logger(__name__)

class BackupScheduler:
    """
    Manages automated backup scheduling and execution
    """

    def __init__(self):
        self.scheduler = None
        self.is_running = False

    async def initialize(self):
        """Initialize the backup scheduler"""
        try:
            from .scheduler import task_scheduler
            self.scheduler = task_scheduler

            # Register backup task handler
            self.scheduler.register_handler("create_backup", self.execute_backup_task)

            self.is_running = True
            logger.info("Backup scheduler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize backup scheduler: {str(e)}")
            raise

    async def schedule_automatic_backups(self):
        """Schedule all automatic backup jobs"""
        if not self.scheduler:
            await self.initialize()

        if not config.AUTO_BACKUP_ENABLED:
            logger.info("Automatic backup is disabled")
            return

        try:
            # Daily backup
            await self.scheduler.add_task(
                task_id="daily_backup",
                schedule_type="cron",
                schedule_config=config.BACKUP_SCHEDULE_DAILY,
                task_data={
                    "action": "create_backup",
                    "backup_type": "daily",
                    "include_media": False,
                    "encrypt": config.BACKUP_ENCRYPTION_ENABLED,
                    "comment": "Automatic daily backup"
                }
            )

            # Weekly backup
            await self.scheduler.add_task(
                task_id="weekly_backup",
                schedule_type="cron",
                schedule_config=config.BACKUP_SCHEDULE_WEEKLY,
                task_data={
                    "action": "create_backup",
                    "backup_type": "weekly",
                    "include_media": True,
                    "encrypt": config.BACKUP_ENCRYPTION_ENABLED,
                    "comment": "Automatic weekly backup"
                }
            )

            # Monthly backup
            await self.scheduler.add_task(
                task_id="monthly_backup",
                schedule_type="cron",
                schedule_config=config.BACKUP_SCHEDULE_MONTHLY,
                task_data={
                    "action": "create_backup",
                    "backup_type": "monthly",
                    "include_media": True,
                    "encrypt": config.BACKUP_ENCRYPTION_ENABLED,
                    "comment": "Automatic monthly backup"
                }
            )

            logger.info("Automatic backup schedules configured")

        except Exception as e:
            logger.error(f"Failed to schedule automatic backups: {str(e)}")
            raise

    async def execute_backup_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a backup task based on task data

        Args:
            task_data: Dictionary containing backup parameters

        Returns:
            Dict containing backup execution result
        """
        try:
            backup_type = task_data.get("backup_type", "daily")
            include_media = task_data.get("include_media", True)
            encrypt = task_data.get("encrypt", config.BACKUP_ENCRYPTION_ENABLED)
            comment = task_data.get("comment", f"Automatic {backup_type} backup")

            logger.info(f"Executing {backup_type} backup task")

            result = await backup_manager.create_backup(
                backup_type=backup_type,
                include_media=include_media,
                encrypt=encrypt,
                comment=comment
            )

            if result["status"] == "success":
                logger.info(f"Automatic backup completed successfully: {result['backup_id']}")
            else:
                logger.error(f"Automatic backup failed: {result.get('message', 'Unknown error')}")

            return result

        except Exception as e:
            logger.error(f"Backup task execution failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "backup_type": task_data.get("backup_type", "unknown")
            }

    async def get_next_backup_times(self) -> Dict[str, Optional[str]]:
        """
        Get next scheduled backup times

        Returns:
            Dict mapping backup types to next run time
        """
        if not self.scheduler:
            return {"daily": None, "weekly": None, "monthly": None}

        try:
            next_runs = {}

            for backup_type in ["daily", "weekly", "monthly"]:
                task_id = f"{backup_type}_backup"
                task = await self.scheduler.get_task(task_id)

                if task and task.get("next_run"):
                    next_runs[backup_type] = task["next_run"]
                else:
                    next_runs[backup_type] = None

            return next_runs

        except Exception as e:
            logger.error(f"Failed to get next backup times: {str(e)}")
            return {"daily": None, "weekly": None, "monthly": None}

    async def get_backup_history(self, limit: int = 10) -> list:
        """
        Get recent backup execution history

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of recent backup information
        """
        try:
            backups = await backup_manager.list_backups()
            return backups[:limit]

        except Exception as e:
            logger.error(f"Failed to get backup history: {str(e)}")
            return []

    async def run_backup_now(self, backup_type: str = "daily") -> Dict[str, Any]:
        """
        Immediately run a backup

        Args:
            backup_type: Type of backup to run

        Returns:
            Dict containing backup result
        """
        task_data = {
            "backup_type": backup_type,
            "include_media": backup_type in ["weekly", "monthly"],
            "encrypt": config.BACKUP_ENCRYPTION_ENABLED,
            "comment": f"Manual {backup_type} backup"
        }

        return await self.execute_backup_task(task_data)

    async def start_scheduler(self):
        """Start the backup scheduler"""
        if not self.is_running:
            await self.initialize()
            await self.schedule_automatic_backups()
            await self.scheduler.start()
            logger.info("Backup scheduler started")

    async def stop_scheduler(self):
        """Stop the backup scheduler"""
        if self.scheduler and self.is_running:
            # Cancel scheduled tasks
            for backup_type in ["daily", "weekly", "monthly"]:
                task_id = f"{backup_type}_backup"
                try:
                    await self.scheduler.cancel_task(task_id)
                except Exception as e:
                    logger.warning(f"Failed to cancel task {task_id}: {str(e)}")

            await self.scheduler.stop()
            self.is_running = False
            logger.info("Backup scheduler stopped")

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status

        Returns:
            Dict containing scheduler status information
        """
        status = {
            "is_running": self.is_running,
            "auto_backup_enabled": config.AUTO_BACKUP_ENABLED,
            "schedules": {
                "daily": config.BACKUP_SCHEDULE_DAILY,
                "weekly": config.BACKUP_SCHEDULE_WEEKLY,
                "monthly": config.BACKUP_SCHEDULE_MONTHLY
            },
            "next_runs": await self.get_next_backup_times(),
            "recent_backups": await self.get_backup_history(limit=3)
        }

        return status

# Global backup scheduler instance
backup_scheduler = BackupScheduler()