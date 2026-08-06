"""Pydantic schemas for customer endpoints."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    user_id: UUID
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[1-9]\d{6,14}$")
    date_of_birth: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[1-9]\d{6,14}$")
    date_of_birth: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CustomerOut(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    full_name: str
    email: EmailStr
    phone: str | None
    date_of_birth: date | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListResponse(BaseModel):
    data: list[CustomerOut]
    limit: int
    offset: int
