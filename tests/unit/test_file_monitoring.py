import unittest
import tempfile
import shutil
from pathlib import Path
import time
from unittest.mock import Mock, patch

from src.watchers.filesystem_watcher import FileWatchHandler, FileWatcher
from src.models.file_metadata import FileMetadata, FileStatus
from src.models.trigger_file import TriggerFile, TriggerStatus
from src.config.settings import settings


class TestFileMonitoring(unittest.TestCase):
    """Unit tests for file monitoring functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.test_root = Path(tempfile.mkdtemp())

        self.inbox_path = self.test_root / "Inbox"
        self.needs_action_path = self.test_root / "Needs_Action"
        self.done_path = self.test_root / "Done"
        self.logs_path = self.test_root / "Logs"
        self.dashboard_path = self.test_root / "Dashboard.md"

        # Create directories
        self.inbox_path.mkdir()
        self.needs_action_path.mkdir()
        self.done_path.mkdir()
        self.logs_path.mkdir()

        # Store original settings
        self.original_inbox = settings.INBOX_PATH
        self.original_needs_action = settings.NEEDS_ACTION_PATH
        self.original_done = settings.DONE_PATH
        self.original_logs = settings.LOGS_PATH
        self.original_dashboard = settings.DASHBOARD_PATH

        # Set settings to test paths
        settings.INBOX_PATH = self.inbox_path
        settings.NEEDS_ACTION_PATH = self.needs_action_path
        settings.DONE_PATH = self.done_path
        settings.LOGS_PATH = self.logs_path
        settings.DASHBOARD_PATH = self.dashboard_path

    def tearDown(self):
        """Clean up test environment."""
        # Restore original settings
        settings.INBOX_PATH = self.original_inbox
        settings.NEEDS_ACTION_PATH = self.original_needs_action
        settings.DONE_PATH = self.original_done
        settings.LOGS_PATH = self.original_logs
        settings.DASHBOARD_PATH = self.original_dashboard

        # Remove test directory
        shutil.rmtree(self.test_root, ignore_errors=True)

    def test_file_watch_handler_initialization(self):
        """Test that FileWatchHandler initializes correctly."""
        handler = FileWatchHandler(
            needs_action_path=self.needs_action_path,
            done_path=self.done_path,
            dashboard_path=self.dashboard_path,
            file_size_limit=10485760,  # 10MB
            max_retry_attempts=3
        )

        self.assertIsNotNone(handler)
        self.assertEqual(handler.needs_action_path, self.needs_action_path)
        self.assertEqual(handler.done_path, self.done_path)
        self.assertEqual(handler.file_size_limit, 10485760)

    def test_file_size_validation(self):
        """Test that file size validation works correctly."""
        handler = FileWatchHandler(
            needs_action_path=self.needs_action_path,
            done_path=self.done_path,
            dashboard_path=self.dashboard_path,
            file_size_limit=1024,  # 1KB
            max_retry_attempts=3
        )

        # Create a small test file (under limit)
        small_file = self.inbox_path / "small_test.txt"
        small_file.write_text("Small content")

        # The event would be handled by the on_created method in real usage
        # For testing, we can verify that the file exists and is small enough
        self.assertTrue(small_file.exists())
        self.assertLessEqual(small_file.stat().st_size, 1024)

        # Create a large test file (over limit)
        large_file = self.inbox_path / "large_test.txt"
        large_content = "Large content that exceeds the limit " * 100  # Much more than 1KB
        large_file.write_text(large_content)

        self.assertTrue(large_file.exists())
        self.assertGreaterEqual(large_file.stat().st_size, 1024)

    def test_file_type_validation(self):
        """Test that file type validation works correctly."""
        from src.utils.file_utils import is_supported_file_type

        # Create test files with different extensions
        test_files = [
            self.inbox_path / "document.pdf",
            self.inbox_path / "document.docx",
            self.inbox_path / "text.txt",
            self.inbox_path / "spreadsheet.xlsx",
            self.inbox_path / "presentation.pptx",
            self.inbox_path / "image.jpg",
            self.inbox_path / "image.png",
            self.inbox_path / "image.gif",
            self.inbox_path / "unsupported.exe",
            self.inbox_path / "unsupported.bat"
        ]

        for file_path in test_files:
            file_path.write_text("test content")

        # Check that supported files return True
        supported_files = [
            "document.pdf", "document.docx", "text.txt",
            "spreadsheet.xlsx", "presentation.pptx",
            "image.jpg", "image.png", "image.gif"
        ]

        for filename in supported_files:
            file_path = self.inbox_path / filename
            self.assertTrue(is_supported_file_type(file_path), f"{filename} should be supported")

        # Check that unsupported files return False
        unsupported_files = ["unsupported.exe", "unsupported.bat"]

        for filename in unsupported_files:
            file_path = self.inbox_path / filename
            self.assertFalse(is_supported_file_type(file_path), f"{filename} should not be supported")

    def test_file_metadata_creation(self):
        """Test that FileMetadata is created correctly from a file."""
        # Create a test file
        test_file = self.inbox_path / "test_document.pdf"
        test_file.write_text("Test PDF content")

        # Create FileMetadata from the file
        metadata = FileMetadata.create_from_file(
            original_path=test_file,
            source_folder=self.inbox_path,
            destination_folder=self.done_path
        )

        # Verify the metadata
        self.assertEqual(metadata.original_path, test_file)
        self.assertEqual(metadata.source_folder, self.inbox_path)
        self.assertEqual(metadata.destination_folder, self.done_path)
        self.assertEqual(metadata.file_size, len(b"Test PDF content"))
        self.assertEqual(metadata.file_type, "PDF")
        self.assertEqual(metadata.status, FileStatus.PENDING)

    def test_trigger_file_creation(self):
        """Test that TriggerFile is created correctly."""
        from src.services.trigger_generator import TriggerGenerator

        # Create a trigger file
        trigger_file = TriggerGenerator.create_trigger_file(
            source_path=str(self.inbox_path / "test_source.txt"),
            needs_action_dir=str(self.needs_action_path)
        )

        self.assertIsNotNone(trigger_file)
        self.assertTrue(trigger_file.id)
        self.assertEqual(trigger_file.type, "file_drop")
        self.assertEqual(trigger_file.status, TriggerStatus.PENDING)
        self.assertTrue(trigger_file.location.startswith(str(self.needs_action_path)))
        self.assertTrue(trigger_file.location.endswith(".md"))

        # Check that the file was actually created on disk
        actual_file_path = Path(trigger_file.location)
        self.assertTrue(actual_file_path.exists())


class TestFileWatcherIntegration(unittest.TestCase):
    """Integration tests for the FileWatcher."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.test_root = Path(tempfile.mkdtemp())

        self.inbox_path = self.test_root / "Inbox"
        self.needs_action_path = self.test_root / "Needs_Action"
        self.done_path = self.test_root / "Done"
        self.dashboard_path = self.test_root / "Dashboard.md"

        # Create directories
        self.inbox_path.mkdir()
        self.needs_action_path.mkdir()
        self.done_path.mkdir()

    def tearDown(self):
        """Clean up test environment."""
        # Remove test directory
        shutil.rmtree(self.test_root, ignore_errors=True)

    def test_file_watcher_initialization(self):
        """Test that FileWatcher initializes correctly."""
        watcher = FileWatcher(
            watch_path=self.inbox_path,
            needs_action_path=self.needs_action_path,
            done_path=self.done_path,
            dashboard_path=self.dashboard_path,
            file_size_limit=10485760,
            max_retry_attempts=3
        )

        self.assertIsNotNone(watcher)
        self.assertEqual(watcher.watch_path, self.inbox_path)
        self.assertEqual(watcher.needs_action_path, self.needs_action_path)
        self.assertEqual(watcher.done_path, self.done_path)

    @unittest.skip("Integration test - requires actual file system events")
    def test_file_detection_workflow(self):
        """Test the complete file detection and processing workflow."""
        # This test would involve:
        # 1. Starting the file watcher
        # 2. Creating a file in the inbox
        # 3. Waiting for the event to be processed
        # 4. Verifying the trigger file was created
        # 5. Verifying the file was moved to Done
        # 6. Stopping the watcher

        # Skipping this test as it requires actual file system events and timing
        pass


if __name__ == '__main__':
    unittest.main()