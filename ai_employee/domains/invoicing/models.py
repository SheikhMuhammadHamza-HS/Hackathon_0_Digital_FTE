"""
Invoice domain models for AI Employee system.

Defines invoice entities, line items, and related data structures
with proper validation and business logic.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from enum import Enum
from decimal import Decimal
import uuid

from .. import BaseEntity, ValueObject


class InvoiceStatus(Enum):
    """Invoice status values."""
    DRAFT = "draft"
    POSTED = "posted"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    VOID = "void"


class LineItemType(ValueObject):
    """Line item type value object."""
    SERVICE = "service"
    PRODUCT = "product"
    EXPENSE = "expense"
    TAX = "tax"
    DISCOUNT = "discount"


@dataclass
class Money(ValueObject):
    """Money value object."""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        """Validate money value."""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency is required")

    def add(self, other: 'Money') -> 'Money':
        """Add money values."""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, multiplier: Decimal) -> 'Money':
        """Multiply money value."""
        return Money(self.amount * multiplier, self.currency)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.currency} {self.amount:,.2f}"


@dataclass
class InvoiceLineItem:
    """Invoice line item."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    quantity: Decimal = Decimal('0')
    unit_price: Money = field(default_factory=lambda: Money(Decimal('0')))
    tax_rate: Decimal = Decimal('0.10')  # Default 10% tax
    item_type: str = LineItemType.SERVICE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate line item."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if not self.description:
            raise ValueError("Description is required")
        if self.tax_rate < 0 or self.tax_rate > 1:
            raise ValueError("Tax rate must be between 0 and 1")

    @property
    def subtotal(self) -> Money:
        """Calculate line item subtotal (quantity * unit_price)."""
        return self.unit_price.multiply(self.quantity)

    @property
    def tax_amount(self) -> Money:
        """Calculate tax amount (subtotal * tax_rate)."""
        return self.subtotal.multiply(self.tax_rate)

    @property
    def total(self) -> Money:
        """Calculate total amount (subtotal + tax)."""
        return self.subtotal.add(self.tax_amount)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'description': self.description,
            'quantity': float(self.quantity),
            'unit_price': {
                'amount': float(self.unit_price.amount),
                'currency': self.unit_price.currency
            },
            'tax_rate': float(self.tax_rate),
            'item_type': self.item_type,
            'subtotal': float(self.subtotal.amount),
            'tax_amount': float(self.tax_amount.amount),
            'total': float(self.total.amount),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvoiceLineItem':
        """Create from dictionary."""
        unit_price = Money(
            Decimal(str(data['unit_price']['amount'])),
            data['unit_price']['currency']
        )

        return cls(
            id=data.get('id', str(uuid.uuid4())),
            description=data['description'],
            quantity=Decimal(str(data['quantity'])),
            unit_price=unit_price,
            tax_rate=Decimal(str(data['tax_rate'])),
            item_type=data.get('item_type', LineItemType.SERVICE),
            metadata=data.get('metadata', {})
        )


@dataclass
class Invoice(BaseEntity):
    """Invoice entity."""
    invoice_number: str = ""
    client_id: str = ""
    client_name: str = ""
    client_email: str = ""
    issue_date: date = field(default_factory=date.today)
    due_date: date = field(default_factory=lambda: date.today())
    status: InvoiceStatus = InvoiceStatus.DRAFT
    line_items: List[InvoiceLineItem] = field(default_factory=list)
    notes: str = ""
    purchase_order: Optional[str] = None
    terms: str = "Net 30"
    currency: str = "USD"

    # Calculated fields
    subtotal: Money = field(default_factory=lambda: Money(Decimal('0')))
    tax_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    amount_paid: Money = field(default_factory=lambda: Money(Decimal('0')))
    balance_due: Money = field(default_factory=lambda: Money(Decimal('0')))

    skill_invoice_id: Optional[str] = None
    approval_request_id: Optional[str] = None
    sent_at: Optional[datetime] = None

    def __post_init__(self):
        """Post-initialization validation and calculations."""
        if not self.invoice_number:
            raise ValueError("Invoice number is required")
        if not self.client_id:
            raise ValueError("Client ID is required")
        if self.due_date < self.issue_date:
            raise ValueError("Due date cannot be before issue date")

        # Calculate totals
        self._calculate_totals()

    def _calculate_totals(self) -> None:
        """Calculate invoice totals."""
        # Calculate subtotal and tax
        subtotal_amount = Decimal('0')
        tax_amount = Decimal('0')

        for item in self.line_items:
            subtotal_amount += item.subtotal.amount
            tax_amount += item.tax_amount.amount

        self.subtotal = Money(subtotal_amount, self.currency)
        self.tax_amount = Money(tax_amount, self.currency)
        self.total_amount = Money(subtotal_amount + tax_amount, self.currency)

        # Calculate balance due
        self.balance_due = Money(
            self.total_amount.amount - self.amount_paid.amount,
            self.currency
        )

    def add_line_item(self, line_item: InvoiceLineItem) -> None:
        """Add a line item to the invoice.

        Args:
            line_item: Line item to add
        """
        self.line_items.append(line_item)
        self._calculate_totals()
        self.update_timestamp()

    def remove_line_item(self, line_item_id: str) -> bool:
        """Remove a line item from the invoice.

        Args:
            line_item_id: ID of line item to remove

        Returns:
            True if removed, False if not found
        """
        original_length = len(self.line_items)
        self.line_items = [item for item in self.line_items if item.id != line_item_id]

        if len(self.line_items) < original_length:
            self._calculate_totals()
            self.update_timestamp()
            return True

        return False

    def update_line_item(self, line_item_id: str, **kwargs) -> bool:
        """Update a line item.

        Args:
            line_item_id: ID of line item to update
            **kwargs: Fields to update

        Returns:
            True if updated, False if not found
        """
        for item in self.line_items:
            if item.id == line_item_id:
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                self._calculate_totals()
                self.update_timestamp()
                return True

        return False

    def apply_payment(self, amount: Money) -> None:
        """Apply payment to invoice.

        Args:
            amount: Payment amount
        """
        if amount.currency != self.currency:
            raise ValueError("Payment currency must match invoice currency")

        self.amount_paid = self.amount_paid.add(amount)
        self._calculate_totals()
        self.update_timestamp()

        # Update status based on payment
        if self.balance_due.amount <= 0:
            self.status = InvoiceStatus.PAID
        elif self.status == InvoiceStatus.POSTED:
            # Keep posted status if partially paid
            pass

    def can_be_posted(self) -> bool:
        """Check if invoice can be posted.

        Returns:
            True if invoice can be posted
        """
        return (
            self.status == InvoiceStatus.DRAFT and
            len(self.line_items) > 0 and
            self.total_amount.amount > 0
        )

    def can_be_cancelled(self) -> bool:
        """Check if invoice can be cancelled.

        Returns:
            True if invoice can be cancelled
        """
        return self.status not in [InvoiceStatus.PAID, InvoiceStatus.VOID]

    def is_overdue(self) -> bool:
        """Check if invoice is overdue.

        Returns:
            True if overdue
        """
        return (
            self.status in [InvoiceStatus.POSTED, InvoiceStatus.SENT] and
            date.today() > self.due_date and
            self.balance_due.amount > 0
        )

    def get_days_overdue(self) -> int:
        """Get days overdue.

        Returns:
            Number of days overdue, 0 if not overdue
        """
        if not self.is_overdue():
            return 0

        return (date.today() - self.due_date).days

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **super().to_dict(),
            'invoice_number': self.invoice_number,
            'client_id': self.client_id,
            'client_name': self.client_name,
            'client_email': self.client_email,
            'issue_date': self.issue_date.isoformat(),
            'due_date': self.due_date.isoformat(),
            'status': self.status.value,
            'line_items': [item.to_dict() for item in self.line_items],
            'notes': self.notes,
            'purchase_order': self.purchase_order,
            'terms': self.terms,
            'currency': self.currency,
            'subtotal': float(self.subtotal.amount),
            'tax_amount': float(self.tax_amount.amount),
            'total_amount': float(self.total_amount.amount),
            'amount_paid': float(self.amount_paid.amount),
            'balance_due': float(self.balance_due.amount),
            'skill_invoice_id': self.skill_invoice_id,
            'approval_request_id': self.approval_request_id,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'is_overdue': self.is_overdue(),
            'days_overdue': self.get_days_overdue()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Invoice':
        """Create from dictionary."""
        # Convert dates
        issue_date = date.fromisoformat(data['issue_date'])
        due_date = date.fromisoformat(data['due_date'])

        # Create line items
        line_items = [
            InvoiceLineItem.from_dict(item_data)
            for item_data in data.get('line_items', [])
        ]

        # Create money objects
        subtotal = Money(Decimal(str(data['subtotal'])), data['currency'])
        tax_amount = Money(Decimal(str(data['tax_amount'])), data['currency'])
        total_amount = Money(Decimal(str(data['total_amount'])), data['currency'])
        amount_paid = Money(Decimal(str(data['amount_paid'])), data['currency'])
        balance_due = Money(Decimal(str(data['balance_due'])), data['currency'])

        # Convert sent_at
        sent_at = None
        if data.get('sent_at'):
            sent_at = datetime.fromisoformat(data['sent_at'])

        return cls(
            id=data['id'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {}),
            invoice_number=data['invoice_number'],
            client_id=data['client_id'],
            client_name=data.get('client_name', ''),
            client_email=data.get('client_email', ''),
            issue_date=issue_date,
            due_date=due_date,
            status=InvoiceStatus(data['status']),
            line_items=line_items,
            notes=data.get('notes', ''),
            purchase_order=data.get('purchase_order'),
            terms=data.get('terms', 'Net 30'),
            currency=data['currency'],
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            amount_paid=amount_paid,
            balance_due=balance_due,
            skill_invoice_id=data.get('skill_invoice_id'),
            approval_request_id=data.get('approval_request_id'),
            sent_at=sent_at
        )


@dataclass
class Client(BaseEntity):
    """Client entity."""
    name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""
    tax_id: Optional[str] = None
    payment_terms: str = "Net 30"
    currency: str = "USD"
    is_active: bool = True
    
    def __post_init__(self):
        """Validate client data."""
        if not self.name:
            raise ValueError("Client name is required")
        if self.email and "@" not in self.email:
            raise ValueError("Invalid email format")

    @property
    def full_address(self) -> str:
        """Get full formatted address."""
        parts = [self.address]

        if self.city:
            parts.append(self.city)

        city_state = []
        if self.state:
            city_state.append(self.state)
        if self.postal_code:
            city_state.append(self.postal_code)

        if city_state:
            parts.append(", ".join(city_state))

        if self.country:
            parts.append(self.country)

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **super().to_dict(),
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'tax_id': self.tax_id,
            'payment_terms': self.payment_terms,
            'currency': self.currency,
            'is_active': self.is_active,
            'odoo_partner_id': self.odoo_partner_id,
            'full_address': self.full_address
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Client':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {}),
            name=data['name'],
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            postal_code=data.get('postal_code', ''),
            country=data.get('country', ''),
            tax_id=data.get('tax_id'),
            payment_terms=data.get('payment_terms', 'Net 30'),
            currency=data.get('currency', 'USD'),
            is_active=data.get('is_active', True)
        )