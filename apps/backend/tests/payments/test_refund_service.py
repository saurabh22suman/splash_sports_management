from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401  (register TenantModel with Base.metadata)
from auth.infrastructure.models import TenantModel
from common.domain.exceptions import Conflict
from payments.application.payment_service import PaymentService
from payments.infrastructure.models import (
    IdempotencyKeyModel,
    InvoiceLineItemModel,
    InvoiceModel,
    PaymentModel,
    ProcessedRazorpayEventModel,
    RefundModel,
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
        await conn.run_sync(RefundModel.__table__.create)
        await conn.run_sync(ProcessedRazorpayEventModel.__table__.create)
        await conn.run_sync(IdempotencyKeyModel.__table__.create)
        await conn.run_sync(TenantPaymentConfigModel.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def make_service(session) -> tuple[PaymentService, MagicMock]:
    events = MagicMock()
    events.publish = AsyncMock()
    provider = MagicMock()
    svc = PaymentService(
        session=session, invoice_repo=InvoiceRepository(session),
        payment_repo=PaymentRepository(session), refund_repo=RefundRepository(session),
        processed_event_repo=ProcessedRazorpayEventRepository(session),
        idempotency=IdempotencyKeyRepository(session),
        tenant_config_repo=TenantPaymentConfigRepository(session),
        events=events, provider=provider,
        settings=MagicMock(app_url="https://app.example"),
    )
    return svc, events


async def test_refund_invoice_creates_razorpay_refund(session):
    tid = uuid4()
    cust = uuid4()
    inv_id = uuid4()
    pay_id = uuid4()
    session.add(TenantPaymentConfigModel(
        tenant_id=tid, razorpay_account_id=None, default_currency="INR",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    inv = InvoiceModel(id=inv_id, tenant_id=tid, customer_id=cust, invoice_number="INV-1",
                       status="paid", subtotal_paise=150000, tax_paise=0, total_paise=150000,
                       currency="INR", due_date=date(2026, 9, 1), paid_at=datetime.now(UTC),
                       description="", metadata_={},
                       created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    session.add(inv)
    payment = PaymentModel(id=pay_id, tenant_id=tid, invoice_id=inv_id, amount_paise=150000,
                           currency="INR", status="captured",
                           razorpay_payment_id="pay_test_1",
                           razorpay_payment_link_id="plink_test_1",
                           idempotency_key=None, captured_at=datetime.now(UTC),
                           created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    session.add(payment)
    await session.commit()

    svc, _ = make_service(session)
    svc._provider.create_refund = AsyncMock(
        return_value={"id": "rfnd_test_99", "amount": 150000, "status": "processed"}
    )

    refund = await svc.refund_invoice(
        tenant_id=tid, invoice_id=inv_id, reason="customer_request", idempotency_key="k1",
    )
    assert refund.razorpay_refund_id == "rfnd_test_99"
    assert refund.status == "pending"  # webhook will flip to completed
    assert refund.amount_paise == 150000


async def test_refund_invoice_409_on_pending(session):
    tid = uuid4()
    cust = uuid4()
    inv_id = uuid4()
    session.add(TenantPaymentConfigModel(
        tenant_id=tid, razorpay_account_id=None, default_currency="INR",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    inv = InvoiceModel(id=inv_id, tenant_id=tid, customer_id=cust, invoice_number="INV-2",
                       status="pending", subtotal_paise=150000, tax_paise=0, total_paise=150000,
                       currency="INR", due_date=date(2026, 9, 1), paid_at=None,
                       description="", metadata_={},
                       created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    session.add(inv)
    await session.commit()

    svc, _ = make_service(session)
    with pytest.raises(Conflict):
        await svc.refund_invoice(tenant_id=tid, invoice_id=inv_id, reason="x", idempotency_key="k")


async def test_list_invoices_filters_by_customer(session):
    tid = uuid4()
    cust_a = uuid4()
    cust_b = uuid4()
    session.add(TenantPaymentConfigModel(
        tenant_id=tid, razorpay_account_id=None, default_currency="INR",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    for cust in (cust_a, cust_b):
        inv = InvoiceModel(
            id=uuid4(), tenant_id=tid, customer_id=cust,
            invoice_number=f"INV-{cust.hex[:4]}",
            status="pending", subtotal_paise=150000, tax_paise=0, total_paise=150000,
            currency="INR", due_date=date(2026, 9, 1), paid_at=None,
            description="", metadata_={},
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        session.add(inv)
    await session.commit()

    svc, _ = make_service(session)
    only_a = await svc.list_invoices(tenant_id=tid, viewer_customer_id=cust_a)
    assert len(only_a) == 1
    assert only_a[0].customer_id == cust_a
