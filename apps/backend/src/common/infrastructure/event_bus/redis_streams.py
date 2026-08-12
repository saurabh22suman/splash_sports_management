"""Redis Streams publisher for domain events.

Publishes events from the outbox to Redis Streams for consumption
by downstream services and event handlers.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from redis.asyncio import Redis

from common.infrastructure.event_bus.outbox import OutboxEvent

logger = logging.getLogger(__name__)


class RedisStreamsPublisher:
    """Publishes events to Redis Streams."""

    def __init__(self, redis_client: Redis, stream_prefix: str = "events:") -> None:
        self._redis = redis_client
        self._stream_prefix = stream_prefix

    async def publish(self, event: OutboxEvent) -> None:
        """Publish an event to Redis Streams.

        The stream name is derived from the event type (e.g., "InvoiceCreated" -> "events:InvoiceCreated").
        The payload includes the event data plus metadata for consumers.
        """
        stream_name = f"{self._stream_prefix}{event.event_type}"

        # Build the message payload
        message = {
            "event_id": str(event.id),
            "event_type": event.event_type,
            "tenant_id": str(event.tenant_id) if event.tenant_id else None,
            "payload": json.dumps(event.payload),
            "created_at": event.created_at.isoformat(),
            "attempts": str(event.attempts),
        }

        # Publish to Redis Stream (XADD)
        await self._redis.xadd(stream_name, message)

        logger.debug(
            "Published event to Redis Stream",
            extra={
                "event_id": str(event.id),
                "event_type": event.event_type,
                "stream": stream_name,
            },
        )

    async def publish_batch(self, events: list[OutboxEvent]) -> None:
        """Publish multiple events to their respective streams."""
        for event in events:
            await self.publish(event)

    async def create_consumer_group(
        self, stream_name: str, group_name: str, consumer_name: str
    ) -> None:
        """Create a consumer group for the stream.

        This enables reliable consumption with offset tracking.
        """
        try:
            # XRANGE to check if stream exists
            await self._redis.xrange(stream_name, count=1)
        except redis.ResponseError:
            # Stream doesn't exist yet, create it with a dummy message
            await self._redis.xadd(stream_name, {"_": "init"})

        try:
            await self._redis.xgroup_create(stream_name, group_name, id="0", mkstream=True)
            logger.info(
                "Created consumer group", extra={"stream": stream_name, "group": group_name}
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            # Group already exists, which is fine

    async def read_from_stream(
        self, stream_name: str, group_name: str, consumer_name: str, count: int = 10
    ) -> list[tuple[str, dict[str, Any]]]:
        """Read messages from a stream using a consumer group.

        Returns a list of (message_id, message_dict) tuples.
        """
        try:
            messages = await self._redis.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_name: ">"},
                count=count,
                block=5000,
            )
            if not messages:
                return []

            results = []
            for stream, stream_messages in messages:
                for msg_id, msg_data in stream_messages:
                    results.append((msg_id, msg_data))
            return results
        except redis.ResponseError as e:
            if "NOGROUP" in str(e):
                # Create the group and retry
                await self.create_consumer_group(stream_name, group_name, consumer_name)
                return await self.read_from_stream(stream_name, group_name, consumer_name, count)
            raise

    async def ack_message(self, stream_name: str, group_name: str, message_id: str) -> None:
        """Acknowledge a processed message."""
        await self._redis.xack(stream_name, group_name, message_id)


class RedisStreamSubscriber:
    """Subscribes to events from Redis Streams."""

    def __init__(self, redis_client: Redis, stream_prefix: str = "events:") -> None:
        self._redis = redis_client
        self._stream_prefix = stream_prefix

    async def subscribe(self, event_types: list[str], group_name: str, consumer_name: str) -> None:
        """Set up consumer group for the given event types."""
        for event_type in event_types:
            stream_name = f"{self._stream_prefix}{event_type}"
            publisher = RedisStreamsPublisher(self._redis, self._stream_prefix)
            await publisher.create_consumer_group(stream_name, group_name, consumer_name)

    async def consume(
        self, event_types: list[str], group_name: str, consumer_name: str, handler: Any
    ) -> None:
        """Consume events and invoke the handler for each."""
        for event_type in event_types:
            stream_name = f"{self._stream_prefix}{event_type}"
            publisher = RedisStreamsPublisher(self._redis, self._stream_prefix)

            while True:
                messages = await publisher.read_from_stream(stream_name, group_name, consumer_name)

                for msg_id, msg_data in messages:
                    try:
                        # Parse the payload
                        payload = json.loads(msg_data["payload"])
                        await handler(event_type, payload)
                        await publisher.ack_message(stream_name, group_name, msg_id)
                    except Exception as e:
                        logger.error(
                            "Error processing message", extra={"error": str(e), "msg_id": msg_id}
                        )
