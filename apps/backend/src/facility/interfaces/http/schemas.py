"""Pydantic schemas for facility endpoints."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from facility.domain.entities import ResourceType


# ---------- Facility ----------


class FacilityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(
        min_length=1, max_length=40, pattern=r"^[a-z0-9](?:[a-z0-9\-]{0,38}[a-z0-9])?$"
    )
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2 code")
    timezone: str = Field(default="Asia/Kolkata", min_length=1, max_length=64)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("country")
    @classmethod
    def _upper_country(cls, v: str) -> str:
        return v.upper()


class FacilityUpdate(BaseModel):
    """Partial update — every field is optional. Slug is intentionally not
    editable here (slug is the canonical URL identifier)."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    address_line1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, min_length=1, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("country")
    @classmethod
    def _upper_country(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else None


class FacilityOut(BaseModel):
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
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FacilityListResponse(BaseModel):
    data: list[FacilityOut]


# ---------- Resource ----------


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(
        min_length=1, max_length=40, pattern=r"^[a-z0-9](?:[a-z0-9\-]{0,38}[a-z0-9])?$"
    )
    resource_type: ResourceType
    capacity: int = Field(default=1, ge=1, le=1000)
    attributes: dict[str, object] = Field(default_factory=dict)


class ResourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    capacity: int | None = Field(default=None, ge=1, le=1000)
    attributes: dict[str, object] | None = None


class ResourceOut(BaseModel):
    id: UUID
    tenant_id: UUID
    facility_id: UUID
    name: str
    slug: str
    resource_type: str
    capacity: int
    attributes: dict[str, object]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceListResponse(BaseModel):
    data: list[ResourceOut]


# ---------- AvailabilityRule ----------


class AvailabilityRuleCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time
    end_time: time
    slot_duration_minutes: int = Field(ge=5, le=480)
    valid_from: date | None = None
    valid_until: date | None = None


class AvailabilityRuleOut(BaseModel):
    id: UUID
    tenant_id: UUID
    resource_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration_minutes: int
    valid_from: date | None
    valid_until: date | None

    model_config = ConfigDict(from_attributes=True)


class AvailabilityRuleListResponse(BaseModel):
    data: list[AvailabilityRuleOut]
