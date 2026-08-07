from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401  (register TenantModel with Base.metadata)
from auth.infrastructure.models import TenantModel
from common.domain.exceptions import Conflict, NotFound
from payments.application.payment_service import PaymentService
from payments.application.provider import PaymentLinkResult
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
    provider = MagicMock()
    provider.create_payment_link = AsyncMock(return_value=PaymentLinkResult(
        short_url="https://stub.test/rzp/abc",
        razorpay_payment_link_id="plink_abc",
        razorpay_order_id=None,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    ))
    svc = PaymentService(
        session=session,
        invoice_repo=InvoiceRepository(session),
        payment_repo=PaymentRepository(session),
        refund_repo=RefundRepository(session),
        processed_event_repo=ProcessedRazorpayEventRepository(session),
        idempotency=IdempotencyKeyRepository(session),
        tenant_config_repo=TenantPaymentConfigRepository(session),
        events=events,
        provider=provider,
        settings=MagicMock(app_url="https://app.example"),
    )
    return svc, events


async def test_create_payment_link_returns_short_url(session):
    tid = uuid4()
    session.add(TenantPaymentConfigModel(
        tenant_id=tid, razorpay_account_id=None, default_currency="INR",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    await session.commit()

    svc, events = make_service(session)
    inv = await svc.create_invoice(
        tenant_id=tid, customer_id=uuid4(),
        line_items=[{"description": "Lane 4", "quantity": 1, "unit_price_paise": 150000}],
        description="Booking", due_date=date(2026, 9, 1), idempotency_key=None,
    )
    events.publish.reset_mock()

    result = await svc.create_payment_link(
        tenant_id=tid, customer_id=inv.customer_id, invoice_id=inv.id, idempotency_key="key-1",
    )
    assert result.short_url.startswith("https://")
    assert result.razorpay_payment_link_id.startswith("plink_")
    # Persisted a Payment row in PENDING
    payments = (
        await session.execute(
            select(PaymentModel).where(PaymentModel.invoice_id == inv.id)
        )
    ).scalars().all()
    assert len(payments) == 1
    assert payments[0].razorpay_payment_link_id == result.razorpay_payment_link_id


async def test_create_payment_link_404_on_unknown_invoice(session):
    svc, _ = make_service(session)
    with pytest.raises(NotFound):
        await svc.create_payment_link(
            tenant_id=uuid4(), customer_id=uuid4(), invoice_id=uuid4(), idempotency_key="k",
        )


async def test_create_payment_link_409_on_paid_invoice(session):
    tid = uuid4()
    session.add(TenantPaymentConfigModel(
        tenant_id=tid, razorpay_account_id=None, default_currency="INR",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    await session.commit()

    svc, _ = make_service(session)
    inv_entity = await svc.create_invoice(
        tenant_id=tid, customer_id=uuid4(),
        line_items=[{"description": "x", "quantity": 1, "unit_price_paise": 10000}],
        description="x", due_date=date(2026, 9, 1), idempotency_key=None,
    )
    # Get the model from DB to mark it as paid (directly set status on the model)
    inv = (
        await session.execute(
            select(InvoiceModel).where(InvoiceModel.id == inv_entity.id)
        )
    ).scalar_one()
    inv.status = "paid"
    inv.paid_at = datetime.now(UTC)
    await svc._invoices.save(inv)
    with pytest.raises(Conflict):
        await svc.create_payment_link(
            tenant_id=tid,
            customer_id=inv_entity.customer_id,
            invoice_id=inv_entity.id,
            idempotency_key="k",
        )
