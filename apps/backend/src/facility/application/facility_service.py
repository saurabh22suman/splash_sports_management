"""FacilityService."""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.domain.exceptions import NotFound
from facility.domain.entities import (
    AvailabilityRule,
    Facility,
    Resource,
    ResourceStatus,
    ResourceType,
)
from facility.infrastructure.repositories import (
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)


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

    async def update_facility(
        self,
        *,
        tenant_id: UUID,
        facility_id: UUID,
        **fields,
    ) -> Facility:
        f = await self.get_facility(tenant_id=tenant_id, facility_id=facility_id)
        f.update_details(**fields)
        return await self.facilities.update(f)

    async def deactivate_facility(self, *, tenant_id: UUID, facility_id: UUID) -> Facility:
        f = await self.get_facility(tenant_id=tenant_id, facility_id=facility_id)
        f.close()
        return await self.facilities.update(f)

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

    async def get_resource(self, *, tenant_id: UUID, resource_id: UUID) -> Resource:
        r = await self.resources.get_by_id(tenant_id, resource_id)
        if r is None:
            raise NotFound("Resource not found", details={"resource_id": str(resource_id)})
        return r

    async def update_resource(
        self,
        *,
        tenant_id: UUID,
        resource_id: UUID,
        **fields,
    ) -> Resource:
        r = await self.get_resource(tenant_id=tenant_id, resource_id=resource_id)
        r.update_details(**fields)
        return await self.resources.update(r)

    async def deactivate_resource(self, *, tenant_id: UUID, resource_id: UUID) -> Resource:
        r = await self.get_resource(tenant_id=tenant_id, resource_id=resource_id)
        r.deactivate()
        return await self.resources.update(r)

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

    async def lock_resource_for_update(self, *, tenant_id: UUID, resource_id: UUID) -> Resource:
        """Lock a resource row for update (SELECT FOR UPDATE).

        Used by BookingRepository.add_safe to serialize concurrent bookings
        against the same resource.
        """
        from facility.infrastructure.models import ResourceModel

        stmt = (
            select(ResourceModel)
            .where(
                ResourceModel.id == resource_id,
                ResourceModel.tenant_id == tenant_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        if m is None:
            raise NotFound(
                "Resource not found",
                details={"resource_id": str(resource_id)},
            )
        return Resource(
            id=m.id,
            tenant_id=m.tenant_id,
            facility_id=m.facility_id,
            name=m.name,
            slug=m.slug,
            resource_type=ResourceType(m.resource_type),
            capacity=m.capacity,
            attributes=dict(m.attributes or {}),
            status=ResourceStatus(m.status),
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def get_resource_names(
        self, *, tenant_id: UUID, resource_ids: list[UUID]
    ) -> dict[UUID, str]:
        """Get resource names for a list of resource IDs.

        Returns a dict mapping resource_id -> resource_name.
        """
        if not resource_ids:
            return {}

        from facility.infrastructure.models import ResourceModel

        stmt = select(ResourceModel.id, ResourceModel.name).where(
            ResourceModel.id.in_(resource_ids),
            ResourceModel.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def get_facility_names(
        self, *, tenant_id: UUID, facility_ids: list[UUID]
    ) -> dict[UUID, str]:
        """Get facility names for a list of facility IDs.

        Returns a dict mapping facility_id -> facility_name.
        """
        if not facility_ids:
            return {}

        from facility.infrastructure.models import FacilityModel

        stmt = select(FacilityModel.id, FacilityModel.name).where(
            FacilityModel.id.in_(facility_ids),
            FacilityModel.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def get_resource_and_facility_names(
        self, *, tenant_id: UUID, resource_ids: list[UUID]
    ) -> dict[UUID, tuple[str | None, str | None]]:
        """Get resource and facility names for a list of resource IDs.

        Returns a dict mapping resource_id -> (resource_name, facility_name).
        This is useful for displaying bookings with their associated names.
        """
        if not resource_ids:
            return {}

        from facility.infrastructure.models import FacilityModel, ResourceModel

        stmt = select(ResourceModel.id, ResourceModel.name, ResourceModel.facility_id).where(
            ResourceModel.id.in_(resource_ids),
            ResourceModel.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        rows = list(result.all())

        if not rows:
            return {}

        # Get facility IDs and fetch facility names
        facility_ids = list(set(row[2] for row in rows if row[2] is not None))
        facility_names = await self.get_facility_names(
            tenant_id=tenant_id, facility_ids=facility_ids
        )

        # Build result
        return {row[0]: (row[1], facility_names.get(row[2])) for row in rows}
