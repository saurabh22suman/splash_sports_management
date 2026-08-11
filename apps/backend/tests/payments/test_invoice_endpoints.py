"""API tests for invoice endpoints (create, list, get)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, UTC
from typing import Annotated
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

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
async def client(seed_invoices_data: dict) -> AsyncIterator[AsyncClient]:
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
            tenant_id=seed_invoices_data["tenant_id"],
            default_currency="INR",
        )
        session.add(cfg)

        # Invoice for the test user
        invoice1 = InvoiceModel(
            id=seed_invoices_data["invoice1_id"],
            tenant_id=seed_invoices_data["tenant_id"],
            customer_id=seed_invoices_data["customer_id"],
            invoice_number="INV-0001",
            status="pending",
            subtotal_paise=10000,
            tax_paise=0,
            total_paise=10000,
            currency="INR",
            due_date=date.today() + timedelta(days=7),
            paid_at=None,
            description="Test invoice 1",
            metadata_={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        invoice1.line_items.append(InvoiceLineItemModel(
            id=uuid4(),
            invoice_id=invoice1.id,
            description="Item 1",
            quantity=1,
            unit_price_paise=10000,
            total_paise=10000,
        ))
        session.add(invoice1)

        # Invoice for another customer
        invoice2 = InvoiceModel(
            id=seed_invoices_data["invoice2_id"],
            tenant_id=seed_invoices_data["tenant_id"],
            customer_id=seed_invoices_data["other_customer_id"],
            invoice_number="INV-0002",
            status="paid",
            subtotal_paise=20000,
            tax_paise=0,
            total_paise=20000,
            currency="INR",
            due_date=date.today() + timedelta(days=7),
            paid_at=datetime.now(UTC),
            description="Test invoice 2",
            metadata_={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        invoice2.line_items.append(InvoiceLineItemModel(
            id=uuid4(),
            invoice_id=invoice2.id,
            description="Item 2",
            quantity=1,
            unit_price_paise=20000,
            total_paise=20000,
        ))
        session.add(invoice2)

        await session.commit()

    # Store the factory for the session override
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

    # Create a mock principal for auth_required override
    # Use Annotated to match CurrentPrincipal structure
    test_principal = CurrentPrincipal(
        user_id=seed_invoices_data["user_id"],
        tenant_id=seed_invoices_data["tenant_id"],
        roles=("tenant_admin",),
        jti="test-jti",
    )

    app.dependency_overrides[auth_required] = lambda: test_principal

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def seed_invoices_data() -> dict:
    """Provide seed data for invoice tests."""
    return {
        "user_id": uuid4(),
        "tenant_id": uuid4(),
        "customer_id": uuid4(),
        "other_customer_id": uuid4(),
        "invoice1_id": uuid4(),
        "invoice2_id": uuid4(),
    }


@pytest.mark.asyncio
class TestInvoiceEndpoints:
    async def test_create_invoice_persists_and_returns_invoice(
        self, client: AsyncClient, seed_invoices_data: dict
    ) -> None:
        """Admin can create an invoice and gets back the created invoice."""
        customer_id = seed_invoices_data["customer_id"]

        resp = await client.post(
            "/v1/payments/invoices",
            json={
                "customer_id": str(customer_id),
                "line_items": [
                    {
                        "description": "New test item",
                        "quantity": 2,
                        "unit_price_paise": 5000,
                    }
                ],
                "description": "New test invoice",
                "due_date": (date.today() + timedelta(days=14)).isoformat(),
            },
            headers={"X-Idempotency-Key": "test-create-invoice-key"},
        )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "pending"
        assert body["total_paise"] == 10000  # 2 * 5000
        assert body["invoice_number"] == "INV-000003"  # Next in sequence (6 digits)
        assert len(body["line_items"]) == 1
        assert body["line_items"][0]["description"] == "New test item"

    async def test_list_invoices_returns_only_user_invoices_for_customer(
        self, client: AsyncClient, seed_invoices_data: dict
    ) -> None:
        """Customer sees only their own invoices when listing."""
        # Override auth_required to return a customer principal
        test_principal = CurrentPrincipal(
            user_id=uuid4(),
            tenant_id=seed_invoices_data["tenant_id"],
            roles=("customer",),
            jti="test-jti-customer",
        )

        # Override both auth_required and get_current_user for customer role
        client._transport.app.dependency_overrides[auth_required] = lambda: test_principal

        async def _customer_user():
            return {
                "user_id": test_principal.user_id,
                "tenant_id": seed_invoices_data["tenant_id"],
                "customer_id": seed_invoices_data["customer_id"],
                "roles": ["customer"],
            }

        client._transport.app.dependency_overrides[get_current_user] = _customer_user

        resp = await client.get("/v1/payments/invoices")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Customer should only see their own invoices
        for invoice in body:
            assert invoice["customer_id"] == str(seed_invoices_data["customer_id"])

    async def test_list_invoices_with_status_filter(
        self, client: AsyncClient, seed_invoices_data: dict
    ) -> None:
        """Admin can filter invoices by status."""
        # Use status query param
        resp = await client.get("/v1/payments/invoices?status=paid")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Should only return paid invoices
        for invoice in body:
            assert invoice["status"] == "paid"

    async def test_get_invoice_404_for_other_customer(
        self, client: AsyncClient, seed_invoices_data: dict
    ) -> None:
        """Customer gets 404 when accessing another customer's invoice."""
        # Override auth_required to return a customer principal
        test_principal = CurrentPrincipal(
            user_id=uuid4(),
            tenant_id=seed_invoices_data["tenant_id"],
            roles=("customer",),
            jti="test-jti-customer",
        )

        client._transport.app.dependency_overrides[auth_required] = lambda: test_principal

        async def _customer_user():
            return {
                "user_id": test_principal.user_id,
                "tenant_id": seed_invoices_data["tenant_id"],
                "customer_id": seed_invoices_data["customer_id"],
                "roles": ["customer"],
            }

        client._transport.app.dependency_overrides[get_current_user] = _customer_user

        # Try to get invoice belonging to other_customer
        invoice_id = seed_invoices_data["invoice2_id"]
        resp = await client.get(f"/v1/payments/invoices/{invoice_id}")

        assert resp.status_code == 404, resp.text

    async def test_get_invoice_returns_invoice(
        self, client: AsyncClient, seed_invoices_data: dict
    ) -> None:
        """Admin can get any invoice."""
        invoice_id = seed_invoices_data["invoice1_id"]

        resp = await client.get(f"/v1/payments/invoices/{invoice_id}")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == str(invoice_id)
        assert body["status"] == "pending"
