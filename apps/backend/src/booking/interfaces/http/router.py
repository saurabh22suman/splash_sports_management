"""HTTP router for booking endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.interfaces.http.dependencies import auth_required, auth_tenant, requires_role
from booking.application.booking_service import BookingService
from booking.domain.entities import BookingStatus
from booking.infrastructure.repositories import BookingRepository
from booking.interfaces.http.schemas import (
    BookingCancel,
    BookingCreate,
    BookingListResponse,
    BookingOut,
)
from booking.domain.entities import BookingStatus
from common.application.context import require_tenant_id
from common.domain.types import TenantId
from common.infrastructure.db import get_session
from facility.application.facility_service import FacilityService
from facility.infrastructure.repositories import (
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)

router = APIRouter(dependencies=[Depends(auth_required)])


def _booking_service(session: AsyncSession = Depends(get_session)) -> BookingService:
    facility_svc = FacilityService(
        session,
        FacilityRepository(session),
        ResourceRepository(session),
        AvailabilityRuleRepository(session),
    )
    return BookingService(
        session,
        BookingRepository(session, facility_service=facility_svc),
        facility_service=facility_svc,
    )


def _to_out(b, *, facility_name: str | None = None, resource_name: str | None = None) -> BookingOut:
    out = BookingOut.model_validate(b, from_attributes=True)
    if facility_name is not None:
        out.facility_name = facility_name
    if resource_name is not None:
        out.resource_name = resource_name
    return out


async def _to_admin_out(
    svc: BookingService, b, tenant_id: TenantId
) -> BookingOut:
    """Convert a booking to admin output with customer and facility details."""
    from customer.infrastructure.repositories import CustomerRepository

    out = BookingOut.model_validate(b, from_attributes=True)

    # Get customer name and email
    customer_repo = CustomerRepository(svc.session)
    customer = await customer_repo.get_by_id(tenant_id, b.customer_id)
    if customer:
        out.customer_name = customer.full_name
        out.customer_email = customer.email

    # Get resource and facility names via FacilityService
    if svc.facility_service:
        names_map = await svc.facility_service.get_resource_and_facility_names(
            tenant_id=tenant_id,
            resource_ids=[b.resource_id],
        )
        resource_name, facility_name = names_map.get(b.resource_id, (None, None))
        out.resource_name = resource_name
        out.facility_name = facility_name

        # Get facility_id for filtering
        if resource_name:
            from facility.infrastructure.repositories import ResourceRepository
            resource_repo = ResourceRepository(svc.session)
            resource = await resource_repo.get_by_id(tenant_id, b.resource_id)
            if resource:
                out.facility_id = resource.facility_id

    return out


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

    Note: Price is computed server-side from BookingTariff table (F-05 fix).
    """
    booking = await svc.create_booking(
        tenant_id=tenant_id,
        customer_id=payload.customer_id,
        resource_id=payload.resource_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
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


@router.post(
    "/{booking_id}/check-in",
    response_model=BookingOut,
    dependencies=[Depends(requires_role("tenant_admin", "manager", "coach", "staff"))],
)
async def check_in(
    booking_id: UUID,
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingOut:
    b = await svc.check_in(tenant_id=tenant_id, booking_id=booking_id)
    return _to_out(b)


@router.post(
    "/{booking_id}/complete",
    response_model=BookingOut,
    dependencies=[Depends(requires_role("tenant_admin", "manager", "coach", "staff"))],
)
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
    return BookingListResponse(
        data=[
            _to_out(b, facility_name=fn, resource_name=rn)
            for b, fn, rn in bookings
        ]
    )


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


@router.get(
    "/admin/bookings",
    response_model=BookingListResponse,
    dependencies=[Depends(requires_role("tenant_admin", "manager"))],
)
async def list_admin_bookings(
    from_at: datetime = Query(default=None),
    to_at: datetime = Query(default=None),
    facility_id: UUID | None = Query(default=None),
    resource_id: UUID | None = Query(default=None),
    status_filter: list[BookingStatus] = Query(default_factory=list, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    svc: BookingService = Depends(_booking_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> BookingListResponse:
    """List bookings for admin dashboard.

    Returns all bookings for the current tenant with optional filters:
    - Date range (from_at, to_at)
    - Facility (facility_id)
    - Resource (resource_id)
    - Status (status)

    Includes customer name/email and resource/facility names via JOINs.
    """
    # Default to today if not specified
    if from_at is None:
        from_at = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if to_at is None:
        to_at = from_at.replace(hour=23, minute=59, second=59)

    bookings = await svc.list_admin_bookings(
        tenant_id=tenant_id,
        from_at=from_at,
        to_at=to_at,
        facility_id=facility_id,
        resource_id=resource_id,
        statuses=status_filter or None,
        limit=limit,
        offset=offset,
    )

    # Enrich with customer and facility info
    return BookingListResponse(data=[await _to_admin_out(svc, b, tenant_id) for b in bookings])
