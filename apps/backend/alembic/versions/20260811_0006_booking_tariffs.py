"""Create booking_tariffs table

Revision ID: 0006_booking_tariffs
Revises: 0005_enable_rls_all_tables
Create Date: 2026-08-11 00:00:00

F-05 fix: Server computes price from BookingTariff table instead of
accepting client-controlled price_cents.

This table stores price rules for bookings by:
- resource_id: which resource (court, slot, etc.)
- day_of_week: 0=Monday, 6=Sunday
- time_start/time_end: hour of day (e.g., 6 = 6:00-7:00 AM)
- price_cents: price in smallest currency unit
- currency: ISO 4217 code (e.g., INR, USD)

Unique constraint ensures one price per resource per time slot.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_booking_tariffs"
down_revision: Union[str, None] = "0005_enable_rls_all_tables"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking_tariffs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("resource_id", sa.UUID(as_uuid=True), sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("day_of_week", sa.SmallInteger, nullable=False),
        sa.Column("time_start", sa.SmallInteger, nullable=False),
        sa.Column("time_end", sa.SmallInteger, nullable=False),
        sa.Column("price_cents", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "resource_id", "day_of_week", "time_start", name="uq_booking_tariff_resource_slot"),
        sa.CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_tariff_day_of_week"),
        sa.CheckConstraint("time_start >= 0 AND time_start <= 23", name="ck_tariff_time_start"),
        sa.CheckConstraint("time_end >= 0 AND time_end <= 23", name="ck_tariff_time_end"),
        sa.CheckConstraint("time_start < time_end", name="ck_tariff_time_window"),
        sa.CheckConstraint("price_cents >= 0", name="ck_tariff_price_non_negative"),
    )

    # Enable RLS on booking_tariffs
    op.execute("ALTER TABLE booking_tariffs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON booking_tariffs
        USING (tenant_id::text = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON booking_tariffs")
    op.execute("ALTER TABLE booking_tariffs DISABLE ROW LEVEL SECURITY")
    op.drop_table("booking_tariffs")
