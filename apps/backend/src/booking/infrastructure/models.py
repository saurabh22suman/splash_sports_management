"""SQLAlchemy ORM models for booking module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db import Base
from common.infrastructure.mixins import TimestampMixin


class BookingModel(Base, TimestampMixin):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_bookings_window_valid"),
        CheckConstraint("price_cents >= 0", name="ck_bookings_price_non_negative"),
        Index(
            "ix_bookings_resource_window",
            "tenant_id",
            "resource_id",
            "start_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT", name="fk_bookings_customer_id"),
        index=True,
        nullable=False,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="RESTRICT", name="fk_bookings_resource_id"),
        index=True,
        nullable=False,
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BookingTariffModel(Base, TimestampMixin):
    """Price rules for bookings by resource, day-of-week, and time-of-day."""

    __tablename__ = "booking_tariffs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "resource_id",
            "day_of_week",
            "time_start",
            name="uq_booking_tariff_resource_slot",
        ),
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_tariff_day_of_week"),
        CheckConstraint("time_start >= 0 AND time_start <= 23", name="ck_tariff_time_start"),
        CheckConstraint("time_end >= 0 AND time_end <= 23", name="ck_tariff_time_end"),
        CheckConstraint("time_start < time_end", name="ck_tariff_time_window"),
        CheckConstraint("price_cents >= 0", name="ck_tariff_price_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE", name="fk_booking_tariffs_resource_id"),
        index=True,
        nullable=False,
    )
    # day_of_week: 0=Monday, 6=Sunday (Python weekday convention)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # time_start/end: hour of day (0-23), e.g., 6 = 6:00 AM - 7:00 AM
    time_start: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    time_end: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
