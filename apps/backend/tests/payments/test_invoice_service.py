from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401  (register TenantModel with Base.metadata)
from auth.infrastructure.models import TenantModel
from common.domain.exceptions import Validation
from payments.application.events import InvoiceCreated
from payments.application.payment_service import PaymentService
from payments.domain.entities import Invoice
from payments.infrastructure.models import (
    InvoiceLineItemModel,
    InvoiceModel,
    PaymentModel,
    ProcessedRazorpayEventModel,
    TenantPaymentConfigModel,
)
from payments.infrastructure.repositories import (
    IdempotencyKeyRepository,
    InvoiceRepository,
    PaymentRepository,
    ProcessedRazorpayEventRepository,
    RefundRepository,
    TenantPaymentConfigRepository,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # Create tables manually to avoid issues with PostgreSQL-specific types
        await conn.run_sync(TenantModel.__table__.create)
        await conn.run_sync(InvoiceModel.__table__.create)
        await conn.run_sync(InvoiceLineItemModel.__table__.create)
        await conn.run_sync(PaymentModel.__table__.create)
        await conn.run_sync(ProcessedRazorpayEventModel.__table__.create)
        await conn.run_sync(TenantPaymentConfigModel.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def make_service(session) -> tuple[PaymentService, MagicMock]:
    events = MagicMock()
    events.publish = AsyncMock()
    svc = PaymentService(
        session=session,
        invoice_repo=InvoiceRepository(session),
        payment_repo=PaymentRepository(session),
        refund_repo=RefundRepository(session),
        processed_event_repo=ProcessedRazorpayEventRepository(session),
        idempotency=IdempotencyKeyRepository(session),
        tenant_config_repo=TenantPaymentConfigRepository(session),
        events=events,
        provider=MagicMock(),
        settings=MagicMock(app_url="https://app.example"),
    )
    return svc, events


async def test_create_invoice_persists_and_publishes(session):
    tid = uuid4()
    session.add(
        TenantPaymentConfigModel(
            tenant_id=tid,
            razorpay_account_id=None,
            default_currency="INR",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    await session.commit()

    svc, events = make_service(session)
    inv = await svc.create_invoice(
        tenant_id=tid,
        customer_id=uuid4(),
        line_items=[{"description": "Lane 4", "quantity": 1, "unit_price_paise": 150000}],
        description="Booking #abc",
        due_date=date(2026, 9, 1),
        idempotency_key=None,
    )
    # Verify we get an Invoice entity, not a model
    assert isinstance(inv, Invoice)
    assert inv.status.value == "pending"
    assert inv.total.amount_paise == 150000
    assert inv.invoice_number.startswith("INV-")
    assert len(inv.line_items) == 1

    # Event was published
    events.publish.assert_awaited_once()
    event = events.publish.await_args.args[0]
    assert isinstance(event, InvoiceCreated)
    assert event.invoice_id == inv.id
    assert event.tenant_id == tid


async def test_create_invoice_rejects_invalid_line_items(session):
    tid = uuid4()
    session.add(
        TenantPaymentConfigModel(
            tenant_id=tid,
            razorpay_account_id=None,
            default_currency="INR",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    await session.commit()

    svc, _ = make_service(session)
    with pytest.raises(Validation):
        await svc.create_invoice(
            tenant_id=tid,
            customer_id=uuid4(),
            line_items=[{"description": "Bad", "quantity": 0, "unit_price_paise": 10000}],
            description="x",
            due_date=date(2026, 9, 1),
            idempotency_key=None,
        )
