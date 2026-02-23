"""
Backup and Restore Manager for AI Employee System
Implements automated backup scheduling, data integrity verification, and restore procedures
"""

import asyncio
import json
import logging
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import gzip
import hashlib
import aiofiles
import os
from cryptography.fernet import Fernet
import tarfile

try:
    from .config import Config
except ImportError:
    from .config import config as Config

logger = logging.getLogger(__name__)

class BackupManager:
    """
    Comprehensive backup and restore management system
    - Automated daily/weekly/monthly backups
    - Data integrity verification with checksums
    - Encrypted backup support
    - Selective restore capabilities
    """

    def __init__(self):
        self.config = Config()
        self.backup_dir = Path(self.config.BACKUP_DIRECTORY)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key) if self.encryption_key else None

    def _get_or_create_encryption_key(self) -> Optional[bytes]:
        """Get or create encryption key for backup encryption"""
        key_file = self.backup_dir / ".backup_key"

        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Restrict file permissions
            os.chmod(key_file, 0o600)
            return key

    async def create_backup(
        self,
        backup_type: str = "daily",
        include_media: bool = True,
        encrypt: bool = True,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a comprehensive backup of the system

        Args:
            backup_type: Type of backup (daily, weekly, monthly, manual)
            include_media: Whether to include media files
            encrypt: Whether to encrypt the backup
            comment: Optional comment for the backup

        Returns:
            Dict containing backup metadata and status
        """
        try:
            timestamp = datetime.now()
            backup_name = f"backup_{backup_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup metadata
            metadata = {
                "backup_id": backup_name,
                "type": backup_type,
                "created_at": timestamp.isoformat(),
                "version": "1.0.0",
                "includes_media": include_media,
                "encrypted": encrypt,
                "comment": comment,
                "checksums": {}
            }

            # Backup database
            db_backup_path = await self._backup_database(backup_path)
            metadata["database_backup"] = str(db_backup_path.relative_to(backup_path))

            # Backup configuration files
            config_backup_path = await self._backup_configurations(backup_path)
            metadata["config_backup"] = str(config_backup_path.relative_to(backup_path))

            # Backup user data
            user_data_path = await self._backup_user_data(backup_path)
            metadata["user_data_backup"] = str(user_data_path.relative_to(backup_path))

            # Backup logs
            logs_backup_path = await self._backup_logs(backup_path)
            metadata["logs_backup"] = str(logs_backup_path.relative_to(backup_path))

            # Backup media files (optional)
            if include_media:
                media_backup_path = await self._backup_media(backup_path)
                metadata["media_backup"] = str(media_backup_path.relative_to(backup_path))

            # Calculate checksums for all backup files
            for file_path in backup_path.rglob("*"):
                if file_path.is_file() and file_path.name != "metadata.json":
                    checksum = await self._calculate_checksum(file_path)
                    rel_path = str(file_path.relative_to(backup_path))
                    metadata["checksums"][rel_path] = checksum

            # Save metadata
            metadata_path = backup_path / "metadata.json"
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))

            # Create archive
            archive_path = await self._create_archive(backup_path, encrypt)

            # Remove temporary directory
            shutil.rmtree(backup_path)

            # Update backup registry
            await self._update_backup_registry(metadata, archive_path)

            # Cleanup old backups
            await self._cleanup_old_backups(backup_type)

            logger.info(f"Backup created successfully: {archive_path}")

            return {
                "status": "success",
                "backup_id": backup_name,
                "archive_path": str(archive_path),
                "size_mb": round(archive_path.stat().st_size / (1024 * 1024), 2),
                "checksum": await self._calculate_checksum(archive_path),
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Backup creation failed: {str(e)}")
            # Cleanup on failure
            if 'backup_path' in locals() and backup_path.exists():
                shutil.rmtree(backup_path)
            return {
                "status": "error",
                "message": str(e)
            }

    async def _backup_database(self, backup_path: Path) -> Path:
        """Backup SQLite database"""
        db_path = backup_path / "database"
        db_path.mkdir(exist_ok=True)

        # Get database path from config
        source_db = Path(self.config.DATABASE_PATH)

        if source_db.exists():
            # Use SQLite backup API for integrity
            backup_db = db_path / "ai_employee.db"
            source = sqlite3.connect(str(source_db))
            backup = sqlite3.connect(str(backup_db))
            source.backup(backup)
            source.close()
            backup.close()

            # Also export as SQL for human readability
            sql_file = db_path / "ai_employee.sql"
            conn = sqlite3.connect(str(source_db))
            with open(sql_file, 'w') as f:
                for line in conn.iterdump():
                    f.write('%s\n' % line)
            conn.close()

        return db_path

    async def _backup_configurations(self, backup_path: Path) -> Path:
        """Backup configuration files"""
        config_path = backup_path / "configurations"
        config_path.mkdir(exist_ok=True)

        # Backup main config
        if Path(self.config.CONFIG_PATH).exists():
            shutil.copy2(self.config.CONFIG_PATH, config_path / "config.yaml")

        # Backup environment file template
        env_template = Path(".env.template")
        if env_template.exists():
            shutil.copy2(env_template, config_path / ".env.template")

        # Backup skill configurations
        skills_dir = Path("skills")
        if skills_dir.exists():
            shutil.copytree(skills_dir, config_path / "skills", dirs_exist_ok=True)

        return config_path

    async def _backup_user_data(self, backup_path: Path) -> Path:
        """Backup user data and workspace"""
        user_data_path = backup_path / "user_data"
        user_data_path.mkdir(exist_ok=True)

        # Backup Obsidian vault if it exists
        vault_paths = [
            "ai_employee/vault",
            "vault",
            "workspace/vault"
        ]

        for vault_path in vault_paths:
            vault = Path(vault_path)
            if vault.exists():
                shutil.copytree(vault, user_data_path / "vault", dirs_exist_ok=True)
                break

        # Backup user preferences and settings
        prefs_paths = [
            "ai_employee/preferences",
            "user_preferences"
        ]

        for prefs_path in prefs_paths:
            prefs = Path(prefs_path)
            if prefs.exists():
                shutil.copytree(prefs, user_data_path / "preferences", dirs_exist_ok=True)
                break

        return user_data_path

    async def _backup_logs(self, backup_path: Path) -> Path:
        """Backup log files"""
        logs_path = backup_path / "logs"
        logs_path.mkdir(exist_ok=True)

        # Collect log files from various locations
        log_locations = [
            "logs",
            "ai_employee/logs",
            ".claude/logs"
        ]

        for log_location in log_locations:
            log_dir = Path(log_location)
            if log_dir.exists():
                for log_file in log_dir.glob("*.log*"):
                    # Only copy recent logs (last 30 days)
                    if log_file.stat().st_mtime > (datetime.now() - timedelta(days=30)).timestamp():
                        shutil.copy2(log_file, logs_path / log_file.name)

        return logs_path

    async def _backup_media(self, backup_path: Path) -> Path:
        """Backup media files and attachments"""
        media_path = backup_path / "media"
        media_path.mkdir(exist_ok=True)

        # Backup media from various locations
        media_locations = [
            "ai_employee/media",
            "media",
            "attachments",
            "uploads"
        ]

        for media_location in media_locations:
            media_dir = Path(media_location)
            if media_dir.exists():
                # Only include files smaller than 100MB to avoid huge backups
                for media_file in media_dir.rglob("*"):
                    if media_file.is_file() and media_file.stat().st_size < 100 * 1024 * 1024:
                        dest_path = media_path / media_file.relative_to(media_dir)
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(media_file, dest_path)

        return media_path

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum for file integrity verification"""
        sha256_hash = hashlib.sha256()

        async with aiofiles.open(file_path, 'rb') as f:
            async for chunk in f:
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    async def _create_archive(self, backup_path: Path, encrypt: bool) -> Path:
        """Create compressed archive of backup"""
        archive_name = backup_path.name + ".tar.gz"
        archive_path = self.backup_dir / archive_name

        # Create tar.gz archive
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(backup_path, arcname=backup_path.name)

        # Encrypt if requested
        if encrypt and self.cipher:
            encrypted_path = self.backup_dir / (archive_name + ".enc")

            async with aiofiles.open(archive_path, 'rb') as src_file:
                data = await src_file.read()
                encrypted_data = self.cipher.encrypt(data)

                async with aiofiles.open(encrypted_path, 'wb') as enc_file:
                    await enc_file.write(encrypted_data)

            # Remove unencrypted archive
            archive_path.unlink()
            archive_path = encrypted_path

        return archive_path

    async def _update_backup_registry(self, metadata: Dict, archive_path: Path):
        """Update backup registry with new backup information"""
        registry_file = self.backup_dir / "backup_registry.json"

        registry = {"backups": []}
        if registry_file.exists():
            async with aiofiles.open(registry_file, 'r') as f:
                content = await f.read()
                registry = json.loads(content)

        registry_entry = {
            "backup_id": metadata["backup_id"],
            "type": metadata["type"],
            "created_at": metadata["created_at"],
            "archive_path": str(archive_path.relative_to(self.backup_dir)),
            "size_mb": round(archive_path.stat().st_size / (1024 * 1024), 2),
            "checksum": await self._calculate_checksum(archive_path),
            "includes_media": metadata["includes_media"],
            "encrypted": metadata["encrypted"],
            "comment": metadata.get("comment", "")
        }

        registry["backups"].append(registry_entry)
        registry["last_updated"] = datetime.now().isoformat()

        async with aiofiles.open(registry_file, 'w') as f:
            await f.write(json.dumps(registry, indent=2))

    async def _cleanup_old_backups(self, backup_type: str):
        """Clean up old backups based on retention policy"""
        retention_policy = {
            "daily": 7,      # Keep daily backups for 7 days
            "weekly": 4,     # Keep weekly backups for 4 weeks
            "monthly": 12,   # Keep monthly backups for 12 months
            "manual": 30     # Keep manual backups for 30 days
        }

        max_age_days = retention_policy.get(backup_type, 7)
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        registry_file = self.backup_dir / "backup_registry.json"
        if not registry_file.exists():
            return

        async with aiofiles.open(registry_file, 'r') as f:
            content = await f.read()
            registry = json.loads(content)

        backups_to_remove = []
        for backup in registry["backups"]:
            if backup["type"] == backup_type:
                backup_date = datetime.fromisoformat(backup["created_at"])
                if backup_date < cutoff_date:
                    backups_to_remove.append(backup)

        # Remove old backups
        for backup in backups_to_remove:
            archive_path = self.backup_dir / backup["archive_path"]
            if archive_path.exists():
                archive_path.unlink()
                logger.info(f"Removed old backup: {backup['backup_id']}")

            registry["backups"].remove(backup)

        # Update registry
        async with aiofiles.open(registry_file, 'w') as f:
            await f.write(json.dumps(registry, indent=2))

    async def list_backups(self, backup_type: Optional[str] = None) -> List[Dict]:
        """List available backups"""
        registry_file = self.backup_dir / "backup_registry.json"

        if not registry_file.exists():
            return []

        async with aiofiles.open(registry_file, 'r') as f:
            content = await f.read()
            registry = json.loads(content)

        backups = registry.get("backups", [])

        if backup_type:
            backups = [b for b in backups if b["type"] == backup_type]

        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)

        return backups

    async def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """Verify backup integrity"""
        registry_file = self.backup_dir / "backup_registry.json"

        if not registry_file.exists():
            return {"status": "error", "message": "No backup registry found"}

        async with aiofiles.open(registry_file, 'r') as f:
            content = await f.read()
            registry = json.loads(content)

        backup_info = None
        for backup in registry["backups"]:
            if backup["backup_id"] == backup_id:
                backup_info = backup
                break

        if not backup_info:
            return {"status": "error", "message": "Backup not found"}

        archive_path = self.backup_dir / backup_info["archive_path"]

        if not archive_path.exists():
            return {"status": "error", "message": "Backup archive not found"}

        # Verify checksum
        current_checksum = await self._calculate_checksum(archive_path)
        if current_checksum != backup_info["checksum"]:
            return {
                "status": "error",
                "message": "Backup integrity check failed - checksum mismatch",
                "expected": backup_info["checksum"],
                "actual": current_checksum
            }

        # Extract and verify metadata
        try:
            temp_extract_path = await self._extract_backup(archive_path, backup_info["encrypted"])
            metadata_path = temp_extract_path / "metadata.json"

            if not metadata_path.exists():
                return {"status": "error", "message": "Backup metadata not found"}

            async with aiofiles.open(metadata_path, 'r') as f:
                metadata = json.loads(await f.read())

            # Verify file checksums
            integrity_issues = []
            for file_path, expected_checksum in metadata["checksums"].items():
                full_path = temp_extract_path / file_path
                if full_path.exists():
                    actual_checksum = await self._calculate_checksum(full_path)
                    if actual_checksum != expected_checksum:
                        integrity_issues.append(f"{file_path}: checksum mismatch")
                else:
                    integrity_issues.append(f"{file_path}: file missing")

            # Cleanup
            shutil.rmtree(temp_extract_path)

            if integrity_issues:
                return {
                    "status": "warning",
                    "message": "Backup verified with integrity issues",
                    "issues": integrity_issues
                }

            return {
                "status": "success",
                "message": "Backup integrity verified",
                "metadata": metadata
            }

        except Exception as e:
            return {"status": "error", "message": f"Backup verification failed: {str(e)}"}

    async def restore_backup(
        self,
        backup_id: str,
        restore_components: List[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Restore from backup

        Args:
            backup_id: ID of backup to restore
            restore_components: List of components to restore (database, config, user_data, logs, media)
            force: Force restore without confirmation

        Returns:
            Dict containing restore status and details
        """
        try:
            # Verify backup first
            verification = await self.verify_backup(backup_id)
            if verification["status"] == "error":
                return verification

            # Get backup info
            registry_file = self.backup_dir / "backup_registry.json"
            async with aiofiles.open(registry_file, 'r') as f:
                content = await f.read()
                registry = json.loads(content)

            backup_info = None
            for backup in registry["backups"]:
                if backup["backup_id"] == backup_id:
                    backup_info = backup
                    break

            if not backup_info:
                return {"status": "error", "message": "Backup not found"}

            # Extract backup
            archive_path = self.backup_dir / backup_info["archive_path"]
            temp_extract_path = await self._extract_backup(archive_path, backup_info["encrypted"])

            # Load metadata
            metadata_path = temp_extract_path / "metadata.json"
            async with aiofiles.open(metadata_path, 'r') as f:
                metadata = json.loads(await f.read())

            # Default to restoring all components
            if not restore_components:
                restore_components = ["database", "config", "user_data", "logs", "media"]

            restore_results = {}

            # Create system restore point before proceeding
            if not force:
                restore_point = await self.create_backup(
                    backup_type="manual",
                    comment=f"Pre-restore point before restoring {backup_id}"
                )
                logger.info(f"Created restore point: {restore_point['backup_id']}")

            # Restore components
            if "database" in restore_components and "database_backup" in metadata:
                result = await self._restore_database(temp_extract_path / metadata["database_backup"])
                restore_results["database"] = result

            if "config" in restore_components and "config_backup" in metadata:
                result = await self._restore_configurations(temp_extract_path / metadata["config_backup"])
                restore_results["config"] = result

            if "user_data" in restore_components and "user_data_backup" in metadata:
                result = await self._restore_user_data(temp_extract_path / metadata["user_data_backup"])
                restore_results["user_data"] = result

            if "logs" in restore_components and "logs_backup" in metadata:
                result = await self._restore_logs(temp_extract_path / metadata["logs_backup"])
                restore_results["logs"] = result

            if "media" in restore_components and "media_backup" in metadata:
                result = await self._restore_media(temp_extract_path / metadata["media_backup"])
                restore_results["media"] = result

            # Cleanup
            shutil.rmtree(temp_extract_path)

            # Check if any restores failed
            failed_components = [comp for comp, result in restore_results.items() if result["status"] == "error"]

            if failed_components:
                return {
                    "status": "partial",
                    "message": f"Restore completed with failures: {', '.join(failed_components)}",
                    "results": restore_results
                }

            logger.info(f"Backup {backup_id} restored successfully")

            return {
                "status": "success",
                "message": "Backup restored successfully",
                "restored_components": list(restore_results.keys()),
                "results": restore_results
            }

        except Exception as e:
            logger.error(f"Backup restore failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _extract_backup(self, archive_path: Path, encrypted: bool) -> Path:
        """Extract backup archive to temporary directory"""
        temp_extract_path = self.backup_dir / f"temp_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_extract_path.mkdir(parents=True, exist_ok=True)

        # Decrypt if necessary
        if encrypted and self.cipher:
            decrypted_path = archive_path.with_suffix('.tar.gz')

            async with aiofiles.open(archive_path, 'rb') as enc_file:
                encrypted_data = await enc_file.read()
                decrypted_data = self.cipher.decrypt(encrypted_data)

                async with aiofiles.open(decrypted_path, 'wb') as dec_file:
                    await dec_file.write(decrypted_data)

            archive_path = decrypted_path

        # Extract archive
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(temp_extract_path)

        # Remove decrypted file if it was created
        if encrypted and 'decrypted_path' in locals():
            decrypted_path.unlink()

        return temp_extract_path

    async def _restore_database(self, backup_db_path: Path):
        """Restore database from backup"""
        try:
            source_db = backup_db_path / "ai_employee.db"
            target_db = Path(self.config.DATABASE_PATH)

            if not source_db.exists():
                return {"status": "error", "message": "Database backup not found"}

            # Create backup of current database
            if target_db.exists():
                backup_current = target_db.with_suffix('.db.backup')
                shutil.copy2(target_db, backup_current)

            # Restore database
            conn = sqlite3.connect(str(source_db))
            backup = sqlite3.connect(str(target_db))
            conn.backup(backup)
            conn.close()
            backup.close()

            return {"status": "success", "message": "Database restored successfully"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _restore_configurations(self, backup_config_path: Path):
        """Restore configuration files"""
        try:
            # Restore main config
            config_backup = backup_config_path / "config.yaml"
            if config_backup.exists():
                shutil.copy2(config_backup, self.config.CONFIG_PATH)

            # Restore environment template
            env_template = backup_config_path / ".env.template"
            if env_template.exists():
                shutil.copy2(env_template, ".env.template")

            # Restore skill configurations
            skills_backup = backup_config_path / "skills"
            if skills_backup.exists():
                skills_dir = Path("skills")
                if skills_dir.exists():
                    shutil.rmtree(skills_dir)
                shutil.copytree(skills_backup, skills_dir)

            return {"status": "success", "message": "Configurations restored successfully"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _restore_user_data(self, backup_user_data_path: Path):
        """Restore user data and workspace"""
        try:
            vault_backup = backup_user_data_path / "vault"
            if vault_backup.exists():
                # Restore to multiple possible locations
                vault_targets = [
                    "ai_employee/vault",
                    "vault",
                    "workspace/vault"
                ]

                for target in vault_targets:
                    target_path = Path(target)
                    if target_path.exists() or target_path.parent.exists():
                        if target_path.exists():
                            shutil.rmtree(target_path)
                        shutil.copytree(vault_backup, target_path)
                        break

            prefs_backup = backup_user_data_path / "preferences"
            if prefs_backup.exists():
                prefs_targets = [
                    "ai_employee/preferences",
                    "user_preferences"
                ]

                for target in prefs_targets:
                    target_path = Path(target)
                    if target_path.exists() or target_path.parent.exists():
                        if target_path.exists():
                            shutil.rmtree(target_path)
                        shutil.copytree(prefs_backup, target_path)
                        break

            return {"status": "success", "message": "User data restored successfully"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _restore_logs(self, backup_logs_path: Path):
        """Restore log files"""
        try:
            # Restore to logs directory
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)

            for log_file in backup_logs_path.glob("*.log*"):
                shutil.copy2(log_file, logs_dir / log_file.name)

            return {"status": "success", "message": "Logs restored successfully"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _restore_media(self, backup_media_path: Path):
        """Restore media files"""
        try:
            # Restore to media directory
            media_dir = Path("ai_employee/media")
            media_dir.mkdir(parents=True, exist_ok=True)

            for media_file in backup_media_path.rglob("*"):
                if media_file.is_file():
                    dest_path = media_dir / media_file.relative_to(backup_media_path)
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(media_file, dest_path)

            return {"status": "success", "message": "Media files restored successfully"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def schedule_automatic_backups(self):
        """Schedule automatic backups"""
        from .scheduler import TaskScheduler

        scheduler = TaskScheduler()

        # Daily backup at 2 AM
        await scheduler.add_task(
            task_id="daily_backup",
            schedule_type="cron",
            schedule_config="0 2 * * *",  # 2 AM every day
            task_data={
                "action": "create_backup",
                "backup_type": "daily",
                "include_media": False,
                "encrypt": True
            }
        )

        # Weekly backup on Sunday at 3 AM
        await scheduler.add_task(
            task_id="weekly_backup",
            schedule_type="cron",
            schedule_config="0 3 * * 0",  # 3 AM every Sunday
            task_data={
                "action": "create_backup",
                "backup_type": "weekly",
                "include_media": True,
                "encrypt": True
            }
        )

        # Monthly backup on 1st at 4 AM
        await scheduler.add_task(
            task_id="monthly_backup",
            schedule_type="cron",
            schedule_config="0 4 1 * *",  # 4 AM on 1st of month
            task_data={
                "action": "create_backup",
                "backup_type": "monthly",
                "include_media": True,
                "encrypt": True
            }
        )

        logger.info("Automatic backup schedules configured")

    async def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics and storage information"""
        backups = await self.list_backups()

        if not backups:
            return {
                "total_backups": 0,
                "total_size_mb": 0,
                "oldest_backup": None,
                "newest_backup": None,
                "by_type": {}
            }

        total_size = sum(b["size_mb"] for b in backups)

        by_type = {}
        for backup in backups:
            backup_type = backup["type"]
            if backup_type not in by_type:
                by_type[backup_type] = {"count": 0, "size_mb": 0}
            by_type[backup_type]["count"] += 1
            by_type[backup_type]["size_mb"] += backup["size_mb"]

        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "oldest_backup": min(b["created_at"] for b in backups),
            "newest_backup": max(b["created_at"] for b in backups),
            "by_type": by_type,
            "storage_path": str(self.backup_dir),
            "encryption_enabled": self.cipher is not None
        }

# Global backup manager instance
backup_manager = BackupManager()