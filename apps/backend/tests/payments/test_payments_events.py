# apps/backend/tests/payments/test_payments_events.py
from uuid import uuid4

from payments.application.events import (
    InvoiceCreated,
    InvoicePaid,
    PaymentFailed,
    RefundIssued,
)


def test_invoice_created_carries_payload():
    e = InvoiceCreated(
        invoice_id=uuid4(),
        tenant_id=uuid4(),
        customer_id=uuid4(),
        total_paise=1500,
        currency="INR",
    )
    assert e.total_paise == 1500
    assert e.currency == "INR"
    assert e.event_id is not None


def test_invoice_paid_carries_payload():
    e = InvoicePaid(
        invoice_id=uuid4(),
        payment_id=uuid4(),
        tenant_id=uuid4(),
        customer_id=uuid4(),
        amount_paise=1500,
        currency="INR",
    )
    assert e.amount_paise == 1500


def test_payment_failed_carries_reason():
    e = PaymentFailed(
        invoice_id=uuid4(),
        payment_id=uuid4(),
        tenant_id=uuid4(),
        customer_id=uuid4(),
        reason="card_declined",
    )
    assert e.reason == "card_declined"


def test_refund_issued_carries_payload():
    e = RefundIssued(
        invoice_id=uuid4(),
        payment_id=uuid4(),
        refund_id=uuid4(),
        tenant_id=uuid4(),
        customer_id=uuid4(),
        amount_paise=1500,
        currency="INR",
    )
    assert e.refund_id is not None
