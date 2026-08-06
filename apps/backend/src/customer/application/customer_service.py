"""CustomerService — application orchestration for customer use cases."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from customer.domain.entities import Customer
from customer.infrastructure.repositories import CustomerRepository
from common.domain.exceptions import NotFound
from sqlalchemy.ext.asyncio import AsyncSession


class CustomerService:
    def __init__(self, session: AsyncSession, customers: CustomerRepository) -> None:
        self.session = session
        self.customers = customers

    async def create_customer(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        full_name: str,
        email: str,
        phone: str | None = None,
        date_of_birth: date | None = None,
        notes: str | None = None,
    ) -> Customer:
        customer = Customer.create(
            tenant_id=tenant_id,
            user_id=user_id,
            full_name=full_name,
            email=email,
            phone=phone,
            date_of_birth=date_of_birth,
            notes=notes,
        )
        return await self.customers.add(customer)

    async def get_customer(self, *, tenant_id: UUID, customer_id: UUID) -> Customer:
        c = await self.customers.get_by_id(tenant_id, customer_id)
        if c is None:
            raise NotFound("Customer not found", details={"customer_id": str(customer_id)})
        return c

    async def list_customers(
        self, *, tenant_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Customer]:
        return list(await self.customers.list_for_tenant(tenant_id, limit=limit, offset=offset))

    async def update_customer(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        full_name: str | None = None,
        phone: str | None = None,
        date_of_birth: date | None = None,
        notes: str | None = None,
    ) -> Customer:
        c = await self.get_customer(tenant_id=tenant_id, customer_id=customer_id)
        c.update_profile(
            full_name=full_name,
            phone=phone,
            date_of_birth=date_of_birth,
            notes=notes,
        )
        return await self.customers.update(c)
