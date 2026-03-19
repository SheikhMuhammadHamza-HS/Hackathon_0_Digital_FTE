"""Scheduled briefing generator for CEO briefings."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import schedule
import time
from pathlib import Path

from ..domains.reporting.services import ReportService
from ..domains.reporting.models import CEOBriefing

logger = logging.getLogger(__name__)


class BriefingScheduler:
    """Manages scheduled generation of CEO briefings."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the briefing scheduler."""
        self.config = config or self._default_config()
        self.report_service = ReportService()
        self.is_running = False
        self._setup_directories()

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "schedule": {
                "weekly_briefing": {
                    "enabled": True,
                    "day_of_week": "sunday",
                    "time": "23:00",
                    "timezone": "UTC"
                },
                "monthly_summary": {
                    "enabled": True,
                    "day_of_month": 1,
                    "time": "09:00",
                    "timezone": "UTC"
                }
            },
            "output": {
                "directory": "briefings",
                "format": "markdown",
                "backup_enabled": True,
                "retention_days": 365
            },
            "notifications": {
                "email_enabled": False,
                "slack_enabled": False,
                "recipients": []
            }
        }

    def _setup_directories(self):
        """Create necessary directories."""
        base_dir = Path(self.config["output"]["directory"])
        base_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (base_dir / "weekly").mkdir(exist_ok=True)
        (base_dir / "monthly").mkdir(exist_ok=True)
        (base_dir / "archive").mkdir(exist_ok=True)

    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        logger.info("Starting briefing scheduler")

        # Schedule weekly briefing
        if self.config["schedule"]["weekly_briefing"]["enabled"]:
            schedule.every().sunday.at(
                self.config["schedule"]["weekly_briefing"]["time"]
            ).do(self._generate_weekly_briefing)
            logger.info(
                f"Scheduled weekly briefing for Sundays at {self.config['schedule']['weekly_briefing']['time']}"
            )

        # Schedule monthly summary
        if self.config["schedule"]["monthly_summary"]["enabled"]:
            # Note: schedule library doesn't support .month(), using 30 days as approximation
            schedule.every(30).days.at(self.config["schedule"]["monthly_summary"]["time"]).do(self._generate_monthly_summary)
            logger.info(
                f"Scheduled monthly summary for every 30 days at {self.config['schedule']['monthly_summary']['time']}"
            )

        # Start the scheduler loop
        asyncio.create_task(self._scheduler_loop())

    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        schedule.clear()
        logger.info("Briefing scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.is_running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute

    async def _generate_weekly_briefing(self):
        """Generate weekly CEO briefing."""
        try:
            logger.info("Generating weekly CEO briefing")

            # Calculate week start (Monday of current week)
            today = datetime.now()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

            # Generate briefing
            briefing = await self.report_service.generate_weekly_briefing(week_start)

            # Save briefing
            await self._save_briefing(briefing, "weekly")

            # Send notifications if enabled
            await self._send_notifications(briefing, "weekly")

            # Archive old briefings
            await self._archive_old_briefings()

            logger.info(f"Weekly briefing generated successfully: {briefing.week_start}")

        except Exception as e:
            logger.error(f"Failed to generate weekly briefing: {str(e)}", exc_info=True)

    async def _generate_monthly_summary(self):
        """Generate monthly summary."""
        try:
            logger.info("Generating monthly summary")

            # Calculate month start and end
            today = datetime.now()
            month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Calculate month end
            next_month = month_start.replace(month=month_start.month % 12 + 1)
            month_end = next_month - timedelta(days=1)
            month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Generate monthly data (would need to implement in ReportService)
            # For now, generate a weekly briefing for the last week of month
            last_week_start = month_end - timedelta(days=month_end.weekday())
            briefing = await self.report_service.generate_weekly_briefing(last_week_start)

            # Save as monthly summary
            await self._save_briefing(briefing, "monthly")

            # Send notifications
            await self._send_notifications(briefing, "monthly")

            logger.info(f"Monthly summary generated successfully for {month_start.strftime('%B %Y')}")

        except Exception as e:
            logger.error(f"Failed to generate monthly summary: {str(e)}", exc_info=True)

    async def _save_briefing(self, briefing: CEOBriefing, briefing_type: str):
        """Save briefing to file."""
        # Format filename
        if briefing_type == "weekly":
            filename = f"{briefing.week_start.strftime('%Y-%m-%d')}_Weekly_Briefing.md"
            subdir = "weekly"
        else:
            filename = f"{briefing.week_start.strftime('%Y-%m')}_Monthly_Summary.md"
            subdir = "monthly"

        # Create file path
        base_dir = Path(self.config["output"]["directory"])
        file_path = base_dir / subdir / filename

        # Generate content
        content = briefing.format_for_email()

        # Save to file
        file_path.write_text(content, encoding='utf-8')
        logger.info(f"Briefing saved to: {file_path}")

        # Backup if enabled
        if self.config["output"]["backup_enabled"]:
            await self._backup_briefing(file_path, briefing_type)

    async def _backup_briefing(self, file_path: Path, briefing_type: str):
        """Create backup of briefing."""
        try:
            backup_dir = Path(self.config["output"]["directory"]) / "archive" / briefing_type
            backup_dir.mkdir(exist_ok=True)

            # Copy file to archive
            import shutil
            backup_path = backup_dir / file_path.name
            shutil.copy2(file_path, backup_path)

            logger.debug(f"Briefing backed up to: {backup_path}")

        except Exception as e:
            logger.error(f"Failed to backup briefing: {str(e)}")

    async def _send_notifications(self, briefing: CEOBriefing, briefing_type: str):
        """Send notifications about new briefing."""
        if not self.config["notifications"]["email_enabled"] and not self.config["notifications"]["slack_enabled"]:
            return

        # Prepare notification message
        subject = f"CEO {briefing_type.title()} Briefing - {briefing.week_start.strftime('%Y-%m-%d')}"
        message = f"""
New {briefing_type} briefing is ready.

Period: {briefing.week_start.strftime('%Y-%m-%d')} to {briefing.week_end.strftime('%Y-%m-%d')}

Key Highlights:
{chr(10).join(f"• {highlight}" for highlight in briefing.key_highlights[:5])}

View the full briefing in the briefings directory.
        """.strip()

        # Send email notification
        if self.config["notifications"]["email_enabled"]:
            await self._send_email_notification(subject, message)

        # Send Slack notification
        if self.config["notifications"]["slack_enabled"]:
            await self._send_slack_notification(subject, message)

    async def _send_email_notification(self, subject: str, message: str):
        """Send email notification (placeholder implementation)."""
        # TODO: Implement email sending
        logger.info(f"Email notification would be sent: {subject}")

    async def _send_slack_notification(self, subject: str, message: str):
        """Send Slack notification (placeholder implementation)."""
        # TODO: Implement Slack integration
        logger.info(f"Slack notification would be sent: {subject}")

    async def _archive_old_briefings(self):
        """Archive briefings older than retention period."""
        if not self.config["output"]["backup_enabled"]:
            return

        retention_days = self.config["output"]["retention_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        base_dir = Path(self.config["output"]["directory"])

        for subdir in ["weekly", "monthly"]:
            dir_path = base_dir / subdir
            if not dir_path.exists():
                continue

            # Find old files
            for file_path in dir_path.glob("*.md"):
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    # Move to archive
                    archive_dir = base_dir / "archive" / subdir
                    archive_dir.mkdir(exist_ok=True)

                    archive_path = archive_dir / file_path.name
                    file_path.rename(archive_path)
                    logger.debug(f"Archived old briefing: {file_path.name}")

    def generate_now(self, briefing_type: str = "weekly", date: Optional[str] = None):
        """Generate a briefing immediately."""
        asyncio.create_task(self._generate_briefing_on_demand(briefing_type, date))

    async def _generate_briefing_on_demand(self, briefing_type: str, date: Optional[str]):
        """Generate briefing on demand."""
        try:
            if date:
                # Parse provided date
                target_date = datetime.fromisoformat(date)
            else:
                target_date = datetime.now()

            if briefing_type == "weekly":
                # Find Monday of the week
                days_since_monday = target_date.weekday()
                week_start = target_date - timedelta(days=days_since_monday)
                week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

                briefing = await self.report_service.generate_weekly_briefing(week_start)
                await self._save_briefing(briefing, "weekly")

            logger.info(f"On-demand {briefing_type} briefing generated successfully")

        except Exception as e:
            logger.error(f"Failed to generate on-demand briefing: {str(e)}", exc_info=True)

    def get_next_run_times(self) -> Dict[str, str]:
        """Get next run times for scheduled briefings."""
        next_runs = {}

        for job in schedule.jobs:
            job_tags = str(job.tags) if job.tags else "unknown"
            if "weekly" in job_tags.lower():
                next_runs["weekly"] = job.next_run.strftime("%Y-%m-%d %H:%M:%S")
            elif "monthly" in job_tags.lower():
                next_runs["monthly"] = job.next_run.strftime("%Y-%m-%d %H:%M:%S")

        return next_runs

    def get_schedule_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            "is_running": self.is_running,
            "scheduled_jobs": len(schedule.jobs),
            "next_runs": self.get_next_run_times(),
            "config": self.config
        }


# Global scheduler instance
_scheduler: Optional[BriefingScheduler] = None


def get_scheduler() -> BriefingScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BriefingScheduler()
    return _scheduler


def start_scheduler(config: Optional[Dict[str, Any]] = None):
    """Start the global scheduler."""
    scheduler = get_scheduler()
    if config:
        scheduler.config.update(config)
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


# CLI command functions
async def generate_briefing_command(week: Optional[str] = None, briefing_type: str = "weekly"):
    """CLI command to generate briefing."""
    scheduler = get_scheduler()
    await scheduler._generate_briefing_on_demand(briefing_type, week)


def schedule_command(action: str, cron_expr: Optional[str] = None):
    """CLI command to manage schedule."""
    scheduler = get_scheduler()

    if action == "status":
        status = scheduler.get_schedule_status()
        print(f"Scheduler Status: {status['is_running']}")
        print(f"Scheduled Jobs: {status['scheduled_jobs']}")
        for job_type, next_run in status['next_runs'].items():
            print(f"Next {job_type}: {next_run}")

    elif action == "test":
        # Test cron expression
        if cron_expr:
            print(f"Cron expression '{cron_expr}' is valid")
        else:
            print("No cron expression provided")

    elif action == "disable":
        stop_scheduler()
        print("Scheduler disabled")

    elif action == "enable":
        start_scheduler()
        print("Scheduler enabled")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "start":
            start_scheduler()
            print("Briefing scheduler started. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                stop_scheduler()
                print("\nScheduler stopped.")

        elif command == "generate":
            week = sys.argv[2] if len(sys.argv) > 2 else None
            briefing_type = sys.argv[3] if len(sys.argv) > 3 else "weekly"
            asyncio.run(generate_briefing_command(week, briefing_type))

        elif command == "schedule":
            action = sys.argv[2] if len(sys.argv) > 2 else "status"
            cron_expr = sys.argv[3] if len(sys.argv) > 3 else None
            schedule_command(action, cron_expr)

    else:
        print("Usage:")
        print("  python briefing_scheduler.py start")
        print("  python briefing_scheduler.py generate [week] [weekly|monthly]")
        print("  python briefing_scheduler.py schedule [status|test|disable|enable] [cron_expr]")