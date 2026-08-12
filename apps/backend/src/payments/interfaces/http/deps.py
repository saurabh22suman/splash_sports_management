"""Dependency injection for payments HTTP endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.interfaces.http.dependencies import CurrentPrincipal, auth_required
from common.infrastructure.db import get_session
from common.infrastructure.settings import get_settings
from customer.infrastructure.repositories import CustomerRepository
from payments.application.payment_service import PaymentService
from payments.infrastructure.idempotency import IdempotencyStore
from payments.infrastructure.repositories import (
    IdempotencyKeyRepository,
    InvoiceRepository,
    PaymentRepository,
    ProcessedRazorpayEventRepository,
    RefundRepository,
    TenantPaymentConfigRepository,
)

if TYPE_CHECKING:
    from common.application.events import EventPublisher
    from payments.application.provider import PaymentProvider


async def get_current_user(
    principal: CurrentPrincipal = Depends(auth_required),
    session=Depends(get_session),
) -> dict:
    """Returns the current user from the authenticated principal.

    Converts the CurrentPrincipal dataclass to a dict with keys:
    user_id, tenant_id, customer_id, roles.
    """
    # Look up customer_id if user has customer role
    customer_id = None
    if "customer" in principal.roles:
        customer_repo = CustomerRepository(session)
        customer = await customer_repo.get_by_user(principal.tenant_id, principal.user_id)
        if customer is not None:
            customer_id = customer.id

    return {
        "user_id": principal.user_id,
        "tenant_id": principal.tenant_id,
        "roles": list(principal.roles),
        "customer_id": customer_id,
    }


async def get_event_bus(request: Request) -> EventPublisher:
    """Resolve the EventPublisher singleton from app.state."""
    return request.app.state.event_bus


async def get_payment_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
    events: EventPublisher = Depends(get_event_bus),
) -> PaymentService:
    """Build PaymentService from the request-scoped session and the singleton provider + event bus.

    The provider and event bus are loaded from app.state (set at app startup).
    """
    provider: PaymentProvider = request.app.state.payment_provider
    redis = getattr(request.app.state, "redis", None)
    settings = get_settings()

    return PaymentService(
        session=session,
        invoice_repo=InvoiceRepository(session),
        payment_repo=PaymentRepository(session),
        refund_repo=RefundRepository(session),
        processed_event_repo=ProcessedRazorpayEventRepository(session),
        idempotency=IdempotencyStore(redis=redis, repo=IdempotencyKeyRepository(session)),
        tenant_config_repo=TenantPaymentConfigRepository(session),
        events=events,
        provider=provider,
        settings=settings,
    )


def idempotency_key(
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
) -> str | None:
    """Extract the X-Idempotency-Key header value (optional)."""
    return x_idempotency_key


def required_idempotency_key(
    x_idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> str:
    """Extract the X-Idempotency-Key header value (required)."""
    return x_idempotency_key
