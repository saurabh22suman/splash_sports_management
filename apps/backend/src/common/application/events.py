from __future__ import annotations

import inspect
import json
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: UUID | None = None


Subscriber = Callable[[DomainEvent], Awaitable[None]]


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...


class InProcessEventPublisher:
    """Synchronous in-memory fan-out.

    Fallback for tests and development when Redis is unavailable.
    NOT for production use - events will be lost on restart.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[Subscriber]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], fn: Subscriber) -> None:
        self._subscribers[event_type].append(fn)

    async def publish(self, event: DomainEvent) -> None:
        for fn in list(self._subscribers[type(event)]):
            if inspect.iscoroutinefunction(fn):
                await fn(event)
            else:
                fn(event)


class OutboxEventPublisher:
    """Event publisher using the transactional outbox pattern.

    Writes events to the outbox table within the same transaction as
    domain changes. A background worker then publishes to Redis Streams.

    This is the production-ready implementation per ADR-0004.
    """

    def __init__(self, outbox_repository: OutboxRepository) -> None:
        self._outbox = outbox_repository

    async def publish(self, event: DomainEvent) -> None:
        """Write event to the outbox table.

        The event will be published to Redis Streams by the background worker.
        This must be called within the same database transaction as the domain change.
        """
        event_type = type(event).__name__
        payload = self._event_to_payload(event)

        await self._outbox.insert(
            event_type=event_type,
            payload=payload,
            tenant_id=event.tenant_id,
        )

        logger.debug(
            "Event written to outbox",
            extra={
                "event_id": str(event.event_id),
                "event_type": event_type,
                "tenant_id": str(event.tenant_id) if event.tenant_id else None,
            },
        )

    def _event_to_payload(self, event: DomainEvent) -> dict:
        """Convert a DomainEvent to a JSON-serializable payload."""
        # Get all fields from the dataclass
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
        }

        if event.tenant_id:
            payload["tenant_id"] = str(event.tenant_id)

        # Add any additional fields from the event
        for key, value in vars(event).items():
            if key not in ("event_id", "occurred_at", "tenant_id"):
                if isinstance(value, UUID):
                    payload[key] = str(value)
                elif isinstance(value, datetime):
                    payload[key] = value.isoformat()
                else:
                    payload[key] = value

        return payload


class OutboxRepository(Protocol):
    """Protocol for outbox persistence."""

    async def insert(self, event_type: str, payload: dict, tenant_id: UUID | None) -> UUID: ...
    async def mark_published(self, event_id: UUID) -> None: ...
    async def increment_attempts(self, event_id: UUID) -> None: ...
    async def fetch_unpublished(self, limit: int = 100) -> list: ...
