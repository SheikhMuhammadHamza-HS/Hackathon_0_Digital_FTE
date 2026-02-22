"""
Invoice domain events for AI Employee system.

Defines all events related to invoice operations
and their handling logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ...core.event_bus import Event, EventHandler, event_handler, handles
from .models import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


class InvoiceEventHandler(EventHandler):
    """Handler for invoice-related events."""

    def __init__(self, invoice_service):
        """Initialize event handler.

        Args:
            invoice_service: Invoice service instance
        """
        super().__init__("invoice_handler")
        self.invoice_service = invoice_service

    async def handle(self, event: Event) -> None:
        """Handle invoice event.

        Args:
            event: Event to handle
        """
        try:
            if isinstance(event, InvoiceCreatedEvent):
                await self.handle_invoice_created(event)
            elif isinstance(event, InvoicePostedEvent):
                await self.handle_invoice_posted(event)
            else:
                logger.warning(f"Unknown event type: {type(event)}")

        except Exception as e:
            logger.error(f"Error handling invoice event: {e}")

    async def handle_invoice_created(self, event: 'InvoiceCreatedEvent'):
        """Handle invoice created event.

        Args:
            event: Invoice created event
        """
        logger.info(f"Handling invoice created event: {event.invoice_id}")

        # Update analytics
        await self._update_analytics("invoice_created", {
            "invoice_id": event.invoice_id,
            "invoice_number": event.invoice_number,
            "client_id": event.client_id,
            "amount": event.total_amount,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Trigger any automated follow-ups
        await self._schedule_follow_ups(event)

    async def handle_invoice_posted(self, event: 'InvoicePostedEvent'):
        """Handle invoice posted event.

        Args:
            event: Invoice posted event
        """
        logger.info(f"Handling invoice posted event: {event.invoice_id}")

        # Update analytics
        await self._update_analytics("invoice_posted", {
            "invoice_id": event.invoice_id,
            "invoice_number": event.invoice_number,
            "posted_by": event.posted_by,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Schedule payment reminders
        await self._schedule_payment_reminders(event)

    async def _update_analytics(self, event_type: str, data: Dict[str, Any]):
        """Update analytics data.

        Args:
            event_type: Type of event
            data: Event data
        """
        # This would typically update an analytics service
        logger.debug(f"Updating analytics for {event_type}: {data}")

    async def _schedule_follow_ups(self, event: 'InvoiceCreatedEvent'):
        """Schedule follow-up actions.

        Args:
            event: Invoice created event
        """
        # Schedule due date reminder
        # This would typically use a scheduler service
        logger.debug(f"Scheduling follow-ups for invoice {event.invoice_id}")

    async def _schedule_payment_reminders(self, event: 'InvoicePostedEvent'):
        """Schedule payment reminders.

        Args:
            event: Invoice posted event
        """
        # Schedule reminders at due date and after
        # This would typically use a scheduler service
        logger.debug(f"Scheduling payment reminders for invoice {event.invoice_id}")


# Register event handlers
@handles(InvoiceCreatedEvent, InvoicePostedEvent)
def create_invoice_handler():
    """Factory function for invoice event handler."""
    from .services import InvoiceService
    return InvoiceEventHandler(InvoiceService())