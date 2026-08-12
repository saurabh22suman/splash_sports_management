"""Base repository.

Modules subclass [`BaseRepository[T]`] for each aggregate root. We provide
session plumbing; the subclass declares which ORM model maps to the aggregate.

Per the handbook ([Repositories](../../../docs/04-backend/repositories.md)):
- one repository per aggregate
- repository methods are explicit (no generic `find_by`)
- no repository calls another repository
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.domain.types import TenantId

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Minimal base class.

    Subclasses expose domain-meaningful methods (e.g. `get_active_for_customer`).
    They MUST NOT expose raw query construction to callers.
    """

    model: type  # set by subclass

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, tenant_id: TenantId, id: UUID) -> T | None:
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id,  # type: ignore[attr-defined]
            self.model.id == id,  # type: ignore[attr-defined]
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0) -> Sequence[T]:
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == tenant_id)  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add(self, instance: T) -> None:
        self.session.add(instance)
        await self.session.flush()

    async def delete(self, instance: T) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def bulk_delete(self, tenant_id: TenantId, ids: list[UUID]) -> None:
        stmt = delete(self.model).where(
            self.model.tenant_id == tenant_id,  # type: ignore[attr-defined]
            self.model.id.in_(ids),  # type: ignore[attr-defined]
        )
        await self.session.execute(stmt)
