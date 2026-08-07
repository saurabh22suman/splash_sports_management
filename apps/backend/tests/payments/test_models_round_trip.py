from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401  (register TenantModel with Base.metadata)
from payments.infrastructure.models import (
    IdempotencyKeyModel,
    InvoiceLineItemModel,
    InvoiceModel,
    PaymentModel,
    ProcessedRazorpayEventModel,
    RefundModel,
    TenantPaymentConfigModel,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # Create tables manually to avoid issues with PostgreSQL-specific types
        # in auth models when using SQLite
        from auth.infrastructure.models import TenantModel
        await conn.run_sync(TenantModel.__table__.create)
        await conn.run_sync(InvoiceModel.__table__.create)
        await conn.run_sync(InvoiceLineItemModel.__table__.create)
        await conn.run_sync(PaymentModel.__table__.create)
        await conn.run_sync(RefundModel.__table__.create)
        await conn.run_sync(TenantPaymentConfigModel.__table__.create)
        await conn.run_sync(ProcessedRazorpayEventModel.__table__.create)
        await conn.run_sync(IdempotencyKeyModel.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_tenant_config_round_trip(session):
    """Test TenantPaymentConfigModel round-trip on SQLite with parent tenant."""
    from auth.infrastructure.models import TenantModel

    # Insert parent tenant first (required for FK)
    tid = uuid4()
    session.add(TenantModel(
        id=tid,
        slug="test-tenant",
        name="Test Tenant",
        primary_contact_email="test@example.com",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ))
    await session.flush()  # ensure tenant is inserted before FK reference

    session.add(TenantPaymentConfigModel(
        tenant_id=tid, razorpay_account_id=None, default_currency="INR",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    await session.commit()
    found = await session.get(TenantPaymentConfigModel, tid)
    assert found is not None
    assert found.default_currency == "INR"
    assert found.razorpay_account_id is None


async def test_invoice_round_trip(session):
    inv = InvoiceModel(
        id=uuid4(), tenant_id=uuid4(), customer_id=uuid4(),
        invoice_number="INV-000001", status="pending",
        subtotal_paise=150000, tax_paise=0, total_paise=150000, currency="INR",
        due_date=date(2026, 9, 1), paid_at=None, description="",
        metadata_={},
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    session.add(inv)
    session.add(InvoiceLineItemModel(
        id=uuid4(), invoice_id=inv.id, description="Lane 4",
        quantity=1, unit_price_paise=150000, total_paise=150000,
    ))
    await session.commit()
    # Use explicit query to load line items (avoiding lazy load issue in async)
    result = await session.execute(
        select(InvoiceModel).where(InvoiceModel.id == inv.id)
    )
    found = result.scalar_one()
    assert found is not None

    # Query line items directly
    result = await session.execute(
        select(InvoiceLineItemModel).where(InvoiceLineItemModel.invoice_id == inv.id)
    )
    line_items = result.scalars().all()
    assert len(line_items) == 1
    assert line_items[0].description == "Lane 4"


async def test_payment_round_trip(session):
    p = PaymentModel(
        id=uuid4(), tenant_id=uuid4(), invoice_id=uuid4(),
        amount_paise=150000, currency="INR", status="pending",
        razorpay_payment_id="pay_test_123",
        razorpay_payment_link_id=None, idempotency_key=None,
        captured_at=None, created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(p)
    await session.commit()
    found = await session.get(PaymentModel, p.id)
    assert found.razorpay_payment_id == "pay_test_123"


async def test_processed_razorpay_event_round_trip(session):
    session.add(ProcessedRazorpayEventModel(
        razorpay_event_id="evt_test_1", tenant_id=uuid4(),
        event_type="payment.captured",
        processed_at=datetime.now(UTC),
    ))
    await session.commit()
    found = await session.get(ProcessedRazorpayEventModel, "evt_test_1")
    assert found.event_type == "payment.captured"
