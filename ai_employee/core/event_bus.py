"""
Event bus implementation for AI Employee system.

Provides publish-subscribe pattern for loose coupling between components.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Callable, Type, TypeVar, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import inspect

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='Event')


class EventPriority(Enum):
    """Event processing priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """Base event class."""
    event_id: str = field(default_factory=lambda: f"{datetime.now(timezone.utc).isoformat()}-{id(object())}")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = field(default_factory="")
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.__class__.__name__,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'priority': self.priority.value,
            'metadata': self.metadata
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id={self.event_id}, source={self.source})"


@dataclass
class InvoiceCreatedEvent(Event):
    """Event fired when an invoice is created."""
    invoice_id: str = field(default_factory="")
    client_id: str = field(default_factory="")
    amount: float = field(default_factory=0.0)
    due_date: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PaymentReceivedEvent(Event):
    """Event fired when a payment is received."""
    payment_id: str = field(default_factory="")
    invoice_id: str = field(default_factory="")
    amount: float = field(default_factory=0.0)
    payment_method: str = field(default_factory="")


@dataclass
class ApprovalRequiredEvent(Event):
    """Event fired when human approval is required."""
    item_type: str = field(default_factory="")
    item_id: str = field(default_factory="")
    amount: Optional[float] = field(default_factory=lambda: None)
    approval_reason: str = field(default_factory="")


@dataclass
class ApprovalDecisionEvent(Event):
    """Event fired when approval decision is made."""
    item_type: str = field(default_factory="")
    item_id: str = field(default_factory="")
    approved: bool = field(default_factory=False)
    approved_by: str = field(default_factory="")
    notes: Optional[str] = field(default_factory=lambda: None)


@dataclass
class SocialMediaPostScheduledEvent(Event):
    """Event fired when a social media post is scheduled."""
    post_id: str = field(default_factory="")
    platform: str = field(default_factory="")
    scheduled_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SocialMediaPostPublishedEvent(Event):
    """Event fired when a social media post is published."""
    post_id: str = field(default_factory="")
    platform: str = field(default_factory="")
    published_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BrandMentionEvent(Event):
    """Event fired when brand is mentioned on social media."""
    mention_id: str = field(default_factory="")
    platform: str = field(default_factory="")
    content: str = field(default_factory="")
    sentiment: str = field(default_factory="")
    mentioned_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthStatusChangedEvent(Event):
    """Event fired when system health status changes."""
    component: str = field(default_factory="")
    old_status: str = field(default_factory="")
    new_status: str = field(default_factory="")
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ErrorEvent(Event):
    """Event fired when an error occurs."""
    error_type: str = field(default_factory="")
    error_message: str = field(default_factory="")
    component: str = field(default_factory="")
    severity: str = field(default_factory="ERROR")


@dataclass
class CircuitBreakerEvent(Event):
    """Event fired when circuit breaker state changes."""
    circuit_name: str = field(default_factory="")
    old_state: str = field(default_factory="")
    new_state: str = field(default_factory="")
    failure_count: int = field(default_factory=0)


class EventBus:
    """Event bus for publish-subscribe pattern."""

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False
        self._statistics = {
            'events_published': 0,
            'events_processed': 0,
            'active_subscriptions': 0,
            'errors': 0
        }

    async def start_background_processing(self):
        """Start background event processing."""
        if self._running:
            logger.warning("Event bus is already running")
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("Event bus background processing started")

    async def stop_background_processing(self):
        """Stop background event processing."""
        if not self._running:
            return

        self._running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus background processing stopped")

    async def publish(self, event: Event) -> None:
        """Publish an event to the bus.

        Args:
            event: Event to publish
        """
        try:
            await self._event_queue.put(event)
            self._statistics['events_published'] += 1
            logger.debug(f"Published event: {event}")

        except Exception as e:
            self._statistics['errors'] += 1
            logger.error(f"Error publishing event {event}: {e}")

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of event to subscribe to
            handler: Handler function to call
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)
        self._statistics['active_subscriptions'] = len(self._subscribers)
        logger.debug(f"Subscribed {handler} to {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from events.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
                self._statistics['active_subscriptions'] = len(self._subscribers)
                logger.debug(f"Unsubscribed {handler} from {event_type}")
            except ValueError:
                logger.warning(f"Handler {handler} not subscribed to {event_type}")

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event(event)
                self._statistics['events_processed'] += 1

            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except Exception as e:
                self._statistics['errors'] += 1
                logger.error(f"Error processing event: {e}")

    async def _handle_event(self, event: Event) -> None:
        """Handle a single event.

        Args:
            event: Event to handle
        """
        event_type = event.__class__.__name__
        handlers = self._subscribers.get(event_type, [])

        # Also check for wildcard subscribers
        wildcard_handlers = self._subscribers.get('*', [])
        handlers.extend(wildcard_handlers)

        if not handlers:
            logger.debug(f"No handlers for event type: {event_type}")
            return

        # Call all handlers
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self._statistics['errors'] += 1
                logger.error(f"Error in event handler {handler}: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics.

        Returns:
            Statistics dictionary
        """
        return self._statistics.copy()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance.

    Returns:
        Event bus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def start_event_bus():
    """Start the global event bus."""
    event_bus = get_event_bus()
    await event_bus.start_background_processing()
    return event_bus