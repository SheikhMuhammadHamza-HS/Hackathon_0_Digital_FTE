"""
Automated cleanup manager for old files and temporary data.

This module provides automated cleanup procedures for old files,
temporary data, and system maintenance tasks.
"""

import asyncio
import logging
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from ai_employee.core.config import get_config
from ai_employee.core.event_bus import get_event_bus
from ai_employee.utils.logging_config import get_logger

logger = get_logger(__name__)


class CleanupStatus(Enum):
    """Cleanup operation status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CleanupRule:
    """Cleanup rule configuration."""
    name: str = field(default_factory="")
    path_pattern: str = field(default_factory="")  # Glob pattern for files to clean
    max_age_days: int = field(default_factory=30)
    min_size_mb: Optional[int] = field(default_factory=lambda: None)
    max_size_mb: Optional[int] = field(default_factory=lambda: None)
    recursive: bool = field(default_factory=True)
    dry_run: bool = field(default_factory=False)
    exclude_patterns: List[str] = field(default_factory=list)
    schedule_hours: int = field(default_factory=24)  # How often to run this cleanup


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    rule_name: str = field(default_factory="")
    status: CleanupStatus = field(default_factory=CleanupStatus.PENDING)
    files_scanned: int = field(default_factory=0)
    files_deleted: int = field(default_factory=0)
    bytes_freed: int = field(default_factory=0)
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = field(default_factory=lambda: None)
    skipped_reason: Optional[str] = field(default_factory=lambda: None)


class CleanupManager:
    """Manages automated cleanup procedures."""

    def __init__(self):
        """Initialize cleanup manager."""
        self.config = get_config()
        self.event_bus = get_event_bus()
        self.rules: Dict[str, CleanupRule] = {}
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default cleanup rules."""
        # Log files older than 30 days
        self.add_rule(CleanupRule(
            name="old_logs",
            path_pattern="**/*.log",
            max_age_days=30,
            min_size_mb=1,
            schedule_hours=24
        ))

        # Temporary files older than 7 days
        self.add_rule(CleanupRule(
            name="temp_files",
            path_pattern="**/*.tmp",
            max_age_days=7,
            schedule_hours=12
        ))

        # Cache files older than 14 days
        self.add_rule(CleanupRule(
            name="cache_files",
            path_pattern="**/cache/**",
            max_age_days=14,
            schedule_hours=24
        ))

        # Old error recovery backups older than 90 days
        self.add_rule(CleanupRule(
            name="error_recovery_backups",
            path_pattern="**/backups/error_recovery/**",
            max_age_days=90,
            schedule_hours=168  # Weekly
        ))

        # Old health reports older than 30 days
        self.add_rule(CleanupRule(
            name="health_reports",
            path_pattern="**/reports/health_*.json",
            max_age_days=30,
            schedule_hours=24
        ))

        # Audit logs older than 2 years (730 days) - compliance requirement
        self.add_rule(CleanupRule(
            name="old_audit_logs",
            path_pattern="**/logs/audit_*.log",
            max_age_days=730,
            schedule_hours=168,  # Weekly
            exclude_patterns=["**/audit_*.log"]  # Exclude from actual deletion, just report
        ))

    def add_rule(self, rule: CleanupRule):
        """Add a cleanup rule.

        Args:
            rule: Cleanup rule to add
        """
        self.rules[rule.name] = rule
        logger.info(f"Added cleanup rule: {rule.name}")

    def remove_rule(self, rule_name: str):
        """Remove a cleanup rule.

        Args:
            rule_name: Name of rule to remove
        """
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Removed cleanup rule: {rule_name}")

    async def start(self):
        """Start the cleanup manager."""
        if self.running:
            logger.warning("Cleanup manager is already running")
            return

        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Cleanup manager started")

    async def stop(self):
        """Stop the cleanup manager."""
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cleanup manager stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop."""
        while self.running:
            try:
                # Run each rule based on its schedule
                for rule in self.rules.values():
                    if not self.running:
                        break

                    # Check if rule should run (simplified - in production, use last run time)
                    should_run = await self._should_run_rule(rule)
                    if should_run:
                        await self._run_cleanup_rule(rule)

                # Sleep for an hour before next check
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _should_run_rule(self, rule: CleanupRule) -> bool:
        """Check if a rule should run based on its schedule.

        Args:
            rule: Cleanup rule to check

        Returns:
            True if rule should run
        """
        # For now, run all rules once per day at 2 AM
        # In production, track last run time per rule
        now = datetime.now()
        if now.hour == 2 and now.minute < 5:  # Between 2:00 and 2:05 AM
            return True
        return False

    async def _run_cleanup_rule(self, rule: CleanupRule):
        """Run a single cleanup rule.

        Args:
            rule: Cleanup rule to run
        """
        result = CleanupResult(rule_name=rule.name, status=CleanupStatus.RUNNING)

        try:
            logger.info(f"Running cleanup rule: {rule.name}")

            # Get base paths to search
            base_paths = await self._get_cleanup_paths()

            for base_path in base_paths:
                if not self.running:
                    break

                await self._cleanup_path(base_path, rule, result)

            result.status = CleanupStatus.COMPLETED
            logger.info(f"Cleanup rule {rule.name} completed: {result.files_deleted} files deleted, {result.bytes_freed} bytes freed")

        except Exception as e:
            result.status = CleanupStatus.FAILED
            result.errors.append(str(e))
            logger.error(f"Cleanup rule {rule.name} failed: {e}")

        finally:
            result.end_time = datetime.now(timezone.utc)
            await self._publish_cleanup_result(result)

    async def _get_cleanup_paths(self) -> List[Path]:
        """Get base paths for cleanup operations.

        Returns:
            List of paths to clean
        """
        paths = []

        # Add logs directory
        if hasattr(self.config, 'paths') and hasattr(self.config.paths, 'logs_path'):
            paths.append(Path(self.config.paths.logs_path))

        # Add temp directory
        temp_dir = Path("temp")
        if temp_dir.exists():
            paths.append(temp_dir)

        # Add cache directories
        cache_dirs = Path(".").glob("**/cache")
        paths.extend(cache_dirs)

        # Add backup directories
        backup_dirs = Path(".").glob("**/backups")
        paths.extend(backup_dirs)

        return [p for p in paths if p.exists()]

    async def _cleanup_path(self, base_path: Path, rule: CleanupRule, result: CleanupResult):
        """Cleanup files in a specific path.

        Args:
            base_path: Base path to clean
            rule: Cleanup rule to apply
            result: Cleanup result to update
        """
        try:
            # Find matching files
            if rule.recursive:
                files = base_path.glob(rule.path_pattern)
            else:
                files = base_path.glob(rule.path_pattern)

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=rule.max_age_days)

            for file_path in files:
                if not file_path.is_file():
                    continue

                result.files_scanned += 1

                # Check if file should be deleted
                should_delete = await self._should_delete_file(file_path, cutoff_date, rule)

                if should_delete:
                    if rule.dry_run:
                        logger.info(f"DRY RUN: Would delete {file_path}")
                    else:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        result.files_deleted += 1
                        result.bytes_freed += file_size
                        logger.debug(f"Deleted {file_path} ({file_size} bytes)")

        except Exception as e:
            result.errors.append(f"Error cleaning {base_path}: {e}")

    async def _should_delete_file(self, file_path: Path, cutoff_date: datetime, rule: CleanupRule) -> bool:
        """Check if a file should be deleted.

        Args:
            file_path: File to check
            cutoff_date: Maximum age for files
            rule: Cleanup rule

        Returns:
            True if file should be deleted
        """
        try:
            # Check exclude patterns
            for exclude_pattern in rule.exclude_patterns:
                if file_path.match(exclude_pattern):
                    return False

            # Check file age
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime > cutoff_date:
                return False

            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)

            if rule.min_size_mb and file_size_mb < rule.min_size_mb:
                return False

            if rule.max_size_mb and file_size_mb > rule.max_size_mb:
                return False

            return True

        except Exception as e:
            logger.warning(f"Error checking file {file_path}: {e}")
            return False

    async def _publish_cleanup_result(self, result: CleanupResult):
        """Publish cleanup result to event bus.

        Args:
            result: Cleanup result to publish
        """
        try:
            event = {
                "event_type": "cleanup_completed",
                "data": {
                    "rule_name": result.rule_name,
                    "status": result.status.value,
                    "files_scanned": result.files_scanned,
                    "files_deleted": result.files_deleted,
                    "bytes_freed": result.bytes_freed,
                    "errors": result.errors,
                    "duration_seconds": (result.end_time - result.start_time).total_seconds() if result.end_time else None
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            await self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Error publishing cleanup result: {e}")

    async def run_manual_cleanup(self, rule_name: Optional[str] = None, dry_run: bool = True):
        """Run cleanup manually.

        Args:
            rule_name: Specific rule to run, or None for all
            dry_run: Whether to perform dry run

        Returns:
            List of cleanup results
        """
        results = []

        rules_to_run = [self.rules[rule_name]] if rule_name else list(self.rules.values())

        for rule in rules_to_run:
            # Temporarily set dry run flag
            original_dry_run = rule.dry_run
            rule.dry_run = dry_run

            try:
                result = CleanupResult(rule_name=rule.name, status=CleanupStatus.RUNNING)
                base_paths = await self._get_cleanup_paths()

                for base_path in base_paths:
                    await self._cleanup_path(base_path, rule, result)

                result.status = CleanupStatus.COMPLETED
                result.end_time = datetime.now(timezone.utc)
                results.append(result)

            finally:
                rule.dry_run = original_dry_run

        return results

    async def get_cleanup_statistics(self) -> Dict:
        """Get cleanup statistics.

        Returns:
            Cleanup statistics
        """
        stats = {
            "rules_count": len(self.rules),
            "rules": [],
            "running": self.running
        }

        for rule_name, rule in self.rules.items():
            stats["rules"].append({
                "name": rule_name,
                "path_pattern": rule.path_pattern,
                "max_age_days": rule.max_age_days,
                "schedule_hours": rule.schedule_hours,
                "recursive": rule.recursive
            })

        return stats


# Global cleanup manager instance
_cleanup_manager: Optional[CleanupManager] = None


def get_cleanup_manager() -> CleanupManager:
    """Get the global cleanup manager instance.

    Returns:
        Cleanup manager instance
    """
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = CleanupManager()
    return _cleanup_manager


async def initialize_cleanup_manager():
    """Initialize the cleanup manager."""
    cleanup_manager = get_cleanup_manager()
    await cleanup_manager.start()
    return cleanup_manager