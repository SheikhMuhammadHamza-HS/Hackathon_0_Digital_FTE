"""
Payment domain events for AI Employee system.

Defines all events related to payment operations
and their handling logic.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ...core.event_bus import Event, EventHandler, event_handler, handles
from .models import Payment, PaymentStatus

logger = logging.getLogger(__name__)


class PaymentEventHandler(EventHandler):
    """Handler for payment-related events."""

    def __init__(self, payment_service):
        """Initialize event handler.

        Args:
            payment_service: Payment service instance
        """
        super().__init__("payment_handler")
        self.payment_service = payment_service

    async def handle(self, event: Event) -> None:
        """Handle payment event.

        Args:
            event: Event to handle
        """
        try:
            if isinstance(event, PaymentReceivedEvent):
                await self.handle_payment_received(event)
            elif isinstance(event, PaymentReconciledEvent):
                await self.handle_payment_reconciled(event)
            else:
                logger.warning(f"Unknown event type: {type(event)}")

        except Exception as e:
            logger.error(f"Error handling payment event: {e}")

    async def handle_payment_received(self, event: 'PaymentReceivedEvent'):
        """Handle payment received event.

        Args:
            event: Payment received event
        """
        logger.info(f"Handling payment received event: {event.payment_id}")

        # Update analytics
        await self._update_analytics("payment_received", {
            "payment_id": event.payment_id,
            "invoice_id": event.invoice_id,
            "amount": event.amount,
            "payment_method": event.payment_method,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Check if this completes an invoice
        if event.invoice_id:
            await self._check_invoice_completion(event)

        # Update client metrics
        await self._update_client_metrics(event)

    async def handle_payment_reconciled(self, event: 'PaymentReconciledEvent'):
        """Handle payment reconciled event.

        Args:
            event: Payment reconciled event
        """
        logger.info(f"Handling payment reconciled event: {event.payment_id}")

        # Update analytics
        await self._update_analytics("payment_reconciled", {
            "payment_id": event.payment_id,
            "invoice_id": event.invoice_id,
            "reconciled_by": event.reconciled_by,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Generate reconciliation report
        await self._generate_reconciliation_report(event)

        # Update cash flow projections
        await self._update_cash_flow_projections(event)

    async def _update_analytics(self, event_type: str, data: Dict[str, Any]):
        """Update analytics data.

        Args:
            event_type: Type of event
            data: Event data
        """
        # This would typically update an analytics service
        logger.debug(f"Updating analytics for {event_type}: {data}")

    async def _check_invoice_completion(self, event: 'PaymentReceivedEvent'):
        """Check if payment completes an invoice.

        Args:
            event: Payment received event
        """
        try:
            # Get invoice (this would typically query a repository)
            invoice = await self.payment_service._get_invoice(event.invoice_id)
            if not invoice:
                return

            # Check if payment fully covers invoice
            if event.amount >= invoice.total_amount.amount:
                logger.info(f"Payment {event.payment_id} fully covers invoice {event.invoice_id}")
                # Mark invoice as paid
                await self._mark_invoice_paid(invoice)

        except Exception as e:
            logger.error(f"Error checking invoice completion: {e}")

    async def _mark_invoice_paid(self, invoice):
        """Mark invoice as paid.

        Args:
            invoice: Invoice to mark
        """
        try:
            
            # Update local invoice status
            invoice.status = InvoiceStatus.PAID

            logger.info(f"Marked invoice {invoice.invoice_number} as paid")

        except Exception as e:
            logger.error(f"Error marking invoice as paid: {e}")

    async def _update_client_metrics(self, event: 'PaymentReceivedEvent'):
        """Update client payment metrics.

        Args:
            event: Payment received event
        """
        try:
            if not event.invoice_id:
                return

            # Get invoice to get client info
            invoice = await self.payment_service._get_invoice(event.invoice_id)
            if not invoice:
                return

            # Update client metrics
            metrics = {
                "client_id": invoice.client_id,
                "total_payments": 1,
                "total_amount": event.amount,
                "last_payment_date": datetime.now(timezone.utc).isoformat()
            }

            # This would typically update a client metrics service
            logger.debug(f"Updated client metrics for {invoice.client_id}: {metrics}")

        except Exception as e:
            logger.error(f"Error updating client metrics: {e}")

    async def _generate_reconciliation_report(self, event: 'PaymentReconciledEvent'):
        """Generate reconciliation report.

        Args:
            event: Payment reconciled event
        """
        try:
            # Get payment details
            payment = await self.payment_service._get_payment(event.payment_id)
            if not payment:
                return

            # Generate report data
            report = {
                "payment_id": payment.id,
                "invoice_id": payment.invoice_id,
                "amount": float(payment.amount.amount),
                "reconciled_by": event.reconciled_by,
                "reconciled_at": datetime.now(timezone.utc).isoformat(),
                "payment_method": payment.payment_method.value,
                "bank_reference": payment.bank_reference
            }

            # Save report
            # This would typically save to a reporting service
            logger.info(f"Generated reconciliation report: {report}")

        except Exception as e:
            logger.error(f"Error generating reconciliation report: {e}")

    async def _update_cash_flow_projections(self, event: 'PaymentReconciledEvent'):
        """Update cash flow projections.

        Args:
            event: Payment reconciled event
        """
        try:
            # Update cash flow projections
            projections = {
                "payment_id": event.payment_id,
                "amount": event.amount,
                "date": datetime.now(timezone.utc).isoformat(),
                "type": "inflow"
            }

            # This would typically update a cash flow service
            logger.debug(f"Updated cash flow projections: {projections}")

        except Exception as e:
            logger.error(f"Error updating cash flow projections: {e}")


# Register event handlers
@handles(PaymentReceivedEvent, PaymentReconciledEvent)
def create_payment_handler():
    """Factory function for payment event handler."""
    from .services import PaymentService
    return PaymentEventHandler(PaymentService())