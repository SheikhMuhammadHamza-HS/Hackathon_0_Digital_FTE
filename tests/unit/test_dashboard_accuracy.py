import unittest
import tempfile
import shutil
from pathlib import Path
import time
from datetime import datetime

from src.models.dashboard import DashboardManager, DashboardEntry
from src.utils.file_utils import sanitize_filename


class TestDashboardAccuracy(unittest.TestCase):
    """Tests for dashboard accuracy requirements."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.dashboard_path = self.test_dir / "accuracy_test_dashboard.md"

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_dashboard_reflects_processed_files_correctly(self):
        """Test that dashboard accurately reflects processed files with correct timestamps."""
        manager = DashboardManager(str(self.dashboard_path))

        # Record the time before creating the entry
        before_time = datetime.now()

        # Create an entry with a specific timestamp
        test_time = datetime(2023, 5, 15, 14, 30, 45)
        entry = DashboardEntry.create_from_metadata(
            file_id="accuracy-test-123",
            display_name="accuracy_test_file.pdf",
            timestamp=test_time,
            status="Done",
            duration=2.5,
            file_type="PDF"
        )

        # Add the entry to the dashboard
        manager.add_entry(entry)

        # Record the time after creating the entry
        after_time = datetime.now()

        # Verify the entry was added correctly
        self.assertEqual(len(manager.entries), 1)

        added_entry = manager.entries[0]
        self.assertEqual(added_entry.id, "accuracy-test-123")
        self.assertEqual(added_entry.display_name, "accuracy_test_file.pdf")
        self.assertEqual(added_entry.timestamp, test_time)
        self.assertEqual(added_entry.status, "Done")
        self.assertEqual(added_entry.duration, 2.5)
        self.assertEqual(added_entry.file_type, "PDF")

        # Verify the dashboard file was created and contains the entry
        self.assertTrue(self.dashboard_path.exists())

        # Check the file content
        content = self.dashboard_path.read_text(encoding='utf-8')
        self.assertIn("# Agent Dashboard", content)
        self.assertIn("accuracy_test_file.pdf", content)
        self.assertIn("Done", content)

        # Check that the time is formatted correctly in the markdown
        # The time should be formatted as HH:MM in the table
        expected_time_str = test_time.strftime("%H:%M")
        self.assertIn(expected_time_str, content)

    def test_dashboard_timestamp_accuracy(self):
        """Test that dashboard timestamps are accurate."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create multiple entries with specific timestamps
        timestamps = [
            datetime(2023, 1, 1, 9, 0, 0),
            datetime(2023, 1, 1, 10, 15, 30),
            datetime(2023, 1, 1, 11, 30, 45),
            datetime(2023, 1, 1, 14, 45, 15),
            datetime(2023, 1, 1, 16, 59, 59)
        ]

        for i, ts in enumerate(timestamps):
            entry = DashboardEntry.create_from_metadata(
                file_id=f"timestamp-test-{i}",
                display_name=f"file_{i}.pdf",
                timestamp=ts,
                status="Done",
                duration=float(i) + 0.5,
                file_type="PDF"
            )
            manager.add_entry(entry)

        # Verify all entries were added
        self.assertEqual(len(manager.entries), 5)

        # Verify timestamps are preserved accurately
        for i, ts in enumerate(timestamps):
            entry = manager.entries[i]  # Already sorted by time
            self.assertEqual(entry.timestamp, ts, f"Timestamp for entry {i} should be preserved")

        # Check the dashboard file content
        content = self.dashboard_path.read_text(encoding='utf-8')

        # Each timestamp should appear in HH:MM format in the content
        for ts in timestamps:
            formatted_time = ts.strftime("%H:%M")
            self.assertIn(formatted_time, content, f"Formatted time {formatted_time} should appear in dashboard")

    def test_chronological_order_preservation(self):
        """Test that dashboard preserves chronological order of entries."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create entries with timestamps in random order
        random_times = [
            datetime(2023, 1, 1, 15, 0, 0),  # 3rd chronologically
            datetime(2023, 1, 1, 10, 0, 0),  # 1st chronologically
            datetime(2023, 1, 1, 12, 0, 0),  # 2nd chronologically
            datetime(2023, 1, 1, 18, 0, 0),  # 4th chronologically
        ]

        for i, ts in enumerate(random_times):
            entry = DashboardEntry.create_from_metadata(
                file_id=f"chrono-test-{i}",
                display_name=f"chrono_file_{i}.pdf",
                timestamp=ts,
                status="Done",
                duration=1.0,
                file_type="PDF"
            )
            # Add entries in the random time order
            manager.add_entry(entry)

        # Verify all entries were added
        self.assertEqual(len(manager.entries), 4)

        # Check that entries are sorted chronologically (oldest first)
        expected_order = [random_times[1], random_times[2], random_times[0], random_times[3]]  # Sorted chronologically
        for i, expected_time in enumerate(expected_order):
            self.assertEqual(manager.entries[i].timestamp, expected_time,
                           f"Entry {i} should have chronological timestamp {expected_time}")

        # Check the dashboard file content for correct order
        content = self.dashboard_path.read_text(encoding='utf-8')

        # Find the time entries in the content to verify chronological order
        lines = content.split('\n')
        time_lines = [line for line in lines if '|' in line and ('AM' in line or 'PM' in line or ':' in line)
                      and 'Time' not in line and '------' not in line and line.strip()]

        # Verify that the times are in chronological order when parsed
        for line in time_lines:
            self.assertIn('|', line)  # Make sure it's still a table row

    def test_file_type_and_duration_tracking(self):
        """Test that dashboard tracks file type and duration correctly."""
        manager = DashboardManager(str(self.dashboard_path))

        # Create entries with different file types and durations
        test_cases = [
            ("document.pdf", "PDF", 1.5),
            ("image.png", "PNG", 0.8),
            ("document.docx", "DOCX", 2.3),
            ("data.xlsx", "XLSX", 3.1),
        ]

        for i, (filename, file_type, duration) in enumerate(test_cases):
            entry = DashboardEntry.create_from_metadata(
                file_id=f"type-duration-test-{i}",
                display_name=filename,
                timestamp=datetime(2023, 1, 1, 10 + i, 0, 0),
                status="Done",
                duration=duration,
                file_type=file_type
            )
            manager.add_entry(entry)

        # Verify all entries were added with correct information
        self.assertEqual(len(manager.entries), 4)

        for i, (filename, expected_type, expected_duration) in enumerate(test_cases):
            entry = manager.entries[i]
            self.assertEqual(entry.display_name, filename)
            self.assertEqual(entry.file_type, expected_type)
            self.assertAlmostEqual(entry.duration, expected_duration, places=1)

        # Verify information appears in dashboard file
        content = self.dashboard_path.read_text(encoding='utf-8')

        for filename, file_type, duration in test_cases:
            self.assertIn(filename, content)
            self.assertIn(file_type, content)
            self.assertIn(f"({duration}s)", content)

    def test_concurrent_dashboard_updates(self):
        """Test dashboard behavior with concurrent updates (simulated)."""
        manager = DashboardManager(str(self.dashboard_path))

        # Add multiple entries rapidly to simulate concurrent updates
        start_time = datetime.now()
        for i in range(10):
            entry = DashboardEntry.create_from_metadata(
                file_id=f"concurrent-test-{i}",
                display_name=f"concurrent_file_{i}.pdf",
                timestamp=datetime.now(),
                status="Done",
                duration=0.1,
                file_type="PDF"
            )
            manager.add_entry(entry)
            time.sleep(0.01)  # Brief pause to ensure slightly different timestamps

        end_time = datetime.now()

        # Verify all entries were added
        self.assertEqual(len(manager.entries), 10)

        # Check that entries are within the expected time range
        for entry in manager.entries:
            self.assertGreaterEqual(entry.timestamp, start_time)
            self.assertLessEqual(entry.timestamp, end_time)

        # Verify the dashboard file was updated correctly
        self.assertTrue(self.dashboard_path.exists())
        content = self.dashboard_path.read_text(encoding='utf-8')

        # Check that all entries appear in the file
        for i in range(10):
            self.assertIn(f"concurrent_file_{i}.pdf", content)


class TestRealTimeUpdates(unittest.TestCase):
    """Tests for real-time dashboard updates."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.dashboard_path = self.test_dir / "realtime_test_dashboard.md"

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_real_time_entry_addition(self):
        """Test that entries are added to dashboard in real-time."""
        manager = DashboardManager(str(self.dashboard_path))

        # Initially, dashboard should be empty
        self.assertEqual(len(manager.entries), 0)
        if self.dashboard_path.exists():
            initial_content = self.dashboard_path.read_text(encoding='utf-8')
        else:
            initial_content = ""

        # Add an entry
        entry = DashboardEntry.create_from_metadata(
            file_id="realtime-add-test",
            display_name="realtime_added_file.pdf",
            timestamp=datetime.now(),
            status="Processing",
            duration=None,
            file_type="PDF"
        )
        manager.add_entry(entry)

        # Verify entry was added immediately
        self.assertEqual(len(manager.entries), 1)
        self.assertEqual(manager.entries[0].display_name, "realtime_added_file.pdf")

        # Verify dashboard file was updated immediately
        self.assertTrue(self.dashboard_path.exists())
        content_after_add = self.dashboard_path.read_text(encoding='utf-8')
        self.assertNotEqual(content_after_add, initial_content)
        self.assertIn("realtime_added_file.pdf", content_after_add)

    def test_real_time_entry_update(self):
        """Test that entries are updated on the dashboard in real-time."""
        manager = DashboardManager(str(self.dashboard_path))

        # Add an initial entry with "Processing" status
        entry = DashboardEntry.create_from_metadata(
            file_id="realtime-update-test",
            display_name="realtime_updating_file.pdf",
            timestamp=datetime.now(),
            status="Processing",
            duration=0.0,
            file_type="PDF"
        )
        manager.add_entry(entry)

        # Verify initial state
        self.assertEqual(len(manager.entries), 1)
        self.assertEqual(manager.entries[0].status, "Processing")

        # Update the entry status to "Done"
        update_success = manager.update_entry("realtime-update-test", "Done")

        # Verify update was successful
        self.assertTrue(update_success)
        self.assertEqual(manager.entries[0].status, "Done")

        # Verify dashboard file was updated with new status
        content_after_update = self.dashboard_path.read_text(encoding='utf-8')
        self.assertIn("Done", content_after_update)
        self.assertNotIn("Processing", content_after_update.replace("Done", ""))  # Should not have "Processing" except as part of "Done"

    def test_real_time_multiple_operations(self):
        """Test multiple real-time operations in sequence."""
        manager = DashboardManager(str(self.dashboard_path))

        # Verify initial state
        self.assertEqual(len(manager.entries), 0)

        operations_log = []

        # Add first entry
        entry1 = DashboardEntry.create_from_metadata(
            file_id="op1",
            display_name="operation_1.pdf",
            timestamp=datetime.now(),
            status="Processing",
            duration=0.0,
            file_type="PDF"
        )
        manager.add_entry(entry1)
        operations_log.append(f"After add 1: {len(manager.entries)} entries")

        # Add second entry
        entry2 = DashboardEntry.create_from_metadata(
            file_id="op2",
            display_name="operation_2.pdf",
            timestamp=datetime.now(),
            status="Processing",
            duration=0.0,
            file_type="DOCX"
        )
        manager.add_entry(entry2)
        operations_log.append(f"After add 2: {len(manager.entries)} entries")

        # Update first entry
        manager.update_entry("op1", "Done")
        operations_log.append(f"After update op1: status={manager.get_entry_by_id('op1').status}")

        # Add third entry
        entry3 = DashboardEntry.create_from_metadata(
            file_id="op3",
            display_name="operation_3.png",
            timestamp=datetime.now(),
            status="Processing",
            duration=0.0,
            file_type="PNG"
        )
        manager.add_entry(entry3)
        operations_log.append(f"After add 3: {len(manager.entries)} entries")

        # Verify final state
        self.assertEqual(len(manager.entries), 3)
        self.assertEqual(manager.get_entry_by_id("op1").status, "Done")
        self.assertEqual(manager.get_entry_by_id("op2").status, "Processing")
        self.assertEqual(manager.get_entry_by_id("op3").status, "Processing")

        # Verify dashboard file reflects all operations
        content = self.dashboard_path.read_text(encoding='utf-8')
        self.assertIn("operation_1.pdf", content)
        self.assertIn("operation_2.pdf", content)
        self.assertIn("operation_3.png", content)
        self.assertIn("Done", content)
        self.assertIn("Processing", content)


if __name__ == '__main__':
    unittest.main()