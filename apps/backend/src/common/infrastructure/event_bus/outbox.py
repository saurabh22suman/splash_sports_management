"""Transactional outbox repository.

Provides atomic persistence of domain events alongside domain changes.
The background worker reads from this table to publish to Redis Streams.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class OutboxEvent:
    """An event stored in the outbox table."""

    id: UUID
    tenant_id: UUID | None
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
    published_at: datetime | None
    attempts: int


# Define the outbox table using SQLAlchemy Table construct
# Using JSON type that works with PostgreSQL (supports JSONB)
_outbox_table = sa.table(
    "event_outbox",
    sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
    sa.Column("tenant_id", sa.UUID(as_uuid=True), index=True),
    sa.Column("event_type", sa.String(255), index=True),
    sa.Column("payload", sa.JSON),  # PostgreSQL will use JSONB automatically
    sa.Column("created_at", sa.DateTime(timezone=True)),
    sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("attempts", sa.Integer),
)


class OutboxRepository(Protocol):
    """Protocol for outbox persistence."""

    async def insert(self, event_type: str, payload: dict[str, Any], tenant_id: UUID | None) -> UUID: ...
    async def mark_published(self, event_id: UUID) -> None: ...
    async def increment_attempts(self, event_id: UUID) -> None: ...
    async def fetch_unpublished(self, limit: int = 100) -> list[OutboxEvent]: ...


class SQLAlchemyOutboxRepository:
    """SQLAlchemy implementation of OutboxRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, event_type: str, payload: dict[str, Any], tenant_id: UUID | None) -> UUID:
        """Insert a new event into the outbox.

        This should be called within the same transaction as the domain change
        to ensure atomicity (the outbox pattern).
        """
        event_id = uuid.uuid4()
        stmt = insert(_outbox_table).values(
            id=event_id,
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(timezone.utc),
            published_at=None,
            attempts=0,
        )
        await self._session.execute(stmt)
        return event_id

    async def mark_published(self, event_id: UUID) -> None:
        """Mark an event as published."""
        stmt = (
            update(_outbox_table)
            .where(_outbox_table.c.id == event_id)
            .values(published_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    async def increment_attempts(self, event_id: UUID) -> None:
        """Increment the attempt counter for a failed publish."""
        stmt = (
            update(_outbox_table)
            .where(_outbox_table.c.id == event_id)
            .values(attempts=_outbox_table.c.attempts + 1)
        )
        await self._session.execute(stmt)

    async def fetch_unpublished(self, limit: int = 100) -> list[OutboxEvent]:
        """Fetch events that haven't been published yet."""
        stmt = (
            select(
                _outbox_table.c.id,
                _outbox_table.c.tenant_id,
                _outbox_table.c.event_type,
                _outbox_table.c.payload,
                _outbox_table.c.created_at,
                _outbox_table.c.published_at,
                _outbox_table.c.attempts,
            )
            .where(_outbox_table.c.published_at.is_(None))
            .order_by(_outbox_table.c.created_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        return [
            OutboxEvent(
                id=row.id,
                tenant_id=row.tenant_id,
                event_type=row.event_type,
                payload=row.payload,
                created_at=row.created_at,
                published_at=row.published_at,
                attempts=row.attempts,
            )
            for row in rows
        ]
