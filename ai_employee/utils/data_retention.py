"""Data retention automation for GDPR compliance and policy enforcement."""

import os
import json
import shutil
import sqlite3
import gzip
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class DataCategory(Enum):
    """Categories of data for retention policies."""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    COMMUNICATION = "communication"
    USER_DATA = "user_data"
    AUDIT_LOGS = "audit_logs"
    SYSTEM_LOGS = "system_logs"
    TEMPORARY = "temporary"
    BACKUP = "backup"


class RetentionAction(Enum):
    """Actions for retained data."""
    KEEP = "keep"
    ARCHIVE = "archive"
    DELETE = "delete"
    ANONYMIZE = "anonymize"


@dataclass
class RetentionPolicy:
    """Data retention policy configuration."""

    category: DataCategory
    retention_days: int
    action: RetentionAction
    archive_location: Optional[str] = None
    compression: bool = True
    exceptions: List[str] = field(default_factory=list)
    description: str = ""

    def is_expired(self, item_date: datetime) -> bool:
        """Check if data item is expired based on policy."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        return item_date < cutoff_date

    def should_retain(self, item_path: str) -> bool:
        """Check if item should be retained based on exceptions."""
        for exception in self.exceptions:
            if exception in item_path:
                return True
        return False


@dataclass
class RetentionItem:
    """Item to be processed for retention."""

    path: str
    category: DataCategory
    created_at: datetime
    modified_at: datetime
    size: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "category": self.category.value,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "size": self.size,
            "metadata": self.metadata
        }


class DataRetentionManager:
    """Manages data retention policies and execution."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/data_retention.json"
        self.policies: Dict[DataCategory, RetentionPolicy] = {}
        self.archive_location = Path("archives")
        self.retention_log: List[Dict[str, Any]] = []
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Ensure archive directory exists
        self.archive_location.mkdir(parents=True, exist_ok=True)

        # Load default policies
        self._load_default_policies()

        # Load custom policies if exists
        if os.path.exists(self.config_path):
            self.load_policies()

    def _load_default_policies(self):
        """Load default retention policies."""
        default_policies = {
            DataCategory.FINANCIAL: RetentionPolicy(
                category=DataCategory.FINANCIAL,
                retention_days=2555,  # 7 years for financial records
                action=RetentionAction.ARCHIVE,
                archive_location="archives/financial",
                compression=True,
                description="Financial records (invoices, payments, transactions)"
            ),
            DataCategory.OPERATIONAL: RetentionPolicy(
                category=DataCategory.OPERATIONAL,
                retention_days=730,  # 2 years
                action=RetentionAction.ARCHIVE,
                archive_location="archives/operational",
                compression=True,
                description="Operational data (tasks, projects, reports)"
            ),
            DataCategory.COMMUNICATION: RetentionPolicy(
                category=DataCategory.COMMUNICATION,
                retention_days=1095,  # 3 years
                action=RetentionAction.ARCHIVE,
                archive_location="archives/communications",
                compression=True,
                description="Email logs, chat histories, notifications"
            ),
            DataCategory.USER_DATA: RetentionPolicy(
                category=DataCategory.USER_DATA,
                retention_days=365,  # 1 year after account deactivation
                action=RetentionAction.ANONYMIZE,
                compression=False,
                description="User preferences, settings, personal data"
            ),
            DataCategory.AUDIT_LOGS: RetentionPolicy(
                category=DataCategory.AUDIT_LOGS,
                retention_days=2555,  # 7 years for compliance
                action=RetentionAction.ARCHIVE,
                archive_location="archives/audit",
                compression=True,
                description="Security audit logs, access logs"
            ),
            DataCategory.SYSTEM_LOGS: RetentionPolicy(
                category=DataCategory.SYSTEM_LOGS,
                retention_days=90,  # 3 months
                action=RetentionAction.DELETE,
                compression=False,
                description="Application logs, debug information"
            ),
            DataCategory.TEMPORARY: RetentionPolicy(
                category=DataCategory.TEMPORARY,
                retention_days=7,  # 1 week
                action=RetentionAction.DELETE,
                compression=False,
                description="Temporary files, cache, drafts"
            ),
            DataCategory.BACKUP: RetentionPolicy(
                category=DataCategory.BACKUP,
                retention_days=365,  # 1 year
                action=RetentionAction.ARCHIVE,
                archive_location="archives/backups",
                compression=True,
                description="System backups, database dumps"
            )
        }

        self.policies = default_policies

    def add_policy(self, policy: RetentionPolicy):
        """Add or update a retention policy."""
        self.policies[policy.category] = policy
        self.save_policies()

    def remove_policy(self, category: DataCategory):
        """Remove a retention policy."""
        if category in self.policies:
            del self.policies[category]
            self.save_policies()

    def save_policies(self):
        """Save policies to configuration file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        policies_dict = {}
        for category, policy in self.policies.items():
            policies_dict[category.value] = {
                "retention_days": policy.retention_days,
                "action": policy.action.value,
                "archive_location": policy.archive_location,
                "compression": policy.compression,
                "exceptions": policy.exceptions,
                "description": policy.description
            }

        with open(self.config_path, 'w') as f:
            json.dump(policies_dict, f, indent=2)

    def load_policies(self):
        """Load policies from configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                policies_dict = json.load(f)

            for category_str, policy_dict in policies_dict.items():
                category = DataCategory(category_str)
                self.policies[category] = RetentionPolicy(
                    category=category,
                    retention_days=policy_dict["retention_days"],
                    action=RetentionAction(policy_dict["action"]),
                    archive_location=policy_dict.get("archive_location"),
                    compression=policy_dict.get("compression", True),
                    exceptions=policy_dict.get("exceptions", []),
                    description=policy_dict.get("description", "")
                )
        except Exception as e:
            logger.error(f"Failed to load retention policies: {e}")

    async def scan_directory(self, directory: str, category: DataCategory) -> List[RetentionItem]:
        """Scan directory for retention items."""
        items = []
        directory_path = Path(directory)

        if not directory_path.exists():
            return items

        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    item = RetentionItem(
                        path=str(file_path),
                        category=category,
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        modified_at=datetime.fromtimestamp(stat.st_mtime),
                        size=stat.st_size,
                        metadata={
                            "extension": file_path.suffix,
                            "is_compressed": file_path.suffix in ['.gz', '.zip', '.bz2']
                        }
                    )
                    items.append(item)
                except Exception as e:
                    logger.warning(f"Failed to scan {file_path}: {e}")

        return items

    async def scan_database(self, db_path: str, table: str, category: DataCategory,
                          date_column: str = "created_at") -> List[RetentionItem]:
        """Scan database table for retention items."""
        items = []

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get table schema to identify date column
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]

            if date_column not in columns:
                logger.warning(f"Date column '{date_column}' not found in table '{table}'")
                return items

            # Query old records
            query = f"""
                SELECT id, {date_column}, COUNT(*) as row_count
                FROM {table}
                WHERE {date_column} < date('now', '-{self.policies[category].retention_days} days')
                GROUP BY id, {date_column}
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                item = RetentionItem(
                    path=f"{db_path}:{table}:{row[0]}",
                    category=category,
                    created_at=datetime.fromisoformat(row[1]),
                    modified_at=datetime.fromisoformat(row[1]),
                    size=row[2],  # Approximate size as row count
                    metadata={
                        "database": db_path,
                        "table": table,
                        "record_id": row[0]
                    }
                )
                items.append(item)

            conn.close()

        except Exception as e:
            logger.error(f"Failed to scan database {db_path}: {e}")

        return items

    async def archive_file(self, item: RetentionItem) -> bool:
        """Archive a file."""
        try:
            source_path = Path(item.path)
            policy = self.policies[item.category]

            # Create archive directory structure
            archive_dir = self.archive_location / policy.archive_location
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Create archive path
            relative_path = source_path.relative_to(Path.cwd())
            archive_path = archive_dir / relative_path

            # Create parent directories
            archive_path.parent.mkdir(parents=True, exist_ok=True)

            # Compress if required
            if policy.compression and not item.metadata.get("is_compressed"):
                archive_path = archive_path.with_suffix(archive_path.suffix + ".gz")
                await self._compress_file(source_path, archive_path)
            else:
                shutil.move(str(source_path), str(archive_path))

            # Log action
            self._log_retention_action(item, "archived", str(archive_path))

            return True

        except Exception as e:
            logger.error(f"Failed to archive {item.path}: {e}")
            return False

    async def delete_file(self, item: RetentionItem) -> bool:
        """Securely delete a file."""
        try:
            file_path = Path(item.path)

            # Secure delete (overwrite before deletion)
            if file_path.exists():
                # For sensitive data, overwrite the file
                if item.category in [DataCategory.USER_DATA, DataCategory.FINANCIAL]:
                    await self._secure_delete(file_path)
                else:
                    file_path.unlink()

            # Log action
            self._log_retention_action(item, "deleted")

            return True

        except Exception as e:
            logger.error(f"Failed to delete {item.path}: {e}")
            return False

    async def anonymize_data(self, item: RetentionItem) -> bool:
        """Anonymize data by removing personal identifiers."""
        try:
            if ":" in item.path:  # Database record
                parts = item.path.split(":")
                db_path, table, record_id = parts[0], parts[1], parts[2]

                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Anonymize common personal data fields
                anonymize_queries = [
                    f"UPDATE {table} SET email = 'anonymized@example.com' WHERE id = ?",
                    f"UPDATE {table} SET phone = '+1-555-000-0000' WHERE id = ?",
                    f"UPDATE {table} SET name = 'Anonymous User' WHERE id = ?",
                    f"UPDATE {table} SET address = '' WHERE id = ?"
                ]

                for query in anonymize_queries:
                    try:
                        cursor.execute(query, (record_id,))
                    except:
                        pass  # Column might not exist

                conn.commit()
                conn.close()

            # Log action
            self._log_retention_action(item, "anonymized")

            return True

        except Exception as e:
            logger.error(f"Failed to anonymize {item.path}: {e}")
            return False

    async def _compress_file(self, source: Path, destination: Path):
        """Compress a file using gzip."""
        def _compress():
            with open(source, 'rb') as f_in:
                with gzip.open(destination, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            source.unlink()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, _compress)

    async def _secure_delete(self, file_path: Path):
        """Securely delete a file by overwriting."""
        def _overwrite():
            file_size = file_path.stat().st_size

            # Overwrite with random data
            with open(file_path, 'wb') as f:
                f.write(os.urandom(file_size))

            # Overwrite with zeros
            with open(file_path, 'wb') as f:
                f.write(b'\x00' * file_size)

            # Delete the file
            file_path.unlink()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, _overwrite)

    def _log_retention_action(self, item: RetentionItem, action: str, destination: Optional[str] = None):
        """Log a retention action."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "item": item.to_dict(),
            "destination": destination
        }

        self.retention_log.append(log_entry)

        # Also log to standard logger
        logger.info(f"Data retention: {action} {item.path} ({item.category.value})")

    async def apply_retention_policies(self, dry_run: bool = False) -> Dict[str, Any]:
        """Apply all retention policies."""
        results = {
            "scanned": 0,
            "processed": 0,
            "archived": 0,
            "deleted": 0,
            "anonymized": 0,
            "errors": 0,
            "dry_run": dry_run
        }

        logger.info(f"Starting retention policy enforcement (dry_run={dry_run})")

        # Scan common directories
        scan_tasks = [
            self._scan_and_process("Vault/Logs", DataCategory.SYSTEM_LOGS, dry_run),
            self._scan_and_process("Vault/Reports", DataCategory.OPERATIONAL, dry_run),
            self._scan_and_process("logs", DataCategory.SYSTEM_LOGS, dry_run),
            self._scan_and_process("temp", DataCategory.TEMPORARY, dry_run),
        ]

        # Wait for all scans to complete
        await asyncio.gather(*scan_tasks, return_exceptions=True)

        # Calculate totals
        for log_entry in self.retention_log:
            if log_entry["timestamp"] > (datetime.now() - timedelta(hours=1)).isoformat():
                results["processed"] += 1
                action = log_entry["action"]
                if action in results:
                    results[action] += 1

        # Save retention log
        await self._save_retention_log()

        logger.info(f"Retention policy enforcement completed: {results}")
        return results

    async def _scan_and_process(self, directory: str, category: DataCategory, dry_run: bool):
        """Scan directory and process expired items."""
        if not os.path.exists(directory):
            return

        # Scan for items
        items = await self.scan_directory(directory, category)

        # Process expired items
        policy = self.policies.get(category)
        if not policy:
            return

        for item in items:
            if policy.is_expired(item.modified_at) and not policy.should_retain(item.path):
                if dry_run:
                    logger.info(f"[DRY RUN] Would {policy.action.value} {item.path}")
                    self._log_retention_action(item, f"dry_run_{policy.action.value}")
                else:
                    success = False
                    if policy.action == RetentionAction.ARCHIVE:
                        success = await self.archive_file(item)
                    elif policy.action == RetentionAction.DELETE:
                        success = await self.delete_file(item)
                    elif policy.action == RetentionAction.ANONYMIZE:
                        success = await self.anonymize_data(item)

                    if not success:
                        logger.error(f"Failed to process {item.path}")

    async def _save_retention_log(self):
        """Save retention log to file."""
        log_path = Path("logs/retention.log")
        log_path.parent.mkdir(exist_ok=True)

        # Keep only last 1000 entries
        recent_log = self.retention_log[-1000:]

        async with aiofiles.open(log_path, 'w') as f:
            await f.write(json.dumps(recent_log, indent=2))

    async def get_retention_report(self) -> Dict[str, Any]:
        """Generate retention policy report."""
        report = {
            "policies": {},
            "summary": {
                "total_items": 0,
                "expired_items": 0,
                "archive_size": 0,
                "last_run": None
            },
            "recent_actions": []
        }

        # Policy information
        for category, policy in self.policies.items():
            policy_info = {
                "retention_days": policy.retention_days,
                "action": policy.action.value,
                "description": policy.description
            }
            report["policies"][category.value] = policy_info

        # Recent actions (last 24 hours)
        cutoff = datetime.now() - timedelta(days=1)
        recent_actions = [
            entry for entry in self.retention_log
            if datetime.fromisoformat(entry["timestamp"]) > cutoff
        ]
        report["recent_actions"] = recent_actions[-50:]  # Last 50 actions
        report["summary"]["last_run"] = recent_actions[0]["timestamp"] if recent_actions else None

        return report


# Global retention manager
retention_manager = DataRetentionManager()


class RetentionScheduler:
    """Scheduler for automated data retention."""

    def __init__(self, manager: DataRetentionManager):
        self.manager = manager
        self.running = False

    async def start(self):
        """Start the retention scheduler."""
        self.running = True

        while self.running:
            try:
                # Run retention policies daily at 2 AM
                now = datetime.now()
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)

                if now > next_run:
                    next_run += timedelta(days=1)

                sleep_seconds = (next_run - now).total_seconds()
                logger.info(f"Next retention run scheduled for {next_run}")

                await asyncio.sleep(sleep_seconds)

                # Apply retention policies
                await self.manager.apply_retention_policies()

            except Exception as e:
                logger.error(f"Retention scheduler error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    def stop(self):
        """Stop the retention scheduler."""
        self.running = False


# Global scheduler
retention_scheduler = RetentionScheduler(retention_manager)