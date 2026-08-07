from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID = field(default_factory=UUID)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: UUID | None = None


Subscriber = Callable[[DomainEvent], Awaitable[None]]


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...


class InProcessEventPublisher:
    """Synchronous in-memory fan-out.

    Replace with Redis pub/sub or DB outbox when async delivery is needed.
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
