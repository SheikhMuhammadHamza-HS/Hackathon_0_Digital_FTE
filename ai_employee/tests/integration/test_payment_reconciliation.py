"""
Integration tests for payment reconciliation workflow.

These tests validate the complete payment matching and reconciliation workflow.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from ai_employee.tests import sample_payment_data, test_config, setup_vault_directories
from ai_employee.core.event_bus import get_event_bus
from ai_employee.utils.approval_system import ApprovalRequest, ApprovalStatus
from ai_employee.domains.payments.models import Payment, PaymentStatus


class TestPaymentReconciliation:
    """Integration tests for payment reconciliation."""

    @pytest.fixture
    async def workflow_components(self, test_config: AppConfig, setup_vault_directories):
        """Setup workflow components for testing."""
        # Mock event bus
        event_bus = get_event_bus()
        await event_bus.start_background_processing()

        # Mock Odoo client
        odoo_client = Mock()
        odoo_client.authenticate = AsyncMock(return_value=True)
        odoo_client.create_payment = AsyncMock(return_value={"id": "odoo_pay_123"})
        odoo_client.reconcile_payment = AsyncMock(return_value=True)
        odoo_client.get_open_invoices = AsyncMock(return_value=[
            {
                "id": "inv_123",
                "invoice_number": "INV-2025-001",
                "amount_due": 6600.00,
                "client_id": "client_123"
            }
        ])

        # Mock bank service
        bank_service = Mock()
        bank_service.get_transactions = AsyncMock(return_value=[
            {
                "id": "txn_123",
                "amount": 6600.00,
                "date": "2025-02-21",
                "reference": "TXN123456",
                "description": "Invoice INV-2025-001",
                "account": "business_account"
            }
        ])

        # Mock approval system
        approval_system = Mock()
        approval_system.create_approval_request = AsyncMock(return_value="approval_123")
        approval_system.check_approval_status = AsyncMock(return_value=None)

        yield {
            "event_bus": event_bus,
            "odoo_client": odoo_client,
            "bank_service": bank_service,
            "approval_system": approval_system,
            "config": test_config
        }

        # Cleanup
        await event_bus.stop_background_processing()

    @pytest.mark.asyncio
    async def test_complete_payment_reconciliation_workflow(self, workflow_components):
        """Test complete payment reconciliation workflow."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given payment service
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        # When processing bank transactions
        reconciled_payments = await payment_service.process_bank_transactions()

        # Then transactions are matched to invoices
        assert len(reconciled_payments) == 1
        payment = reconciled_payments[0]

        assert payment.invoice_id == "inv_123"
        assert payment.amount == 6600.00
        assert payment.status == PaymentStatus.PENDING  # Pending approval

        # And approval request is created for amount > $100
        approval_system.create_approval_request.assert_called_once()

        # When payment is approved
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="payment",
            item_id=payment.id,
            amount=payment.amount
        )
        approval_request.status = ApprovalStatus.APPROVED
        approval_request.approved_by = "Test User"

        approval_system.check_approval_status.return_value = approval_request

        # And reconciling payment
        result = await payment_service.reconcile_payment(payment.id)

        # Then reconciliation succeeds
        assert result is True
        assert payment.status == PaymentStatus.RECONCILED

        # And Odoo is updated
        odoo_client.reconcile_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_payment_reconciliation(self, workflow_components):
        """Test partial payment reconciliation."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given partial payment transaction
        bank_service.get_transactions.return_value = [
            {
                "id": "txn_456",
                "amount": 3300.00,  # Half of invoice amount
                "date": "2025-02-21",
                "reference": "TXN456789",
                "description": "Partial payment INV-2025-001"
            }
        ]

        # When processing transactions
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        reconciled_payments = await payment_service.process_bank_transactions()

        # Then partial payment is created
        assert len(reconciled_payments) == 1
        payment = reconciled_payments[0]

        assert payment.amount == 3300.00
        assert payment.status == PaymentStatus.PENDING

        # When reconciling partial payment
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="payment",
            item_id=payment.id,
            amount=payment.amount
        )
        approval_request.status = ApprovalStatus.APPROVED

        approval_system.check_approval_status.return_value = approval_request

        result = await payment_service.reconcile_payment(payment.id)

        # Then reconciliation succeeds with partial amount noted
        assert result is True
        assert payment.status == PaymentStatus.RECONCILED

    @pytest.mark.asyncio
    async def test_unmatched_transaction_handling(self, workflow_components):
        """Test handling of unmatched transactions."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given transaction with no matching invoice
        bank_service.get_transactions.return_value = [
            {
                "id": "txn_789",
                "amount": 1000.00,
                "date": "2025-02-21",
                "reference": "MYSTERY123",
                "description": "Unknown payment"
            }
        ]

        # When processing transactions
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        reconciled_payments = await payment_service.process_bank_transactions()

        # Then unmatched transaction is flagged for review
        assert len(reconciled_payments) == 1
        payment = reconciled_payments[0]

        assert payment.invoice_id is None  # No invoice matched
        assert payment.amount == 1000.00
        assert "unmatched" in payment.metadata.get("status", "")

        # And manual review is required
        approval_system.create_approval_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_payment_rejection_workflow(self, workflow_components):
        """Test payment rejection workflow."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given payment service
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        # When processing transactions
        reconciled_payments = await payment_service.process_bank_transactions()
        payment = reconciled_payments[0]

        # And payment is rejected
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="payment",
            item_id=payment.id,
            amount=payment.amount
        )
        approval_request.status = ApprovalStatus.REJECTED
        approval_request.notes = "Incorrect invoice reference"

        approval_system.check_approval_status.return_value = approval_request

        # When attempting reconciliation
        result = await payment_service.reconcile_payment(payment.id)

        # Then reconciliation fails
        assert result is False
        assert payment.status == PaymentStatus.PENDING

        # And Odoo is not updated
        odoo_client.reconcile_payment.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_payments_same_invoice(self, workflow_components):
        """Test multiple payments for same invoice."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given multiple partial payments
        bank_service.get_transactions.return_value = [
            {
                "id": "txn_001",
                "amount": 2000.00,
                "date": "2025-02-20",
                "reference": "PAYMENT1",
                "description": "Partial INV-2025-001"
            },
            {
                "id": "txn_002",
                "amount": 3000.00,
                "date": "2025-02-21",
                "reference": "PAYMENT2",
                "description": "Partial INV-2025-001"
            },
            {
                "id": "txn_003",
                "amount": 1600.00,
                "date": "2025-02-22",
                "reference": "PAYMENT3",
                "description": "Final INV-2025-001"
            }
        ]

        # When processing transactions
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        reconciled_payments = await payment_service.process_bank_transactions()

        # Then all payments are matched to same invoice
        assert len(reconciled_payments) == 3
        total_amount = sum(p.amount for p in reconciled_payments)
        assert total_amount == 6600.00  # Full invoice amount

        # All should be linked to same invoice
        for payment in reconciled_payments:
            assert payment.invoice_id == "inv_123"

    @pytest.mark.asyncio
    async def test_overpayment_handling(self, workflow_components):
        """Test overpayment handling."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given overpayment transaction
        bank_service.get_transactions.return_value = [
            {
                "id": "txn_over",
                "amount": 7000.00,  # More than invoice amount
                "date": "2025-02-21",
                "reference": "OVERPAY",
                "description": "Overpayment INV-2025-001"
            }
        ]

        # When processing transactions
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        reconciled_payments = await payment_service.process_bank_transactions()

        # Then overpayment is flagged
        assert len(reconciled_payments) == 1
        payment = reconciled_payments[0]

        assert payment.amount == 7000.00
        assert payment.invoice_id == "inv_123"
        assert payment.metadata.get("overpayment") is True

    @pytest.mark.asyncio
    async def test_payment_matching_algorithm(self, workflow_components):
        """Test payment matching algorithm accuracy."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given multiple invoices and transactions
        odoo_client.get_open_invoices.return_value = [
            {
                "id": "inv_001",
                "invoice_number": "INV-2025-001",
                "amount_due": 1000.00,
                "client_id": "client_A"
            },
            {
                "id": "inv_002",
                "invoice_number": "INV-2025-002",
                "amount_due": 2000.00,
                "client_id": "client_B"
            }
        ]

        bank_service.get_transactions.return_value = [
            {
                "id": "txn_001",
                "amount": 1000.00,
                "reference": "INV-2025-001",
                "description": "Payment for INV-2025-001"
            },
            {
                "id": "txn_002",
                "amount": 2000.00,
                "reference": "INV-2025-002",
                "description": "Payment for INV-2025-002"
            }
        ]

        # When processing transactions
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        reconciled_payments = await payment_service.process_bank_transactions()

        # Then matching is accurate
        assert len(reconciled_payments) == 2

        # Check correct matching
        payments_by_invoice = {p.invoice_id: p for p in reconciled_payments}
        assert payments_by_invoice["inv_001"].amount == 1000.00
        assert payments_by_invoice["inv_002"].amount == 2000.00

    @pytest.mark.asyncio
    async def test_payment_approval_threshold(self, workflow_components):
        """Test payment approval threshold ($100)."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given small payment (<$100)
        bank_service.get_transactions.return_value = [
            {
                "id": "txn_small",
                "amount": 50.00,
                "date": "2025-02-21",
                "reference": "SMALLPAY",
                "description": "Small payment"
            }
        ]

        # When processing transactions
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        reconciled_payments = await payment_service.process_bank_transactions()

        # Then small payment doesn't require approval
        assert len(reconciled_payments) == 1
        payment = reconciled_payments[0]

        assert payment.amount == 50.00
        assert payment.status == PaymentStatus.RECONCILED  # Auto-reconciled

        # And no approval request was created
        approval_system.create_approval_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_payment_error_recovery(self, workflow_components):
        """Test payment workflow error recovery."""
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given bank service failure
        bank_service.get_transactions.side_effect = Exception("Bank API unavailable")

        # When processing transactions
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        # Then error is handled gracefully
        with pytest.raises(Exception, match="Bank API unavailable"):
            await payment_service.process_bank_transactions()

        # When bank service recovers
        bank_service.get_transactions.side_effect = None
        bank_service.get_transactions.return_value = []

        # Then processing can continue
        reconciled_payments = await payment_service.process_bank_transactions()
        assert isinstance(reconciled_payments, list)

    @pytest.mark.asyncio
    async def test_payment_event_publishing(self, workflow_components):
        """Test payment workflow event publishing."""
        event_bus = workflow_components["event_bus"]
        odoo_client = workflow_components["odoo_client"]
        bank_service = workflow_components["bank_service"]
        approval_system = workflow_components["approval_system"]

        # Given event listener
        events_received = []

        async def event_handler(event):
            events_received.append(event)

        event_bus.subscribe(event_handler)

        # When processing transactions
        from ai_employee.domains.payments.services import PaymentService
        payment_service = PaymentService(
            odoo_client=odoo_client,
            bank_service=bank_service,
            approval_system=approval_system
        )

        reconciled_payments = await payment_service.process_bank_transactions()

        # Then appropriate events are published
        await asyncio.sleep(0.1)  # Allow async event processing

        event_types = [type(event).__name__ for event in events_received]
        assert "PaymentReceivedEvent" in event_types

        # When payment is reconciled
        payment = reconciled_payments[0]
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="payment",
            item_id=payment.id,
            amount=payment.amount
        )
        approval_request.status = ApprovalStatus.APPROVED

        approval_system.check_approval_status.return_value = approval_request

        await payment_service.reconcile_payment(payment.id)

        # Then reconciliation event is published
        await asyncio.sleep(0.1)
        event_types = [type(event).__name__ for event in events_received]
        assert "PaymentReconciledEvent" in event_types