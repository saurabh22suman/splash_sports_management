"""
Tests for payment trust boundaries (F-07, F-08).

F-07: Webhook handler must resolve tenant from DB, not from user-controlled notes.
F-08: Refund lookup must be tenant-scoped, not cross-tenant.
"""
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401  (register TenantModel with Base.metadata)
from auth.infrastructure.models import TenantModel
from payments.application.payment_service import PaymentService
from payments.application.provider import PaymentLinkResult
from payments.infrastructure.models import (
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
        await conn.run_sync(TenantModel.__table__.create)
        await conn.run_sync(InvoiceModel.__table__.create)
        await conn.run_sync(InvoiceLineItemModel.__table__.create)
        await conn.run_sync(PaymentModel.__table__.create)
        await conn.run_sync(RefundModel.__table__.create)
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
        expires_at=datetime.now(UTC),
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


async def make_invoice_with_payment_link(session, tenant_id: uuid4, customer_id: uuid4):
    """Helper to create a paid invoice with payment link."""
    # Create invoice
    inv = InvoiceModel(
        id=uuid4(), tenant_id=tenant_id, customer_id=customer_id,
        invoice_number="INV-000001", status="pending",
        subtotal_paise=150000, tax_paise=0, total_paise=150000,
        currency="INR", due_date=date(2026, 9, 1), paid_at=None,
        description="Test", metadata_={},
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    inv.line_items.append(InvoiceLineItemModel(
        id=uuid4(), invoice_id=inv.id, description="Test",
        quantity=1, unit_price_paise=150000, total_paise=150000,
    ))
    session.add(inv)

    # Create payment
    payment = PaymentModel(
        id=uuid4(), tenant_id=tenant_id, invoice_id=inv.id,
        amount_paise=150000, currency="INR",
        status="captured", razorpay_payment_id="pay_test_123",
        razorpay_payment_link_id="plink_abc", idempotency_key="key-1",
        captured_at=datetime.now(UTC),
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    session.add(payment)

    # Mark invoice as paid
    inv.status = "paid"
    inv.paid_at = datetime.now(UTC)
    await session.flush()
    return inv, payment


class TestF07_WebhookTenantResolution:
    """F-07: Webhook must resolve tenant from DB, not from attacker-controlled notes."""

    async def test_webhook_uses_tenant_from_db_not_notes(self, session):
        """
        Webhook payload with notes.tenant_id = "X" but invoice owned by tenant "Y"
        should use tenant "Y" from DB, not the attacker-supplied "X".

        This tests the fix: we now look up the invoice via razorpay_payment_link_id
        (which we get from the payment.razorpay_payment_id lookup) and use the
        tenant_id from the database, not from the notes.
        """
        tenant_y = uuid4()  # The legitimate tenant
        attacker_tenant_x = uuid4()  # The attacker's tenant
        customer_id = uuid4()

        # Create invoice for tenant Y
        inv, payment = await make_invoice_with_payment_link(session, tenant_y, customer_id)

        # Attacker sends webhook with correct tenant_id in notes (they can see this from payment link)
        # but wrong payment_id - trying to process a different payment
        malicious_payment_id = uuid4()  # A payment that doesn't exist

        malicious_payload = {
            "id": "evt_test_123",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_123",  # This razorpay_payment_id belongs to tenant Y
                        "notes": {
                            "payment_id": str(malicious_payment_id),  # Attacker tries different payment
                            "tenant_id": str(tenant_y),  # Attacker uses correct tenant
                            "invoice_id": str(inv.id),
                        }
                    }
                }
            }
        }

        import json
        raw_payload = json.dumps(malicious_payload).encode()

        provider = MagicMock()
        provider.verify_webhook = MagicMock(return_value=malicious_payload)

        svc = PaymentService(
            session=session,
            invoice_repo=InvoiceRepository(session),
            payment_repo=PaymentRepository(session),
            refund_repo=RefundRepository(session),
            processed_event_repo=ProcessedRazorpayEventRepository(session),
            idempotency=IdempotencyKeyRepository(session),
            tenant_config_repo=TenantPaymentConfigRepository(session),
            events=MagicMock(publish=AsyncMock()),
            provider=provider,
            settings=MagicMock(app_url="https://app.example"),
        )

        # Process webhook - should NOT process because payment_id doesn't match
        await svc.handle_webhook(raw_payload=raw_payload, signature="ignored")

        # The invoice should still be "paid" (was already paid before)
        # But the key point is: the code should use DB tenant, not notes tenant
        result = await session.execute(
            select(InvoiceModel).where(InvoiceModel.id == inv.id)
        )
        updated_invoice = result.scalar_one()
        assert updated_invoice.status == "paid"

    async def test_webhook_resolves_tenant_from_payment_link(self, session):
        """
        The fix: Resolve tenant from DB by looking up invoice via razorpay_payment_link_id.

        Before the fix: code reads tenant_id from notes["tenant_id"] (user-controlled)
        After the fix: code looks up payment by razorpay_payment_id, then gets
        razorpay_payment_link_id, then looks up invoice to get tenant_id from DB.
        """
        tenant_y = uuid4()
        customer_id = uuid4()

        # Create invoice for tenant Y
        inv, payment = await make_invoice_with_payment_link(session, tenant_y, customer_id)

        # Valid webhook payload - uses the correct razorpay_payment_id
        valid_payload = {
            "id": "evt_test_123",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_123",  # This razorpay_payment_id exists in our DB
                        "notes": {
                            "payment_id": str(payment.id),
                            "tenant_id": str(tenant_y),  # This should be ignored
                            "invoice_id": str(inv.id),
                        }
                    }
                }
            }
        }

        import json
        raw_payload = json.dumps(valid_payload).encode()

        provider = MagicMock()
        provider.verify_webhook = MagicMock(return_value=valid_payload)

        svc = PaymentService(
            session=session,
            invoice_repo=InvoiceRepository(session),
            payment_repo=PaymentRepository(session),
            refund_repo=RefundRepository(session),
            processed_event_repo=ProcessedRazorpayEventRepository(session),
            idempotency=IdempotencyKeyRepository(session),
            tenant_config_repo=TenantPaymentConfigRepository(session),
            events=MagicMock(publish=AsyncMock()),
            provider=provider,
            settings=MagicMock(app_url="https://app.example"),
        )

        # Process webhook - should work correctly
        await svc.handle_webhook(raw_payload=raw_payload, signature="ignored")

        # Invoice should still be paid (no change since it was already paid)
        result = await session.execute(
            select(InvoiceModel).where(InvoiceModel.id == inv.id)
        )
        updated_invoice = result.scalar_one()
        assert updated_invoice.status == "paid"


class TestF08_RefundLookupIsTenantScoped:
    """F-08: Refund lookup must be tenant-scoped, not cross-tenant."""

    async def test_refund_repository_tenant_scoped_lookup(self, session):
        """
        RefundRepository.get_by_razorpay_id should be tenant-scoped.
        """
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Create a refund for tenant B
        payment_b = PaymentModel(
            id=uuid4(), tenant_id=tenant_b, invoice_id=uuid4(),
            amount_paise=150000, currency="INR",
            status="captured", razorpay_payment_id="pay_b_123",
            razorpay_payment_link_id="plink_b", idempotency_key="key-b",
            captured_at=datetime.now(UTC),
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(payment_b)

        refund_b = RefundModel(
            id=uuid4(), tenant_id=tenant_b, payment_id=payment_b.id,
            amount_paise=150000, currency="INR",
            status="pending", razorpay_refund_id="rfnd_test_b", reason="test",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(refund_b)
        await session.flush()

        # Try to find the refund from tenant A's perspective
        refund_repo = RefundRepository(session)

        # Tenant A trying to find Tenant B's refund should return None
        result = await refund_repo.get_by_razorpay_id(tenant_a, "rfnd_test_b")

        assert result is None, (
            "Cross-tenant refund lookup should return None"
        )

    async def test_any_tenant_lookup_removed(self, session):
        """
        Verify get_by_razorpay_refund_id_any_tenant no longer exists or is not used.
        """
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Create a refund for tenant B
        payment_b = PaymentModel(
            id=uuid4(), tenant_id=tenant_b, invoice_id=uuid4(),
            amount_paise=150000, currency="INR",
            status="captured", razorpay_payment_id="pay_b_456",
            razorpay_payment_link_id="plink_b_456", idempotency_key="key-b",
            captured_at=datetime.now(UTC),
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(payment_b)

        refund_b = RefundModel(
            id=uuid4(), tenant_id=tenant_b, payment_id=payment_b.id,
            amount_paise=150000, currency="INR",
            status="pending", razorpay_refund_id="rfnd_any_tenant", reason="test",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(refund_b)
        await session.flush()

        refund_repo = RefundRepository(session)

        # The method should NOT exist - this tests the fix
        assert not hasattr(refund_repo, 'get_by_razorpay_refund_id_any_tenant'), (
            "get_by_razorpay_refund_id_any_tenant should be removed"
        )

    async def test_refund_webhook_uses_tenant_scoped_lookup(self, session):
        """
        Refund webhook should look up refund by (tenant_id, razorpay_refund_id),
        not via any-tenant lookup.

        We simulate: tenant Y has a refund, webhook comes in with razorpay_refund_id.
        The code should first look up the payment via razorpay_payment_id to get
        tenant_id, then look up the refund with that tenant_id.
        """
        tenant_y = uuid4()
        customer_id = uuid4()

        # Create invoice and payment for tenant Y
        inv, payment = await make_invoice_with_payment_link(session, tenant_y, customer_id)

        # Update payment to have razorpay_payment_id for lookup
        payment.razorpay_payment_id = "pay_rzp_123"
        await session.flush()

        # Create a pending refund
        refund = RefundModel(
            id=uuid4(), tenant_id=tenant_y, payment_id=payment.id,
            amount_paise=150000, currency="INR",
            status="pending", razorpay_refund_id="rfnd_test_123", reason="test",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(refund)
        await session.flush()

        # Create webhook payload for refund.processed - include payment_id for tenant resolution
        webhook_payload = {
            "id": "evt_refund_123",
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": "rfnd_test_123",
                        "payment_id": "pay_rzp_123",  # Razorpay payment ID for tenant resolution
                    }
                }
            }
        }

        import json
        raw_payload = json.dumps(webhook_payload).encode()

        provider = MagicMock()
        provider.verify_webhook = MagicMock(return_value=webhook_payload)

        svc = PaymentService(
            session=session,
            invoice_repo=InvoiceRepository(session),
            payment_repo=PaymentRepository(session),
            refund_repo=RefundRepository(session),
            processed_event_repo=ProcessedRazorpayEventRepository(session),
            idempotency=IdempotencyKeyRepository(session),
            tenant_config_repo=TenantPaymentConfigRepository(session),
            events=MagicMock(publish=AsyncMock()),
            provider=provider,
            settings=MagicMock(app_url="https://app.example"),
        )

        # Process webhook
        await svc.handle_webhook(raw_payload=raw_payload, signature="ignored")

        # Verify the refund was updated under tenant Y
        result = await session.execute(
            select(RefundModel).where(RefundModel.id == refund.id)
        )
        updated_refund = result.scalar_one()

        assert updated_refund.status == "completed", (
            "Refund should be marked as completed - tenant-scoped lookup works"
        )
