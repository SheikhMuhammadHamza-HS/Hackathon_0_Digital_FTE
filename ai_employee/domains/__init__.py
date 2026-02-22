"""
Business domains for AI Employee system.

Each domain represents a business capability with its own models,
services, and events:
- invoicing: Invoice creation and management
- payments: Payment reconciliation
- social_media: Social media automation
- reporting: CEO briefing generation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import uuid
import json


@dataclass
class BaseEntity:
    """Base entity class for all domain entities."""

    # Identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary.

        Returns:
            Dictionary representation
        """
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEntity':
        """Create entity from dictionary.

        Args:
            data: Dictionary data

        Returns:
            Entity instance
        """
        # Convert ISO strings to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        return cls(**data)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.update_timestamp()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value.

        Args:
            key: Metadata key
            default: Default value if not found

        Returns:
            Metadata value
        """
        return self.metadata.get(key, default)


class DomainService(ABC):
    """Base class for domain services."""

    def __init__(self, name: str):
        """Initialize domain service.

        Args:
            name: Service name
        """
        self.name = name

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the service."""
        pass


class Repository(ABC):
    """Base repository pattern for data access."""

    @abstractmethod
    async def create(self, entity: BaseEntity) -> BaseEntity:
        """Create an entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity
        """
        pass

    @abstractmethod
    async def get(self, entity_id: str) -> Optional[BaseEntity]:
        """Get an entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity or None if not found
        """
        pass

    @abstractmethod
    async def update(self, entity: BaseEntity) -> BaseEntity:
        """Update an entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity.

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def list(self, filters: Optional[Dict[str, Any]] = None, limit: int = 50, offset: int = 0) -> List[BaseEntity]:
        """List entities with optional filtering.

        Args:
            filters: Optional filters
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entities
        """
        pass


class ValueObject(ABC):
    """Base class for value objects."""

    def __eq__(self, other) -> bool:
        """Check equality based on values."""
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        """Generate hash based on values."""
        return hash(tuple(sorted(self.__dict__.items())))


# Domain-specific imports will be added as needed
from . import invoicing
from . import payments
from . import social_media
from . import reporting