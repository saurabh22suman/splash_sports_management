"""HTTP router for customer endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.interfaces.http.dependencies import auth_required, auth_tenant
from common.application.context import require_tenant_id
from common.domain.types import TenantId
from common.infrastructure.db import get_session

from customer.application.customer_service import CustomerService
from customer.infrastructure.repositories import CustomerRepository
from customer.interfaces.http.schemas import (
    CustomerCreate,
    CustomerListResponse,
    CustomerOut,
    CustomerUpdate,
)

router = APIRouter(dependencies=[Depends(auth_required)])


def _customer_service(session: AsyncSession = Depends(get_session)) -> CustomerService:
    return CustomerService(session, CustomerRepository(session))


def _to_out(c) -> CustomerOut:  # type: ignore[no-untyped-def]
    return CustomerOut.model_validate(c, from_attributes=True)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    svc: CustomerService = Depends(_customer_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> CustomerOut:
    c = await svc.create_customer(
        tenant_id=tenant_id,
        user_id=payload.user_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        notes=payload.notes,
    )
    return _to_out(c)


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    svc: CustomerService = Depends(_customer_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> CustomerListResponse:
    items = await svc.list_customers(tenant_id=tenant_id, limit=limit, offset=offset)
    return CustomerListResponse(data=[_to_out(c) for c in items], limit=limit, offset=offset)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: UUID,
    svc: CustomerService = Depends(_customer_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> CustomerOut:
    c = await svc.get_customer(tenant_id=tenant_id, customer_id=customer_id)
    return _to_out(c)


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    svc: CustomerService = Depends(_customer_service),
    tenant_id: TenantId = Depends(auth_tenant),
) -> CustomerOut:
    c = await svc.update_customer(
        tenant_id=tenant_id,
        customer_id=customer_id,
        full_name=payload.full_name,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        notes=payload.notes,
    )
    return _to_out(c)
