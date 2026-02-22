"""
Payment domain services for AI Employee system.

Provides business logic for payment processing, reconciliation,
and bank transaction matching.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple, Union
from decimal import Decimal
import re

from .. import DomainService
from .models import Payment, BankTransaction, PaymentStatus, PaymentMethod, TransactionType, Money, PaymentMatch
from ..invoicing.models import Invoice, InvoiceStatus
from ...core.event_bus import get_event_bus, Event
from ...core.workflow_engine import get_workflow_engine
from ...utils.approval_system import get_approval_system
from ...utils.logging_config import business_logger

logger = logging.getLogger(__name__)


class PaymentReceivedEvent(Event):
    """Event fired when payment is received."""
    payment_id: str
    invoice_id: str
    amount: float
    payment_method: str
    source: str = "payment_service"


class PaymentReconciledEvent(Event):
    """Event fired when payment is reconciled."""
    payment_id: str
    invoice_id: str
    reconciled_by: str
    source: str = "payment_service"


class PaymentService(DomainService):
    """Service for managing payments and reconciliation."""

    def __init__(self, odoo_client=None, bank_service=None, approval_system=None):
        """Initialize payment service.

        Args:
            odoo_client: Odoo ERP client
            bank_service: Bank service client
            approval_system: Approval system
        """
        super().__init__("payment_service")
        self.odoo_client = odoo_client
        self.bank_service = bank_service
        self.approval_system = approval_system
        self.event_bus = get_event_bus()
        self.workflow_engine = get_workflow_engine()

        # Matching configuration
        self.matching_thresholds = {
            "exact_match": 0.95,
            "reference_match": 0.85,
            "amount_match": 0.70,
            "client_match": 0.60
        }

    async def initialize(self) -> None:
        """Initialize the service."""
        logger.info("Payment service initialized")

    async def shutdown(self) -> None:
        """Shutdown the service."""
        logger.info("Payment service shutdown")

    async def process_bank_transactions(self) -> List[Payment]:
        """Process bank transactions and match to invoices.

        Returns:
            List of created payments
        """
        try:
            # Get bank transactions
            transactions = await self._get_bank_transactions()
            payments = []

            for transaction in transactions:
                # Only process credit transactions (money in)
                if not transaction.is_credit:
                    continue

                # Match to invoices
                match_result = await self._match_transaction_to_invoice(transaction)

                if match_result:
                    # Create payment
                    payment = await self._create_payment_from_transaction(
                        transaction, match_result
                    )
                    payments.append(payment)

                    # Log business event
                    business_logger.log_payment_processed(
                        payment.id,
                        payment.invoice_id,
                        float(payment.amount.amount)
                    )

                    # Emit event
                    await self.event_bus.publish(PaymentReceivedEvent(
                        payment_id=payment.id,
                        invoice_id=payment.invoice_id or "",
                        amount=float(payment.amount.amount),
                        payment_method=payment.payment_method.value
                    ))

            logger.info(f"Processed {len(transactions)} transactions, created {len(payments)} payments")
            return payments

        except Exception as e:
            logger.error(f"Failed to process bank transactions: {e}")
            raise

    async def _get_bank_transactions(self) -> List[BankTransaction]:
        """Get bank transactions.

        Returns:
            List of bank transactions
        """
        if not self.bank_service:
            # Return mock data for testing
            return [
                BankTransaction(
                    transaction_date=date.today(),
                    amount=Money(Decimal('6600.00')),
                    description="Invoice INV-2025-001",
                    reference="TXN123456",
                    account_number="1234567890",
                    transaction_type=TransactionType.CREDIT
                )
            ]

        # Get transactions from bank service
        transactions_data = await self.bank_service.get_transactions(
            from_date=date.today() - timedelta(days=30),
            to_date=date.today()
        )

        transactions = []
        for tx_data in transactions_data:
            transaction = BankTransaction(
                transaction_date=date.fromisoformat(tx_data["date"]),
                amount=Money(Decimal(str(tx_data["amount"]))),
                description=tx_data.get("description", ""),
                reference=tx_data.get("reference", ""),
                account_number=tx_data.get("account_number", ""),
                transaction_type=TransactionType(tx_data.get("type", "credit"))
            )
            transactions.append(transaction)

        return transactions

    async def _match_transaction_to_invoice(self, transaction: BankTransaction) -> Optional[PaymentMatch]:
        """Match bank transaction to invoice.

        Args:
            transaction: Bank transaction

        Returns:
            Payment match result or None
        """
        # Get open invoices
        open_invoices = await self._get_open_invoices()
        if not open_invoices:
            return None

        best_match = None
        best_score = 0.0

        for invoice in open_invoices:
            score = await self._calculate_match_score(transaction, invoice)
            if score > best_score and score >= self.matching_thresholds["client_match"]:
                best_score = score
                best_match = PaymentMatch(
                    payment_id="",  # Will be set when payment is created
                    invoice_id=invoice.id,
                    confidence_score=score,
                    match_method=self._determine_match_method(transaction, invoice, score),
                    match_details={
                        "transaction_reference": transaction.reference,
                        "transaction_amount": float(transaction.amount.amount),
                        "invoice_amount": float(invoice.total_amount.amount),
                        "invoice_number": invoice.invoice_number
                    }
                )

        return best_match

    async def _get_open_invoices(self) -> List[Invoice]:
        """Get open invoices.

        Returns:
            List of open invoices
        """
        if not self.odoo_client:
            # Return mock data for testing
            return [
                Invoice(
                    id="inv_123",
                    invoice_number="INV-2025-001",
                    client_id="client_123",
                    status=InvoiceStatus.POSTED
                )
            ]

        # Get open invoices from Odoo
        invoices_data = await self.odoo_client.get_open_invoices()

        invoices = []
        for inv_data in invoices_data:
            invoice = Invoice(
                id=inv_data["id"],
                invoice_number=inv_data["invoice_number"],
                client_id=inv_data["client_id"],
                status=InvoiceStatus.POSTED
            )
            invoices.append(invoice)

        return invoices

    async def _calculate_match_score(self, transaction: BankTransaction, invoice: Invoice) -> float:
        """Calculate match score between transaction and invoice.

        Args:
            transaction: Bank transaction
            invoice: Invoice

        Returns:
            Match score (0.0 to 1.0)
        """
        score = 0.0
        weights = {
            "reference": 0.4,
            "amount": 0.3,
            "description": 0.2,
            "date": 0.1
        }

        # Reference matching (highest weight)
        if transaction.reference and invoice.invoice_number:
            if invoice.invoice_number in transaction.reference:
                score += weights["reference"]
            elif self._fuzzy_match(invoice.invoice_number, transaction.reference):
                score += weights["reference"] * 0.7

        # Amount matching
        if transaction.amount.amount == invoice.total_amount.amount:
            score += weights["amount"]
        elif self._is_close_amount(transaction.amount, invoice.total_amount, tolerance=0.05):
            score += weights["amount"] * 0.8
        elif self._is_close_amount(transaction.amount, invoice.total_amount, tolerance=0.10):
            score += weights["amount"] * 0.5

        # Description matching
        if transaction.description and invoice.invoice_number:
            if invoice.invoice_number in transaction.description:
                score += weights["description"]
            elif self._fuzzy_match(invoice.invoice_number, transaction.description):
                score += weights["description"] * 0.7

        # Date proximity (payments should be around or after invoice date)
        days_diff = abs((transaction.transaction_date - invoice.issue_date).days)
        if days_diff <= 30:
            score += weights["date"] * (1 - days_diff / 30)
        elif days_diff <= 60:
            score += weights["date"] * 0.5 * (1 - (days_diff - 30) / 30)

        return min(score, 1.0)

    def _determine_match_method(self, transaction: BankTransaction, invoice: Invoice, score: float) -> str:
        """Determine the matching method used.

        Args:
            transaction: Bank transaction
            invoice: Invoice
            score: Match score

        Returns:
            Match method name
        """
        if score >= self.matching_thresholds["exact_match"]:
            return "exact_match"
        elif transaction.reference and invoice.invoice_number in transaction.reference:
            return "reference_match"
        elif transaction.amount.amount == invoice.total_amount.amount:
            return "amount_match"
        else:
            return "ai_match"

    def _fuzzy_match(self, pattern: str, text: str) -> bool:
        """Fuzzy match pattern in text.

        Args:
            pattern: Pattern to match
            text: Text to search in

        Returns:
            True if fuzzy match found
        """
        # Remove common separators and convert to lowercase
        pattern_clean = re.sub(r'[-_\s]', '', pattern.lower())
        text_clean = re.sub(r'[-_\s]', '', text.lower())

        # Check for partial matches
        if pattern_clean in text_clean or text_clean in pattern_clean:
            return True

        # Check for character-level similarity (simple implementation)
        if len(pattern_clean) >= 3:
            # Check if at least 80% of characters match in order
            matches = 0
            pattern_chars = list(pattern_clean)
            text_chars = list(text_clean)

            i = 0
            for char in pattern_chars:
                try:
                    idx = text_chars.index(char, i)
                    matches += 1
                    i = idx + 1
                except ValueError:
                    continue

            similarity = matches / len(pattern_chars)
            return similarity >= 0.8

        return False

    def _is_close_amount(self, amount1: Money, amount2: Money, tolerance: float = 0.05) -> bool:
        """Check if amounts are close within tolerance.

        Args:
            amount1: First amount
            amount2: Second amount
            tolerance: Tolerance (e.g., 0.05 for 5%)

        Returns:
            True if amounts are close
        """
        if amount1.currency != amount2.currency:
            return False

        difference = abs(amount1.amount - amount2.amount)
        max_amount = max(amount1.amount, amount2.amount)
        tolerance_amount = max_amount * Decimal(str(tolerance))

        return difference <= tolerance_amount

    async def _create_payment_from_transaction(
        self,
        transaction: BankTransaction,
        match_result: PaymentMatch
    ) -> Payment:
        """Create payment from bank transaction.

        Args:
            transaction: Bank transaction
            match_result: Match result

        Returns:
            Created payment
        """
        # Determine payment method
        payment_method = self._infer_payment_method(transaction)

        # Create payment
        payment = Payment(
            invoice_id=match_result.invoice_id,
            amount=transaction.amount,
            payment_date=transaction.transaction_date,
            payment_method=payment_method,
            bank_reference=transaction.reference,
            transaction_id=transaction.id,
            match_confidence=match_result.confidence_score,
            matched_invoice_amount=Money(Decimal('6600.00'))  # Would come from invoice
        )

        # Create in Odoo
        if self.odoo_client:
            odoo_data = await self._create_payment_in_odoo(payment)
            payment.odoo_payment_id = odoo_data["id"]

        # Request approval if required
        if payment.approval_required:
            approval_id = await self._request_payment_approval(payment)
            payment.approval_request_id = approval_id

        # Update match result with payment ID
        match_result.payment_id = payment.id

        # Auto-approve small payments
        if not payment.approval_required:
            payment.approve("AI Employee", "Auto-approved for amount <= $100")

        return payment

    def _infer_payment_method(self, transaction: BankTransaction) -> PaymentMethod:
        """Infer payment method from transaction.

        Args:
            transaction: Bank transaction

        Returns:
            Payment method
        """
        description = transaction.description.lower()
        reference = transaction.reference.lower()

        # Check for specific patterns
        if "paypal" in description or "paypal" in reference:
            return PaymentMethod.PAYPAL
        elif "stripe" in description or "stripe" in reference:
            return PaymentMethod.STRIPE
        elif "card" in description or "credit" in description:
            return PaymentMethod.CREDIT_CARD
        elif "check" in description or "cheque" in reference:
            return PaymentMethod.CHECK
        elif "cash" in description:
            return PaymentMethod.CASH
        elif "wire" in description or "transfer" in description:
            return PaymentMethod.WIRE

        # Default to bank transfer
        return PaymentMethod.BANK_TRANSFER

    async def _create_payment_in_odoo(self, payment: Payment) -> Dict[str, Any]:
        """Create payment in Odoo.

        Args:
            payment: Payment entity

        Returns:
            Odoo payment data
        """
        if not self.odoo_client:
            return {"id": f"local_{payment.id}"}

        # Prepare Odoo data
        odoo_data = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "amount": float(payment.amount.amount),
            "payment_date": payment.payment_date.isoformat(),
            "journal_id": 1,  # Default bank journal
            "state": "draft",
            "invoice_ids": [(4, payment.invoice_id)] if payment.invoice_id else []
        }

        # Create in Odoo
        result = await self.odoo_client.create_payment(odoo_data)
        return result

    async def _request_payment_approval(self, payment: Payment) -> Optional[str]:
        """Request approval for payment.

        Args:
            payment: Payment to approve

        Returns:
            Approval request ID
        """
        if not self.approval_system:
            return None

        # Create approval request
        approval_id = await self.approval_system.create_approval_request(
            item_type="payment",
            item_id=payment.id,
            amount=float(payment.amount.amount),
            reason=f"Payment reconciliation for ${payment.amount.amount}",
            metadata={
                "invoice_id": payment.invoice_id,
                "payment_method": payment.payment_method.value,
                "bank_reference": payment.bank_reference
            }
        )

        return approval_id

    async def reconcile_payment(self, payment_id: str) -> bool:
        """Reconcile a payment.

        Args:
            payment_id: Payment ID

        Returns:
            True if reconciled successfully
        """
        try:
            # Get payment
            payment = await self._get_payment(payment_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            # Check if can be reconciled
            if not payment.can_be_reconciled():
                logger.warning(f"Payment {payment_id} cannot be reconciled")
                return False

            # Check approval if required
            if payment.approval_request_id:
                approval_status = await self.approval_system.check_approval_status(payment.approval_request_id)
                if not approval_status or approval_status.status.value != "approved":
                    logger.warning(f"Payment {payment_id} approval not granted")
                    return False

            # Reconcile in Odoo
            if self.odoo_client and payment.odoo_payment_id:
                await self.odoo_client.reconcile_payment(payment.odoo_payment_id)

            # Update payment status
            payment.reconcile("AI Employee")

            # Log business event
            business_logger.log_approval_decision(
                "payment", payment_id, True, "AI Employee"
            )

            # Emit event
            await self.event_bus.publish(PaymentReconciledEvent(
                payment_id=payment.id,
                invoice_id=payment.invoice_id or "",
                reconciled_by="AI Employee"
            ))

            logger.info(f"Reconciled payment {payment_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to reconcile payment {payment_id}: {e}")
            raise

    async def _get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID.

        Args:
            payment_id: Payment ID

        Returns:
            Payment or None if not found
        """
        # This would typically query a repository
        # For now, return a mock payment
        return Payment(
            id=payment_id,
            amount=Money(Decimal('6600.00')),
            status=PaymentStatus.APPROVED
        )

    async def list_payments(self, filters: Optional[Dict[str, Any]] = None) -> List[Payment]:
        """List payments with optional filtering.

        Args:
            filters: Optional filters

        Returns:
            List of payments
        """
        # This would typically query a repository
        # For now, return mock data
        payments = [
            Payment(
                id="pay_123",
                invoice_id="inv_123",
                amount=Money(Decimal('6600.00')),
                status=PaymentStatus.RECONCILED
            ),
            Payment(
                id="pay_456",
                invoice_id="inv_456",
                amount=Money(Decimal('3300.00')),
                status=PaymentStatus.PENDING
            )
        ]

        # Apply filters
        if filters:
            if "invoice_id" in filters:
                payments = [p for p in payments if p.invoice_id == filters["invoice_id"]]
            if "status" in filters:
                payments = [p for p in payments if p.status == PaymentStatus(filters["status"])]

        return payments

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status information.

        Args:
            payment_id: Payment ID

        Returns:
            Status information
        """
        payment = await self._get_payment(payment_id)
        if not payment:
            return {"error": "Payment not found"}

        return {
            "id": payment.id,
            "invoice_id": payment.invoice_id,
            "amount": float(payment.amount.amount),
            "status": payment.status.value,
            "payment_method": payment.payment_method.value,
            "approval_required": payment.approval_required,
            "is_overpayment": payment.is_overpayment(),
            "is_underpayment": payment.is_underpayment(),
            "match_confidence": payment.match_confidence,
            "reconciled_at": payment.reconciled_at.isoformat() if payment.reconciled_at else None
        }

    async def create_payment_reconciliation_workflow(self, payment_data: Dict[str, Any]) -> str:
        """Create payment reconciliation workflow.

        Args:
            payment_data: Payment data

        Returns:
            Workflow ID
        """
        # Create workflow
        workflow = await self.workflow_engine.create_workflow(
            workflow_id=f"payment_workflow_{datetime.utcnow().isoformat()}",
            name="Payment Reconciliation Workflow",
            description="Reconcile payment with approval",
            initial_data=payment_data
        )

        # Add workflow steps
        from ...core.workflow_engine import WorkflowStep, ApprovalStep

        # Step 1: Create payment
        class CreatePaymentStep(WorkflowStep):
            async def execute(self, context):
                payment_service = context.get("payment_service")
                transaction_data = context.get("data")

                # Create transaction
                transaction = BankTransaction(
                    amount=Money(Decimal(str(transaction_data["amount"]))),
                    reference=transaction_data.get("reference", ""),
                    description=transaction_data.get("description", "")
                )

                # Match to invoice
                match_result = await payment_service._match_transaction_to_invoice(transaction)

                if match_result:
                    payment = await payment_service._create_payment_from_transaction(transaction, match_result)
                    context.set("payment", payment)

                    return StepResult(
                        step_id=self.step_id,
                        status=StepStatus.COMPLETED,
                        data={"payment_id": payment.id, "matched": True}
                    )
                else:
                    # Unmatched transaction
                    payment = await payment_service._create_unmatched_payment(transaction)
                    context.set("payment", payment)

                    return StepResult(
                        step_id=self.step_id,
                        status=StepStatus.COMPLETED,
                        data={"payment_id": payment.id, "matched": False}
                    )

        workflow.add_step(CreatePaymentStep("create", "Create Payment"))

        # Step 2: Check approval
        class CheckApprovalStep(WorkflowStep):
            async def execute(self, context):
                payment = context.get("payment")

                if payment.approval_required:
                    # Add approval step
                    approval_step = ApprovalStep(
                        "approval",
                        "Payment Approval",
                        "payment",
                        f"Approve payment of ${payment.amount.amount}"
                    )
                    workflow.add_step(approval_step)

                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.COMPLETED
                )

        workflow.add_step(CheckApprovalStep("check_approval", "Check Approval"))

        # Step 3: Reconcile payment
        class ReconcileStep(WorkflowStep):
            async def execute(self, context):
                payment = context.get("payment")
                payment_service = context.get("payment_service")
                success = await payment_service.reconcile_payment(payment.id)

                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.COMPLETED if success else StepStatus.FAILED,
                    data={"reconciled": success}
                )

        workflow.add_step(ReconcileStep("reconcile", "Reconcile Payment"))

        # Add payment service to context
        workflow.context.set("payment_service", self)

        # Execute workflow
        success = await self.workflow_engine.execute_workflow(workflow.id)

        if success:
            logger.info(f"Payment workflow {workflow.id} completed successfully")
        else:
            logger.error(f"Payment workflow {workflow.id} failed")

        return workflow.id

    async def _create_unmatched_payment(self, transaction: BankTransaction) -> Payment:
        """Create payment for unmatched transaction.

        Args:
            transaction: Bank transaction

        Returns:
            Created payment
        """
        payment = Payment(
            amount=transaction.amount,
            payment_date=transaction.transaction_date,
            payment_method=self._infer_payment_method(transaction),
            bank_reference=transaction.reference,
            transaction_id=transaction.id,
            match_confidence=0.0,
            notes="Unmatched transaction - requires manual review"
        )

        # Always require approval for unmatched payments
        payment.approval_required = True

        # Request approval
        if self.approval_system:
            approval_id = await self.approval_system.create_approval_request(
                item_type="payment",
                item_id=payment.id,
                amount=float(payment.amount.amount),
                reason="Unmatched transaction requires manual review",
                metadata={
                    "transaction_id": transaction.id,
                    "bank_reference": transaction.reference,
                    "description": transaction.description
                }
            )
            payment.approval_request_id = approval_id

        return payment