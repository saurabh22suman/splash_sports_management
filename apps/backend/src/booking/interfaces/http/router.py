"""HTTP router for booking endpoints."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.interfaces.http.dependencies import auth_required, auth_tenant
from booking.application.booking_service import BookingService
from booking.domain.entities import BookingStatus
from booking.infrastructure.repositories import BookingRepository
from booking.interfaces.http.schemas import (
    BookingCancel,
    BookingCreate,
    BookingListResponse,
    BookingOut,
)
from common.application.context import require_tenant_id
from common.domain.types import TenantId
from common.infrastructure.db import get_session

router = APIRouter(dependencies=[Depends(auth_required)])


def _booking_service(session: AsyncSession = Depends(get_session)) -> BookingService:
    return BookingService(session, BookingRepository(session))


def _to_out(b) -> BookingOut:  # type: ignore[no-untyped-def]
    return BookingOut.model_validate(b, from_attributes=True)


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingOut:
    """Create a booking. This is the critical no-double-booking endpoint.

    Acquires a row-level lock on the resource, then verifies no overlapping
    confirmed booking exists before inserting. Concurrent calls for the same
    resource are serialized by Postgres at the resource row.
    """
    booking = await svc.create_booking(
        tenant_id=tenant_id,
        customer_id=payload.customer_id,
        resource_id=payload.resource_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        price_cents=payload.price_cents,
        currency=payload.currency,
        notes=payload.notes,
    )
    return _to_out(booking)


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: UUID,
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingOut:
    b = await svc.get_booking(tenant_id=tenant_id, booking_id=booking_id)
    return _to_out(b)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: UUID,
    payload: BookingCancel,
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingOut:
    b = await svc.cancel_booking(
        tenant_id=tenant_id, booking_id=booking_id, reason=payload.reason
    )
    return _to_out(b)


@router.post("/{booking_id}/check-in", response_model=BookingOut)
async def check_in(
    booking_id: UUID,
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingOut:
    b = await svc.check_in(tenant_id=tenant_id, booking_id=booking_id)
    return _to_out(b)


@router.post("/{booking_id}/complete", response_model=BookingOut)
async def complete(
    booking_id: UUID,
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingOut:
    b = await svc.complete(tenant_id=tenant_id, booking_id=booking_id)
    return _to_out(b)


@router.get("/by-customer/{customer_id}", response_model=BookingListResponse)
async def list_for_customer(
    customer_id: UUID,
    status_filter: list[BookingStatus] = Query(default_factory=list, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingListResponse:
    bookings = await svc.list_customer_bookings(
        tenant_id=tenant_id,
        customer_id=customer_id,
        statuses=status_filter or None,
        limit=limit,
        offset=offset,
    )
    return BookingListResponse(data=[_to_out(b) for b in bookings])


@router.get("/by-resource/{resource_id}", response_model=BookingListResponse)
async def list_for_resource(
    resource_id: UUID,
    from_at: datetime = Query(...),
    to_at: datetime = Query(...),
    status_filter: list[BookingStatus] = Query(default_factory=list, alias="status"),
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingListResponse:
    bookings = await svc.list_resource_bookings(
        tenant_id=tenant_id,
        resource_id=resource_id,
        from_at=from_at,
        to_at=to_at,
        statuses=status_filter or None,
    )
    return BookingListResponse(data=[_to_out(b) for b in bookings])
