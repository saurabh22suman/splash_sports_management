"""DevSimAdapter — PaymentProvider implementation that returns dev checkout URLs.

Satisfies the same Protocol as NullAdapter and RazorpayAdapter (see
`apps/backend/src/payments/application/provider.py`). Drop-in replacement.

Differences from NullAdapter:
- short_url points at the backend's own /dev/mock-checkout/ route (real URL)
- state is encoded as a signed JWT in the URL (real state, not a fake stub)
- verify_webhook uses real HMAC verification (same as RazorpayAdapter)

Differences from RazorpayAdapter:
- No SDK calls. No external network. No idempotency-key header (we mint
  the link id locally).
- short_url is a backend path; redirect happens server-side via the
  simulator router (Task 5).
"""
from __future__ import annotations

import json
from typing import Protocol
from uuid import UUID, uuid4

from payments.application.devsim_state import encode_state

# Importing from the same module as NullAdapter/RazorpayAdapter to share
# the dataclass and Protocol definitions.
from payments.application.provider import (  # noqa: F401  (re-exported via type)
    PaymentLinkResult,
    PaymentProvider,
)


class DevSimAdapter:
    """Dev-only PaymentProvider. Routes checkout through the backend's own
    /dev/mock-checkout router (mounted only when DEV_PAYMENT_SIMULATOR_ENABLED).
    """

    def __init__(
        self,
        *,
        app_url: str,
        dev_state_secret: str,
        webhook_secret: str,
    ) -> None:
        self.app_url = app_url.rstrip("/")
        self.dev_state_secret = dev_state_secret
        self.webhook_secret = webhook_secret

    async def create_payment_link(
        self,
        *,
        invoice: dict,
        payment_id: UUID,
        idempotency_key: str,
        success_url: str,
        cancel_url: str,
        customer: dict,
    ) -> PaymentLinkResult:
        link_id = f"plink_dev_{uuid4().hex[:16]}"
        from datetime import UTC, datetime, timedelta

        amount_paise = invoice["total"]["amount_paise"]
        currency = invoice["total"]["currency"]
        line_items = invoice.get("line_items", [])

        state_token = encode_state(
            {
                "tenant_id": str(invoice["tenant_id"]),
                "invoice_id": str(invoice["id"]),
                "payment_id": str(payment_id),
                "payment_link_id": link_id,
                "amount_paise": amount_paise,
                "currency": currency,
                "line_items": line_items,
            },
            secret=self.dev_state_secret,
            ttl_seconds=86_400,
        )

        short_url = f"{self.app_url}/dev/mock-checkout/{link_id}?state={state_token}"
        return PaymentLinkResult(
            short_url=short_url,
            razorpay_payment_link_id=link_id,
            razorpay_order_id=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

    async def fetch_payment(self, razorpay_payment_id: str) -> dict:
        # The dev simulator never stores payment state — callers should
        # use the webhook path to learn payment status.
        return {
            "id": razorpay_payment_id,
            "status": "captured",
            "amount": 0,
            "currency": "INR",
        }

    async def create_refund(
        self,
        *,
        razorpay_payment_id: str,
        amount_paise: int,
        idempotency_key: str,
    ) -> dict:
        return {
            "id": f"rfnd_dev_{uuid4().hex[:16]}",
            "amount": amount_paise,
            "status": "processed",
        }

    def verify_webhook(self, payload: bytes, signature: str) -> dict:
        # Same HMAC-SHA256 verification format as RazorpayAdapter —
        # exercise the real signature path so the simulator is a faithful
        # substitute for the real provider.
        import hashlib
        import hmac

        expected = hmac.new(
            self.webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("invalid webhook signature")
        return json.loads(payload.decode())
