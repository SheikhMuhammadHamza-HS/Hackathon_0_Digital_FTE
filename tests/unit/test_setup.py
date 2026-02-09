import unittest
import tempfile
import shutil
from pathlib import Path
import os

from src.services.file_mover import FileMover
from src.services.trigger_generator import TriggerGenerator
from src.config.settings import settings


class TestSetupFunctionality(unittest.TestCase):
    """Unit tests for setup functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp())

        # Temporarily modify settings for testing
        self.original_inbox = settings.INBOX_PATH
        self.original_needs_action = settings.NEEDS_ACTION_PATH
        self.original_done = settings.DONE_PATH
        self.original_logs = settings.LOGS_PATH
        self.original_dashboard = settings.DASHBOARD_PATH
        self.original_handbook = settings.COMPANY_HANDBOOK_PATH

        # Point settings to test directory
        settings.INBOX_PATH = self.test_dir / "Inbox"
        settings.NEEDS_ACTION_PATH = self.test_dir / "Needs_Action"
        settings.DONE_PATH = self.test_dir / "Done"
        settings.LOGS_PATH = self.test_dir / "Logs"
        settings.DASHBOARD_PATH = self.test_dir / "Dashboard.md"
        settings.COMPANY_HANDBOOK_PATH = self.test_dir / "Company_Handbook.md"
        settings.CLAUDE_CODE_API_KEY = "test-claude-key"
        settings.GEMINI_API_KEY = "test-gemini-key"

    def tearDown(self):
        """Clean up test environment."""
        # Restore original settings
        settings.INBOX_PATH = self.original_inbox
        settings.NEEDS_ACTION_PATH = self.original_needs_action
        settings.DONE_PATH = self.original_done
        settings.LOGS_PATH = self.original_logs
        settings.DASHBOARD_PATH = self.original_dashboard
        settings.COMPANY_HANDBOOK_PATH = self.original_handbook
        settings.GEMINI_API_KEY = ""
        settings.CLAUDE_CODE_API_KEY = ""

        # Remove test directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ensure_directory_structure(self):
        """Test that directory structure is created correctly."""
        directories = [
            settings.INBOX_PATH,
            settings.NEEDS_ACTION_PATH,
            settings.DONE_PATH,
            settings.LOGS_PATH
        ]

        results = FileMover.ensure_directory_structure(directories)

        # Check that all directories were created successfully
        for dir_path in directories:
            self.assertTrue(results[str(dir_path)], f"Directory {dir_path} should be created successfully")
            self.assertTrue(dir_path.exists(), f"Directory {dir_path} should exist on filesystem")

    def test_create_initial_dashboard(self):
        """Test that initial dashboard is created correctly."""
        dashboard_path = self.test_dir / "test_dashboard.md"

        success = TriggerGenerator.create_initial_dashboard(str(dashboard_path))

        self.assertTrue(success, "Dashboard creation should succeed")
        self.assertTrue(dashboard_path.exists(), "Dashboard file should exist")

        # Check content of dashboard
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("# Agent Dashboard", content, "Dashboard should contain title")
        self.assertIn("| Time | Task | Status |", content, "Dashboard should contain table headers")

    def test_create_company_handbook(self):
        """Test that company handbook is created correctly."""
        handbook_path = self.test_dir / "test_handbook.md"

        success = TriggerGenerator.create_company_handbook(str(handbook_path))

        self.assertTrue(success, "Handbook creation should succeed")
        self.assertTrue(handbook_path.exists(), "Handbook file should exist")

        # Check content of handbook
        with open(handbook_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("# Company Handbook", content, "Handbook should contain title")
        self.assertIn("Agent Behaviors", content, "Handbook should contain agent behaviors section")

    def test_configuration_validation(self):
        """Test that configuration validation works correctly."""
        # With valid settings, validation should return no errors
        errors = settings.validate()
        self.assertEqual(len(errors), 0, f"No errors should be found in valid configuration, got: {errors}")

    def test_file_move_functionality(self):
        """Test basic file moving functionality."""
        # Create a test source file
        source_file = self.test_dir / "test_source.txt"
        source_file.write_text("Test content")

        # Destination path
        dest_file = self.test_dir / "test_destination.txt"

        # Move the file
        success = FileMover.move_file(source_file, dest_file)

        self.assertTrue(success, "File move should succeed")
        self.assertFalse(source_file.exists(), "Source file should no longer exist")
        self.assertTrue(dest_file.exists(), "Destination file should exist")
        self.assertEqual(dest_file.read_text(), "Test content", "Content should be preserved")


if __name__ == '__main__':
    unittest.main()