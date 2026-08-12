"""Build Razorpay-shaped webhook events, HMAC-sign them, POST to the real endpoint.

This module is what makes the dev simulator exercise the production webhook
code path: every event is signed with the same secret the production handler
verifies against, and POSTed over HTTP to /v1/payments/webhook.

Webhook signing format matches the production Razorpay format:
    signature = hex(HMAC_SHA256(webhook_secret, raw_body))
The production webhook handler verifies with the same algorithm — see
`apps/backend/src/payments/application/provider.py` (RazorpayAdapter.verify_webhook).
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Literal

import httpx


def build_event(
    event_type: Literal["payment.captured", "payment.failed"],
    *,
    payment_id: str,
    amount_paise: int,
    currency: str,
    description: str,
    tenant_id: str,
    invoice_id: str,
    payment_link_id: str,
) -> dict:
    """Build a Razorpay-shaped event payload.

    The shape mirrors what the production webhook handler parses
    (`payments.application.webhook_service` — verify against current
    implementation before relying on any field).
    """
    if event_type == "payment.captured":
        status = "captured"
        entity: dict = {
            "id": payment_id,
            "amount": amount_paise,
            "currency": currency,
            "status": status,
            "description": description[:255],
            "notes": {
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "payment_id": payment_id,
                "payment_link_id": payment_link_id,
            },
        }
    elif event_type == "payment.failed":
        status = "failed"
        entity = {
            "id": payment_id,
            "amount": amount_paise,
            "currency": currency,
            "status": status,
            "error_description": "Payment declined by user",
            "error_code": "PAYMENT_DECLINED",
            "description": description[:255],
            "notes": {
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "payment_id": payment_id,
                "payment_link_id": payment_link_id,
            },
        }
    else:
        raise ValueError(f"unsupported event_type: {event_type!r}")

    return {
        "entity": "event",
        "account_id": "acc_dev",
        "event": event_type,
        "contains": ["payment"],
        "payload": {"payment": {"entity": entity}},
        "created_at": int(time.time()),
    }


def sign_payload(payload: bytes, *, secret: str) -> str:
    """Return hex(HMAC_SHA256(secret, payload)).

    This matches the format Razorpay uses and the format the production
    webhook handler verifies against (see `RazorpayAdapter.verify_webhook`).
    """
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def post_webhook(url: str, payload: bytes, *, signature: str) -> int:
    """POST `payload` to `url` with the X-Razorpay-Signature header.

    Returns the HTTP status code from the webhook endpoint.

    Raises:
        httpx.HTTPError: on transport-level failure (connection refused,
            timeout, etc.). The caller (router action handler) is
            responsible for converting this to a 502 user-facing response.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
        )
        return response.status_code
