"""Dependency injection for payments HTTP endpoints."""
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Header, Request

from common.infrastructure.settings import get_settings
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


async def get_current_user(request: Request) -> dict:
    """Auth shim - returns the current user from request.state.

    In production, this would be set by authentication middleware.
    TODO: Replace with real auth middleware that populates request.state.current_user
          with a CurrentPrincipal dataclass containing user_id, tenant_id, roles.

    This shim returns a dict with: user_id, tenant_id, customer_id, roles.
    """
    return request.state.current_user


async def get_payment_service(
    request: Request,
    session=Depends(lambda: None),  # overridden by app
    events: EventPublisher = Depends(lambda: None),  # overridden by app
) -> PaymentService:
    """Build PaymentService from the request-scoped session and the singleton provider + event bus.

    In production, session and events are injected via dependency_overrides.
    The provider is loaded from app.state.payment_provider.
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
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None
) -> str | None:
    """Extract the X-Idempotency-Key header value."""
    return x_idempotency_key
