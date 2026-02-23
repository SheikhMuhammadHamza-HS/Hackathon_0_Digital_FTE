"""
Payment domain models for AI Employee system.

Defines payment entities, transactions, and related data structures
with proper validation and business logic.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from decimal import Decimal
import uuid

from .. import BaseEntity, ValueObject


class PaymentStatus(Enum):
    """Payment status values."""
    PENDING = "pending"
    APPROVED = "approved"
    RECONCILED = "reconciled"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(Enum):
    """Payment method types."""
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    CHECK = "check"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    WIRE = "wire"
    OTHER = "other"


class TransactionType(Enum):
    """Bank transaction types."""
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    FEE = "fee"
    INTEREST = "interest"


@dataclass
class Money(ValueObject):
    """Money value object."""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        """Validate money value."""
        if self.currency != "USD":
            raise ValueError("Only USD currency is currently supported")

    def add(self, other: 'Money') -> 'Money':
        """Add money values."""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: 'Money') -> 'Money':
        """Subtract money values."""
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, multiplier: Decimal) -> 'Money':
        """Multiply money value."""
        return Money(self.amount * multiplier, self.currency)

    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == Decimal('0')

    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > Decimal('0')

    def is_negative(self) -> bool:
        """Check if amount is negative."""
        return self.amount < Decimal('0')

    def __str__(self) -> str:
        """String representation."""
        return f"${self.amount:,.2f}"

    def __lt__(self, other: 'Money') -> bool:
        """Less than comparison."""
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount < other.amount

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency


@dataclass
class BankTransaction:
    """Bank transaction entity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transaction_date: date = field(default_factory=date.today)
    amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    description: str = ""
    reference: str = ""
    account_number: str = ""
    account_type: str = ""
    transaction_type: TransactionType = TransactionType.CREDIT
    balance: Optional[Money] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate transaction."""
        if not self.description and not self.reference:
            raise ValueError("Either description or reference is required")
        if not self.account_number:
            raise ValueError("Account number is required")

    @property
    def is_credit(self) -> bool:
        """Check if transaction is a credit."""
        return self.transaction_type in [TransactionType.CREDIT, TransactionType.TRANSFER]

    @property
    def is_debit(self) -> bool:
        """Check if transaction is a debit."""
        return self.transaction_type == TransactionType.DEBIT

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'transaction_date': self.transaction_date.isoformat(),
            'amount': {
                'amount': float(self.amount.amount),
                'currency': self.amount.currency
            },
            'description': self.description,
            'reference': self.reference,
            'account_number': self.account_number,
            'account_type': self.account_type,
            'transaction_type': self.transaction_type.value,
            'balance': {
                'amount': float(self.balance.amount) if self.balance else 0,
                'currency': self.balance.currency if self.balance else 'USD'
            } if self.balance else None,
            'metadata': self.metadata,
            'is_credit': self.is_credit,
            'is_debit': self.is_debit
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BankTransaction':
        """Create from dictionary."""
        amount = Money(Decimal(str(data['amount']['amount'])), data['amount']['currency'])

        balance = None
        if data.get('balance'):
            balance = Money(
                Decimal(str(data['balance']['amount'])),
                data['balance']['currency']
            )

        return cls(
            id=data.get('id', str(uuid.uuid4())),
            transaction_date=date.fromisoformat(data['transaction_date']),
            amount=amount,
            description=data.get('description', ''),
            reference=data.get('reference', ''),
            account_number=data['account_number'],
            account_type=data.get('account_type', ''),
            transaction_type=TransactionType(data['transaction_type']),
            balance=balance,
            metadata=data.get('metadata', {})
        )


@dataclass
class Payment(BaseEntity):
    """Payment entity."""
    invoice_id: Optional[str] = None
    amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    payment_date: date = field(default_factory=date.today)
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    status: PaymentStatus = PaymentStatus.PENDING
    bank_reference: str = ""
    transaction_id: Optional[str] = None
    client_reference: str = ""
    notes: str = ""
    approval_required: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    reconciled_at: Optional[datetime] = None
    reconciled_by: Optional[str] = None

    # External references
    odoo_payment_id: Optional[str] = None
    approval_request_id: Optional[str] = None
    bank_transaction_id: Optional[str] = None

    # Matching information
    match_confidence: float = 0.0
    matched_invoice_amount: Optional[Money] = None
    overpayment_amount: Optional[Money] = None
    underpayment_amount: Optional[Money] = None

    def __post_init__(self):
        """Validate payment."""
        if self.amount.is_zero():
            raise ValueError("Payment amount cannot be zero")
        if self.amount.is_negative():
            raise ValueError("Payment amount cannot be negative")
        if not self.payment_date:
            raise ValueError("Payment date is required")

        # Determine if approval is required (> $100)
        self.approval_required = self.amount.amount > Decimal('100')

        # Calculate payment differences if invoice is matched
        if self.invoice_id and self.matched_invoice_amount:
            if self.amount > self.matched_invoice_amount:
                self.overpayment_amount = self.amount.subtract(self.matched_invoice_amount)
            elif self.amount < self.matched_invoice_amount:
                self.underpayment_amount = self.matched_invoice_amount.subtract(self.amount)

    def approve(self, approved_by: str, notes: str = "") -> None:
        """Approve the payment.

        Args:
            approved_by: Who approved the payment
            notes: Approval notes
        """
        if self.status != PaymentStatus.PENDING:
            raise ValueError(f"Cannot approve payment in status {self.status}")

        self.status = PaymentStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = datetime.now(timezone.utc)
        if notes:
            self.notes = f"{self.notes}\n\nApproved by {approved_by}: {notes}".strip()

        self.update_timestamp()

    def reject(self, rejected_by: str, reason: str) -> None:
        """Reject the payment.

        Args:
            rejected_by: Who rejected the payment
            reason: Rejection reason
        """
        if self.status != PaymentStatus.PENDING:
            raise ValueError(f"Cannot reject payment in status {self.status}")

        self.status = PaymentStatus.CANCELLED
        self.notes = f"{self.notes}\n\nRejected by {rejected_by}: {reason}".strip()

        self.update_timestamp()

    def reconcile(self, reconciled_by: str) -> None:
        """Reconcile the payment.

        Args:
            reconciled_by: Who reconciled the payment
        """
        if self.status != PaymentStatus.APPROVED:
            raise ValueError(f"Cannot reconcile payment in status {self.status}")

        self.status = PaymentStatus.RECONCILED
        self.reconciled_at = datetime.now(timezone.utc)
        self.reconciled_by = reconciled_by

        self.update_timestamp()

    def can_be_approved(self) -> bool:
        """Check if payment can be approved.

        Returns:
            True if payment can be approved
        """
        return self.status == PaymentStatus.PENDING

    def can_be_reconciled(self) -> bool:
        """Check if payment can be reconciled.

        Returns:
            True if payment can be reconciled
        """
        return self.status == PaymentStatus.APPROVED

    def is_overpayment(self) -> bool:
        """Check if payment is an overpayment.

        Returns:
            True if overpayment
        """
        return self.overpayment_amount is not None and not self.overpayment_amount.is_zero()

    def is_underpayment(self) -> bool:
        """Check if payment is an underpayment.

        Returns:
            True if underpayment
        """
        return self.underpayment_amount is not None and not self.underpayment_amount.is_zero()

    def get_payment_difference(self) -> Optional[Money]:
        """Get the difference between payment and matched invoice.

        Returns:
            Payment difference (positive for overpayment, negative for underpayment)
        """
        if not self.matched_invoice_amount:
            return None

        return self.amount.subtract(self.matched_invoice_amount)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **super().to_dict(),
            'invoice_id': self.invoice_id,
            'amount': {
                'amount': float(self.amount.amount),
                'currency': self.amount.currency
            },
            'payment_date': self.payment_date.isoformat(),
            'payment_method': self.payment_method.value,
            'status': self.status.value,
            'bank_reference': self.bank_reference,
            'transaction_id': self.transaction_id,
            'client_reference': self.client_reference,
            'notes': self.notes,
            'approval_required': self.approval_required,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'reconciled_at': self.reconciled_at.isoformat() if self.reconciled_at else None,
            'reconciled_by': self.reconciled_by,
            'odoo_payment_id': self.odoo_payment_id,
            'approval_request_id': self.approval_request_id,
            'bank_transaction_id': self.bank_transaction_id,
            'match_confidence': self.match_confidence,
            'matched_invoice_amount': {
                'amount': float(self.matched_invoice_amount.amount),
                'currency': self.matched_invoice_amount.currency
            } if self.matched_invoice_amount else None,
            'overpayment_amount': {
                'amount': float(self.overpayment_amount.amount),
                'currency': self.overpayment_amount.currency
            } if self.overpayment_amount else None,
            'underpayment_amount': {
                'amount': float(self.underpayment_amount.amount),
                'currency': self.underpayment_amount.currency
            } if self.underpayment_amount else None,
            'is_overpayment': self.is_overpayment(),
            'is_underpayment': self.is_underpayment(),
            'payment_difference': {
                'amount': float(self.get_payment_difference().amount),
                'currency': self.get_payment_difference().currency
            } if self.get_payment_difference() else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Payment':
        """Create from dictionary."""
        amount = Money(Decimal(str(data['amount']['amount'])), data['amount']['currency'])

        matched_invoice_amount = None
        if data.get('matched_invoice_amount'):
            matched_invoice_amount = Money(
                Decimal(str(data['matched_invoice_amount']['amount'])),
                data['matched_invoice_amount']['currency']
            )

        overpayment_amount = None
        if data.get('overpayment_amount'):
            overpayment_amount = Money(
                Decimal(str(data['overpayment_amount']['amount'])),
                data['overpayment_amount']['currency']
            )

        underpayment_amount = None
        if data.get('underpayment_amount'):
            underpayment_amount = Money(
                Decimal(str(data['underpayment_amount']['amount'])),
                data['underpayment_amount']['currency']
            )

        return cls(
            id=data['id'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {}),
            invoice_id=data.get('invoice_id'),
            amount=amount,
            payment_date=date.fromisoformat(data['payment_date']),
            payment_method=PaymentMethod(data['payment_method']),
            status=PaymentStatus(data['status']),
            bank_reference=data.get('bank_reference', ''),
            transaction_id=data.get('transaction_id'),
            client_reference=data.get('client_reference', ''),
            notes=data.get('notes', ''),
            approval_required=data.get('approval_required', True),
            approved_by=data.get('approved_by'),
            approved_at=datetime.fromisoformat(data['approved_at']) if data.get('approved_at') else None,
            reconciled_at=datetime.fromisoformat(data['reconciled_at']) if data.get('reconciled_at') else None,
            reconciled_by=data.get('reconciled_by'),
            odoo_payment_id=data.get('odoo_payment_id'),
            approval_request_id=data.get('approval_request_id'),
            bank_transaction_id=data.get('bank_transaction_id'),
            match_confidence=data.get('match_confidence', 0.0),
            matched_invoice_amount=matched_invoice_amount,
            overpayment_amount=overpayment_amount,
            underpayment_amount=underpayment_amount
        )


        return cls(
            id=data['id'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {}),
            payment_id=data['payment_id'],
            invoice_id=data['invoice_id'],
            confidence_score=data['confidence_score'],
            match_method=data.get('match_method', 'reference'),
            match_details=data.get('match_details', {}),
            verified=data.get('verified', False),
            verified_by=data.get('verified_by'),
            verified_at=datetime.fromisoformat(data['verified_at']) if data.get('verified_at') else None
        )