from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import razorpay

from common.domain.exceptions import Validation


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


class RazorpayAdapter:
    """Production adapter. Wraps the official `razorpay` SDK.
    All SDK calls are sync; we wrap them in asyncio.to_thread.
    """

    def __init__(self, *, key_id: str, key_secret: str, webhook_secret: str) -> None:
        self._client = razorpay.Client(auth=(key_id, key_secret))
        self._webhook_secret = webhook_secret

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
        if invoice.get("currency") != "INR":
            raise Validation("Only INR currency is supported in v1")
        amount_paise = sum(li["total_paise"] for li in invoice["line_items"])
        description = "; ".join(li["description"] for li in invoice["line_items"])
        plink = await asyncio.to_thread(
            self._client.payment_link.create,
            {
                "amount": amount_paise,
                "currency": invoice["currency"],
                "accept_partial": False,
                "description": description[:255],
                "reference_id": str(payment_id),
                "customer": {
                    "name": customer.get("name", "Customer"),
                    "email": customer.get("email", ""),
                    "contact": customer.get("contact", ""),
                },
                "notify": {"sms": False, "email": False},
                "reminder_enable": False,
                "notes": {
                    "tenant_id": str(invoice.get("tenant_id", "")),
                    "invoice_id": str(invoice["id"]),
                    "payment_id": str(payment_id),
                },
                "callback_url": success_url,
                "callback_method": "get",
                "cancel_url": cancel_url,
            },
            headers={"Idempotency-Key": idempotency_key},
        )
        expire_by_timestamp = plink.get("expire_by")
        if expire_by_timestamp is not None:
            expires_at = datetime.fromtimestamp(int(expire_by_timestamp), tz=UTC)
        else:
            expires_at = datetime.now(UTC) + timedelta(hours=24)
        return PaymentLinkResult(
            short_url=plink["short_url"],
            razorpay_payment_link_id=plink["id"],
            razorpay_order_id=None,
            expires_at=expires_at,
        )

    async def fetch_payment(self, razorpay_payment_id: str) -> dict:
        payment = await asyncio.to_thread(self._client.payment.fetch, razorpay_payment_id)
        return payment

    async def create_refund(
        self,
        *,
        razorpay_payment_id: str,
        amount_paise: int,
        idempotency_key: str,
    ) -> dict:
        refund = await asyncio.to_thread(
            self._client.payment.refund,
            razorpay_payment_id,
            {"amount": amount_paise},
            headers={"Idempotency-Key": idempotency_key},
        )
        return {"id": refund["id"], "amount": refund["amount"], "status": refund["status"]}

    def verify_webhook(self, payload: bytes, signature: str) -> dict:
        # Raises razorpay.errors.SignatureVerificationError on mismatch.
        self._client.utility.verify_webhook_signature(
            payload.decode(), signature, self._webhook_secret
        )
        return json.loads(payload.decode())
