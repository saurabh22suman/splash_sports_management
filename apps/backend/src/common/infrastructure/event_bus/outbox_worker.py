"""Background worker for publishing outbox events to Redis Streams.

This worker:
1. Polls the outbox table for unpublished events
2. Publishes each event to Redis Streams
3. Marks events as published on success
4. Handles failures gracefully with retry logic

Run as: python -m common.infrastructure.event_bus.outbox_worker
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from common.infrastructure.event_bus.outbox import OutboxEvent, SQLAlchemyOutboxRepository
from common.infrastructure.event_bus.redis_streams import RedisStreamsPublisher
from common.infrastructure.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Background worker that publishes outbox events to Redis Streams."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_client: redis.Redis,
        poll_interval: float = 1.0,
        batch_size: int = 100,
        max_attempts: int = 5,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis_client
        self._publisher = RedisStreamsPublisher(redis_client)
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._max_attempts = max_attempts
        self._running = False

    async def start(self) -> None:
        """Start the background worker loop."""
        self._running = True
        logger.info("Outbox worker started")

        while self._running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.exception("Error in outbox worker", extra={"error": str(e)})

            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        """Stop the background worker."""
        self._running = False
        logger.info("Outbox worker stopped")

    async def _process_batch(self) -> None:
        """Process a batch of unpublished events."""
        async with self._session_factory() as session:
            repository = SQLAlchemyOutboxRepository(session)

            # Fetch unpublished events
            events = await repository.fetch_unpublished(limit=self._batch_size)

            if not events:
                return

            logger.debug("Processing batch", extra={"count": len(events)})

            for event in events:
                await self._process_event(event, repository)

            # Commit the session to persist the mark_published changes
            await session.commit()

    async def _process_event(self, event: OutboxEvent, repository: Any) -> None:
        """Process a single event."""
        try:
            # Check if max attempts exceeded
            if event.attempts >= self._max_attempts:
                logger.warning(
                    "Event exceeded max attempts, skipping",
                    extra={
                        "event_id": str(event.id),
                        "event_type": event.event_type,
                        "attempts": event.attempts,
                    },
                )
                return

            # Publish to Redis Streams
            await self._publisher.publish(event)

            # Mark as published
            await repository.mark_published(event.id)

            logger.debug(
                "Published event",
                extra={
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                },
            )

        except Exception as e:
            logger.exception(
                "Failed to publish event",
                extra={
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "error": str(e),
                },
            )
            # Increment attempts for retry
            await repository.increment_attempts(event.id)


@asynccontextmanager
async def create_worker(settings: Settings | None = None):
    """Create and configure an outbox worker."""
    settings = settings or get_settings()

    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=2,
        max_overflow=5,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Create Redis client
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    # Create worker
    worker = OutboxWorker(
        session_factory=session_factory,
        redis_client=redis_client,
    )

    try:
        yield worker
    finally:
        worker.stop()
        await redis_client.aclose()
        await engine.dispose()


async def drain_unpublished_events(settings: Settings | None = None) -> int:
    """Drain all unpublished events (for startup recovery).

    Returns the number of events processed.
    """
    settings = settings or get_settings()

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    worker = OutboxWorker(
        session_factory=session_factory,
        redis_client=redis_client,
        poll_interval=0,  # Don't loop
    )

    count = 0
    async with session_factory() as session:
        repository = SQLAlchemyOutboxRepository(session)
        events = await repository.fetch_unpublished(limit=1000)

        for event in events:
            await worker._process_event(event, repository)
            count += 1

        await session.commit()

    await redis_client.aclose()
    await engine.dispose()

    return count


async def main() -> None:
    """Run the outbox worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    settings = get_settings()
    logger.info("Starting outbox worker", extra={"redis_url": settings.redis_url})

    async with create_worker(settings) as worker:
        await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
