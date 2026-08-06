# Event Idempotency

> This document covers event deduplication to ensure exactly-once processing despite retries.

## Overview

Events may be delivered multiple times due to retries. Consumer idempotency ensures processing the same event twice has no side effects.

## Event Idempotency Keys

Every event carries a unique identifier:

```python
@dataclass
class BookingCreatedEvent:
    event_id: UUID  # Unique per event
    booking_id: UUID
    tenant_id: UUID
    # ... other fields
```

The `event_id` is the idempotency key.

## Deduplication Table

```sql
CREATE TABLE processed_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    tenant_id UUID NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    result JSONB  -- Optional: store result for response caching
);

CREATE INDEX idx_processed_events_tenant
    ON processed_events(tenant_id, event_type)
    WHERE processed_at > NOW() - INTERVAL '7 days';
```

## Consumer Implementation

```python
class EventConsumer:
    """Event consumer with idempotency."""

    def __init__(self, db, redis, handler):
        self._db = db
        self._redis = redis
        self._handler = handler
        self._ttl_days = 7

    async def process_event(self, event_data: dict):
        """Process event with idempotency check."""
        event_id = event_data["event_id"]
        event_type = event_data["event_type"]
        tenant_id = event_data["tenant_id"]

        # Check if already processed
        existing = await self._check_processed(event_id)
        if existing:
            logger.info(
                "Event already processed, skipping",
                event_id=event_id,
            )
            return existing.get("result")

        # Process the event
        try:
            result = await self._handler.handle(event_data)

            # Mark as processed
            await self._mark_processed(event_id, event_type, tenant_id, result)

            return result

        except Exception as e:
            logger.error(
                "Event processing failed",
                event_id=event_id,
                error=str(e),
            )
            raise

    async def _check_processed(self, event_id: str) -> Optional[dict]:
        """Check if event was already processed."""
        # Check Redis first (faster)
        cached = await self._redis.get(f"processed:{event_id}")
        if cached:
            return json.loads(cached)

        # Check database
        result = await self._db.fetchrow(
            "SELECT result FROM processed_events WHERE event_id = $1",
            event_id,
        )

        if result:
            # Cache in Redis
            await self._redis.setex(
                f"processed:{event_id}",
                self._ttl_days * 24 * 60 * 60,
                json.dumps(result),
            )

        return result

    async def _mark_processed(
        self,
        event_id: str,
        event_type: str,
        tenant_id: str,
        result: dict,
    ) -> None:
        """Mark event as processed."""
        # Insert into database
        await self._db.execute(
            """
            INSERT INTO processed_events (event_id, event_type, tenant_id, result)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (event_id) DO NOTHING
            """,
            event_id,
            event_type,
            tenant_id,
            json.dumps(result),
        )

        # Cache in Redis
        await self._redis.setex(
            f"processed:{event_id}",
            self._ttl_days * 24 * 60 * 60,
            json.dumps(result),
        )
```

## Event ID Generation

```python
# Generate event_id at event creation
@dataclass
class BookingCreatedEvent:
    event_id: UUID = field(default_factory=uuid.uuid4)
    booking_id: UUID
    # ...

# Event bus publishes with event_id
class EventBus:
    def publish(self, event: Any) -> None:
        if not hasattr(event, 'event_id'):
            event.event_id = uuid.uuid4()

        # ... save to outbox
```

## TTL Considerations

| Event Type | TTL | Rationale |
|------------|-----|-----------|
| Bookings | 7 days | Processing window |
| Payments | 30 days | Dispute window |
| Membership | 7 days | Quick processing |
| Analytics | 1 day | Near real-time |

```python
# TTL by event type
TTL_MAP = {
    "BookingCreatedEvent": 7 * 24 * 60 * 60,
    "PaymentCapturedEvent": 30 * 24 * 60 * 60,
    "MembershipStartedEvent": 7 * 24 * 60 * 60,
    "AnalyticsEvent": 24 * 60 * 60,
}
```

## Testing Idempotency

```python
# tests/events/test_idempotency.py
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_duplicate_event_skipped(consumer):
    """Test that duplicate events are skipped."""
    event_data = {
        "event_id": "event-123",
        "event_type": "BookingCreatedEvent",
        "tenant_id": "tenant-1",
        "booking_id": "booking-1",
    }

    # Process once
    await consumer.process_event(event_data)

    # Process again (duplicate)
    result = await consumer.process_event(event_data)

    # Handler should only be called once
    assert consumer._handler.handle.call_count == 1


@pytest.mark.asyncio
async def test_different_events_processed(consumer):
    """Test that different events are processed."""
    event1 = {"event_id": "event-1", "event_type": "BookingCreatedEvent", ...}
    event2 = {"event_id": "event-2", "event_type": "BookingCreatedEvent", ...}

    await consumer.process_event(event1)
    await consumer.process_event(event2)

    # Handler should be called twice
    assert consumer._handler.handle.call_count == 2
```

## Performance Considerations

1. **Redis-first lookup** — Faster than database
2. **Write-through cache** — On process, cache immediately
3. **Batch cleanup** — Delete old records in batches

```python
# Cleanup old records (run daily)
async def cleanup_processed_events():
    """Delete processed events older than TTL."""
    await db.execute("""
        DELETE FROM processed_events
        WHERE processed_at < NOW() - INTERVAL '7 days'
    """)
```

## Related Documents

- [Event Bus](event-bus.md)
- [Event Catalog](event-catalog.md)
- [Retry & Failure](retry-failure.md)
