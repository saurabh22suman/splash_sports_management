# Retry & Failure

> This document covers event retry strategies, dead letter queues, and failure handling patterns.

## Overview

Events can fail due to transient errors (network, temporary unavailability) or permanent errors (invalid data, missing dependencies). We handle both with exponential backoff and a dead letter queue.

## Retry Policy

| Attempt | Delay | Cumulative |
|---------|-------|------------|
| 1 | 1s | 1s |
| 2 | 5s | 6s |
| 3 | 30s | 36s |
| 4 | 5m | 5m 36s |
| 5 | 30m | 35m 36s |
| 6 | 2h | 2h 35m |
| 7+ | DLQ | - |

## Implementation

### Retry Configuration

```python
# src/common/retry.py
from datetime import timedelta


RETRY_DELAYS = [
    timedelta(seconds=1),
    timedelta(seconds=5),
    timedelta(seconds=30),
    timedelta(minutes=5),
    timedelta(minutes=30),
    timedelta(hours=2),
]

MAX_RETRIES = 6


def get_retry_delay(attempt: int) -> timedelta:
    """Get delay for retry attempt."""
    if attempt >= len(RETRY_DELAYS):
        return RETRY_DELAYS[-1]
    return RETRY_DELAYS[attempt]
```

### Consumer with Retry

```python
# src/events/consumer.py
import asyncio
from datetime import datetime


class EventConsumer:
    """Event consumer with retry logic."""

    def __init__(self, redis, db, handler):
        self._redis = redis
        self._db = db
        self._handler = handler

    async def process_message(self, msg_id: str, event_data: dict):
        """Process event with retry."""
        attempt = 0

        while attempt <= MAX_RETRIES:
            try:
                await self._handler.handle(event_data)

                # Success - acknowledge
                await self._redis.xack(
                    self._stream,
                    self._group,
                    msg_id
                )
                return

            except TransientError as e:
                # Transient - retry
                attempt += 1
                delay = get_retry_delay(attempt)

                logger.warning(
                    f"Event processing failed, retry {attempt}/{MAX_RETRIES}",
                    event_id=event_data.get("event_id"),
                    error=str(e),
                    retry_in=str(delay),
                )

                await asyncio.sleep(delay.total_seconds())

            except PermanentError as e:
                # Permanent - send to DLQ
                await self._send_to_dlq(msg_id, event_data, str(e))
                await self._redis.xack(self._stream, self._group, msg_id)
                return

        # Max retries exceeded - send to DLQ
        await self._send_to_dlq(msg_id, event_data, "Max retries exceeded")
        await self._redis.xack(self._stream, self._group, msg_id)
```

## Dead Letter Queue (DLQ)

### DLQ Structure

```python
# Events that fail permanently go to DLQ
# Key: splashh:events:dlq
# Fields: event_type, event_id, payload, error, failed_at, original_msg_id
```

### Sending to DLQ

```python
async def _send_to_dlq(self, msg_id: str, event_data: dict, error: str):
    """Send failed event to dead letter queue."""
    dlq_record = {
        "event_type": event_data.get("event_type"),
        "event_id": event_data.get("event_id"),
        "payload": json.dumps(event_data.get("payload")),
        "error": error,
        "failed_at": datetime.utcnow().isoformat(),
        "original_msg_id": msg_id,
    }

    await self._redis.hset(
        f"splashh:events:dlq:{event_data['tenant_id']}",
        event_data["event_id"],
        json.dumps(dlq_record)
    )

    # Set TTL - keep DLQ for 7 days
    await self._redis.expire(
        f"splashh:events:dlq:{event_data['tenant_id']}",
        7 * 24 * 60 * 60
    )
```

### Monitoring DLQ

```python
# Check DLQ size
async def get_dlq_size(self, tenant_id: str) -> int:
    """Get number of failed events."""
    return await self._redis.hlen(f"splashh:events:dlq:{tenant_id}")
```

## Poison Message Handling

Messages that consistently fail may be "poison" (malformed data, bug in handler).

```python
async def handle_poison_message(self, msg_id: str, event_data: dict):
    """Handle poison message after max retries."""
    logger.error(
        "Poison message detected",
        event_id=event_data.get("event_id"),
        event_type=event_data.get("event_type"),
    )

    # Send to DLQ
    await self._send_to_dlq(
        msg_id,
        event_data,
        "Poison message - max retries exceeded"
    )

    # Alert on-call
    await alerts.notify(
        alert_type="poison_message",
        event_type=event_data.get("event_type"),
        event_id=event_data.get("event_id"),
    )
```

## Manual Replay

For recoverable failures, allow manual replay from DLQ:

```python
class ReplayService:
    """Service to replay events from DLQ."""

    def __init__(self, redis, event_bus):
        self._redis = redis
        self._event_bus = event_bus

    async def replay_event(self, tenant_id: str, event_id: str):
        """Replay a single event from DLQ."""
        # Get from DLQ
        dlq_data = await self._redis.hget(
            f"splashh:events:dlq:{tenant_id}",
            event_id
        )

        if not dlq_data:
            raise ValueError(f"Event {event_id} not in DLQ")

        # Remove from DLQ
        await self._redis.hdel(
            f"splashh:events:dlq:{tenant_id}",
            event_id
        )

        # Re-publish to stream
        event = json.loads(dlq_data["payload"])
        await self._event_bus.publish(event)

        return {"replayed": event_id}

    async def replay_all(self, tenant_id: str):
        """Replay all events in DLQ."""
        dlq_keys = await self._redis.hkeys(
            f"splashh:events:dlq:{tenant_id}"
        )

        for event_id in dlq_keys:
            await self.replay_event(tenant_id, event_id)

        return {"replayed_count": len(dlq_keys)}
```

## Error Classification

```python
class TransientError(Exception):
    """Temporary error that may succeed on retry."""
    pass


class PermanentError(Exception):
    """Error that will never succeed."""
    pass


# Examples
async def handle_booking_created(event):
    try:
        # Try to send notification
        await notification_service.send(...)
    except ServiceUnavailableError:
        raise TransientError("Notification service unavailable")
    except InvalidRecipientError:
        raise PermanentError("Invalid email address")
```

## Monitoring

### Alerts

```yaml
# prometheus/alerts.yml
- alert: DLQSizeHigh
  expr: dlq_events > 100
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Dead letter queue has {{ $value }} events"

- alert: EventProcessingFailuresHigh
  expr: rate(event_processing_failures[5m]) > 0.1
  for: 5m
  labels:
    severity: warning
```

## Related Documents

- [Event Bus](event-bus.md)
- [Event Catalog](event-catalog.md)
- [Event Idempotency](idempotency.md)
