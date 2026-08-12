"""Domain entities for auth.

Per the handbook, the domain layer has zero framework dependencies. Entities
here are pure Python dataclasses. The ORM models in `infrastructure/models.py`
are a separate concern.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum
from uuid import UUID

from common.domain.exceptions import InvariantViolation, Validation


class UserRole(str, Enum):
    """Roles defined in [RBAC](../../../docs/09-security/authorization-rbac.md).

    Enum values match the role names stored in the database.
    """

    TENANT_ADMIN = "tenant_admin"
    MANAGER = "manager"
    COACH = "coach"
    STAFF = "staff"
    MEMBER = "member"
    CUSTOMER = "customer"


# Roles available in v1 — listed for tenant_id scoping rules
PLATFORM_ROLES = frozenset()  # No platform roles in v1; everything is tenant-scoped


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ONBOARDING = "onboarding"


@dataclass(slots=True)
class Tenant:
    """Tenant aggregate root.

    A tenant is a single sports club. Every business resource in the system
    belongs to exactly one tenant. Tenant isolation is enforced via:
    - Row-level security policies on every business table
    - Application-level tenant_id filtering on every query
    - Database session GUCs set on connection acquisition

    Invariants:
    - `slug` is unique and immutable
    - At least one TenantAdmin must exist before tenant can become ACTIVE
    - Status transitions: ONBOARDING -> ACTIVE -> SUSPENDED -> ACTIVE
    """

    id: UUID
    name: str
    slug: str
    status: TenantStatus
    primary_contact_email: str
    created_at: datetime
    updated_at: datetime

    _SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9\-]{0,38}[a-z0-9])?$")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        slug: str,
        primary_contact_email: str,
    ) -> Tenant:
        name = name.strip()
        if len(name) < 2 or len(name) > 100:
            raise Validation("Tenant name must be 2-100 characters")
        if not cls._SLUG_PATTERN.match(slug):
            raise Validation("Slug must be lowercase alphanumeric with hyphens")
        if "@" not in primary_contact_email:
            raise Validation("Invalid contact email")
        now = datetime.now(UTC)
        return cls(
            id=UUID(int=0),  # assigned by DB
            name=name,
            slug=slug,
            status=TenantStatus.ONBOARDING,
            primary_contact_email=primary_contact_email,
            created_at=now,
            updated_at=now,
        )

    def activate(self) -> None:
        if self.status == TenantStatus.SUSPENDED or self.status == TenantStatus.ONBOARDING:
            self.status = TenantStatus.ACTIVE
            self.updated_at = datetime.now(UTC)
        else:
            raise InvariantViolation(f"Cannot activate from {self.status}")


@dataclass(slots=True)
class User:
    """User aggregate root.

    Authentication identity. A user belongs to exactly one tenant (in v1;
    multi-tenant users will be supported via explicit tenant switching later).

    Invariants:
    - Email is unique within tenant
    - Password is never stored in clear; only the Argon2id hash
    - Status transitions: ACTIVE -> LOCKED -> ACTIVE, ACTIVE -> DISABLED
    """

    id: UUID
    tenant_id: UUID
    email: str
    password_hash: str
    full_name: str
    roles: list[UserRole]
    is_active: bool
    failed_login_count: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    _MAX_FAILED_LOGINS = 10
    _LOCKOUT_MINUTES = 15

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        email: str,
        password_hash: str,
        full_name: str,
        roles: list[UserRole],
    ) -> User:
        if not email or "@" not in email:
            raise Validation("Invalid email")
        if len(full_name.strip()) < 1:
            raise Validation("Full name required")
        if not roles:
            raise Validation("User must have at least one role")
        if password_hash.startswith("$argon2") is False:
            raise InvariantViolation("password_hash must be Argon2id encoded")
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name.strip(),
            roles=list(roles),
            is_active=True,
        )

    def is_locked(self, now: datetime | None = None) -> bool:
        if self.locked_until is None:
            return False
        now = now or datetime.now(UTC)
        return self.locked_until > now

    def record_failed_login(self, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        self.failed_login_count += 1
        if self.failed_login_count >= self._MAX_FAILED_LOGINS:
            from datetime import timedelta

            self.locked_until = now + timedelta(minutes=self._LOCKOUT_MINUTES)
            self.updated_at = now

    def record_successful_login(self, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = now
        self.updated_at = now

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles

    def add_role(self, role: UserRole) -> None:
        if role not in self.roles:
            self.roles.append(role)
            self.updated_at = datetime.now(UTC)

    def remove_role(self, role: UserRole) -> None:
        if role in self.roles:
            self.roles.remove(role)
            self.updated_at = datetime.now(UTC)


@dataclass(slots=True)
class RefreshToken:
    """Refresh-token handle.

    Stored server-side (we keep the hash, not the plaintext). On rotation:
    1. Lookup by token_hash
    2. If token not found: REUSE DETECTED → revoke entire family
    3. If token found and not used: mark used, issue new pair with same family_id

    Not frozen — `mark_used()` and `revoke()` transition the token's lifecycle
    state in-place. (A truly immutable token would return a new instance from
    every transition; we choose mutability here for clarity at the cost of
    identity safety within a single request.)
    """

    id: UUID
    tenant_id: UUID
    user_id: UUID
    token_hash: str
    family_id: str
    issued_at: datetime
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return self.used_at is None and self.revoked_at is None and self.expires_at > now

    def mark_used(self, now: datetime | None = None) -> None:
        self.used_at = now or datetime.now(UTC)

    def revoke(self, now: datetime | None = None) -> None:
        self.revoked_at = now or datetime.now(UTC)
