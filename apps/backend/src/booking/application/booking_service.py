"""BookingService — orchestrates the booking lifecycle.

The booking flow:
1. Validate inputs (window, pricing)
2. Lock the resource row
3. Check for overlapping confirmed bookings
4. Validate against resource availability rules (if any)
5. Insert the booking
6. Return the booking

This service is the only entry point for booking creation. Repositories are
private collaborators.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from booking.domain.entities import Booking, BookingStatus, CancellationReason
from booking.infrastructure.repositories import BookingRepository
from common.domain.exceptions import NotFound, Validation
from sqlalchemy.ext.asyncio import AsyncSession


class BookingService:
    def __init__(self, session: AsyncSession, bookings: BookingRepository) -> None:
        self.session = session
        self.bookings = bookings

    async def create_booking(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        resource_id: UUID,
        start_at: datetime,
        end_at: datetime,
        price_cents: int = 0,
        currency: str = "INR",
        notes: str | None = None,
    ) -> Booking:
        booking = Booking.create(
            tenant_id=tenant_id,
            customer_id=customer_id,
            resource_id=resource_id,
            start_at=start_at,
            end_at=end_at,
            price_cents=price_cents,
            currency=currency,
            notes=notes,
        )
        return await self.bookings.add_safe(booking)

    async def cancel_booking(
        self,
        *,
        tenant_id: UUID,
        booking_id: UUID,
        reason: CancellationReason = CancellationReason.CUSTOMER_REQUEST,
    ) -> Booking:
        b = await self.bookings.get_by_id(tenant_id, booking_id)
        if b is None:
            raise NotFound("Booking not found", details={"booking_id": str(booking_id)})
        b.cancel(reason=reason)
        return await self.bookings.update(b)

    async def get_booking(self, *, tenant_id: UUID, booking_id: UUID) -> Booking:
        b = await self.bookings.get_by_id(tenant_id, booking_id)
        if b is None:
            raise NotFound("Booking not found", details={"booking_id": str(booking_id)})
        return b

    async def list_customer_bookings(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        statuses: list[BookingStatus] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Booking]:
        return list(
            await self.bookings.list_for_customer(
                tenant_id, customer_id, statuses=statuses, limit=limit, offset=offset
            )
        )

    async def list_resource_bookings(
        self,
        *,
        tenant_id: UUID,
        resource_id: UUID,
        from_at: datetime,
        to_at: datetime,
        statuses: list[BookingStatus] | None = None,
    ) -> list[Booking]:
        if from_at >= to_at:
            raise Validation("from_at must be before to_at")
        return list(
            await self.bookings.list_for_resource(
                tenant_id, resource_id, from_at=from_at, to_at=to_at, statuses=statuses
            )
        )

    async def check_in(self, *, tenant_id: UUID, booking_id: UUID) -> Booking:
        b = await self.get_booking(tenant_id=tenant_id, booking_id=booking_id)
        b.check_in()
        return await self.bookings.update(b)

    async def complete(self, *, tenant_id: UUID, booking_id: UUID) -> Booking:
        b = await self.get_booking(tenant_id=tenant_id, booking_id=booking_id)
        b.complete()
        return await self.bookings.update(b)

    async def mark_no_show(self, *, tenant_id: UUID, booking_id: UUID) -> Booking:
        b = await self.get_booking(tenant_id=tenant_id, booking_id=booking_id)
        b.mark_no_show()
        return await self.bookings.update(b)
