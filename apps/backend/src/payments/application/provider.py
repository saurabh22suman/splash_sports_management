from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PaymentLinkResult:
    # https://stub.test/rzp/<id> in NullAdapter; https://rzp.io/i/<short> in prod
    short_url: str
    # "plink_XXXX" — used as the unique backstop on payment rows
    razorpay_payment_link_id: str
    # None for Payment Links flow (order is auto-created on capture)
    razorpay_order_id: str | None
    expires_at: datetime


class PaymentProvider(Protocol):
    async def create_payment_link(
        self,
        *,
        invoice: dict,
        payment_id: UUID,
        idempotency_key: str,
        success_url: str,
        cancel_url: str,
        customer: dict,
    ) -> PaymentLinkResult: ...

    async def fetch_payment(self, razorpay_payment_id: str) -> dict: ...

    async def create_refund(
        self,
        *,
        razorpay_payment_id: str,
        amount_paise: int,
        idempotency_key: str,
    ) -> dict: ...

    def verify_webhook(self, payload: bytes, signature: str) -> dict: ...


class NullAdapter:
    """Test/stub adapter. Returns deterministic fake values; no network calls."""

    async def create_payment_link(
        self,
        *,
        invoice,
        payment_id,
        idempotency_key,
        success_url,
        cancel_url,
        customer,
    ) -> PaymentLinkResult:
        lid = f"plink_test_{uuid4().hex[:16]}"
        return PaymentLinkResult(
            short_url=f"https://stub.test/rzp/{lid}",
            razorpay_payment_link_id=lid,
            razorpay_order_id=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

    async def fetch_payment(
        self, razorpay_payment_id: str
    ) -> dict:
        return {"id": razorpay_payment_id, "status": "captured", "amount": 150000}

    async def create_refund(
        self,
        *,
        razorpay_payment_id,
        amount_paise,
        idempotency_key,
    ) -> dict:
        return {
            "id": f"rfnd_test_{uuid4().hex[:16]}",
            "amount": amount_paise,
            "status": "processed",
        }

    def verify_webhook(
        self, payload: bytes, signature: str
    ) -> dict:
        return json.loads(payload)
