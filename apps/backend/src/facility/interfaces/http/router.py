"""HTTP router for facility endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.application.context import require_tenant_id
from common.domain.types import TenantId
from common.infrastructure.db import get_session

from auth.interfaces.http.dependencies import auth_required, auth_tenant, requires_role
from facility.application.facility_service import FacilityService
from facility.infrastructure.repositories import (
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)
from facility.interfaces.http.schemas import (
    AvailabilityRuleCreate,
    AvailabilityRuleListResponse,
    AvailabilityRuleOut,
    FacilityCreate,
    FacilityListResponse,
    FacilityOut,
    FacilityUpdate,
    ResourceCreate,
    ResourceListResponse,
    ResourceOut,
    ResourceUpdate,
)

router = APIRouter(dependencies=[Depends(auth_required)])


def _facility_service(session: AsyncSession = Depends(get_session)) -> FacilityService:
    return FacilityService(
        session,
        FacilityRepository(session),
        ResourceRepository(session),
        AvailabilityRuleRepository(session),
    )


# ---------- Facility ----------


@router.post(
    "",
    response_model=FacilityOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires_role("tenant_admin", "manager"))],
)
async def create_facility(
    payload: FacilityCreate,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> FacilityOut:
    f = await svc.create_facility(
        tenant_id=tenant_id,
        name=payload.name,
        slug=payload.slug,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
        timezone_=payload.timezone,
        phone=payload.phone,
    )
    return FacilityOut.model_validate(f, from_attributes=True)


@router.get("", response_model=FacilityListResponse)
async def list_facilities(
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> FacilityListResponse:
    items = await svc.list_facilities(tenant_id=tenant_id)
    return FacilityListResponse(
        data=[FacilityOut.model_validate(f, from_attributes=True) for f in items]
    )


@router.get("/{facility_id}", response_model=FacilityOut)
async def get_facility(
    facility_id: UUID,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> FacilityOut:
    f = await svc.get_facility(tenant_id=tenant_id, facility_id=facility_id)
    return FacilityOut.model_validate(f, from_attributes=True)


@router.patch(
    "/{facility_id}",
    response_model=FacilityOut,
    dependencies=[Depends(requires_role("tenant_admin", "manager"))],
)
async def update_facility(
    facility_id: UUID,
    payload: FacilityUpdate,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> FacilityOut:
    f = await svc.update_facility(
        tenant_id=tenant_id,
        facility_id=facility_id,
        **payload.model_dump(exclude_unset=True),
    )
    return FacilityOut.model_validate(f, from_attributes=True)


@router.delete(
    "/{facility_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requires_role("tenant_admin", "manager"))],
)
async def deactivate_facility(
    facility_id: UUID,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> None:
    """Soft-delete: sets the facility's status to inactive. Returns 204."""
    await svc.deactivate_facility(tenant_id=tenant_id, facility_id=facility_id)


# ---------- Resource ----------


@router.post(
    "/{facility_id}/resources",
    response_model=ResourceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires_role("tenant_admin", "manager"))],
)
async def create_resource(
    facility_id: UUID,
    payload: ResourceCreate,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> ResourceOut:
    r = await svc.create_resource(
        tenant_id=tenant_id,
        facility_id=facility_id,
        name=payload.name,
        slug=payload.slug,
        resource_type=payload.resource_type,
        capacity=payload.capacity,
        attributes=payload.attributes,
    )
    return ResourceOut.model_validate(r, from_attributes=True)


@router.get(
    "/{facility_id}/resources",
    response_model=ResourceListResponse,
)
async def list_resources(
    facility_id: UUID,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> ResourceListResponse:
    items = await svc.list_resources(tenant_id=tenant_id, facility_id=facility_id)
    return ResourceListResponse(
        data=[ResourceOut.model_validate(r, from_attributes=True) for r in items]
    )


@router.patch(
    "/resources/{resource_id}",
    response_model=ResourceOut,
    dependencies=[Depends(requires_role("tenant_admin", "manager"))],
)
async def update_resource(
    resource_id: UUID,
    payload: ResourceUpdate,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> ResourceOut:
    r = await svc.update_resource(
        tenant_id=tenant_id,
        resource_id=resource_id,
        **payload.model_dump(exclude_unset=True),
    )
    return ResourceOut.model_validate(r, from_attributes=True)


@router.delete(
    "/resources/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requires_role("tenant_admin", "manager"))],
)
async def deactivate_resource(
    resource_id: UUID,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> None:
    """Soft-delete: sets the resource's status to inactive. Returns 204."""
    await svc.deactivate_resource(tenant_id=tenant_id, resource_id=resource_id)


# ---------- Availability ----------


@router.post(
    "/resources/{resource_id}/availability-rules",
    response_model=AvailabilityRuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires_role("tenant_admin", "manager"))],
)
async def create_availability_rule(
    resource_id: UUID,
    payload: AvailabilityRuleCreate,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> AvailabilityRuleOut:
    rule = await svc.create_availability_rule(
        tenant_id=tenant_id,
        resource_id=resource_id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        slot_duration_minutes=payload.slot_duration_minutes,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
    )
    return AvailabilityRuleOut.model_validate(rule, from_attributes=True)


@router.get(
    "/resources/{resource_id}/availability-rules",
    response_model=AvailabilityRuleListResponse,
)
async def list_availability_rules(
    resource_id: UUID,
    svc: FacilityService = Depends(_facility_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> AvailabilityRuleListResponse:
    rules = await svc.list_availability_rules(tenant_id=tenant_id, resource_id=resource_id)
    return AvailabilityRuleListResponse(
        data=[AvailabilityRuleOut.model_validate(r, from_attributes=True) for r in rules]
    )
