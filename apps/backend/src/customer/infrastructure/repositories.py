"""Customer repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.infrastructure.models import UserModel  # for FK existence check at creation
from customer.domain.entities import Customer, CustomerStatus
from customer.infrastructure.models import CustomerModel
from common.domain.exceptions import Conflict
from common.infrastructure.repository import BaseRepository
from common.domain.types import TenantId


def _to_domain(m: CustomerModel) -> Customer:
    return Customer(
        id=m.id,
        tenant_id=m.tenant_id,
        user_id=m.user_id,
        full_name=m.full_name,
        email=m.email,
        phone=m.phone,
        date_of_birth=m.date_of_birth,
        status=CustomerStatus(m.status),
        notes=m.notes,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class CustomerRepository(BaseRepository[Customer]):
    model = CustomerModel

    async def get_by_id(self, tenant_id: TenantId, customer_id: UUID) -> Customer | None:
        m = await super().get(tenant_id, customer_id)
        return _to_domain(m) if m else None

    async def get_by_user(self, tenant_id: UUID, user_id: UUID) -> Customer | None:
        stmt = select(CustomerModel).where(
            CustomerModel.tenant_id == tenant_id, CustomerModel.user_id == user_id
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def get_by_email(self, tenant_id: UUID, email: str) -> Customer | None:
        stmt = select(CustomerModel).where(
            CustomerModel.tenant_id == tenant_id, CustomerModel.email == email.lower().strip()
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def list_for_tenant(
        self, tenant_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Customer]:
        stmt = (
            select(CustomerModel)
            .where(CustomerModel.tenant_id == tenant_id)
            .order_by(CustomerModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [_to_domain(m) for m in result.scalars().all()]

    async def add(self, customer: Customer) -> Customer:
        # Validate user_id exists for this tenant
        user_stmt = select(UserModel).where(
            UserModel.id == customer.user_id, UserModel.tenant_id == customer.tenant_id
        )
        user_result = await self.session.execute(user_stmt)
        if user_result.scalar_one_or_none() is None:
            raise Conflict(
                "User does not exist in this tenant", details={"user_id": str(customer.user_id)}
            )

        existing = await self.get_by_user(customer.tenant_id, customer.user_id)
        if existing is not None:
            raise Conflict(
                "Customer profile already exists for this user",
                details={"customer_id": str(existing.id)},
            )

        m = CustomerModel(
            tenant_id=customer.tenant_id,
            user_id=customer.user_id,
            full_name=customer.full_name,
            email=customer.email,
            phone=customer.phone,
            date_of_birth=customer.date_of_birth,
            status=customer.status.value,
            notes=customer.notes,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _to_domain(m)

    async def update(self, customer: Customer) -> Customer:
        m = await self.session.get(CustomerModel, customer.id)
        if m is None:
            raise LookupError(customer.id)
        m.full_name = customer.full_name
        m.phone = customer.phone
        m.date_of_birth = customer.date_of_birth
        m.status = customer.status.value
        m.notes = customer.notes
        await self.session.flush()
        # Refresh to load server-updated columns (e.g. `updated_at` from onupdate=func.now())
        # so subsequent attribute access doesn't trigger lazy-load IO.
        await self.session.refresh(m)
        return _to_domain(m)
