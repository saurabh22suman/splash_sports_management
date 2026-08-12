"""ORM mixins shared by all modules.

Every business table has:
- `id` UUID primary key
- `tenant_id` UUID NOT NULL with index (enables RLS + fast tenant filtering)
- `created_at` / `updated_at` timestamps
- `created_by` / `updated_by` audit fields (nullable for system actions)
- `version` integer for optimistic concurrency
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.domain.types import TenantId

uuid_pk = Annotated[
    uuid.UUID,
    mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
]
tenant_id_col = Annotated[
    uuid.UUID,
    mapped_column(UUID(as_uuid=True), index=True, nullable=False),
]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditMixin:
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class OptimisticLockMixin:
    """Adds a `version` column. Bumped on every update.

    Use with `SELECT ... FOR UPDATE` or version-check on update:

        if row.version != expected_version:
            raise ConcurrencyConflict
        row.version += 1
    """

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


def tenant_fk_column() -> Mapped[uuid.UUID]:
    """Helper for FK columns referencing tenants(id)."""
    return mapped_column(  # type: ignore[return-value]
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_tenants_tenant_id"),
        nullable=False,
        index=True,
    )
