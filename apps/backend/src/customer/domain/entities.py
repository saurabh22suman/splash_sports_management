"""Customer aggregate.

A Customer represents an end-user (member) of a sports club. Customers are
distinct from `auth.User` because:
- A User is an authentication identity (can log in)
- A Customer is a profile (can be linked to a User or stand-alone for guest bookings)

In v1 every Customer must have a linked User. Future versions may allow guest
bookings with stand-alone Customers.

Invariants:
- `email` is unique within tenant
- Phone numbers are E.164 when provided
- `status` transitions: ACTIVE -> INACTIVE -> ACTIVE, ACTIVE -> BANNED
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from uuid import UUID

from common.domain.exceptions import Validation


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"


_PHONE_RE = re.compile(r"^\+?[1-9]\d{6,14}$")


@dataclass(slots=True)
class Customer:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    full_name: str
    email: str
    phone: str | None
    date_of_birth: date | None
    status: CustomerStatus
    notes: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        user_id: UUID,
        full_name: str,
        email: str,
        phone: str | None = None,
        date_of_birth: date | None = None,
        notes: str | None = None,
    ) -> Customer:
        full_name = full_name.strip()
        if not full_name:
            raise Validation("Full name required")
        if "@" not in email or "." not in email:
            raise Validation("Invalid email")
        if phone is not None and not _PHONE_RE.match(phone):
            raise Validation("Phone must be E.164 format")
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            user_id=user_id,
            full_name=full_name,
            email=email.lower().strip(),
            phone=phone,
            date_of_birth=date_of_birth,
            status=CustomerStatus.ACTIVE,
            notes=notes,
        )

    def deactivate(self) -> None:
        if self.status != CustomerStatus.BANNED:
            self.status = CustomerStatus.INACTIVE
            self.updated_at = datetime.now(timezone.utc)

    def activate(self) -> None:
        if self.status != CustomerStatus.BANNED:
            self.status = CustomerStatus.ACTIVE
            self.updated_at = datetime.now(timezone.utc)

    def ban(self) -> None:
        self.status = CustomerStatus.BANNED
        self.updated_at = datetime.now(timezone.utc)

    def update_profile(
        self,
        *,
        full_name: str | None = None,
        phone: str | None = None,
        date_of_birth: date | None = None,
        notes: str | None = None,
    ) -> None:
        if full_name is not None:
            full_name = full_name.strip()
            if not full_name:
                raise Validation("Full name cannot be empty")
            self.full_name = full_name
        if phone is not None:
            if phone and not _PHONE_RE.match(phone):
                raise Validation("Phone must be E.164 format")
            self.phone = phone
        if date_of_birth is not None:
            self.date_of_birth = date_of_birth
        if notes is not None:
            self.notes = notes
        self.updated_at = datetime.now(timezone.utc)
