from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401  (register TenantModel with Base.metadata)
from auth.infrastructure.models import TenantModel
from payments.application.events import InvoicePaid, PaymentFailed, RefundIssued
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
        await conn.run_sync(TenantPaymentConfigModel.__table__.create)
        await conn.run_sync(IdempotencyKeyModel.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def make_service(session) -> tuple[PaymentService, MagicMock, MagicMock]:
    events = MagicMock()
    events.publish = AsyncMock()
    provider = MagicMock()
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
    return svc, events, provider


async def _seed_invoice_and_payment(session, status: str = "pending"):
    tid = uuid4()
    cust = uuid4()
    pid = uuid4()
    inv_id = uuid4()
    session.add(
        TenantPaymentConfigModel(
            tenant_id=tid,
            razorpay_account_id=None,
            default_currency="INR",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    inv = InvoiceModel(
        id=inv_id,
        tenant_id=tid,
        customer_id=cust,
        invoice_number="INV-000001",
        status=status,
        subtotal_paise=150000,
        tax_paise=0,
        total_paise=150000,
        currency="INR",
        due_date=date(2026, 9, 1),
        paid_at=None,
        description="",
        metadata_={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(inv)
    session.add(
        InvoiceLineItemModel(
            id=uuid4(),
            invoice_id=inv_id,
            description="x",
            quantity=1,
            unit_price_paise=150000,
            total_paise=150000,
        )
    )
    payment = PaymentModel(
        id=pid,
        tenant_id=tid,
        invoice_id=inv_id,
        amount_paise=150000,
        currency="INR",
        status="pending",
        razorpay_payment_id="pay_test_1",
        razorpay_payment_link_id="plink_test_1",
        idempotency_key=None,
        captured_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(payment)
    await session.commit()
    return tid, inv, payment


async def test_webhook_payment_captured_marks_paid(session):
    tid, inv, payment = await _seed_invoice_and_payment(session)
    svc, events, provider = make_service(session)
    provider.verify_webhook.return_value = {
        "id": "evt_test_1",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_1",
                    "amount": 150000,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {
                        "payment_id": str(payment.id),
                        "invoice_id": str(inv.id),
                        "tenant_id": str(tid),
                    },
                }
            }
        },
    }

    await svc.handle_webhook(raw_payload=b"{}", signature="abc")

    await session.refresh(inv)
    await session.refresh(payment)
    assert inv.status == "paid"
    assert payment.status == "captured"
    assert payment.razorpay_payment_id == "pay_test_1"

    events.publish.assert_awaited_once()
    event = events.publish.await_args.args[0]
    assert isinstance(event, InvoicePaid)
    assert event.amount_paise == 150000


async def test_webhook_dedup_by_event_id(session):
    tid, inv, payment = await _seed_invoice_and_payment(session)
    svc, events, provider = make_service(session)
    provider.verify_webhook.return_value = {
        "id": "evt_test_dup",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_1",
                    "amount": 150000,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {
                        "payment_id": str(payment.id),
                        "invoice_id": str(inv.id),
                        "tenant_id": str(tid),
                    },
                }
            }
        },
    }

    await svc.handle_webhook(raw_payload=b"{}", signature="abc")
    events.publish.reset_mock()

    # Second time: same event id -> no-op, no event re-published
    await svc.handle_webhook(raw_payload=b"{}", signature="abc")
    events.publish.assert_not_awaited()


async def test_webhook_payment_failed(session):
    tid, inv, payment = await _seed_invoice_and_payment(session)
    svc, events, provider = make_service(session)
    provider.verify_webhook.return_value = {
        "id": "evt_fail",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_1",
                    "amount": 150000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed",
                    "notes": {
                        "payment_id": str(payment.id),
                        "invoice_id": str(inv.id),
                        "tenant_id": str(tid),
                    },
                }
            }
        },
    }
    await svc.handle_webhook(raw_payload=b"{}", signature="abc")
    await session.refresh(inv)
    await session.refresh(payment)
    assert inv.status == "failed"
    assert payment.status == "failed"

    event = events.publish.await_args.args[0]
    assert isinstance(event, PaymentFailed)
    assert event.reason == "BAD_REQUEST_ERROR"


async def test_webhook_refund_processed_marks_refund(session):
    tid, inv, payment = await _seed_invoice_and_payment(session, status="paid")
    payment.status = "captured"
    await session.commit()
    # Seed a pending refund with razorpay id
    refund = RefundModel(
        id=uuid4(),
        tenant_id=tid,
        payment_id=payment.id,
        amount_paise=150000,
        currency="INR",
        status="pending",
        razorpay_refund_id="rfnd_test_1",
        reason="customer request",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(refund)
    await session.commit()

    svc, events, provider = make_service(session)
    provider.verify_webhook.return_value = {
        "id": "evt_refund",
        "event": "refund.processed",
        "payload": {
            "refund": {
                "entity": {
                    "id": "rfnd_test_1",
                    "payment_id": "pay_test_1",
                    "amount": 150000,
                    "currency": "INR",
                    "status": "processed",
                }
            }
        },
    }
    await svc.handle_webhook(raw_payload=b"{}", signature="abc")
    await session.refresh(inv)
    await session.refresh(refund)
    assert inv.status == "refunded"
    assert refund.status == "completed"

    event = events.publish.await_args.args[0]
    assert isinstance(event, RefundIssued)
    assert event.amount_paise == 150000
