"""Tests for DevSimAdapter — drop-in PaymentProvider that returns dev URLs."""

from __future__ import annotations

import hashlib
import hmac
from uuid import uuid4

import pytest

from payments.application.devsim_adapter import DevSimAdapter
from payments.application.devsim_state import decode_state
from payments.application.provider import PaymentLinkResult


@pytest.fixture
def adapter() -> DevSimAdapter:
    return DevSimAdapter(
        app_url="http://localhost:5173",
        dev_state_secret="dev-state-secret-32chars-or-more-12345",
        webhook_secret="whsec_test_secret",
    )


def _invoice(amount_paise: int = 150000):
    return {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "customer_id": uuid4(),
        "invoice_number": "INV-000001",
        "description": "Lane 4 booking",
        "line_items": [
            {
                "description": "Lane 4",
                "quantity": 1,
                "unit_price_paise": amount_paise,
                "total_paise": amount_paise,
            }
        ],
        "currency": "INR",
        "total": {"amount_paise": amount_paise, "currency": "INR"},
    }


@pytest.mark.asyncio
async def test_create_payment_link_returns_dev_url_with_signed_state(adapter):
    inv = _invoice()
    result = await adapter.create_payment_link(
        invoice=inv,
        payment_id=uuid4(),
        idempotency_key="key-1",
        success_url="https://app.example/book/pay/abc/return",
        cancel_url="https://app.example/book/pay/abc",
        customer={"name": "Alex", "email": "alex@example.com", "contact": "+919999999999"},
    )
    assert isinstance(result, PaymentLinkResult)
    assert result.short_url.startswith("http://localhost:5173/dev/mock-checkout/")
    assert "?state=" in result.short_url
    assert result.razorpay_payment_link_id.startswith("plink_dev_")
    assert result.razorpay_order_id is None


@pytest.mark.asyncio
async def test_state_payload_includes_invoice_amount_and_currency(adapter):
    inv = _invoice(amount_paise=200000)
    payment_id = uuid4()
    result = await adapter.create_payment_link(
        invoice=inv,
        payment_id=payment_id,
        idempotency_key="key-2",
        success_url="https://app.example/x",
        cancel_url="https://app.example/y",
        customer={"name": "B", "email": "b@x.com", "contact": "+910000000000"},
    )
    # Parse the state JWT
    state_token = result.short_url.split("?state=")[1]
    payload = decode_state(state_token, secret=adapter.dev_state_secret)
    assert payload["amount_paise"] == 200000
    assert payload["currency"] == "INR"
    assert payload["payment_id"] == str(payment_id)
    assert payload["tenant_id"] == str(inv["tenant_id"])
    assert payload["invoice_id"] == str(inv["id"])
    assert payload["payment_link_id"] == result.razorpay_payment_link_id


@pytest.mark.asyncio
async def test_short_url_uses_configured_app_url():
    adapter = DevSimAdapter(
        app_url="https://my-dev.example.com",
        dev_state_secret="dev-state-secret-32chars-or-more-12345",
        webhook_secret="whsec_test_secret",
    )
    result = await adapter.create_payment_link(
        invoice=_invoice(),
        payment_id=uuid4(),
        idempotency_key="k",
        success_url="https://x/y",
        cancel_url="https://x/z",
        customer={"name": "B", "email": "b@x.com", "contact": "+910000000000"},
    )
    assert result.short_url.startswith("https://my-dev.example.com/dev/mock-checkout/")


@pytest.mark.asyncio
async def test_refund_returns_deterministic_id(adapter):
    refund = await adapter.create_refund(
        razorpay_payment_id="pay_dev_abc",
        amount_paise=50000,
        idempotency_key="rk",
    )
    assert refund["id"].startswith("rfnd_dev_")
    assert refund["amount"] == 50000
    assert refund["status"] == "processed"


def test_verify_webhook_uses_real_hmac_signature(adapter):
    payload = b'{"event":"payment.captured"}'
    expected_sig = hmac.new(adapter.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    # Should NOT raise — same code path as RazorpayAdapter
    event = adapter.verify_webhook(payload, expected_sig)
    assert event["event"] == "payment.captured"


def test_verify_webhook_rejects_bad_signature(adapter):
    payload = b'{"event":"payment.captured"}'
    with pytest.raises(Exception):
        adapter.verify_webhook(payload, "bad-signature")
