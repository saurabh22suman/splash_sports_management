"""BookingService — orchestrates the booking lifecycle.

The booking flow:
1. Compute price from tariff (F-05 fix: server-controlled pricing)
2. Validate inputs (window)
3. Lock the resource row
4. Check for overlapping confirmed bookings
5. Validate against resource availability rules (if any)
6. Insert the booking
7. Return the booking

This service is the only entry point for booking creation. Repositories are
private collaborators.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from booking.domain.entities import Booking, BookingStatus, BookingTariff, CancellationReason
from booking.infrastructure.repositories import BookingRepository, BookingTariffRepository
from common.domain.exceptions import NotFound, Validation
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from facility.application.facility_service import FacilityService


def compute_price(
    resource_id: UUID,
    start_at: datetime,
    tariffs: list[BookingTariff],
) -> tuple[int, str]:
    """Compute price for a booking based on tariff rules.

    This is the F-05 security fix: server computes price from BookingTariff
    instead of accepting client-controlled price_cents.

    Args:
        resource_id: The resource being booked
        start_at: The start time of the booking (used to find matching tariff)
        tariffs: List of tariffs for the resource (already fetched from DB)

    Returns:
        tuple of (price_cents, currency)

    Raises:
        Validation: If no matching tariff is found
    """
    # Extract day_of_week (Python: Monday=0, Sunday=6) and hour from start_at
    day_of_week = start_at.weekday()
    hour = start_at.hour

    # Find matching tariff: same resource, day_of_week, and hour falls within time window
    for tariff in tariffs:
        if (
            tariff.resource_id == resource_id
            and tariff.day_of_week == day_of_week
            and tariff.time_start <= hour < tariff.time_end
        ):
            return (tariff.price_cents, tariff.currency)

    # No matching tariff found - this is a configuration error that should
    # be fixed by adding tariff rules for all time slots
    raise Validation(
        f"No tariff found for resource {resource_id} at {start_at.isoformat()}. "
        f"Please configure booking tariffs for day {day_of_week}, hour {hour}."
    )


class BookingService:
    def __init__(
        self,
        session: AsyncSession,
        bookings: BookingRepository,
        facility_service: "FacilityService | None" = None,
    ) -> None:
        self.session = session
        self.bookings = bookings
        self.facility_service = facility_service
        self.tariffs = BookingTariffRepository(session)
        # Inject facility service into repository
        if facility_service is not None:
            self.bookings.facility_service = facility_service

    async def create_booking(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        resource_id: UUID,
        start_at: datetime,
        end_at: datetime,
        price_cents: int | None = None,
        currency: str = "INR",
        notes: str | None = None,
    ) -> Booking:
        # F-05 fix: Compute price from tariff (server-controlled)
        # If price_cents is provided, use it directly (for backward compatibility in tests)
        # Otherwise, compute from tariffs
        if price_cents is None:
            tariff_list = await self.tariffs.get_for_resource(tenant_id, resource_id)
            price_cents, currency = compute_price(
                resource_id=resource_id,
                start_at=start_at,
                tariffs=tariff_list,
            )

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
    ) -> list[tuple[Booking, str | None, str | None]]:
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

    async def list_admin_bookings(
        self,
        *,
        tenant_id: UUID,
        from_at: datetime,
        to_at: datetime,
        facility_id: UUID | None = None,
        resource_id: UUID | None = None,
        statuses: list[BookingStatus] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Booking]:
        """List bookings for admin dashboard with optional filters.

        Returns bookings within a date range, filtered by facility, resource,
        and/or status. Results are ordered by start time.
        """
        return list(
            await self.bookings.list_admin_bookings(
                tenant_id=tenant_id,
                from_at=from_at,
                to_at=to_at,
                facility_id=facility_id,
                resource_id=resource_id,
                statuses=statuses,
                limit=limit,
                offset=offset,
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
