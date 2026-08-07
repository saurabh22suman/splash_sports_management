import pytest
from datetime import date, datetime, timezone
from uuid import uuid4
from payments.domain.entities import Invoice, LineItem, Payment, Refund, TenantPaymentConfig
from payments.domain.value_objects import InvoiceStatus, Money, PaymentStatus, RefundStatus
from common.domain.exceptions import Conflict

UTC = timezone.utc

def make_line_item(total_paise: int = 150000) -> LineItem:
    return LineItem(id=uuid4(), description="Lane 4", quantity=1, unit_price=Money(total_paise, "INR"), total=Money(total_paise, "INR"))

def make_invoice(status: InvoiceStatus = InvoiceStatus.PENDING) -> Invoice:
    return Invoice(
        id=uuid4(),
        tenant_id=uuid4(),
        customer_id=uuid4(),
        invoice_number="INV-000001",
        status=status,
        subtotal=Money(150000, "INR"),
        tax=Money(0, "INR"),
        total=Money(150000, "INR"),
        due_date=date(2026, 9, 1),
        paid_at=None,
        description="",
        line_items=[make_line_item()],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

class TestInvoiceInvariants:
    def test_can_pay_when_pending(self):
        assert make_invoice(InvoiceStatus.PENDING).can_pay() is True

    def test_cannot_pay_when_paid(self):
        assert make_invoice(InvoiceStatus.PAID).can_pay() is False

    def test_can_refund_when_paid(self):
        assert make_invoice(InvoiceStatus.PAID).can_refund() is True

    def test_cannot_refund_when_pending(self):
        assert make_invoice(InvoiceStatus.PENDING).can_refund() is False

    def test_mark_paid_from_pending_succeeds(self):
        inv = make_invoice(InvoiceStatus.PENDING)
        when = datetime.now(UTC)
        inv.mark_paid(when)
        assert inv.status == InvoiceStatus.PAID
        assert inv.paid_at == when

    def test_mark_paid_from_paid_raises(self):
        inv = make_invoice(InvoiceStatus.PAID)
        with pytest.raises(Conflict):
            inv.mark_paid(datetime.now(UTC))

    def test_mark_failed_from_pending_succeeds(self):
        inv = make_invoice(InvoiceStatus.PENDING)
        inv.mark_failed()
        assert inv.status == InvoiceStatus.FAILED

    def test_mark_refunded_from_paid_succeeds(self):
        inv = make_invoice(InvoiceStatus.PAID)
        inv.mark_refunded(datetime.now(UTC))
        assert inv.status == InvoiceStatus.REFUNDED

    def test_mark_refunded_from_pending_raises(self):
        inv = make_invoice(InvoiceStatus.PENDING)
        with pytest.raises(Conflict):
            inv.mark_refunded(datetime.now(UTC))

class TestPaymentInvariants:
    def test_mark_captured_from_pending(self):
        p = Payment(id=uuid4(), tenant_id=uuid4(), invoice_id=uuid4(),
                   amount=Money(150000, "INR"), status=PaymentStatus.PENDING,
                   razorpay_payment_id=None, razorpay_payment_link_id=None,
                   idempotency_key=None, captured_at=None, created_at=datetime.now(UTC))
        p.mark_captured(datetime.now(UTC))
        assert p.status == PaymentStatus.CAPTURED

    def test_mark_captured_from_captured_raises(self):
        p = Payment(id=uuid4(), tenant_id=uuid4(), invoice_id=uuid4(),
                   amount=Money(150000, "INR"), status=PaymentStatus.CAPTURED,
                   razorpay_payment_id=None, razorpay_payment_link_id=None,
                   idempotency_key=None, captured_at=datetime.now(UTC), created_at=datetime.now(UTC))
        with pytest.raises(Conflict):
            p.mark_captured(datetime.now(UTC))
