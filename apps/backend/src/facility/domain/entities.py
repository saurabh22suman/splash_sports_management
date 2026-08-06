"""Facility domain entities.

A Facility is a physical location (e.g., "Splashh Koramangala"). A Facility
has Resources (e.g., "Court 1", "25m Lane 3", "Tennis Court A"). Each
Resource has AvailabilityRules that define when it can be booked.

Invariants:
- `Facility.slug` is unique within tenant
- `Resource.slug` is unique within facility
- Availability rules don't overlap for the same resource
- A Resource's facility_id must reference an existing Facility in the same tenant
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from enum import Enum
from uuid import UUID

from common.domain.exceptions import Validation


class FacilityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_MAINTENANCE = "under_maintenance"


class ResourceType(str, Enum):
    """What kind of physical resource this is.

    We keep this enum small in v1. New types are added as needed; they map
    1:1 to sports but we don't enumerate sports here because the booking
    model is sport-agnostic.
    """

    COURT = "court"
    LANE = "lane"
    POOL = "pool"
    FIELD = "field"
    NET = "net"
    STUDIO = "studio"
    GYM_FLOOR = "gym_floor"
    ROOM = "room"


class ResourceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_MAINTENANCE = "under_maintenance"


_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9\-]{0,38}[a-z0-9])?$")


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise Validation("Slug must be lowercase alphanumeric with hyphens")


@dataclass(slots=True)
class Facility:
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    address_line1: str
    address_line2: str | None
    city: str
    state: str
    postal_code: str
    country: str
    timezone: str
    phone: str | None
    status: FacilityStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
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
        if len(name.strip()) < 2:
            raise Validation("Facility name required")
        _validate_slug(slug)
        if not city.strip() or not country.strip():
            raise Validation("City and country required")
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            name=name.strip(),
            slug=slug,
            address_line1=address_line1.strip(),
            address_line2=address_line2.strip() if address_line2 else None,
            city=city.strip(),
            state=state.strip(),
            postal_code=postal_code.strip(),
            country=country.strip(),
            timezone=timezone_,
            phone=phone,
            status=FacilityStatus.ACTIVE,
        )

    def close(self) -> None:
        self.status = FacilityStatus.INACTIVE
        self.updated_at = datetime.now(timezone.utc)

    def open(self) -> None:
        self.status = FacilityStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)

    def put_under_maintenance(self) -> None:
        self.status = FacilityStatus.UNDER_MAINTENANCE
        self.updated_at = datetime.now(timezone.utc)


@dataclass(slots=True)
class Resource:
    id: UUID
    tenant_id: UUID
    facility_id: UUID
    name: str
    slug: str
    resource_type: ResourceType
    capacity: int
    attributes: dict[str, object]
    status: ResourceStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        facility_id: UUID,
        name: str,
        slug: str,
        resource_type: ResourceType,
        capacity: int = 1,
        attributes: dict[str, object] | None = None,
    ) -> Resource:
        if len(name.strip()) < 1:
            raise Validation("Resource name required")
        _validate_slug(slug)
        if capacity < 1:
            raise Validation("Capacity must be >= 1")
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            facility_id=facility_id,
            name=name.strip(),
            slug=slug,
            resource_type=resource_type,
            capacity=capacity,
            attributes=attributes or {},
            status=ResourceStatus.ACTIVE,
        )

    def deactivate(self) -> None:
        self.status = ResourceStatus.INACTIVE
        self.updated_at = datetime.now(timezone.utc)


@dataclass(slots=True)
class AvailabilityRule:
    """Defines when a Resource can be booked.

    `day_of_week`: 0=Monday, 6=Sunday
    `start_time` / `end_time`: local times in the Facility's timezone
    `slot_duration_minutes`: how bookings are sliced (e.g., 60 = hourly slots)
    `valid_from` / `valid_until`: optional date range
    """

    id: UUID
    tenant_id: UUID
    resource_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration_minutes: int
    valid_from: date | None
    valid_until: date | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
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
        if not 0 <= day_of_week <= 6:
            raise Validation("day_of_week must be 0-6")
        if start_time >= end_time:
            raise Validation("start_time must be before end_time")
        if slot_duration_minutes < 5:
            raise Validation("Slot duration must be >= 5 minutes")
        if valid_from and valid_until and valid_from > valid_until:
            raise Validation("valid_from must be before valid_until")
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            resource_id=resource_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            slot_duration_minutes=slot_duration_minutes,
            valid_from=valid_from,
            valid_until=valid_until,
        )
