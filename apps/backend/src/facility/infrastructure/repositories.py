"""Facility repositories."""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from facility.domain.entities import (
    AvailabilityRule,
    Facility,
    FacilityStatus,
    Resource,
    ResourceStatus,
    ResourceType,
)
from facility.infrastructure.models import AvailabilityRuleModel, FacilityModel, ResourceModel
from common.domain.exceptions import Conflict
from common.infrastructure.repository import BaseRepository
from common.domain.types import TenantId


def _facility_to_domain(m: FacilityModel) -> Facility:
    return Facility(
        id=m.id,
        tenant_id=m.tenant_id,
        name=m.name,
        slug=m.slug,
        address_line1=m.address_line1,
        address_line2=m.address_line2,
        city=m.city,
        state=m.state,
        postal_code=m.postal_code,
        country=m.country,
        timezone=m.timezone,
        phone=m.phone,
        status=FacilityStatus(m.status),
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _resource_to_domain(m: ResourceModel) -> Resource:
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


def _rule_to_domain(m: AvailabilityRuleModel) -> AvailabilityRule:
    return AvailabilityRule(
        id=m.id,
        tenant_id=m.tenant_id,
        resource_id=m.resource_id,
        day_of_week=m.day_of_week,
        start_time=m.start_time,
        end_time=m.end_time,
        slot_duration_minutes=m.slot_duration_minutes,
        valid_from=m.valid_from,
        valid_until=m.valid_until,
        created_at=m.created_at,
    )


class FacilityRepository(BaseRepository[Facility]):
    model = FacilityModel

    async def get_by_id(self, tenant_id: TenantId, facility_id: UUID) -> Facility | None:
        m = await super().get(tenant_id, facility_id)
        return _facility_to_domain(m) if m else None

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Facility | None:
        stmt = select(FacilityModel).where(
            FacilityModel.tenant_id == tenant_id, FacilityModel.slug == slug
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _facility_to_domain(m) if m else None

    async def list_for_tenant(self, tenant_id: UUID) -> list[Facility]:
        stmt = (
            select(FacilityModel)
            .where(FacilityModel.tenant_id == tenant_id)
            .order_by(FacilityModel.name)
        )
        result = await self.session.execute(stmt)
        return [_facility_to_domain(m) for m in result.scalars().all()]

    async def add(self, facility: Facility) -> Facility:
        existing = await self.get_by_slug(facility.tenant_id, facility.slug)
        if existing is not None:
            raise Conflict(
                "Facility slug already exists",
                details={"slug": facility.slug, "facility_id": str(existing.id)},
            )
        m = FacilityModel(
            tenant_id=facility.tenant_id,
            name=facility.name,
            slug=facility.slug,
            address_line1=facility.address_line1,
            address_line2=facility.address_line2,
            city=facility.city,
            state=facility.state,
            postal_code=facility.postal_code,
            country=facility.country,
            timezone=facility.timezone,
            phone=facility.phone,
            status=facility.status.value,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _facility_to_domain(m)

    async def update(self, facility: Facility) -> Facility:
        m = await self.session.get(FacilityModel, facility.id)
        if m is None:
            raise LookupError(facility.id)
        m.name = facility.name
        m.address_line1 = facility.address_line1
        m.address_line2 = facility.address_line2
        m.city = facility.city
        m.state = facility.state
        m.postal_code = facility.postal_code
        m.country = facility.country
        m.timezone = facility.timezone
        m.phone = facility.phone
        m.status = facility.status.value
        await self.session.flush()
        await self.session.refresh(m)
        return _facility_to_domain(m)


class ResourceRepository(BaseRepository[Resource]):
    model = ResourceModel

    async def get_by_id(self, tenant_id: TenantId, resource_id: UUID) -> Resource | None:
        m = await super().get(tenant_id, resource_id)
        return _resource_to_domain(m) if m else None

    async def list_for_facility(self, tenant_id: UUID, facility_id: UUID) -> list[Resource]:
        stmt = (
            select(ResourceModel)
            .where(ResourceModel.tenant_id == tenant_id, ResourceModel.facility_id == facility_id)
            .order_by(ResourceModel.name)
        )
        result = await self.session.execute(stmt)
        return [_resource_to_domain(m) for m in result.scalars().all()]

    async def add(self, resource: Resource) -> Resource:
        # Validate facility exists in tenant
        facility_check = select(FacilityModel).where(
            FacilityModel.id == resource.facility_id,
            FacilityModel.tenant_id == resource.tenant_id,
        )
        if (await self.session.execute(facility_check)).scalar_one_or_none() is None:
            raise Conflict("Facility not found in this tenant")
        m = ResourceModel(
            tenant_id=resource.tenant_id,
            facility_id=resource.facility_id,
            name=resource.name,
            slug=resource.slug,
            resource_type=resource.resource_type.value,
            capacity=resource.capacity,
            attributes=resource.attributes,
            status=resource.status.value,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _resource_to_domain(m)

    async def update(self, resource: Resource) -> Resource:
        m = await self.session.get(ResourceModel, resource.id)
        if m is None:
            raise LookupError(resource.id)
        m.name = resource.name
        m.capacity = resource.capacity
        m.attributes = resource.attributes
        m.status = resource.status.value
        await self.session.flush()
        await self.session.refresh(m)
        return _resource_to_domain(m)


class AvailabilityRuleRepository(BaseRepository[AvailabilityRule]):
    model = AvailabilityRuleModel

    async def list_for_resource(self, tenant_id: UUID, resource_id: UUID) -> list[AvailabilityRule]:
        stmt = (
            select(AvailabilityRuleModel)
            .where(
                AvailabilityRuleModel.tenant_id == tenant_id,
                AvailabilityRuleModel.resource_id == resource_id,
            )
            .order_by(
                AvailabilityRuleModel.day_of_week,
                AvailabilityRuleModel.start_time,
            )
        )
        result = await self.session.execute(stmt)
        return [_rule_to_domain(m) for m in result.scalars().all()]

    async def add(self, rule: AvailabilityRule) -> AvailabilityRule:
        # Check no overlapping rule for same resource/day
        stmt = select(AvailabilityRuleModel).where(
            AvailabilityRuleModel.tenant_id == rule.tenant_id,
            AvailabilityRuleModel.resource_id == rule.resource_id,
            AvailabilityRuleModel.day_of_week == rule.day_of_week,
        )
        existing = (await self.session.execute(stmt)).scalars().all()
        for ex in existing:
            if ex.start_time < rule.end_time and rule.start_time < ex.end_time:
                raise Conflict(
                    "Availability rule overlaps with existing rule",
                    details={"existing_id": str(ex.id)},
                )
        m = AvailabilityRuleModel(
            tenant_id=rule.tenant_id,
            resource_id=rule.resource_id,
            day_of_week=rule.day_of_week,
            start_time=rule.start_time,
            end_time=rule.end_time,
            slot_duration_minutes=rule.slot_duration_minutes,
            valid_from=rule.valid_from,
            valid_until=rule.valid_until,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _rule_to_domain(m)
