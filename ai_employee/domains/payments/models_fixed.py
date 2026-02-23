"""Fixed PaymentMatch class without BaseEntity inheritance."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid


@dataclass
class PaymentMatch:
    """Payment matching result."""

    # Core matching data (required fields)
    payment_id: str
    invoice_id: str

    # Matching metadata
    confidence_score: float = 0.0
    match_method: Optional[str] = None  # reference, amount, client, ai
    match_details: Dict[str, Any] = field(default_factory=dict)

    # Verification data
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    # Timestamps (from BaseEntity)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate match."""
        if not self.payment_id:
            raise ValueError("Payment ID is required")
        if not self.invoice_id:
            raise ValueError("Invoice ID is required")
        if not 0 <= self.confidence_score <= 1:
            raise ValueError("Confidence score must be between 0 and 1")
        if self.match_method is None:
            self.match_method = "reference"

    def verify(self, verified_by: str) -> None:
        """Verify the match."""
        self.verified = True
        self.verified_by = verified_by
        self.verified_at = datetime.now(timezone.utc)

    def get_confidence_level(self) -> str:
        """Get confidence level description."""
        if self.confidence_score >= 0.9:
            return "Very High"
        elif self.confidence_score >= 0.7:
            return "High"
        elif self.confidence_score >= 0.5:
            return "Medium"
        else:
            return "Low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'invoice_id': self.invoice_id,
            'confidence_score': self.confidence_score,
            'match_method': str(self.match_method),
            'match_details': self.match_details,
            'verified': self.verified,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaymentMatch':
        """Create from dictionary."""
        verified_at = None
        if data.get('verified_at'):
            verified_at = datetime.fromisoformat(data['verified_at'])

        created_at = datetime.now(timezone.utc)
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])

        updated_at = datetime.now(timezone.utc)
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])

        return cls(
            id=data.get('id', str(uuid.uuid4())),
            payment_id=data['payment_id'],
            invoice_id=data['invoice_id'],
            confidence_score=data.get('confidence_score', 0.0),
            match_method=data.get('match_method', 'reference'),
            match_details=data.get('match_details', {}),
            verified=data.get('verified', False),
            verified_by=data.get('verified_by'),
            verified_at=verified_at,
            created_at=created_at,
            updated_at=updated_at
        )
