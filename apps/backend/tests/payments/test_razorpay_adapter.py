import hashlib
import hmac
import json
import uuid

import pytest
import responses
from razorpay.errors import SignatureVerificationError

from common.domain.exceptions import Validation
from payments.application.provider import RazorpayAdapter

RAZORPAY_BASE = "https://api.razorpay.com/v1"


def _make_adapter() -> RazorpayAdapter:
    return RazorpayAdapter(
        key_id="rzp_test_xxx",
        key_secret="test_secret",
        webhook_secret="whsec_test_secret",
    )


def _plink_response(
    plink_id: str,
    payment_id: str,
    short_url: str,
    expire_by: int | None = None,
) -> dict:
    resp = {
        "id": plink_id,
        "entity": "payment_link",
        "amount": 150000,
        "currency": "INR",
        "status": "created",
        "short_url": short_url,
        "payments": [
            {
                "id": payment_id,
                "entity": "payment",
                "status": "captured",
                "amount": 150000,
            }
        ],
    }
    if expire_by is not None:
        resp["expire_by"] = expire_by
    return resp


async def test_razorpay_adapter_create_payment_link_sends_correct_payload():
    payment_id = uuid.uuid4()
    plink_id = "plink_test_abc123"
    payment_rzp_id = "pay_test_xyz789"
    inv = {
        "id": uuid.uuid4(),
        "customer_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "line_items": [
            {
                "description": "Lane 4 - 1 hr",
                "quantity": 1,
                "unit_price_paise": 150000,
                "total_paise": 150000,
            }
        ],
        "currency": "INR",
    }
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            f"{RAZORPAY_BASE}/payment_links",
            json=_plink_response(
                plink_id,
                payment_rzp_id,
                "https://rzp.io/i/abc",
                expire_by=1735689600,
            ),
            status=200,
        )
        result = await _make_adapter().create_payment_link(
            invoice=inv,
            payment_id=payment_id,
            idempotency_key="key-1",
            success_url="https://app.example/return?payment_link_id={PAYMENT_LINK_ID}",
            cancel_url="https://app.example/cancel",
            customer={
                "name": "Alex",
                "email": "alex@example.com",
                "contact": "+919999999999",
            },
        )
        sent_body = json.loads(rsps.calls[0].request.body)
        # Must check header inside context manager - calls are cleared on exit
        idempotency_key_sent = rsps.calls[0].request.headers["Idempotency-Key"]

    assert result.short_url == "https://rzp.io/i/abc"
    assert result.razorpay_payment_link_id == plink_id
    assert sent_body["amount"] == 150000
    assert sent_body["currency"] == "INR"
    assert sent_body["reference_id"] == str(payment_id)
    assert sent_body["notes"]["invoice_id"] == str(inv["id"])
    assert sent_body["notes"]["payment_id"] == str(payment_id)
    assert sent_body["notes"]["tenant_id"] == str(inv["tenant_id"])
    assert sent_body["customer"]["name"] == "Alex"
    assert sent_body["customer"]["email"] == "alex@example.com"
    assert sent_body["customer"]["contact"] == "+919999999999"
    assert idempotency_key_sent == "key-1"


async def test_razorpay_adapter_create_refund_calls_payment_refund():
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            f"{RAZORPAY_BASE}/payments/pay_test_xyz789/refund",
            json={
                "id": "rfnd_test_001",
                "entity": "refund",
                "amount": 150000,
                "status": "processed",
            },
            status=200,
        )
        refund = await _make_adapter().create_refund(
            razorpay_payment_id="pay_test_xyz789",
            amount_paise=150000,
            idempotency_key="k1",
        )
        sent_body = json.loads(rsps.calls[0].request.body)
        # Must check header inside context manager - calls are cleared on exit
        idempotency_key_sent = rsps.calls[0].request.headers["Idempotency-Key"]

    assert refund["id"] == "rfnd_test_001"
    assert refund["status"] == "processed"
    assert refund["amount"] == 150000
    assert sent_body["amount"] == 150000
    assert idempotency_key_sent == "k1"


def test_razorpay_adapter_verify_webhook_signature():
    payload = b'{"event":"payment.captured"}'
    secret = "whsec_test_secret"  # noqa: S105
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    evt = _make_adapter().verify_webhook(payload, sig)
    assert evt["event"] == "payment.captured"


def test_razorpay_adapter_verify_webhook_rejects_bad_signature():
    with pytest.raises(SignatureVerificationError):
        _make_adapter().verify_webhook(b'{"event":"x"}', "badsig")


async def test_razorpay_adapter_rejects_non_inr_currency():
    inv = {
        "id": uuid.uuid4(),
        "customer_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "line_items": [
            {
                "description": "Test",
                "quantity": 1,
                "unit_price_paise": 150000,
                "total_paise": 150000,
            }
        ],
        "currency": "USD",  # Not INR
    }
    with pytest.raises(Validation) as exc_info:
        await _make_adapter().create_payment_link(
            invoice=inv,
            payment_id=uuid.uuid4(),
            idempotency_key="key-1",
            success_url="https://app.example/return",
            cancel_url="https://app.example/cancel",
            customer={"name": "Test"},
        )
    assert "INR" in str(exc_info.value)
