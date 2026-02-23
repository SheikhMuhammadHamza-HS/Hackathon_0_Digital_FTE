"""Fixes the PaymentMatch dataclass issue by removing BaseEntity inheritance."""

import re

# Read the original file
with open('models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the PaymentMatch class
# This pattern matches from @dataclass before PaymentMatch to the end of the from_dict method
pattern = r'(@dataclass\s*\nclass PaymentMatch\(BaseEntity\):.*?def from_dict\(cls, data.*?\n.*?\n.*?\n)'

replacement = '''@dataclass
class PaymentMatch:
    """Payment matching result."""

    payment_id: str
    invoice_id: str
    confidence_score: float = 0.0
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    match_method: Optional[str] = None  # reference, amount, client, ai
    match_details: Dict[str, Any] = field(default_factory=dict)

    # Fields from BaseEntity
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

    def verify(self, verified_by: str) -> None:
        """Verify the match."""
        self.verified = True
        self.verified_by = verified_by
        self.verified_at = datetime.now(timezone.utc)

    def is_high_confidence(self) -> bool:
        """Check if match is high confidence."""
        return self.confidence_score > 0.9

    def is_medium_confidence(self) -> bool:
        """Check if match is medium confidence."""
        return 0.7 <= self.confidence_score <= 0.9

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
    def from_dict(cls, data: Dict[str, Any]):
        """Create from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            payment_id=data['payment_id'],
            invoice_id=data['invoice_id'],
            confidence_score=data.get('confidence_score', 0.0),
            match_method=data.get('match_method', 'reference'),
            match_details=data.get('match_details', {}),
            verified=data.get('verified', False),
            verified_by=data.get('verified_by'),
            verified_at=datetime.fromisoformat(data['verified_at']) if data.get('verified_at') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(timezone.utc)
        )
'''

# Now let's write the new content
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('models.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("PaymentMatch class fixed successfully!")
