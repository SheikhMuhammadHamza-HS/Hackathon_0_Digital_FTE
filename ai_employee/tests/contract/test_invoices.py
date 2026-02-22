"""
Contract tests for invoice API endpoints.

These tests validate the external contracts of the invoice system
and should pass before any implementation exists.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import json

from ai_employee.tests import sample_invoice_data, test_config
from ai_employee.core.config import get_config


class TestInvoiceContracts:
    """Contract tests for invoice endpoints."""

    @pytest.fixture
    async def invoice_client(self):
        """Create invoice API client for testing."""
        # This would be a real API client - for now we'll simulate
        class MockInvoiceClient:
            def __init__(self):
                self.base_url = "http://localhost:8000/api/v1"
                self.invoices = []

            async def create_invoice(self, data: Dict[str, Any]) -> Dict[str, Any]:
                """Create invoice contract."""
                # Validate required fields
                required_fields = ["client_id", "issue_date", "due_date", "line_items"]
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f"Missing required field: {field}")

                # Validate line items
                if not data["line_items"]:
                    raise ValueError("At least one line item required")

                for item in data["line_items"]:
                    if "description" not in item or "quantity" not in item or "unit_price" not in item:
                        raise ValueError("Invalid line item format")

                # Return contract-compliant response
                invoice = {
                    "id": "inv_123",
                    "invoice_number": "INV-2025-001",
                    "status": "draft",
                    "client_id": data["client_id"],
                    "issue_date": data["issue_date"],
                    "due_date": data["due_date"],
                    "subtotal": 6000.00,
                    "tax_amount": 600.00,
                    "total_amount": 6600.00,
                    "line_items": data["line_items"],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                return invoice

            async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
                """Get invoice contract."""
                if invoice_id == "not_found":
                    raise ValueError("Invoice not found")

                return {
                    "id": invoice_id,
                    "invoice_number": "INV-2025-001",
                    "status": "draft",
                    "client_id": "client_123",
                    "subtotal": 6000.00,
                    "tax_amount": 600.00,
                    "total_amount": 6600.00,
                    "created_at": datetime.utcnow().isoformat()
                }

            async def list_invoices(self, status: str = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
                """List invoices contract."""
                return {
                    "invoices": [
                        {
                            "id": "inv_123",
                            "invoice_number": "INV-2025-001",
                            "status": "draft",
                            "total_amount": 6600.00,
                            "created_at": datetime.utcnow().isoformat()
                        }
                    ],
                    "total": 1,
                    "limit": limit,
                    "offset": offset
                }

            async def post_invoice(self, invoice_id: str) -> Dict[str, Any]:
                """Post invoice contract."""
                if invoice_id == "inv_no_approval":
                    raise ValueError("Approval required")

                return {
                    "id": invoice_id,
                    "status": "posted",
                    "posted_at": datetime.utcnow().isoformat()
                }

        return MockInvoiceClient()

    @pytest.mark.asyncio
    async def test_create_invoice_contract(self, invoice_client):
        """Test invoice creation contract."""
        # Given valid invoice data
        invoice_data = {
            "client_id": "client_123",
            "issue_date": "2025-02-21",
            "due_date": "2025-03-21",
            "line_items": [
                {
                    "description": "Consulting services",
                    "quantity": 40,
                    "unit_price": 150.00
                }
            ]
        }

        # When creating invoice
        result = await invoice_client.create_invoice(invoice_data)

        # Then contract is satisfied
        assert "id" in result
        assert "invoice_number" in result
        assert result["status"] == "draft"
        assert result["client_id"] == "client_123"
        assert "total_amount" in result
        assert isinstance(result["total_amount"], (int, float))
        assert "line_items" in result
        assert len(result["line_items"]) == 1

    @pytest.mark.asyncio
    async def test_create_invoice_validation_contract(self, invoice_client):
        """Test invoice creation validation contract."""
        # Given invalid invoice data (missing client_id)
        invalid_data = {
            "issue_date": "2025-02-21",
            "due_date": "2025-03-21",
            "line_items": []
        }

        # When creating invoice, should raise validation error
        with pytest.raises(ValueError, match="Missing required field"):
            await invoice_client.create_invoice(invalid_data)

    @pytest.mark.asyncio
    async def test_get_invoice_contract(self, invoice_client):
        """Test get invoice contract."""
        # Given existing invoice ID
        invoice_id = "inv_123"

        # When getting invoice
        result = await invoice_client.get_invoice(invoice_id)

        # Then contract is satisfied
        assert "id" in result
        assert result["id"] == invoice_id
        assert "invoice_number" in result
        assert "status" in result
        assert "total_amount" in result

    @pytest.mark.asyncio
    async def test_get_not_found_invoice_contract(self, invoice_client):
        """Test get invoice not found contract."""
        # Given non-existent invoice ID
        invoice_id = "not_found"

        # When getting invoice, should raise error
        with pytest.raises(ValueError, match="Invoice not found"):
            await invoice_client.get_invoice(invoice_id)

    @pytest.mark.asyncio
    async def test_list_invoices_contract(self, invoice_client):
        """Test list invoices contract."""
        # When listing invoices
        result = await invoice_client.list_invoices()

        # Then contract is satisfied
        assert "invoices" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert isinstance(result["invoices"], list)

    @pytest.mark.asyncio
    async def test_list_invoices_with_filters_contract(self, invoice_client):
        """Test list invoices with filters contract."""
        # Given filters
        status = "draft"
        limit = 10
        offset = 5

        # When listing invoices with filters
        result = await invoice_client.list_invoices(status=status, limit=limit, offset=offset)

        # Then contract is satisfied
        assert result["limit"] == limit
        assert result["offset"] == offset

    @pytest.mark.asyncio
    async def test_post_invoice_contract(self, invoice_client):
        """Test post invoice contract."""
        # Given invoice in draft status
        invoice_id = "inv_123"

        # When posting invoice
        result = await invoice_client.post_invoice(invoice_id)

        # Then contract is satisfied
        assert "id" in result
        assert result["id"] == invoice_id
        assert result["status"] == "posted"
        assert "posted_at" in result

    @pytest.mark.asyncio
    async def test_post_invoice_approval_required_contract(self, invoice_client):
        """Test post invoice approval required contract."""
        # Given invoice requiring approval
        invoice_id = "inv_no_approval"

        # When posting invoice, should raise approval error
        with pytest.raises(ValueError, match="Approval required"):
            await invoice_client.post_invoice(invoice_id)

    @pytest.mark.asyncio
    async def test_invoice_calculations_contract(self, invoice_client):
        """Test invoice calculation contract."""
        # Given invoice with multiple items
        invoice_data = {
            "client_id": "client_123",
            "issue_date": "2025-02-21",
            "due_date": "2025-03-21",
            "line_items": [
                {
                    "description": "Service A",
                    "quantity": 10,
                    "unit_price": 100.00
                },
                {
                    "description": "Service B",
                    "quantity": 5,
                    "unit_price": 200.00
                }
            ]
        }

        # When creating invoice
        result = await invoice_client.create_invoice(invoice_data)

        # Then calculations are correct
        assert result["subtotal"] == 2000.00  # 10*100 + 5*200
        assert result["tax_amount"] == 200.00  # 10% tax
        assert result["total_amount"] == 2200.00  # subtotal + tax

    @pytest.mark.asyncio
    async def test_invoice_date_validation_contract(self, invoice_client):
        """Test invoice date validation contract."""
        # Given invoice with invalid dates
        invalid_data = {
            "client_id": "client_123",
            "issue_date": "2025-03-21",  # Issue after due date
            "due_date": "2025-02-21",
            "line_items": [{"description": "Test", "quantity": 1, "unit_price": 100}]
        }

        # When creating invoice, should raise validation error
        with pytest.raises(ValueError, match="Invalid dates"):
            await invoice_client.create_invoice(invalid_data)

    @pytest.mark.asyncio
    async def test_invoice_line_item_validation_contract(self, invoice_client):
        """Test invoice line item validation contract."""
        # Given invoice with invalid line item
        invalid_data = {
            "client_id": "client_123",
            "issue_date": "2025-02-21",
            "due_date": "2025-03-21",
            "line_items": [
                {
                    "description": "Test",
                    # Missing quantity and unit_price
                }
            ]
        }

        # When creating invoice, should raise validation error
        with pytest.raises(ValueError, match="Invalid line item"):
            await invoice_client.create_invoice(invalid_data)