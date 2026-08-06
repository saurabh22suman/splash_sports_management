"""FacilityService."""
from __future__ import annotations

from datetime import date, time
from uuid import UUID

from facility.domain.entities import (
    AvailabilityRule,
    Facility,
    Resource,
    ResourceType,
)
from facility.infrastructure.repositories import (
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)
from common.domain.exceptions import NotFound
from sqlalchemy.ext.asyncio import AsyncSession


class FacilityService:
    def __init__(
        self,
        session: AsyncSession,
        facilities: FacilityRepository,
        resources: ResourceRepository,
        rules: AvailabilityRuleRepository,
    ) -> None:
        self.session = session
        self.facilities = facilities
        self.resources = resources
        self.rules = rules

    async def create_facility(
        self,
        *,
        tenant_id: UUID,
        name: str,
        slug: str,
        address_line1: str,
        address_line2: str | None,
        city: str,
        state: str,
        postal_code: str,
        country: str,
        timezone_: str,
        phone: str | None = None,
    ) -> Facility:
        f = Facility.create(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            timezone_=timezone_,
            phone=phone,
        )
        return await self.facilities.add(f)

    async def get_facility(self, *, tenant_id: UUID, facility_id: UUID) -> Facility:
        f = await self.facilities.get_by_id(tenant_id, facility_id)
        if f is None:
            raise NotFound("Facility not found", details={"facility_id": str(facility_id)})
        return f

    async def list_facilities(self, *, tenant_id: UUID) -> list[Facility]:
        return list(await self.facilities.list_for_tenant(tenant_id))

    async def create_resource(
        self,
        *,
        tenant_id: UUID,
        facility_id: UUID,
        name: str,
        slug: str,
        resource_type: ResourceType,
        capacity: int = 1,
        attributes: dict[str, object] | None = None,
    ) -> Resource:
        r = Resource.create(
            tenant_id=tenant_id,
            facility_id=facility_id,
            name=name,
            slug=slug,
            resource_type=resource_type,
            capacity=capacity,
            attributes=attributes,
        )
        return await self.resources.add(r)

    async def list_resources(self, *, tenant_id: UUID, facility_id: UUID) -> list[Resource]:
        return list(await self.resources.list_for_facility(tenant_id, facility_id))

    async def create_availability_rule(
        self,
        *,
        tenant_id: UUID,
        resource_id: UUID,
        day_of_week: int,
        start_time: time,
        end_time: time,
        slot_duration_minutes: int,
        valid_from: date | None = None,
        valid_until: date | None = None,
    ) -> AvailabilityRule:
        rule = AvailabilityRule.create(
            tenant_id=tenant_id,
            resource_id=resource_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            slot_duration_minutes=slot_duration_minutes,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        return await self.rules.add(rule)

    async def list_availability_rules(
        self, *, tenant_id: UUID, resource_id: UUID
    ) -> list[AvailabilityRule]:
        return list(await self.rules.list_for_resource(tenant_id, resource_id))
