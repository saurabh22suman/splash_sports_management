from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from common.application.events import DomainEvent, InProcessEventPublisher


@dataclass(frozen=True)
class TestEvent(DomainEvent):
    payload: str = ""


async def test_publish_calls_subscribers():
    bus = InProcessEventPublisher()
    received: list[TestEvent] = []

    async def handler(event: TestEvent) -> None:
        received.append(event)

    bus.subscribe(TestEvent, handler)
    event = TestEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(UTC),
        tenant_id=uuid4(),
        payload="hello",
    )
    await bus.publish(event)
    assert len(received) == 1
    assert received[0].payload == "hello"


async def test_publish_without_subscribers_is_noop():
    bus = InProcessEventPublisher()
    await bus.publish(TestEvent(event_id=uuid4(), occurred_at=datetime.now(UTC), tenant_id=uuid4()))


async def test_multiple_subscribers_all_called():
    bus = InProcessEventPublisher()
    received_a: list[TestEvent] = []
    received_b: list[TestEvent] = []
    bus.subscribe(TestEvent, lambda e: received_a.append(e))  # noqa: PLW0108
    bus.subscribe(TestEvent, lambda e: received_b.append(e))  # noqa: PLW0108
    event = TestEvent(event_id=uuid4(), occurred_at=datetime.now(UTC), tenant_id=uuid4())
    await bus.publish(event)
    assert len(received_a) == 1
    assert len(received_b) == 1
