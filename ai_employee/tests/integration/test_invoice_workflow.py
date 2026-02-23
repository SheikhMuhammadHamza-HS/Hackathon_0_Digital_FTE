"""
Integration tests for invoice workflow.

These tests validate the complete invoice creation and approval workflow.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch

from ai_employee.tests import sample_invoice_data, test_config, setup_vault_directories
from ai_employee.core.config import AppConfig
from ai_employee.core.event_bus import get_event_bus
from ai_employee.utils.approval_system import ApprovalRequest, ApprovalStatus
from ai_employee.domains.invoicing.models import Invoice, InvoiceStatus


class TestInvoiceWorkflow:
    """Integration tests for invoice workflow."""

    @pytest.fixture
    async def workflow_components(self, test_config: AppConfig, setup_vault_directories):
        """Setup workflow components for testing."""
        # Mock event bus
        event_bus = get_event_bus()
        await event_bus.start_background_processing()

        # Mock Odoo client
        odoo_client = Mock()
        odoo_client.authenticate = AsyncMock(return_value=True)
        odoo_client.create_invoice = AsyncMock(return_value={"id": "odoo_inv_123"})
        odoo_client.post_invoice = AsyncMock(return_value=True)

        # Mock email service
        email_service = Mock()
        email_service.send_invoice = AsyncMock(return_value=True)

        # Mock approval system
        approval_system = Mock()
        approval_system.create_approval_request = AsyncMock(return_value="approval_123")
        approval_system.check_approval_status = AsyncMock(return_value=None)

        yield {
            "event_bus": event_bus,
            "odoo_client": odoo_client,
            "email_service": email_service,
            "approval_system": approval_system,
            "config": test_config
        }

        # Cleanup
        await event_bus.stop_background_processing()

    @pytest.mark.asyncio
    async def test_complete_invoice_workflow(self, workflow_components):
        """Test complete invoice creation workflow."""
        event_bus = workflow_components["event_bus"]
        odoo_client = workflow_components["odoo_client"]
        email_service = workflow_components["email_service"]
        approval_system = workflow_components["approval_system"]
        config = workflow_components["config"]

        # Given invoice data
        invoice_data = sample_invoice_data

        # Create invoice service
        from ai_employee.domains.invoicing.services import InvoiceService
        invoice_service = InvoiceService(
            odoo_client=odoo_client,
            email_service=email_service,
            approval_system=approval_system
        )

        # When creating invoice
        invoice = await invoice_service.create_invoice(invoice_data)

        # Then invoice is created with correct properties
        assert invoice is not None
        assert invoice.status == InvoiceStatus.DRAFT
        assert invoice.client_id == invoice_data["client_id"]
        assert invoice.total_amount > 0

        # And Odoo integration was called
        odoo_client.create_invoice.assert_called_once()

        # And approval request was created for amount > $100
        approval_system.create_approval_request.assert_called_once()

        # When invoice is approved
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="invoice",
            item_id=invoice.id,
            amount=invoice.total_amount
        )
        approval_request.status = ApprovalStatus.APPROVED
        approval_request.approved_by = "Test User"

        approval_system.check_approval_status.return_value = approval_request

        # And posting invoice
        result = await invoice_service.post_invoice(invoice.id)

        # Then invoice is posted successfully
        assert result is True
        assert invoice.status == InvoiceStatus.POSTED

        # And Odoo was called to post
        odoo_client.post_invoice.assert_called_once()

        # And email was sent
        email_service.send_invoice.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoice_rejection_workflow(self, workflow_components):
        """Test invoice rejection workflow."""
        event_bus = workflow_components["event_bus"]
        odoo_client = workflow_components["odoo_client"]
        email_service = workflow_components["email_service"]
        approval_system = workflow_components["approval_system"]

        # Given invoice service
        from ai_employee.domains.invoicing.services import InvoiceService
        invoice_service = InvoiceService(
            odoo_client=odoo_client,
            email_service=email_service,
            approval_system=approval_system
        )

        # When creating invoice
        invoice = await invoice_service.create_invoice(sample_invoice_data)

        # And invoice is rejected
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="invoice",
            item_id=invoice.id,
            amount=invoice.total_amount
        )
        approval_request.status = ApprovalStatus.REJECTED
        approval_request.notes = "Client not verified"

        approval_system.check_approval_status.return_value = approval_request

        # When attempting to post rejected invoice
        result = await invoice_service.post_invoice(invoice.id)

        # Then posting fails
        assert result is False
        assert invoice.status == InvoiceStatus.DRAFT

        # And Odoo was not called to post
        odoo_client.post_invoice.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoice_approval_timeout_workflow(self, workflow_components):
        """Test invoice approval timeout workflow."""
        odoo_client = workflow_components["odoo_client"]
        email_service = workflow_components["email_service"]
        approval_system = workflow_components["approval_system"]

        # Given invoice service
        from ai_employee.domains.invoicing.services import InvoiceService
        invoice_service = InvoiceService(
            odoo_client=odoo_client,
            email_service=email_service,
            approval_system=approval_system
        )

        # When creating invoice
        invoice = await invoice_service.create_invoice(sample_invoice_data)

        # And approval expires
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="invoice",
            item_id=invoice.id,
            amount=invoice.total_amount,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        )
        approval_request.status = ApprovalStatus.EXPIRED

        approval_system.check_approval_status.return_value = approval_request

        # When attempting to post expired invoice
        result = await invoice_service.post_invoice(invoice.id)

        # Then posting fails
        assert result is False

        # And new approval request is created
        assert approval_system.create_approval_request.call_count == 2

    @pytest.mark.asyncio
    async def test_small_invoice_auto_approval(self, workflow_components):
        """Test auto-approval for small invoices (<$100)."""
        odoo_client = workflow_components["odoo_client"]
        email_service = workflow_components["email_service"]
        approval_system = workflow_components["approval_system"]

        # Given invoice service
        from ai_employee.domains.invoicing.services import InvoiceService
        invoice_service = InvoiceService(
            odoo_client=odoo_client,
            email_service=email_service,
            approval_system=approval_system
        )

        # When creating small invoice (<$100)
        small_invoice_data = {
            "client_id": "client_123",
            "issue_date": "2025-02-21",
            "due_date": "2025-03-21",
            "line_items": [
                {
                    "description": "Small service",
                    "quantity": 1,
                    "unit_price": 50.00
                }
            ]
        }

        invoice = await invoice_service.create_invoice(small_invoice_data)

        # Then approval should not be required for small amounts
        approval_system.create_approval_request.assert_not_called()

        # When posting small invoice
        result = await invoice_service.post_invoice(invoice.id)

        # Then posting succeeds without approval
        assert result is True
        assert invoice.status == InvoiceStatus.POSTED

    @pytest.mark.asyncio
    async def test_invoice_calculation_workflow(self, workflow_components):
        """Test invoice calculation workflow with multiple line items."""
        odoo_client = workflow_components["odoo_client"]
        email_service = workflow_components["email_service"]
        approval_system = workflow_components["approval_system"]

        # Given invoice service
        from ai_employee.domains.invoicing.services import InvoiceService
        invoice_service = InvoiceService(
            odoo_client=odoo_client,
            email_service=email_service,
            approval_system=approval_system
        )

        # When creating invoice with multiple items and different tax rates
        complex_invoice_data = {
            "client_id": "client_123",
            "issue_date": "2025-02-21",
            "due_date": "2025-03-21",
            "line_items": [
                {
                    "description": "Standard service",
                    "quantity": 10,
                    "unit_price": 100.00,
                    "tax_rate": 0.10  # 10% tax
                },
                {
                    "description": "Premium service",
                    "quantity": 5,
                    "unit_price": 200.00,
                    "tax_rate": 0.15  # 15% tax
                },
                {
                    "description": "Tax-exempt item",
                    "quantity": 2,
                    "unit_price": 50.00,
                    "tax_rate": 0.00  # No tax
                }
            ]
        }

        invoice = await invoice_service.create_invoice(complex_invoice_data)

        # Then calculations are correct
        # Standard: 10 * 100 = 1000, tax = 100
        # Premium: 5 * 200 = 1000, tax = 150
        # Exempt: 2 * 50 = 100, tax = 0
        assert invoice.subtotal == 2100.00
        assert invoice.tax_amount == 250.00
        assert invoice.total_amount == 2350.00

        # And line items are preserved
        assert len(invoice.line_items) == 3

    @pytest.mark.asyncio
    async def test_invoice_error_handling_workflow(self, workflow_components):
        """Test invoice workflow error handling."""
        odoo_client = workflow_components["odoo_client"]
        email_service = workflow_components["email_service"]
        approval_system = workflow_components["approval_system"]

        # Given Odoo client failure
        odoo_client.create_invoice.side_effect = Exception("Odoo connection failed")

        # When creating invoice
        from ai_employee.domains.invoicing.services import InvoiceService
        invoice_service = InvoiceService(
            odoo_client=odoo_client,
            email_service=email_service,
            approval_system=approval_system
        )

        # Then creation should fail gracefully
        with pytest.raises(Exception, match="Odoo connection failed"):
            await invoice_service.create_invoice(sample_invoice_data)

        # And no approval request is created
        approval_system.create_approval_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoice_event_publishing(self, workflow_components):
        """Test invoice workflow event publishing."""
        event_bus = workflow_components["event_bus"]
        odoo_client = workflow_components["odoo_client"]
        email_service = workflow_components["email_service"]
        approval_system = workflow_components["approval_system"]

        # Given event listener
        events_received = []

        async def event_handler(event):
            events_received.append(event)

        event_bus.subscribe(event_handler)

        # When creating invoice
        from ai_employee.domains.invoicing.services import InvoiceService
        invoice_service = InvoiceService(
            odoo_client=odoo_client,
            email_service=email_service,
            approval_system=approval_system
        )

        invoice = await invoice_service.create_invoice(sample_invoice_data)

        # Then appropriate events are published
        await asyncio.sleep(0.1)  # Allow async event processing

        event_types = [type(event).__name__ for event in events_received]
        assert "InvoiceCreatedEvent" in event_types

        # When invoice is approved and posted
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="invoice",
            item_id=invoice.id,
            amount=invoice.total_amount
        )
        approval_request.status = ApprovalStatus.APPROVED

        approval_system.check_approval_status.return_value = approval_request

        await invoice_service.post_invoice(invoice.id)

        # Then additional events are published
        await asyncio.sleep(0.1)
        event_types = [type(event).__name__ for event in events_received]
        assert "InvoicePostedEvent" in event_types

    @pytest.mark.asyncio
    async def test_invoice_duplicate_detection(self, workflow_components):
        """Test invoice duplicate detection."""
        odoo_client = workflow_components["odoo_client"]
        email_service = workflow_components["email_service"]
        approval_system = workflow_components["approval_system"]

        # Given invoice service
        from ai_employee.domains.invoicing.services import InvoiceService
        invoice_service = InvoiceService(
            odoo_client=odoo_client,
            email_service=email_service,
            approval_system=approval_system
        )

        # When creating first invoice
        invoice1 = await invoice_service.create_invoice(sample_invoice_data)

        # And creating identical invoice
        invoice2 = await invoice_service.create_invoice(sample_invoice_data)

        # Then invoices should have different IDs but same content
        assert invoice1.id != invoice2.id
        assert invoice1.client_id == invoice2.client_id
        assert invoice1.total_amount == invoice2.total_amount

        # And both are tracked separately
        invoices = await invoice_service.list_invoices({"client_id": "client_123"})
        assert len(invoices) == 2