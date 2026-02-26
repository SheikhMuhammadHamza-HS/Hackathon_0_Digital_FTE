"""
Invoice domain services for AI Employee system.

Provides business logic for invoice creation, management,
and integration with external systems.
"""

import asyncio
import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal

from .. import DomainService
from .models import Invoice, InvoiceLineItem, Client, InvoiceStatus, Money, LineItemType
from ..payments.models import Payment, PaymentStatus
from ...core.event_bus import get_event_bus, Event
from ...core.workflow_engine import get_workflow_engine, Workflow, WorkflowStep
from ...utils.approval_system import get_approval_system
from ...utils.logging_config import business_logger

logger = logging.getLogger(__name__)


class InvoiceCreatedEvent(Event):
    """Event fired when invoice is created."""
    invoice_id: str
    invoice_number: str
    client_id: str
    total_amount: float
    source: str = "invoice_service"


class InvoicePostedEvent(Event):
    """Event fired when invoice is posted."""
    invoice_id: str
    invoice_number: str
    posted_by: str
    source: str = "invoice_service"


class InvoiceService(DomainService):
    """Service for managing invoices."""

    def __init__(self, odoo_client=None, email_service=None, approval_system=None):
        """Initialize invoice service.

        Args:
            odoo_client: Odoo ERP client
            email_service: Email service client
            approval_system: Approval system
        """
        super().__init__("invoice_service")
        self.odoo_client = odoo_client
        self.email_service = email_service
        self.approval_system = approval_system
        self.event_bus = get_event_bus()
        self.workflow_engine = get_workflow_engine()
        self._invoice_counter = 1000

    async def initialize(self) -> None:
        """Initialize the service."""
        logger.info("Invoice service initialized")

    async def shutdown(self) -> None:
        """Shutdown the service."""
        logger.info("Invoice service shutdown")

    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Invoice:
        """Create a new invoice.

        Args:
            invoice_data: Invoice data

        Returns:
            Created invoice
        """
        try:
            # Validate invoice data
            self._validate_invoice_data(invoice_data)

            # Create invoice entity
            invoice = self._create_invoice_entity(invoice_data)

            # Create in Odoo
            if self.odoo_client:
                odoo_data = await self._create_in_odoo(invoice)
                invoice.odoo_invoice_id = odoo_data["id"]

            # Check if approval is required
            if invoice.total_amount.amount > Decimal('100'):
                await self._request_approval(invoice)

            # Log business event
            business_logger.log_invoice_created(
                invoice.id,
                invoice.client_id,
                float(invoice.total_amount.amount)
            )

            # Emit event
            await self.event_bus.publish(InvoiceCreatedEvent(
                invoice_id=invoice.id,
                invoice_number=invoice.invoice_number,
                client_id=invoice.client_id,
                total_amount=float(invoice.total_amount.amount)
            ))

            logger.info(f"Created invoice {invoice.invoice_number} for client {invoice.client_id}")
            return invoice

        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            raise

    def _validate_invoice_data(self, data: Dict[str, Any]) -> None:
        """Validate invoice data.

        Args:
            data: Invoice data to validate

        Raises:
            ValueError: If validation fails
        """
        required_fields = ["client_id", "issue_date", "due_date", "line_items"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        if not data["line_items"]:
            raise ValueError("At least one line item is required")

        # Validate line items
        for item in data["line_items"]:
            if not all(k in item for k in ["description", "quantity", "unit_price"]):
                raise ValueError("Line item missing required fields")

            if item["quantity"] <= 0:
                raise ValueError("Line item quantity must be positive")

            if item["unit_price"] <= 0:
                raise ValueError("Line item unit price must be positive")

        # Validate dates
        issue_date = date.fromisoformat(data["issue_date"])
        due_date = date.fromisoformat(data["due_date"])
        if due_date < issue_date:
            raise ValueError("Due date cannot be before issue date")

    def _create_invoice_entity(self, data: Dict[str, Any]) -> Invoice:
        """Create invoice entity from data.

        Args:
            data: Invoice data

        Returns:
            Invoice entity
        """
        # Generate invoice number
        invoice_number = self._generate_invoice_number()

        # Create line items
        line_items = []
        for item_data in data["line_items"]:
            unit_price = Money(Decimal(str(item_data["unit_price"])))
            tax_rate = Decimal(str(item_data.get("tax_rate", "0.10")))

            line_item = InvoiceLineItem(
                description=item_data["description"],
                quantity=Decimal(str(item_data["quantity"])),
                unit_price=unit_price,
                tax_rate=tax_rate,
                item_type=item_data.get("item_type", LineItemType.SERVICE)
            )
            line_items.append(line_item)

        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            client_id=data["client_id"],
            client_name=data.get("client_name", ""),
            client_email=data.get("client_email", ""),
            issue_date=date.fromisoformat(data["issue_date"]),
            due_date=date.fromisoformat(data["due_date"]),
            line_items=line_items,
            notes=data.get("notes", ""),
            purchase_order=data.get("purchase_order"),
            terms=data.get("terms", "Net 30")
        )

        return invoice

    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number.

        Returns:
            Invoice number
        """
        self._invoice_counter += 1
        today = date.today()
        return f"INV-{today.year}-{self._invoice_counter:04d}"

    async def _create_in_odoo(self, invoice: Invoice) -> Dict[str, Any]:
        """Create invoice in Odoo.

        Args:
            invoice: Invoice entity

        Returns:
            Odoo invoice data
        """
        if not self.odoo_client:
            return {"id": f"local_{invoice.id}"}

        # Prepare Odoo data
        odoo_data = {
            "partner_id": invoice.client_id,
            "move_type": "out_invoice",
            "invoice_date": invoice.issue_date.isoformat(),
            "invoice_date_due": invoice.due_date.isoformat(),
            "invoice_line_ids": [],
            "state": "draft"
        }

        # Add line items
        for item in invoice.line_items:
            line_data = {
                "name": item.description,
                "quantity": float(item.quantity),
                "price_unit": float(item.unit_price.amount),
                "tax_ids": [],
                "account_id": 24  # Corrected for Odoo 17 (Product Sales)
            }
            odoo_data["invoice_line_ids"].append((0, 0, line_data))

        # Create in Odoo
        result = await self.odoo_client.create_invoice(odoo_data)
        return result

    async def _request_approval(self, invoice: Invoice) -> Optional[str]:
        """Request approval for invoice.

        Args:
            invoice: Invoice to approve

        Returns:
            Approval request ID
        """
        if not self.approval_system:
            return None

        # Create approval request
        approval_id = await self.approval_system.create_approval_request(
            item_type="invoice",
            item_id=invoice.id,
            amount=float(invoice.total_amount.amount),
            reason=f"Invoice {invoice.invoice_number} for {invoice.client_name}",
            metadata={
                "invoice_number": invoice.invoice_number,
                "client_id": invoice.client_id,
                "total_amount": float(invoice.total_amount.amount)
            }
        )

        invoice.approval_request_id = approval_id
        return approval_id

    async def post_invoice(self, invoice_id: str) -> bool:
        """Post an invoice to accounting system.

        Args:
            invoice_id: Invoice ID

        Returns:
            True if posted successfully
        """
        try:
            # Get invoice (this would typically come from a repository)
            invoice = await self._get_invoice(invoice_id)
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")

            # Check if already posted
            if invoice.status != InvoiceStatus.DRAFT:
                logger.warning(f"Invoice {invoice.invoice_number} is not in draft status")
                return False

            # Check approval if required
            if invoice.approval_request_id:
                approval_status = await self.approval_system.check_approval_status(invoice.approval_request_id)
                if not approval_status or approval_status.status.value != "approved":
                    logger.warning(f"Invoice {invoice.invoice_number} approval not granted")
                    return False

            # Post in Odoo
            if self.odoo_client and invoice.odoo_invoice_id:
                await self.odoo_client.post_invoice(invoice.odoo_invoice_id)

            # Update invoice status
            invoice.status = InvoiceStatus.POSTED
            invoice.sent_at = datetime.now(timezone.utc)

            # Send invoice
            await self._send_invoice(invoice)

            # Log business event
            business_logger.log_approval_decision(
                "invoice", invoice_id, True, "system"
            )

            # Emit event
            await self.event_bus.publish(InvoicePostedEvent(
                invoice_id=invoice.id,
                invoice_number=invoice.invoice_number,
                posted_by="AI Employee"
            ))

            logger.info(f"Posted invoice {invoice.invoice_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to post invoice {invoice_id}: {e}")
            raise

    async def _get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID.

        Args:
            invoice_id: Invoice ID

        Returns:
            Invoice or None if not found
        """
        # This would typically query a repository
        # For now, return a mock invoice
        return Invoice(
            id=invoice_id,
            invoice_number="INV-2025-001",
            client_id="client_123",
            status=InvoiceStatus.DRAFT
        )

    async def _send_invoice(self, invoice: Invoice) -> None:
        """Send invoice to client.

        Args:
            invoice: Invoice to send
        """
        if not self.email_service or not invoice.client_email:
            logger.warning(f"No email service or client email for invoice {invoice.invoice_number}")
            return

        # Prepare email content
        subject = f"Invoice {invoice.invoice_number}"
        body = self._generate_invoice_email_body(invoice)

        # Send email
        await self.email_service.send_invoice(
            to_email=invoice.client_email,
            subject=subject,
            body=body,
            invoice_id=invoice.id
        )

        logger.info(f"Sent invoice {invoice.invoice_number} to {invoice.client_email}")

    def _generate_invoice_email_body(self, invoice: Invoice) -> str:
        """Generate email body for invoice.

        Args:
            invoice: Invoice entity

        Returns:
            Email body
        """
        body = f"""
Dear {invoice.client_name},

Please find attached your invoice {invoice.invoice_number}.

Invoice Details:
================
Invoice Number: {invoice.invoice_number}
Issue Date: {invoice.issue_date}
Due Date: {invoice.due_date}
Total Amount: {invoice.total_amount}

"""

        if invoice.line_items:
            body += "\nLine Items:\n"
            for item in invoice.line_items:
                body += f"- {item.description}: {item.quantity} x ${item.unit_price.amount} = ${item.total.amount}\n"

        body += f"""

Payment Terms: {invoice.terms}

If you have any questions, please don't hesitate to contact us.

Best regards,
AI Employee System
        """.strip()

        return body

    async def list_invoices(self, filters: Optional[Dict[str, Any]] = None) -> List[Invoice]:
        """List invoices with optional filtering.

        Args:
            filters: Optional filters

        Returns:
            List of invoices
        """
        # This would typically query a repository
        # For now, return mock data
        invoices = [
            Invoice(
                invoice_number="INV-2025-001",
                client_id="client_123",
                status=InvoiceStatus.POSTED
            ),
            Invoice(
                invoice_number="INV-2025-002",
                client_id="client_456",
                status=InvoiceStatus.DRAFT
            )
        ]

        # Apply filters
        if filters:
            if "client_id" in filters:
                invoices = [inv for inv in invoices if inv.client_id == filters["client_id"]]
            if "status" in filters:
                invoices = [inv for inv in invoices if inv.status == InvoiceStatus(filters["status"])]

        return invoices

    async def get_invoice_status(self, invoice_id: str) -> Dict[str, Any]:
        """Get invoice status information.

        Args:
            invoice_id: Invoice ID

        Returns:
            Status information
        """
        invoice = await self._get_invoice(invoice_id)
        if not invoice:
            return {"error": "Invoice not found"}

        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status.value,
            "total_amount": float(invoice.total_amount.amount),
            "amount_paid": float(invoice.amount_paid.amount),
            "balance_due": float(invoice.balance_due.amount),
            "is_overdue": invoice.is_overdue(),
            "days_overdue": invoice.get_days_overdue(),
            "approval_status": "pending" if invoice.approval_request_id else "not_required"
        }

    async def create_invoice_workflow(self, invoice_data: Dict[str, Any]) -> str:
        """Create invoice using workflow engine.

        Args:
            invoice_data: Invoice data

        Returns:
            Workflow ID
        """
        # Create workflow
        workflow = await self.workflow_engine.create_workflow(
            workflow_id=f"invoice_workflow_{datetime.now(timezone.utc).isoformat()}",
            name="Invoice Creation Workflow",
            description="Create and post invoice with approval",
            initial_data=invoice_data
        )

        # Add workflow steps
        from ...core.workflow_engine import WorkflowStep, ApprovalStep

        # Step 1: Create invoice
        class CreateInvoiceStep(WorkflowStep):
            async def execute(self, context):
                invoice_service = context.get("invoice_service")
                invoice_data = context.get("data")
                invoice = await invoice_service.create_invoice(invoice_data)
                context.set("invoice", invoice)
                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.COMPLETED,
                    data={"invoice_id": invoice.id}
                )

        workflow.add_step(CreateInvoiceStep("create", "Create Invoice"))

        # Step 2: Request approval if needed
        class CheckApprovalStep(WorkflowStep):
            async def execute(self, context):
                invoice = context.get("invoice")
                if invoice.total_amount.amount > 100:
                    # Add approval step
                    approval_step = ApprovalStep(
                        "approval",
                        "Invoice Approval",
                        "invoice",
                        f"Approve invoice {invoice.invoice_number} for ${invoice.total_amount}"
                    )
                    workflow.add_step(approval_step)

                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.COMPLETED
                )

        workflow.add_step(CheckApprovalStep("check_approval", "Check Approval"))

        # Step 3: Post invoice
        class PostInvoiceStep(WorkflowStep):
            async def execute(self, context):
                invoice = context.get("invoice")
                invoice_service = context.get("invoice_service")
                success = await invoice_service.post_invoice(invoice.id)

                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.COMPLETED if success else StepStatus.FAILED,
                    data={"posted": success}
                )

        workflow.add_step(PostInvoiceStep("post", "Post Invoice"))

        # Add invoice service to context
        workflow.context.set("invoice_service", self)

        # Execute workflow
        success = await self.workflow_engine.execute_workflow(workflow.id)

        if success:
            logger.info(f"Invoice workflow {workflow.id} completed successfully")
        else:
            logger.error(f"Invoice workflow {workflow.id} failed")

        return workflow.id