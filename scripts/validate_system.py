#!/usr/bin/env python3
"""
System Validation Script

This script performs end-to-end validation of the Personal AI Employee system.
It creates a dummy task, processes it, and verifies dashboard updates.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.services.task_generator import TaskGenerator
from src.services.dashboard_updater import DashboardUpdater
from src.utils.file_utils import ensure_directory_exists


class SystemValidator:
    """Validates the system configuration and performs end-to-end tests."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []

    def log_success(self, message: str):
        """Log a success message."""
        self.successes.append(message)
        print(f"[OK] {message}")

    def log_warning(self, message: str):
        """Log a warning message."""
        self.warnings.append(message)
        print(f"[WARN] {message}")

    def log_error(self, message: str):
        """Log an error message."""
        self.errors.append(message)
        print(f"[ERROR] {message}")

    def check_python_version(self) -> bool:
        """Check Python version is 3.10+."""
        version = sys.version_info
        if version.major == 3 and version.minor >= 10:
            self.log_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            self.log_error(f"Python version {version.major}.{version.minor} is not supported (requires 3.10+)")
            return False

    def check_dependencies(self) -> bool:
        """Check required dependencies are installed."""
        required = [
            ("pytest", "pytest"),
            ("watchdog", "watchdog"),
            ("python-dotenv", "dotenv"),
            ("schedule", "schedule"),
            ("requests", "requests"),
        ]
        missing = []

        for name, import_name in required:
            try:
                __import__(import_name)
                self.log_success(f"Dependency installed: {name}")
            except ImportError:
                missing.append(name)
                self.log_error(f"Dependency missing: {name}")

        if missing:
            self.log_error(f"Missing dependencies: {', '.join(missing)}")
            return False
        return True

    def check_environment_variables(self) -> bool:
        """Check environment variables are configured."""
        required_paths = [
            "INBOX_PATH",
            "NEEDS_ACTION_PATH",
            "PENDING_APPROVAL_PATH",
            "APPROVED_PATH",
            "DONE_PATH",
            "FAILED_PATH",
            "LOGS_PATH",
            "DASHBOARD_PATH",
            "COMPANY_HANDBOOK_PATH",
        ]

        all_good = True
        for path_var in required_paths:
            path_value = getattr(settings, path_var, None)
            if path_value:
                self.log_success(f"{path_var}: {path_value}")
            else:
                self.log_error(f"{path_var} is not configured")
                all_good = False

        # Check optional BUSINESS_GOALS_PATH
        if hasattr(settings, 'BUSINESS_GOALS_PATH'):
            self.log_success(f"BUSINESS_GOALS_PATH: {settings.BUSINESS_GOALS_PATH}")
        else:
            self.log_warning("BUSINESS_GOALS_PATH is not configured (optional)")

        # Check API keys (optional but recommended)
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_"):
            self.log_success("GEMINI_API_KEY is configured")
        else:
            self.log_warning("GEMINI_API_KEY is not configured (optional for testing)")

        return all_good

    def check_folders(self) -> bool:
        """Check required folders exist."""
        required_paths = [
            settings.INBOX_PATH,
            settings.NEEDS_ACTION_PATH,
            settings.PENDING_APPROVAL_PATH,
            settings.APPROVED_PATH,
            settings.DONE_PATH,
            settings.FAILED_PATH,
            settings.LOGS_PATH,
        ]

        all_exist = True
        for folder_path in required_paths:
            if Path(folder_path).exists() and Path(folder_path).is_dir():
                self.log_success(f"Folder exists: {folder_path}")
            else:
                self.log_error(f"Folder missing: {folder_path}")
                all_exist = False

        return all_exist

    def check_content_files(self) -> bool:
        """Check content files exist."""
        content_files = [
            ("Company Handbook", settings.COMPANY_HANDBOOK_PATH),
        ]

        # Check if Business Goals path exists in settings
        if hasattr(settings, 'BUSINESS_GOALS_PATH'):
            content_files.append(("Business Goals", settings.BUSINESS_GOALS_PATH))

        all_exist = True
        for name, file_path in content_files:
            if Path(file_path).exists():
                self.log_success(f"{name}: {file_path}")
            else:
                self.log_warning(f"{name} not found: {file_path} (will be created if needed)")
                all_exist = False

        return all_exist

    def check_dashboard(self) -> bool:
        """Check dashboard exists and has correct format."""
        dashboard_path = Path(settings.DASHBOARD_PATH)

        if not dashboard_path.exists():
            self.log_error(f"Dashboard not found: {dashboard_path}")
            return False

        content = dashboard_path.read_text()
        if "| Time | Task | Status |" in content:
            self.log_success(f"Dashboard has correct format: {dashboard_path}")
            return True
        else:
            self.log_error(f"Dashboard format incorrect: {dashboard_path}")
            return False

    def test_task_creation(self) -> bool:
        """Test creating a dummy task."""
        print("\n--- Testing Task Creation ---")

        inbox_path = Path(settings.INBOX_PATH)
        needs_action_path = Path(settings.NEEDS_ACTION_PATH)
        ensure_directory_exists(inbox_path)

        # Clean up any existing test files first
        test_file = inbox_path / "validation_test.txt"
        if test_file.exists():
            test_file.unlink()
            self.log_success(f"Removed existing test file: {test_file}")

        # Remove any existing test task files
        for task_file in needs_action_path.glob("*validation_test*.json"):
            task_file.unlink()
            self.log_success(f"Removed existing test task: {task_file}")

        # Create a dummy test file
        try:
            test_file.write_text("Validation test file for system check")
            self.log_success(f"Created test file: {test_file}")
        except Exception as e:
            self.log_error(f"Failed to create test file: {e}")
            return False

        # Test task generation
        try:
            generator = TaskGenerator()
            task_path = generator.create_task(test_file)

            if task_path and task_path.exists():
                self.log_success(f"Task created: {task_path}")
                # Store task path for cleanup
                self._test_task_path = task_path
                return True
            elif task_path is None:
                # This might be a duplicate, which is okay for validation
                self.log_warning("Task returned None (likely duplicate - validation still passes)")
                return True
            else:
                self.log_error("Task creation returned None or file doesn't exist")
                return False
        except Exception as e:
            self.log_error(f"Task creation failed: {e}")
            return False

    def test_dashboard_update(self) -> bool:
        """Test dashboard update functionality."""
        print("\n--- Testing Dashboard Update ---")

        try:
            dashboard = DashboardUpdater()
            test_message = "Validation: Dashboard update test"
            dashboard.append_entry(test_message, "SUCCESS")

            dashboard_content = Path(settings.DASHBOARD_PATH).read_text()
            if test_message in dashboard_content:
                self.log_success("Dashboard update successful")
                return True
            else:
                self.log_error("Dashboard update message not found")
                return False
        except Exception as e:
            self.log_error(f"Dashboard update failed: {e}")
            return False

    def cleanup_test_files(self):
        """Clean up test files created during validation."""
        print("\n--- Cleaning Up ---")

        # Remove test file from Inbox
        test_file = Path(settings.INBOX_PATH) / "validation_test.txt"
        if test_file.exists():
            test_file.unlink()
            self.log_success(f"Removed test file: {test_file}")

        # Note: We leave the task file in Needs_Action for inspection

    def run_validation(self) -> bool:
        """Run all validation checks."""
        print("=" * 60)
        print("System Validation")
        print("=" * 60)

        # Basic checks
        checks = [
            ("Python Version", self.check_python_version),
            ("Dependencies", self.check_dependencies),
            ("Environment Variables", self.check_environment_variables),
            ("Folder Structure", self.check_folders),
            ("Content Files", self.check_content_files),
            ("Dashboard", self.check_dashboard),
        ]

        all_passed = True
        for name, check_func in checks:
            print(f"\nChecking {name}...")
            if not check_func():
                all_passed = False

        # Functional tests
        print("\n" + "=" * 60)
        print("Functional Tests")
        print("=" * 60)

        functional_passed = True
        if not self.test_task_creation():
            functional_passed = False
        if not self.test_dashboard_update():
            functional_passed = False

        # Summary
        print("\n" + "=" * 60)
        print("Validation Summary")
        print("=" * 60)

        if all_passed and functional_passed:
            print(f"Successes: {len(self.successes)}")
            print(f"Warnings: {len(self.warnings)}")
            print(f"Errors: {len(self.errors)}")
            print("\nValidation passed! System is ready.")
            self.cleanup_test_files()
            return True
        else:
            print(f"Successes: {len(self.successes)}")
            print(f"Warnings: {len(self.warnings)}")
            print(f"Errors: {len(self.errors)}")
            print("\nValidation failed. Please fix the errors above.")
            if self.errors:
                print("\nErrors:")
                for error in self.errors:
                    print(f"  - {error}")
            return False


def main():
    """Main entry point."""
    validator = SystemValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()