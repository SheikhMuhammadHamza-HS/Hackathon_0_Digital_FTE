"""
Unit tests for backup and restore functionality
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
import sqlite3

from ai_employee.utils.backup_manager import BackupManager
from ai_employee.utils.config import Config


@pytest.fixture
def temp_backup_dir():
    """Create a temporary directory for testing backups"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_config(temp_backup_dir):
    """Create a mock configuration for testing"""
    class MockConfig:
        def __init__(self):
            self.BACKUP_DIRECTORY = str(temp_backup_dir)
            self.DATABASE_PATH = str(temp_backup_dir / "test.db")
            self.CONFIG_PATH = str(temp_backup_dir / "config.yaml")
            self.VAULT_PATH = str(temp_backup_dir / "vault")
            self.LOGS_PATH = str(temp_backup_dir / "logs")
            self.MEDIA_PATH = str(temp_backup_dir / "media")

    return MockConfig()


@pytest.fixture
async def backup_manager(mock_config):
    """Create a BackupManager instance with mock configuration"""
    # Patch the config
    import ai_employee.utils.backup_manager
    original_config = ai_employee.utils.backup_manager.Config
    ai_employee.utils.backup_manager.Config = mock_config

    manager = BackupManager()

    # Restore original config
    ai_employee.utils.backup_manager.Config = original_config

    return manager


@pytest.fixture
async def sample_database(mock_config):
    """Create a sample database for testing"""
    db_path = Path(mock_config.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create test tables
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert test data
    cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", ("testuser", "test@example.com"))
    cursor.execute("INSERT INTO tasks (title, status) VALUES (?, ?)", ("Test Task", "completed"))

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
async def sample_data(mock_config):
    """Create sample files for testing backup"""
    # Create vault
    vault_path = Path(mock_config.VAULT_PATH)
    vault_path.mkdir(parents=True, exist_ok=True)
    (vault_path / "test_note.md").write_text("# Test Note\n\nThis is a test note.")

    # Create logs
    logs_path = Path(mock_config.LOGS_PATH)
    logs_path.mkdir(parents=True, exist_ok=True)
    (logs_path / "app.log").write_text("2024-01-01 12:00:00 INFO Test log message\n")

    # Create media
    media_path = Path(mock_config.MEDIA_PATH)
    media_path.mkdir(parents=True, exist_ok=True)
    (media_path / "test_image.png").write_bytes(b"fake png data")

    # Create config
    config_path = Path(mock_config.CONFIG_PATH)
    config_path.write_text("test_config: value\n")


class TestBackupManager:
    """Test cases for BackupManager"""

    @pytest.mark.asyncio
    async def test_create_backup_success(self, backup_manager, sample_database, sample_data):
        """Test successful backup creation"""
        result = await backup_manager.create_backup(
            backup_type="manual",
            include_media=True,
            encrypt=False,  # Disable encryption for testing
            comment="Test backup"
        )

        assert result["status"] == "success"
        assert "backup_id" in result
        assert "archive_path" in result
        assert Path(result["archive_path"]).exists()
        assert result["size_mb"] > 0

        # Check metadata
        assert result["metadata"]["type"] == "manual"
        assert result["metadata"]["includes_media"] is True
        assert result["metadata"]["encrypted"] is False
        assert result["metadata"]["comment"] == "Test backup"

    @pytest.mark.asyncio
    async def test_create_backup_without_media(self, backup_manager, sample_database, sample_data):
        """Test backup creation without media files"""
        result = await backup_manager.create_backup(
            backup_type="daily",
            include_media=False,
            encrypt=False
        )

        assert result["status"] == "success"
        assert result["metadata"]["includes_media"] is False

    @pytest.mark.asyncio
    async def test_create_backup_encrypted(self, backup_manager, sample_database, sample_data):
        """Test backup creation with encryption"""
        result = await backup_manager.create_backup(
            backup_type="weekly",
            include_media=True,
            encrypt=True
        )

        assert result["status"] == "success"
        assert result["metadata"]["encrypted"] is True
        # Encrypted backup should have .enc extension
        assert result["archive_path"].endswith(".enc")

    @pytest.mark.asyncio
    async def test_list_backups(self, backup_manager, sample_database, sample_data):
        """Test listing backups"""
        # Create multiple backups
        await backup_manager.create_backup(backup_type="daily", encrypt=False)
        await backup_manager.create_backup(backup_type="weekly", encrypt=False)
        await backup_manager.create_backup(backup_type="monthly", encrypt=False)

        # List all backups
        all_backups = await backup_manager.list_backups()
        assert len(all_backups) == 3

        # List specific type
        daily_backups = await backup_manager.list_backups(backup_type="daily")
        assert len(daily_backups) == 1
        assert daily_backups[0]["type"] == "daily"

    @pytest.mark.asyncio
    async def test_verify_backup_integrity(self, backup_manager, sample_database, sample_data):
        """Test backup verification"""
        # Create backup
        create_result = await backup_manager.create_backup(encrypt=False)
        backup_id = create_result["backup_id"]

        # Verify backup
        verify_result = await backup_manager.verify_backup(backup_id)

        assert verify_result["status"] == "success"
        assert "metadata" in verify_result

    @pytest.mark.asyncio
    async def test_verify_nonexistent_backup(self, backup_manager):
        """Test verification of non-existent backup"""
        result = await backup_manager.verify_backup("nonexistent_backup")
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_restore_backup(self, backup_manager, sample_database, sample_data):
        """Test backup restore"""
        # Create backup
        create_result = await backup_manager.create_backup(encrypt=False)
        backup_id = create_result["backup_id"]

        # Modify data
        db_path = Path(backup_manager.config.DATABASE_PATH)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", ("newuser", "new@example.com"))
        conn.commit()
        conn.close()

        # Restore backup
        restore_result = await backup_manager.restore_backup(
            backup_id=backup_id,
            restore_components=["database"],
            force=True
        )

        assert restore_result["status"] == "success"
        assert "database" in restore_result["restored_components"]

        # Verify restore
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()

        # Should be back to original state (1 user)
        assert count == 1

    @pytest.mark.asyncio
    async def test_restore_nonexistent_backup(self, backup_manager):
        """Test restore of non-existent backup"""
        result = await backup_manager.restore_backup(
            backup_id="nonexistent_backup",
            force=True
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_backup_statistics(self, backup_manager, sample_database, sample_data):
        """Test backup statistics"""
        # Create backups
        await backup_manager.create_backup(backup_type="daily", encrypt=False)
        await backup_manager.create_backup(backup_type="weekly", encrypt=False)

        stats = await backup_manager.get_backup_statistics()

        assert stats["total_backups"] == 2
        assert stats["total_size_mb"] > 0
        assert "daily" in stats["by_type"]
        assert "weekly" in stats["by_type"]
        assert stats["by_type"]["daily"]["count"] == 1
        assert stats["by_type"]["weekly"]["count"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, backup_manager, sample_database, sample_data):
        """Test automatic cleanup of old backups"""
        # Create backup with old date by manipulating metadata
        result = await backup_manager.create_backup(backup_type="daily", encrypt=False)
        backup_id = result["backup_id"]

        # Manually update backup registry to simulate old backup
        registry_file = backup_manager.backup_dir / "backup_registry.json"
        async with backup_manager.aiofiles.open(registry_file, 'r') as f:
            registry = json.loads(await f.read())

        for backup in registry["backups"]:
            if backup["backup_id"] == backup_id:
                # Set created_at to 10 days ago
                old_date = (datetime.now() - timedelta(days=10)).isoformat()
                backup["created_at"] = old_date
                break

        async with backup_manager.aiofiles.open(registry_file, 'w') as f:
            await f.write(json.dumps(registry, indent=2))

        # Run cleanup (daily retention is 7 days)
        await backup_manager._cleanup_old_backups("daily")

        # Check that old backup was removed
        backups = await backup_manager.list_backups()
        assert len(backups) == 0

    @pytest.mark.asyncio
    async def test_checksum_calculation(self, backup_manager, temp_backup_dir):
        """Test checksum calculation for files"""
        # Create test file
        test_file = temp_backup_dir / "test.txt"
        test_content = "Test content for checksum"
        test_file.write_text(test_content)

        # Calculate checksum
        checksum = await backup_manager._calculate_checksum(test_file)

        # Verify checksum is consistent
        checksum2 = await backup_manager._calculate_checksum(test_file)
        assert checksum == checksum2

        # Verify checksum changes with content
        test_file.write_text("Modified content")
        checksum3 = await backup_manager._calculate_checksum(test_file)
        assert checksum != checksum3


class TestBackupScheduler:
    """Test cases for BackupScheduler"""

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, backup_manager):
        """Test backup scheduler initialization"""
        from ai_employee.utils.backup_scheduler import BackupScheduler

        scheduler = BackupScheduler()
        await scheduler.initialize()

        assert scheduler.is_running is True
        assert scheduler.scheduler is not None

    @pytest.mark.asyncio
    async def test_schedule_automatic_backups(self, backup_manager):
        """Test scheduling automatic backups"""
        from ai_employee.utils.backup_scheduler import BackupScheduler

        scheduler = BackupScheduler()
        await scheduler.initialize()
        await scheduler.schedule_automatic_backups()

        # Check that tasks were scheduled
        daily_task = await scheduler.scheduler.get_task("daily_backup")
        weekly_task = await scheduler.scheduler.get_task("weekly_backup")
        monthly_task = await scheduler.scheduler.get_task("monthly_backup")

        assert daily_task is not None
        assert weekly_task is not None
        assert monthly_task is not None

    @pytest.mark.asyncio
    async def test_execute_backup_task(self, backup_manager, sample_database, sample_data):
        """Test execution of backup task"""
        from ai_employee.utils.backup_scheduler import BackupScheduler

        scheduler = BackupScheduler()
        await scheduler.initialize()

        task_data = {
            "backup_type": "manual",
            "include_media": False,
            "encrypt": False,
            "comment": "Test task execution"
        }

        result = await scheduler.execute_backup_task(task_data)

        assert result["status"] == "success"
        assert "backup_id" in result

    @pytest.mark.asyncio
    async def test_get_next_backup_times(self, backup_manager):
        """Test getting next scheduled backup times"""
        from ai_employee.utils.backup_scheduler import BackupScheduler

        scheduler = BackupScheduler()
        await scheduler.initialize()
        await scheduler.schedule_automatic_backups()

        next_times = await scheduler.get_next_backup_times()

        assert "daily" in next_times
        assert "weekly" in next_times
        assert "monthly" in next_times
        assert next_times["daily"] is not None

    @pytest.mark.asyncio
    async def test_run_backup_now(self, backup_manager, sample_database, sample_data):
        """Test immediate backup execution"""
        from ai_employee.utils.backup_scheduler import BackupScheduler

        scheduler = BackupScheduler()
        await scheduler.initialize()

        result = await scheduler.run_backup_now("daily")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_scheduler_status(self, backup_manager):
        """Test getting scheduler status"""
        from ai_employee.utils.backup_scheduler import BackupScheduler

        scheduler = BackupScheduler()
        await scheduler.initialize()

        status = await scheduler.get_scheduler_status()

        assert "is_running" in status
        assert "auto_backup_enabled" in status
        assert "schedules" in status
        assert "next_runs" in status
        assert "recent_backups" in status


class TestTaskScheduler:
    """Test cases for TaskScheduler"""

    @pytest.mark.asyncio
    async def test_add_task(self):
        """Test adding a scheduled task"""
        from ai_employee.utils.scheduler import TaskScheduler

        scheduler = TaskScheduler()
        task = await scheduler.add_task(
            task_id="test_task",
            schedule_type="interval",
            schedule_config="3600",  # 1 hour
            task_data={"action": "test", "param": "value"}
        )

        assert task.task_id == "test_task"
        assert task.schedule_type == "interval"
        assert task.is_active is True
        assert task.next_run is not None

    @pytest.mark.asyncio
    async def test_cron_parsing(self):
        """Test cron expression parsing"""
        from ai_employee.utils.scheduler import TaskScheduler

        scheduler = TaskScheduler()
        now = datetime.now()

        # Test daily at 2 AM
        next_run = scheduler._parse_cron_expression("0 2 * * *", now)
        assert next_run.hour == 2
        assert next_run.minute == 0

        # Test weekly on Sunday at 3 AM
        next_run = scheduler._parse_cron_expression("0 3 * * 0", now)
        assert next_run.hour == 3
        assert next_run.minute == 0

        # Test monthly on 1st at 4 AM
        next_run = scheduler._parse_cron_expression("0 4 1 * *", now)
        assert next_run.hour == 4
        assert next_run.minute == 0
        assert next_run.day == 1

    @pytest.mark.asyncio
    async def test_task_execution(self):
        """Test task execution with handler"""
        from ai_employee.utils.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        # Register a test handler
        executed_tasks = []

        async def test_handler(task_data):
            executed_tasks.append(task_data)
            return {"status": "success"}

        scheduler.register_handler("test_action", test_handler)

        # Add and execute task
        task = await scheduler.add_task(
            task_id="test_task",
            schedule_type="once",
            schedule_config="0",
            task_data={"action": "test_action", "param": "value"}
        )

        await scheduler._execute_task(task)

        assert len(executed_tasks) == 1
        assert executed_tasks[0]["param"] == "value"
        assert task.run_count == 1
        assert task.is_active is False  # 'once' tasks deactivate after running

    @pytest.mark.asyncio
    async def test_task_statistics(self):
        """Test getting task statistics"""
        from ai_employee.utils.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        # Add some tasks
        await scheduler.add_task(
            task_id="task1",
            schedule_type="interval",
            schedule_config="3600",
            task_data={"action": "test"}
        )

        await scheduler.add_task(
            task_id="task2",
            schedule_type="cron",
            schedule_config="0 2 * * *",
            task_data={"action": "test"}
        )

        stats = await scheduler.get_task_statistics()

        assert stats["total_tasks"] == 2
        assert stats["active_tasks"] == 2
        assert stats["running"] is False
        assert "task1" in stats["next_runs"]
        assert "task2" in stats["next_runs"]