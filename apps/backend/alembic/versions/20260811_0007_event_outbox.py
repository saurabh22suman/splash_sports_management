"""Create event_outbox table

Revision ID: 0007_event_outbox
Revises: 0006_booking_tariffs
Create Date: 2026-08-11 00:00:00

F-11 fix: Transactional outbox pattern for reliable event delivery.
Events are written to this table atomically with domain changes,
then published to Redis Streams by a background worker.

The outbox ensures:
- Events survive process restarts
- Events are delivered at-least-once
- Events can be replayed on consumer failure
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_event_outbox"
down_revision: Union[str, None] = "0006_booking_tariffs"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_outbox",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("event_type", sa.String(255), nullable=False, index=True),
        sa.Column("payload", sa.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
    )
    # Index for fetching unpublished events efficiently
    op.create_index("ix_event_outbox_unpublished", "event_outbox", ["published_at", "created_at"], unique=False, postgresql_where=sa.text("published_at IS NULL"))


def downgrade() -> None:
    op.drop_index("ix_event_outbox_unpublished", table_name="event_outbox")
    op.drop_table("event_outbox")
