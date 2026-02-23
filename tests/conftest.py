"""Pytest configuration and fixtures."""

import os
import sys
import pytest
from unittest.mock import Mock

# Set test environment variables
os.environ.update({
    "SECRET_KEY": "test_secret_key_for_testing",
    "JWT_SECRET_KEY": "test_jwt_secret_key_for_testing",
    "ODOO_URL": "http://test-odoo:8069",
    "ODOO_DB": "test_db",
    "ODOO_USERNAME": "test_user",
    "ODOO_PASSWORD": "test_password",
    "EMAIL_HOST": "smtp.test.com",
    "EMAIL_PORT": "587",
    "EMAIL_USER": "test@test.com",
    "EMAIL_PASSWORD": "test_email_password",
    "TWITTER_API_KEY": "test_twitter_key",
    "FACEBOOK_PAGE_ID": "test_page_id",
    "INSTAGRAM_USER_ID": "test_user_id",
    "LINKEDIN_CLIENT_ID": "test_linkedin_id",
    "LOG_LEVEL": "DEBUG",
    "DATA_RETENTION_DAYS": "730",
    "APPROVAL_TIMEOUT_HOURS": "4"
})

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock modules that might cause issues
sys.modules['watchdog'] = Mock()
sys.modules['watchdog.observers'] = Mock()
sys.modules['watchdog.events'] = Mock()

# Mock file monitor to avoid filesystem issues during tests
@pytest.fixture(autouse=True)
def mock_file_monitor():
    """Mock file monitor to avoid filesystem issues."""
    import ai_employee.utils.file_monitor
    ai_employee.utils.file_monitor.file_monitor = Mock()
    ai_employee.utils.file_monitor.get_file_monitor = Mock(return_value=Mock())
