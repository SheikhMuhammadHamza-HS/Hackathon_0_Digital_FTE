#!/usr/bin/env python3
"""Run unit tests with proper environment setup."""

import os
import sys
import subprocess

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
    "APPROVAL_TIMEOUT_HOURS": "4",
    "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
})

# Run pytest
cmd = [
    sys.executable, "-m", "pytest",
    "tests/unit/",
    "-v",
    "--tb=short",
    "-p", "no:warnings"
]

result = subprocess.run(cmd, env=os.environ.copy())
sys.exit(result.returncode)