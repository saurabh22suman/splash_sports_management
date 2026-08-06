# ADR-0004: Event Bus with Redis Streams

> Internal event communication.

## Status
Accepted

## Context
Modules need to communicate asynchronously for:
- Decoupling (producer doesn't need consumer)
- Reliability (events survive process restarts)
- Auditability (event log is the system of record)
- Future extensibility (add consumers without modifying producers)

## Decision
We will use **Redis Streams** with the **outbox pattern**:
- Redis Streams for event transport
- Outbox table in PostgreSQL for durable event storage
- Background worker publishes outbox events to Redis
- Consumers subscribe to streams

## Consequences

### Positive
- **Simple ops** — Redis is already in our stack
- **Durable** — Outbox ensures events are not lost
- **Replayable** — Streams retain history for replay
- **Scalable** — Can add consumers without touching producers

### Negative
- **Eventual consistency** — Consumers lag behind producers
- **Complexity** — Outbox pattern adds code
- **Not Kafka** — Less features, less durability

### Neutral
- Suitable for our scale (1000s events/sec, not millions)
- Can migrate to Kafka later if needed

## Alternatives Considered

### Alternative 1: Kafka
Rejected because:
- Operational complexity (requires cluster management)
- Overkill for our current scale
- Higher cost
- Team lacks experience

### Alternative 2: RabbitMQ
Rejected because:
- More complex than Redis Streams
- Less flexible
- Similar trade-offs to Kafka

### Alternative 3: Synchronous HTTP calls
Rejected because:
- Tight coupling between modules
- Failure propagation
- No audit trail

## Implementation

```python
# Outbox pattern
class EventOutbox:
    async def save(self, event: DomainEvent):
        await self._repo.save(OutboxEvent(
            event_type=event.__class__.__name__,
            payload=event.model_dump_json(),
            created_at=datetime.utcnow(),
        ))

class EventPublisher:
    async def publish_pending(self):
        events = await self._outbox.get_unpublished(limit=100)
        for event in events:
            await self._streams.xadd(event.event_type, event.payload)
            await self._outbox.mark_published(event.id)
```

## References
- [Event Bus Architecture](../07-events/event-bus.md)
- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Redis Streams](https://redis.io/docs/data-types/streams/)
