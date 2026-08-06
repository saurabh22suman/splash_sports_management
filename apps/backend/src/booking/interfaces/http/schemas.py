"""Pydantic schemas for booking endpoints."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from booking.domain.entities import BookingStatus, CancellationReason


class BookingCreate(BaseModel):
    customer_id: UUID
    resource_id: UUID
    start_at: datetime
    end_at: datetime
    price_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=1000)


class BookingCancel(BaseModel):
    reason: CancellationReason = CancellationReason.CUSTOMER_REQUEST


class BookingOut(BaseModel):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    resource_id: UUID
    start_at: datetime
    end_at: datetime
    status: str
    price_cents: int
    currency: str
    notes: str | None
    cancellation_reason: str | None
    cancelled_at: datetime | None
    checked_in_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingListResponse(BaseModel):
    data: list[BookingOut]
