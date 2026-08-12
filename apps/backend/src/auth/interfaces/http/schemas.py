"""Pydantic schemas for auth HTTP endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from auth.domain.entities import UserRole


class RegisterTenantRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=100)
    tenant_slug: str = Field(
        min_length=1, max_length=40, pattern=r"^[a-z0-9](?:[a-z0-9\-]{0,38}[a-z0-9])?$"
    )
    primary_contact_email: EmailStr
    admin_email: EmailStr
    admin_password: str = Field(min_length=12, max_length=128)
    admin_full_name: str = Field(min_length=1, max_length=120)

    @field_validator("admin_password")
    @classmethod
    def _pw_strength(cls, v: str) -> str:
        # Per handbook: min length 12, no forced complexity. We just enforce
        # length here; complexity is a guideline enforced via UX hints.
        if len(v) < 12:
            msg = "Password must be at least 12 characters"
            raise ValueError(msg)
        return v


class RegisterTenantResponse(BaseModel):
    tenant_id: UUID
    tenant_slug: str
    admin_user_id: UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    user_id: UUID
    tenant_id: UUID
    roles: list[str] = Field(default_factory=list)
    customer_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class RefreshRequest(BaseModel):
    """Either provide refresh_token in body OR send it as the refresh cookie.

    The router reads cookie first; body is a fallback for server-to-server callers.
    """

    refresh_token: str | None = Field(default=None, min_length=10)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=10)


class UserOut(BaseModel):
    id: UUID
    tenant_id: UUID
    email: EmailStr
    full_name: str
    roles: list[str]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TenantOut(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    primary_contact_email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    roles: list[Literal["customer", "staff"]] = Field(min_length=1, max_length=4)


class CreateUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    roles: list[str]


class UserListItem(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    roles: list[str]
    is_active: bool
    created_at: datetime


class UserListResponse(BaseModel):
    data: list[UserListItem]
