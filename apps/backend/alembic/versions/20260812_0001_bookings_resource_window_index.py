"""add composite time-range index on bookings (F-28)

Revision ID: 20260812_0001
Revises: 20260811_0007
Create Date: 2026-08-12 00:00:00
"""
from __future__ import annotations

from alembic import op


revision = "20260812_0001"
down_revision = "20260811_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_bookings_resource_window",
        "bookings",
        ["tenant_id", "resource_id", "start_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bookings_resource_window", table_name="bookings")
