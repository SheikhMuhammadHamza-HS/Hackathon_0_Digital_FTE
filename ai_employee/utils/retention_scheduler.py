"""Scheduler for automated data retention tasks."""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Optional

from .data_retention import retention_manager, retention_scheduler

logger = logging.getLogger(__name__)


class RetentionTaskManager:
    """Manages scheduled data retention tasks."""

    def __init__(self):
        self.tasks = []
        self.running = False

    async def start_scheduler(self):
        """Start the retention scheduler."""
        logger.info("Starting data retention scheduler")
        self.running = True

        # Start the main scheduler
        scheduler_task = asyncio.create_task(retention_scheduler.start())
        self.tasks.append(scheduler_task)

        # Add periodic maintenance tasks
        maintenance_task = asyncio.create_task(self._maintenance_loop())
        self.tasks.append(maintenance_task)

        logger.info(f"Data retention scheduler started with {len(self.tasks)} tasks")

    async def stop_scheduler(self):
        """Stop the retention scheduler."""
        logger.info("Stopping data retention scheduler")
        self.running = False
        retention_scheduler.stop()

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        logger.info("Data retention scheduler stopped")

    async def _maintenance_loop(self):
        """Periodic maintenance tasks."""
        while self.running:
            try:
                # Run maintenance every hour
                await asyncio.sleep(3600)

                if not self.running:
                    break

                # Clean up old retention logs
                await self._cleanup_old_logs()

                # Validate archive integrity
                await self._validate_archives()

                # Generate retention statistics
                await self._generate_statistics()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retention maintenance error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _cleanup_old_logs(self):
        """Clean up old retention logs."""
        try:
            # Keep logs for 90 days
            cutoff = datetime.now() - timedelta(days=90)
            cutoff_str = cutoff.isoformat()

            original_count = len(retention_manager.retention_log)
            retention_manager.retention_log = [
                log for log in retention_manager.retention_log
                if log["timestamp"] > cutoff_str
            ]

            removed = original_count - len(retention_manager.retention_log)
            if removed > 0:
                logger.info(f"Cleaned up {removed} old retention log entries")

        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")

    async def _validate_archives(self):
        """Validate archive integrity."""
        try:
            from pathlib import Path
            import gzip

            archive_path = Path("archives")
            if not archive_path.exists():
                return

            # Validate a sample of archives (not all to save time)
            archives = list(archive_path.rglob("*.gz"))
            sample_size = min(10, len(archives))

            for archive_file in archives[:sample_size]:
                try:
                    # Try to read the gzip file
                    with gzip.open(archive_file, 'rb') as f:
                        f.read(1024)  # Read first 1KB
                except Exception as e:
                    logger.warning(f"Archive validation failed for {archive_file}: {e}")

        except Exception as e:
            logger.error(f"Archive validation error: {e}")

    async def _generate_statistics(self):
        """Generate and log retention statistics."""
        try:
            report = await retention_manager.get_retention_report()

            # Log key statistics
            logger.info("Data Retention Statistics:")
            logger.info(f"  Total policies: {len(report['policies'])}")
            logger.info(f"  Recent actions: {len(report['recent_actions'])}")

            if report['recent_actions']:
                # Count actions by type
                actions = {}
                for action in report['recent_actions'][-24:]:  # Last 24 actions
                    act_type = action.get('action', 'unknown')
                    actions[act_type] = actions.get(act_type, 0) + 1

                logger.info(f"  Recent actions (24h): {actions}")

        except Exception as e:
            logger.error(f"Failed to generate statistics: {e}")

    async def run_immediate_retention(self, dry_run: bool = False):
        """Run retention policies immediately."""
        logger.info(f"Running immediate retention (dry_run={dry_run})")
        result = await retention_manager.apply_retention_policies(dry_run=dry_run)

        logger.info(f"Retention completed: {result}")
        return result

    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time."""
        # Runs daily at 2 AM
        now = datetime.now()
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)

        if now > next_run:
            next_run += timedelta(days=1)

        return next_run

    def get_scheduler_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "tasks": len(self.tasks),
            "next_run": self.get_next_run_time().isoformat() if self.get_next_run_time() else None,
            "last_run": retention_manager.retention_log[-1]["timestamp"] if retention_manager.retention_log else None
        }


# Global task manager
retention_task_manager = RetentionTaskManager()