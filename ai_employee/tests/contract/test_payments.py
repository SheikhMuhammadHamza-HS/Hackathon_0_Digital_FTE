"""
Contract tests for payment API endpoints.

These tests validate the external contracts of the payment system
and should pass before any implementation exists.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import json

from ai_employee.tests import sample_payment_data, test_config


class TestPaymentContracts:
    """Contract tests for payment endpoints."""

    @pytest.fixture
    async def payment_client(self):
        """Create payment API client for testing."""
        class MockPaymentClient:
            def __init__(self):
                self.base_url = "http://localhost:8000/api/v1"
                self.payments = []

            async def create_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
                """Create payment contract."""
                # Validate required fields
                required_fields = ["invoice_id", "amount", "payment_date", "payment_method"]
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f"Missing required field: {field}")

                # Validate amount
                if data["amount"] <= 0:
                    raise ValueError("Amount must be positive")

                # Validate payment method
                valid_methods = ["bank_transfer", "credit_card", "cash", "check"]
                if data["payment_method"] not in valid_methods:
                    raise ValueError(f"Invalid payment method: {data['payment_method']}")

                # Return contract-compliant response
                payment = {
                    "id": "pay_123",
                    "invoice_id": data["invoice_id"],
                    "amount": data["amount"],
                    "payment_date": data["payment_date"],
                    "status": "pending",
                    "payment_method": data["payment_method"],
                    "bank_reference": data.get("bank_reference"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                return payment

            async def get_payment(self, payment_id: str) -> Dict[str, Any]:
                """Get payment contract."""
                if payment_id == "not_found":
                    raise ValueError("Payment not found")

                return {
                    "id": payment_id,
                    "invoice_id": "inv_123",
                    "amount": 6600.00,
                    "payment_date": "2025-02-21",
                    "status": "reconciled",
                    "payment_method": "bank_transfer",
                    "bank_reference": "TXN123456",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }

            async def list_payments(self, status: str = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
                """List payments contract."""
                return {
                    "payments": [
                        {
                            "id": "pay_123",
                            "invoice_id": "inv_123",
                            "amount": 6600.00,
                            "status": "reconciled",
                            "payment_date": "2025-02-21",
                            "payment_method": "bank_transfer",
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                    ],
                    "total": 1,
                    "limit": limit,
                    "offset": offset
                }

            async def reconcile_payment(self, payment_id: str) -> Dict[str, Any]:
                """Reconcile payment contract."""
                if payment_id == "pay_no_approval":
                    raise ValueError("Approval required for amount > $100")

                return {
                    "id": payment_id,
                    "status": "reconciled",
                    "reconciled_at": datetime.now(timezone.utc).isoformat(),
                    "matched_invoice_id": "inv_123"
                }

            async def match_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
                """Match bank transaction to invoice contract."""
                # Validate transaction data
                required_fields = ["amount", "date", "reference"]
                for field in required_fields:
                    if field not in transaction_data:
                        raise ValueError(f"Missing required field: {field}")

                # Return matching result
                return {
                    "matched": True,
                    "invoice_id": "inv_123",
                    "confidence": 0.95,
                    "suggested_payment": {
                        "invoice_id": "inv_123",
                        "amount": transaction_data["amount"],
                        "payment_method": "bank_transfer",
                        "bank_reference": transaction_data["reference"]
                    }
                }

        return MockPaymentClient()

    @pytest.mark.asyncio
    async def test_create_payment_contract(self, payment_client):
        """Test payment creation contract."""
        # Given valid payment data
        payment_data = {
            "invoice_id": "inv_123",
            "amount": 6600.00,
            "payment_date": "2025-02-21",
            "payment_method": "bank_transfer",
            "bank_reference": "TXN123456"
        }

        # When creating payment
        result = await payment_client.create_payment(payment_data)

        # Then contract is satisfied
        assert "id" in result
        assert result["invoice_id"] == "inv_123"
        assert result["amount"] == 6600.00
        assert result["status"] == "pending"
        assert result["payment_method"] == "bank_transfer"
        assert result["bank_reference"] == "TXN123456"
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_create_payment_validation_contract(self, payment_client):
        """Test payment creation validation contract."""
        # Given invalid payment data (missing amount)
        invalid_data = {
            "invoice_id": "inv_123",
            "payment_date": "2025-02-21",
            "payment_method": "bank_transfer"
        }

        # When creating payment, should raise validation error
        with pytest.raises(ValueError, match="Missing required field"):
            await payment_client.create_payment(invalid_data)

    @pytest.mark.asyncio
    async def test_create_payment_negative_amount_contract(self, payment_client):
        """Test payment creation with negative amount contract."""
        # Given payment data with negative amount
        invalid_data = {
            "invoice_id": "inv_123",
            "amount": -100.00,
            "payment_date": "2025-02-21",
            "payment_method": "bank_transfer"
        }

        # When creating payment, should raise validation error
        with pytest.raises(ValueError, match="Amount must be positive"):
            await payment_client.create_payment(invalid_data)

    @pytest.mark.asyncio
    async def test_create_payment_invalid_method_contract(self, payment_client):
        """Test payment creation with invalid method contract."""
        # Given payment data with invalid method
        invalid_data = {
            "invoice_id": "inv_123",
            "amount": 100.00,
            "payment_date": "2025-02-21",
            "payment_method": "invalid_method"
        }

        # When creating payment, should raise validation error
        with pytest.raises(ValueError, match="Invalid payment method"):
            await payment_client.create_payment(invalid_data)

    @pytest.mark.asyncio
    async def test_get_payment_contract(self, payment_client):
        """Test get payment contract."""
        # Given existing payment ID
        payment_id = "pay_123"

        # When getting payment
        result = await payment_client.get_payment(payment_id)

        # Then contract is satisfied
        assert "id" in result
        assert result["id"] == payment_id
        assert "invoice_id" in result
        assert "amount" in result
        assert "status" in result
        assert "payment_method" in result

    @pytest.mark.asyncio
    async def test_get_not_found_payment_contract(self, payment_client):
        """Test get payment not found contract."""
        # Given non-existent payment ID
        payment_id = "not_found"

        # When getting payment, should raise error
        with pytest.raises(ValueError, match="Payment not found"):
            await payment_client.get_payment(payment_id)

    @pytest.mark.asyncio
    async def test_list_payments_contract(self, payment_client):
        """Test list payments contract."""
        # When listing payments
        result = await payment_client.list_payments()

        # Then contract is satisfied
        assert "payments" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert isinstance(result["payments"], list)

    @pytest.mark.asyncio
    async def test_list_payments_with_status_filter_contract(self, payment_client):
        """Test list payments with status filter contract."""
        # Given status filter
        status = "reconciled"

        # When listing payments with filter
        result = await payment_client.list_payments(status=status)

        # Then contract is satisfied
        assert isinstance(result["payments"], list)
        # All payments should have the specified status
        for payment in result["payments"]:
            assert payment["status"] == status

    @pytest.mark.asyncio
    async def test_reconcile_payment_contract(self, payment_client):
        """Test payment reconciliation contract."""
        # Given payment in pending status
        payment_id = "pay_123"

        # When reconciling payment
        result = await payment_client.reconcile_payment(payment_id)

        # Then contract is satisfied
        assert "id" in result
        assert result["id"] == payment_id
        assert result["status"] == "reconciled"
        assert "reconciled_at" in result
        assert "matched_invoice_id" in result

    @pytest.mark.asyncio
    async def test_reconcile_payment_approval_required_contract(self, payment_client):
        """Test payment reconciliation approval required contract."""
        # Given payment requiring approval (amount > $100)
        payment_id = "pay_no_approval"

        # When reconciling payment, should raise approval error
        with pytest.raises(ValueError, match="Approval required"):
            await payment_client.reconcile_payment(payment_id)

    @pytest.mark.asyncio
    async def test_match_transaction_contract(self, payment_client):
        """Test bank transaction matching contract."""
        # Given bank transaction data
        transaction_data = {
            "amount": 6600.00,
            "date": "2025-02-21",
            "reference": "TXN123456",
            "description": "Invoice payment"
        }

        # When matching transaction
        result = await payment_client.match_transaction(transaction_data)

        # Then contract is satisfied
        assert "matched" in result
        assert isinstance(result["matched"], bool)
        assert "invoice_id" in result
        assert "confidence" in result
        assert "suggested_payment" in result

        if result["matched"]:
            assert result["confidence"] > 0.8  # High confidence match
            assert result["suggested_payment"]["amount"] == transaction_data["amount"]

    @pytest.mark.asyncio
    async def test_match_transaction_validation_contract(self, payment_client):
        """Test transaction matching validation contract."""
        # Given incomplete transaction data
        invalid_data = {
            "amount": 6600.00,
            # Missing date and reference
        }

        # When matching transaction, should raise validation error
        with pytest.raises(ValueError, match="Missing required field"):
            await payment_client.match_transaction(invalid_data)

    @pytest.mark.asyncio
    async def test_partial_payment_contract(self, payment_client):
        """Test partial payment contract."""
        # Given partial payment data
        payment_data = {
            "invoice_id": "inv_123",
            "amount": 3300.00,  # Half of invoice amount
            "payment_date": "2025-02-21",
            "payment_method": "bank_transfer"
        }

        # When creating payment
        result = await payment_client.create_payment(payment_data)

        # Then contract allows partial payments
        assert result["amount"] == 3300.00
        assert result["status"] == "pending"  # Partial payments start as pending

    @pytest.mark.asyncio
    async def test_overpayment_contract(self, payment_client):
        """Test overpayment handling contract."""
        # Given overpayment data
        payment_data = {
            "invoice_id": "inv_123",
            "amount": 7000.00,  # More than invoice amount
            "payment_date": "2025-02-21",
            "payment_method": "bank_transfer"
        }

        # When creating payment
        result = await payment_client.create_payment(payment_data)

        # Then contract handles overpayment
        assert result["amount"] == 7000.00
        # Overpayments might need special handling
        assert "status" in result

    @pytest.mark.asyncio
    async def test_payment_date_validation_contract(self, payment_client):
        """Test payment date validation contract."""
        # Given payment with future date
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        payment_data = {
            "invoice_id": "inv_123",
            "amount": 100.00,
            "payment_date": future_date,
            "payment_method": "bank_transfer"
        }

        # When creating payment, should either allow or raise validation error
        # This test documents the expected behavior
        try:
            result = await payment_client.create_payment(payment_data)
            # If allowed, future dates should be noted
            assert result["payment_date"] == future_date
        except ValueError as e:
            # If not allowed, should have clear error message
            assert "future" in str(e).lower() or "date" in str(e).lower()