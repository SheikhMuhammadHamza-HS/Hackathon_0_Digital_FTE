import unittest
import tempfile
import shutil
from pathlib import Path
import os
from datetime import datetime

from src.models.dashboard import DashboardManager, DashboardEntry
from src.utils.security import SecurityLogger


class TestDashboardFunctionality(unittest.TestCase):
    """Unit tests for dashboard functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.dashboard_path = self.test_dir / "test_dashboard.md"

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_dashboard_manager_initialization(self):
        """Test that DashboardManager initializes correctly."""
        manager = DashboardManager(str(self.dashboard_path))

        self.assertIsNotNone(manager)
        self.assertEqual(manager.dashboard_path, self.dashboard_path)
        self.assertIsInstance(manager.entries, list)
        self.assertEqual(len(manager.entries), 0)

    def test_add_dashboard_entry(self):
        """Test adding a dashboard entry."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create a test entry
        entry = DashboardEntry.create_from_metadata(
            file_id="test-id-123",
            display_name="test_file.pdf",
            timestamp=datetime.now(),
            status="Done",
            duration=1.5,
            file_type="PDF"
        )

        # Add the entry
        manager.add_entry(entry)

        # Verify the entry was added
        self.assertEqual(len(manager.entries), 1)
        self.assertEqual(manager.entries[0].display_name, "test_file.pdf")
        self.assertEqual(manager.entries[0].status, "Done")

    def test_dashboard_file_creation(self):
        """Test that dashboard file is created with proper format."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create and add an entry
        entry = DashboardEntry.create_from_metadata(
            file_id="test-id-123",
            display_name="test_file.pdf",
            timestamp=datetime.now(),
            status="Done",
            duration=1.5,
            file_type="PDF"
        )

        manager.add_entry(entry)

        # Verify the file exists
        self.assertTrue(self.dashboard_path.exists())

        # Read and check the content
        content = self.dashboard_path.read_text(encoding='utf-8')

        self.assertIn("# Agent Dashboard", content)
        self.assertIn("| Time | Task | Status |", content)
        self.assertIn("test_file.pdf", content)
        self.assertIn("Done", content)

    def test_chronological_ordering(self):
        """Test that entries are ordered chronologically."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create entries with different timestamps
        time1 = datetime(2023, 1, 1, 10, 0, 0)
        time2 = datetime(2023, 1, 1, 9, 0, 0)  # Earlier time
        time3 = datetime(2023, 1, 1, 11, 0, 0)  # Later time

        entry1 = DashboardEntry.create_from_metadata(
            file_id="id1", display_name="file1.pdf", timestamp=time1, status="Done", duration=1.0, file_type="PDF"
        )
        entry2 = DashboardEntry.create_from_metadata(
            file_id="id2", display_name="file2.pdf", timestamp=time2, status="Done", duration=1.5, file_type="PDF"
        )
        entry3 = DashboardEntry.create_from_metadata(
            file_id="id3", display_name="file3.pdf", timestamp=time3, status="Done", duration=2.0, file_type="PDF"
        )

        # Add entries out of chronological order
        manager.add_entry(entry1)
        manager.add_entry(entry3)
        manager.add_entry(entry2)

        # Verify they are in chronological order
        self.assertEqual(len(manager.entries), 3)
        # Second entry (earliest) should be first
        self.assertEqual(manager.entries[0].id, "id2")
        # First entry should be second
        self.assertEqual(manager.entries[1].id, "id1")
        # Third entry (latest) should be last
        self.assertEqual(manager.entries[2].id, "id3")

    def test_update_existing_entry(self):
        """Test updating an existing dashboard entry."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create and add an entry
        entry = DashboardEntry.create_from_metadata(
            file_id="test-id-123",
            display_name="test_file.pdf",
            timestamp=datetime.now(),
            status="Processing",
            duration=0.0,
            file_type="PDF"
        )

        manager.add_entry(entry)

        # Verify initial status
        self.assertEqual(manager.entries[0].status, "Processing")

        # Update the entry status
        success = manager.update_entry("test-id-123", "Done")

        # Verify update was successful
        self.assertTrue(success)
        self.assertEqual(manager.entries[0].status, "Done")

    def test_remove_entry(self):
        """Test removing a dashboard entry."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create and add entries
        entry1 = DashboardEntry.create_from_metadata(
            file_id="id1", display_name="file1.pdf", timestamp=datetime.now(), status="Done", duration=1.0, file_type="PDF"
        )
        entry2 = DashboardEntry.create_from_metadata(
            file_id="id2", display_name="file2.pdf", timestamp=datetime.now(), status="Done", duration=1.5, file_type="PDF"
        )

        manager.add_entry(entry1)
        manager.add_entry(entry2)

        # Verify both entries exist
        self.assertEqual(len(manager.entries), 2)

        # Remove one entry
        success = manager.remove_entry("id1")

        # Verify removal was successful
        self.assertTrue(success)
        self.assertEqual(len(manager.entries), 1)
        self.assertEqual(manager.entries[0].id, "id2")

    def test_get_entry_by_id(self):
        """Test retrieving an entry by its ID."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create and add entries
        entry1 = DashboardEntry.create_from_metadata(
            file_id="id1", display_name="file1.pdf", timestamp=datetime.now(), status="Done", duration=1.0, file_type="PDF"
        )
        entry2 = DashboardEntry.create_from_metadata(
            file_id="id2", display_name="file2.pdf", timestamp=datetime.now(), status="Processing", duration=0.5, file_type="DOCX"
        )

        manager.add_entry(entry1)
        manager.add_entry(entry2)

        # Get first entry by ID
        retrieved_entry = manager.get_entry_by_id("id1")

        # Verify retrieval was successful
        self.assertIsNotNone(retrieved_entry)
        self.assertEqual(retrieved_entry.id, "id1")
        self.assertEqual(retrieved_entry.display_name, "file1.pdf")
        self.assertEqual(retrieved_entry.status, "Done")

        # Try to get non-existent entry
        nonexistent_entry = manager.get_entry_by_id("nonexistent")

        # Verify it returns None
        self.assertIsNone(nonexistent_entry)

    def test_dashboard_update_on_add(self):
        """Test that dashboard file is updated automatically when adding entries."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create and add an entry
        entry = DashboardEntry.create_from_metadata(
            file_id="test-id-123",
            display_name="test_file.pdf",
            timestamp=datetime.now(),
            status="Done",
            duration=1.5,
            file_type="PDF"
        )

        manager.add_entry(entry)

        # Verify the file was updated
        self.assertTrue(self.dashboard_path.exists())

        # Check that the content includes the entry
        content = self.dashboard_path.read_text(encoding='utf-8')
        self.assertIn("test_file.pdf", content)

    def test_to_markdown_row_formatting(self):
        """Test that markdown row formatting works correctly."""
        entry = DashboardEntry.create_from_metadata(
            file_id="test-id-123",
            display_name="test_file.pdf",
            timestamp=datetime(2023, 1, 1, 10, 30, 0),
            status="Done",
            duration=1.5,
            file_type="PDF"
        )

        # Test the markdown row output
        row = entry.to_markdown_row()

        # Should contain formatted time, filename, and status
        self.assertIn("10:30", row)  # Time format
        self.assertIn("test_file.pdf", row)  # Filename
        self.assertIn("(1.5s)", row)  # Duration
        self.assertIn("Done", row)  # Status
        self.assertIn("|", row)  # Markdown table formatting


class TestSecurityLogging(unittest.TestCase):
    """Unit tests for security logging functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.log_file_path = self.test_dir / "test_security.log"

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_security_logger_initialization(self):
        """Test that SecurityLogger initializes correctly."""
        logger = SecurityLogger(str(self.log_file_path))

        self.assertIsNotNone(logger)
        self.assertEqual(logger.log_file_path, self.log_file_path)

    def test_log_file_access(self):
        """Test logging of file access events."""
        logger = SecurityLogger(str(self.log_file_path))

        success = logger.log_file_access("/path/to/file.txt", "system", "READ", "SUCCESS")

        self.assertTrue(success)
        self.assertTrue(self.log_file_path.exists())

        # Check content of log
        content = self.log_file_path.read_text()
        self.assertIn("[SECURITY]", content)
        self.assertIn("ACTION:READ", content)
        self.assertIn("RESULT:SUCCESS", content)

    def test_log_file_processing(self):
        """Test logging of file processing events."""
        logger = SecurityLogger(str(self.log_file_path))

        success = logger.log_file_processing("/path/to/file.txt", "Claude Code", "PROCESS")

        self.assertTrue(success)
        self.assertTrue(self.log_file_path.exists())

        # Check content of log
        content = self.log_file_path.read_text()
        self.assertIn("[PROCESSING]", content)
        self.assertIn("PROCESSOR:Claude Code", content)
        self.assertIn("ACTION:PROCESS", content)

    def test_calculate_file_checksum(self):
        """Test file checksum calculation."""
        # Create a test file
        test_file = self.test_dir / "test_file.txt"
        test_file.write_text("This is test content for checksum calculation.")

        logger = SecurityLogger(str(self.log_file_path))

        checksum = logger.calculate_file_checksum(str(test_file))

        self.assertIsNotNone(checksum)
        self.assertIsInstance(checksum, str)
        self.assertEqual(len(checksum), 64)  # SHA-256 produces 64-character hex

        # Calculate checksum for same content separately to verify
        import hashlib
        expected_checksum = hashlib.sha256(b"This is test content for checksum calculation.").hexdigest()
        self.assertEqual(checksum, expected_checksum)

    def test_log_integrity_check(self):
        """Test logging of integrity check events."""
        logger = SecurityLogger(str(self.log_file_path))

        success = logger.log_integrity_check(
            "/path/to/file.txt",
            "abc123def456",  # expected
            "abc123def456"   # actual (matching)
        )

        self.assertTrue(success)
        self.assertTrue(self.log_file_path.exists())

        # Check content of log
        content = self.log_file_path.read_text()
        self.assertIn("[INTEGRITY]", content)
        self.assertIn("STATUS:PASS", content)

        # Test with mismatched checksums
        success = logger.log_integrity_check(
            "/path/to/file.txt",
            "abc123def456",  # expected
            "xyz789uvw012"   # actual (not matching)
        )

        self.assertTrue(success)

        # Check content of log for failure
        content = self.log_file_path.read_text()
        self.assertIn("STATUS:FAIL", content)


if __name__ == '__main__':
    unittest.main()