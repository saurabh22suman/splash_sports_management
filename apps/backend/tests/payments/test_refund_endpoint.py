"""API tests for refund endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401
from auth.infrastructure.models import TenantModel
from auth.interfaces.http.dependencies import auth_required, CurrentPrincipal
from common.application.events import InProcessEventPublisher
from common.infrastructure import db as db_module
from payments.infrastructure.models import (
    InvoiceLineItemModel,
    InvoiceModel,
    PaymentModel,
    ProcessedRazorpayEventModel,
    RefundModel,
    TenantPaymentConfigModel,
)
from payments.interfaces.http.deps import get_current_user, get_payment_service


@pytest_asyncio.fixture
async def client(seed_paid_invoice_data: dict) -> AsyncIterator[AsyncClient]:
    """Build FastAPI app with payments router and dependency overrides for testing."""
    from fastapi import FastAPI

    from common.interfaces.http.errors import register_error_handlers
    from payments.interfaces.http.router import router as payments_router

    app = FastAPI()
    # Register error handlers to convert domain exceptions to HTTP responses
    register_error_handlers(app)
    # Include router at /v1/payments to match main app behavior
    app.include_router(payments_router, prefix="/v1/payments")

    # Create in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(TenantModel.__table__.create)
        await conn.run_sync(TenantPaymentConfigModel.__table__.create)
        await conn.run_sync(InvoiceModel.__table__.create)
        await conn.run_sync(InvoiceLineItemModel.__table__.create)
        await conn.run_sync(PaymentModel.__table__.create)
        await conn.run_sync(RefundModel.__table__.create)
        await conn.run_sync(ProcessedRazorpayEventModel.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Seed test data
    async with factory() as session:
        cfg = TenantPaymentConfigModel(
            tenant_id=seed_paid_invoice_data["tenant_id"],
            default_currency="INR",
        )
        session.add(cfg)

        # Create paid invoice
        invoice = InvoiceModel(
            id=seed_paid_invoice_data["invoice_id"],
            tenant_id=seed_paid_invoice_data["tenant_id"],
            customer_id=seed_paid_invoice_data["customer_id"],
            invoice_number="INV-0002",
            status="paid",
            subtotal_paise=15000,
            tax_paise=0,
            total_paise=15000,
            currency="INR",
            due_date=date.today() + timedelta(days=7),
            paid_at=datetime.now(UTC),
            description="Test paid invoice",
            metadata_={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        invoice.line_items.append(
            InvoiceLineItemModel(
                id=uuid4(),
                invoice_id=invoice.id,
                description="Test item",
                quantity=1,
                unit_price_paise=15000,
                total_paise=15000,
            )
        )
        session.add(invoice)

        # Create captured payment
        payment = PaymentModel(
            id=seed_paid_invoice_data["payment_id"],
            tenant_id=seed_paid_invoice_data["tenant_id"],
            invoice_id=invoice.id,
            amount_paise=15000,
            currency="INR",
            status="captured",
            razorpay_payment_id="pay_test_123",
            razorpay_payment_link_id="plink_test_123",
            idempotency_key=None,
            captured_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(payment)
        await session.commit()

    _factory = factory

    async def override_get_session():
        async with _factory() as s:
            yield s

    async def get_event_bus():
        return InProcessEventPublisher()

    async def _service(session=Depends(db_module.get_session), events=Depends(get_event_bus)):
        from payments.application.payment_service import PaymentService
        from payments.infrastructure.repositories import (
            IdempotencyKeyRepository,
            InvoiceRepository,
            PaymentRepository,
            ProcessedRazorpayEventRepository,
            RefundRepository,
            TenantPaymentConfigRepository,
        )
        from common.infrastructure.settings import get_settings

        settings = get_settings()
        mock_provider = MagicMock()
        mock_provider.create_refund = AsyncMock(
            return_value={"id": "rfnd_test_123", "amount": 10000, "status": "processed"}
        )
        return PaymentService(
            session=session,
            invoice_repo=InvoiceRepository(session),
            payment_repo=PaymentRepository(session),
            refund_repo=RefundRepository(session),
            processed_event_repo=ProcessedRazorpayEventRepository(session),
            idempotency=IdempotencyKeyRepository(session),
            tenant_config_repo=TenantPaymentConfigRepository(session),
            events=events,
            provider=mock_provider,
            settings=settings,
        )

    app.dependency_overrides[db_module.get_session] = override_get_session
    app.dependency_overrides[get_payment_service] = _service

    # Default user fixture - tenant_admin role
    test_principal = CurrentPrincipal(
        user_id=seed_paid_invoice_data["user_id"],
        tenant_id=seed_paid_invoice_data["tenant_id"],
        roles=("tenant_admin",),
        jti="test-jti",
    )

    app.dependency_overrides[auth_required] = lambda: test_principal

    async def _user():
        return {
            "user_id": seed_paid_invoice_data["user_id"],
            "tenant_id": seed_paid_invoice_data["tenant_id"],
            "customer_id": seed_paid_invoice_data["customer_id"],
            "roles": ["tenant_admin"],
        }

    app.dependency_overrides[get_current_user] = _user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def seed_paid_invoice_data() -> dict:
    """Provide seed data for paid invoice tests."""
    return {
        "user_id": uuid4(),
        "tenant_id": uuid4(),
        "customer_id": uuid4(),
        "invoice_id": uuid4(),
        "payment_id": uuid4(),
    }


@pytest.mark.asyncio
class TestRefundEndpoint:
    async def test_post_refund_returns_pending_refund(
        self, client: AsyncClient, seed_paid_invoice_data: dict
    ) -> None:
        """Tenant admin can refund a paid invoice."""
        invoice_id = seed_paid_invoice_data["invoice_id"]

        resp = await client.post(
            f"/v1/payments/invoices/{invoice_id}/refund",
            json={"reason": "Customer requested refund"},
            headers={"X-Idempotency-Key": "test-refund-idempotency-123"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "id" in body
        assert body["status"] == "pending"
        assert body["reason"] == "Customer requested refund"

    async def test_post_refund_403_when_not_admin(
        self, client: AsyncClient, seed_paid_invoice_data: dict
    ) -> None:
        """Customer cannot refund invoices."""
        # Override user to be customer
        customer_principal = CurrentPrincipal(
            user_id=uuid4(),
            tenant_id=seed_paid_invoice_data["tenant_id"],
            roles=("customer",),
            jti="test-jti-customer",
        )

        client._transport.app.dependency_overrides[auth_required] = lambda: customer_principal

        async def _customer_user():
            return {
                "user_id": customer_principal.user_id,
                "tenant_id": seed_paid_invoice_data["tenant_id"],
                "customer_id": seed_paid_invoice_data["customer_id"],
                "roles": ["customer"],
            }

        client._transport.app.dependency_overrides[get_current_user] = _customer_user

        invoice_id = seed_paid_invoice_data["invoice_id"]
        resp = await client.post(
            f"/v1/payments/invoices/{invoice_id}/refund",
            json={"reason": "Customer requested refund"},
            headers={"X-Idempotency-Key": "test-refund-idempotency-123"},
        )

        assert resp.status_code == 403, resp.text
        body = resp.json()
        assert "tenant_admin" in body["detail"].lower()
