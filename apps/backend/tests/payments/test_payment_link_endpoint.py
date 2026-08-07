"""API tests for payment link endpoint."""
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

import auth.infrastructure.models  # noqa: F401  (register TenantModel with Base.metadata)
from auth.infrastructure.models import TenantModel
from common.application.events import InProcessEventPublisher
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
async def client(seed_invoice_data: dict) -> AsyncIterator[AsyncClient]:
    """Build FastAPI app with payments router and dependency overrides for testing."""
    from fastapi import FastAPI

    from payments.interfaces.http.router import router as payments_router

    app = FastAPI()
    app.include_router(payments_router, prefix="/v1")

    # Create in-memory SQLite for testing - create tables manually
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

    # Seed the test data
    async with factory() as session:
        cfg = TenantPaymentConfigModel(
            tenant_id=seed_invoice_data["tenant_id"],
            default_currency="INR",
        )
        session.add(cfg)

        invoice = InvoiceModel(
            id=seed_invoice_data["invoice_id"],
            tenant_id=seed_invoice_data["tenant_id"],
            customer_id=seed_invoice_data["customer_id"],
            invoice_number="INV-0001",
            status="pending",
            subtotal_paise=10000,
            tax_paise=0,
            total_paise=10000,
            currency="INR",
            due_date=date.today() + timedelta(days=7),
            paid_at=None,
            description="Test invoice",
            metadata_={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        invoice.line_items.append(InvoiceLineItemModel(
            id=uuid4(),
            invoice_id=invoice.id,
            description="Test item",
            quantity=1,
            unit_price_paise=10000,
            total_paise=10000,
        ))
        session.add(invoice)
        await session.commit()

    async def get_session():
        async with factory() as s:
            yield s

    async def get_event_bus():
        return InProcessEventPublisher()

    async def _service(session=Depends(get_session), events=Depends(get_event_bus)):
        from payments.application.payment_service import PaymentService
        from payments.infrastructure.repositories import (
            IdempotencyKeyRepository,
            InvoiceRepository,
            PaymentRepository,
            ProcessedRazorpayEventRepository,
            RefundRepository,
            TenantPaymentConfigRepository,
        )

        settings = MagicMock(app_url="https://app.example")
        mock_provider = MagicMock()
        mock_provider.create_payment_link = AsyncMock(
            return_value=MagicMock(
                short_url="https://stub.test/rzp/test123",
                razorpay_payment_link_id="plink_test_123",
                razorpay_order_id=None,
                expires_at=datetime.now(UTC) + timedelta(hours=24),
            )
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

    app.dependency_overrides[get_payment_service] = _service

    # Default user fixture
    test_user = {
        "user_id": uuid4(),
        "tenant_id": seed_invoice_data["tenant_id"],
        "customer_id": seed_invoice_data["customer_id"],
        "roles": ["customer"],
    }

    async def _user():
        return test_user

    app.dependency_overrides[get_current_user] = _user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def seed_invoice_data() -> dict:
    """Provide seed data for tests."""
    return {
        "tenant_id": uuid4(),
        "customer_id": uuid4(),
        "invoice_id": uuid4(),
    }


@pytest.mark.asyncio
class TestPaymentLinkEndpoint:
    async def test_post_payment_link_returns_short_url(
        self, client: AsyncClient, seed_invoice_data: dict
    ) -> None:
        """Customer can create payment link for their pending invoice."""
        invoice_id = seed_invoice_data["invoice_id"]

        resp = await client.post(
            f"/v1/payments/invoices/{invoice_id}/payment-link",
            headers={"X-Idempotency-Key": "test-idempotency-key-123"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "short_url" in body
        assert "razorpay_payment_link_id" in body
        assert body["short_url"].startswith("https://stub.test/")

    async def test_post_payment_link_403_when_not_customer(
        self, client: AsyncClient, seed_invoice_data: dict
    ) -> None:
        """Non-customer (tenant_admin) cannot create payment link."""
        # Override user to be tenant_admin
        async def _admin_user():
            return {
                "user_id": uuid4(),
                "tenant_id": seed_invoice_data["tenant_id"],
                "customer_id": uuid4(),
                "roles": ["tenant_admin"],
            }

        client._transport.app.dependency_overrides[get_current_user] = _admin_user

        invoice_id = seed_invoice_data["invoice_id"]
        resp = await client.post(
            f"/v1/payments/invoices/{invoice_id}/payment-link",
            headers={"X-Idempotency-Key": "test-idempotency-key-123"},
        )

        assert resp.status_code == 403, resp.text
        body = resp.json()
        assert "customer" in body["detail"].lower()

    async def test_post_payment_link_400_when_no_idempotency_key(
        self, client: AsyncClient, seed_invoice_data: dict
    ) -> None:
        """Request without idempotency key returns 400."""
        # Reset to customer role
        async def _customer_user():
            return {
                "user_id": uuid4(),
                "tenant_id": seed_invoice_data["tenant_id"],
                "customer_id": seed_invoice_data["customer_id"],
                "roles": ["customer"],
            }

        client._transport.app.dependency_overrides[get_current_user] = _customer_user

        invoice_id = seed_invoice_data["invoice_id"]
        resp = await client.post(f"/v1/payments/invoices/{invoice_id}/payment-link")

        assert resp.status_code == 400, resp.text
