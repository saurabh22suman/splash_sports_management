"""Tests for devsim_webhook: Razorpay event shape + HMAC signing + HTTP POST."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest

from payments.application.devsim_webhook import (
    build_event,
    post_webhook,
    sign_payload,
)

WEBHOOK_SECRET = "whsec_test_secret"


def test_build_event_payment_captured_shape():
    event = build_event(
        "payment.captured",
        payment_id="pay_dev_abc123",
        amount_paise=150000,
        currency="INR",
        description="Lane 4 booking",
        tenant_id="11111111-1111-1111-1111-111111111111",
        invoice_id="22222222-2222-2222-2222-222222222222",
        payment_link_id="plink_dev_abc",
    )
    assert event["entity"] == "event"
    assert event["event"] == "payment.captured"
    assert event["contains"] == ["payment"]
    assert event["payload"]["payment"]["entity"]["id"] == "pay_dev_abc123"
    assert event["payload"]["payment"]["entity"]["amount"] == 150000
    assert event["payload"]["payment"]["entity"]["currency"] == "INR"
    assert event["payload"]["payment"]["entity"]["status"] == "captured"
    assert event["payload"]["payment"]["entity"]["notes"]["tenant_id"] == (
        "11111111-1111-1111-1111-111111111111"
    )
    assert event["payload"]["payment"]["entity"]["notes"]["invoice_id"] == (
        "22222222-2222-2222-2222-222222222222"
    )
    assert event["payload"]["payment"]["entity"]["notes"]["payment_link_id"] == "plink_dev_abc"
    assert "created_at" in event
    assert isinstance(event["created_at"], int)


def test_build_event_payment_failed_shape():
    event = build_event(
        "payment.failed",
        payment_id="pay_dev_xyz",
        amount_paise=150000,
        currency="INR",
        description="Lane 4 booking",
        tenant_id="11111111-1111-1111-1111-111111111111",
        invoice_id="22222222-2222-2222-2222-222222222222",
        payment_link_id="plink_dev_xyz",
    )
    assert event["event"] == "payment.failed"
    assert event["payload"]["payment"]["entity"]["status"] == "failed"
    assert "error_description" in event["payload"]["payment"]["entity"]


def test_sign_payload_matches_production_format():
    payload = b'{"event":"payment.captured"}'
    sig = sign_payload(payload, secret=WEBHOOK_SECRET)
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    assert sig == expected


@pytest.mark.asyncio
async def test_post_webhook_calls_httpx_with_correct_url_and_headers():
    payload = b'{"event":"payment.captured"}'
    sig = sign_payload(payload, secret=WEBHOOK_SECRET)
    with patch(
        "payments.application.devsim_webhook.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        status = await post_webhook(
            "http://localhost:8000/v1/payments/webhook", payload, signature=sig
        )

    assert status == 200
    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.call_args.kwargs
    assert call_kwargs["content"] == payload
    assert call_kwargs["headers"]["X-Razorpay-Signature"] == sig
    assert call_kwargs["headers"]["Content-Type"] == "application/json"
    assert mock_client.post.call_args.args[0] == "http://localhost:8000/v1/payments/webhook"
