from uuid import uuid4

from payments.application.provider import NullAdapter, PaymentLinkResult


async def test_null_adapter_create_payment_link_returns_short_url():
    adapter = NullAdapter()
    inv = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "customer_id": uuid4(),
        "invoice_number": "INV-000001",
        "description": "Lane 4 booking",
        "line_items": [
            {
                "description": "Lane 4",
                "quantity": 1,
                "unit_price_paise": 150000,
                "total_paise": 150000,
            }
        ],
        "currency": "INR",
        "total": {"amount_paise": 150000, "currency": "INR"},
    }
    result = await adapter.create_payment_link(
        invoice=inv, payment_id=uuid4(), idempotency_key="key-1",
        success_url="https://app.example/book/pay/abc/return",
        cancel_url="https://app.example/book/pay/abc",
        customer={"name": "Alex", "email": "alex@example.com", "contact": "+919999999999"},
    )
    assert isinstance(result, PaymentLinkResult)
    assert result.short_url.startswith("https://stub.test/rzp/")
    assert result.razorpay_payment_link_id.startswith("plink_test_")


async def test_null_adapter_create_refund():
    adapter = NullAdapter()
    refund = await adapter.create_refund(
        razorpay_payment_id="pay_test_1", amount_paise=150000, idempotency_key="k",
    )
    assert refund["id"].startswith("rfnd_test_")
    assert refund["amount"] == 150000


def test_null_adapter_verify_webhook_accepts_anything():
    adapter = NullAdapter()
    payload = b'{"id":"evt_test_1","event":"payment.captured"}'
    event = adapter.verify_webhook(payload, "any-sig")
    assert event["event"] == "payment.captured"
