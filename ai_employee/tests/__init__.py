"""
Test suite for AI Employee system.

Provides comprehensive testing including:
- Unit tests for individual components
- Integration tests for workflows
- Contract tests for external APIs
- Test fixtures and utilities
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock

from ai_employee.core.config import AppConfig, PathsConfig


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_config(temp_dir: Path) -> AppConfig:
    """Create test configuration."""
    vault_path = temp_dir / "vault"

    return AppConfig(
        log_level="DEBUG",
        environment="test",
        debug=True,
        paths=PathsConfig(
            vault_path=vault_path,
            inbox_path=vault_path / "Inbox",
            needs_action_path=vault_path / "Needs_Action",
            pending_approval_path=vault_path / "Pending_Approval",
            approved_path=vault_path / "Approved",
            rejected_path=vault_path / "Rejected",
            done_path=vault_path / "Done",
            logs_path=vault_path / "Logs",
            reports_path=vault_path / "Reports",
            archive_path=vault_path / "Archive",
        )
    )


@pytest.fixture
def mock_odoo_client():
    """Create a mock Odoo client."""
    client = Mock()
    client.authenticate = AsyncMock(return_value=True)
    client.create_invoice = AsyncMock(return_value={"id": "test_invoice_123"})
    client.create_payment = AsyncMock(return_value={"id": "test_payment_123"})
    client.post_invoice = AsyncMock(return_value=True)
    client.reconcile_payment = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_email_service():
    """Create a mock email service."""
    service = Mock()
    service.send_email = AsyncMock(return_value=True)
    service.send_invoice = AsyncMock(return_value=True)
    service.send_notification = AsyncMock(return_value=True)
    return service


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    return {
        "client_id": "client_123",
        "issue_date": "2025-02-21",
        "due_date": "2025-03-21",
        "line_items": [
            {
                "description": "Consulting services",
                "quantity": 40,
                "unit_price": 150.00,
                "tax_rate": 0.10
            }
        ],
        "notes": "Monthly consulting retainer"
    }


@pytest.fixture
def sample_payment_data():
    """Sample payment data for testing."""
    return {
        "invoice_id": "invoice_123",
        "amount": 6600.00,
        "payment_date": "2025-02-21",
        "payment_method": "bank_transfer",
        "bank_reference": "TXN123456"
    }


@pytest.fixture
def sample_social_post_data():
    """Sample social media post data for testing."""
    return {
        "platform": "twitter",
        "content": "Check out our latest AI automation features! #AI #Automation",
        "scheduled_at": "2025-02-21T14:00:00Z",
        "media_urls": []
    }


@pytest.fixture
async def setup_vault_directories(test_config: AppConfig) -> None:
    """Setup vault directories for testing."""
    for path in [
        test_config.paths.inbox_path,
        test_config.paths.needs_action_path,
        test_config.paths.pending_approval_path,
        test_config.paths.approved_path,
        test_config.paths.rejected_path,
        test_config.paths.done_path,
        test_config.paths.logs_path,
        test_config.paths.reports_path,
        test_config.paths.archive_path,
    ]:
        path.mkdir(parents=True, exist_ok=True)