from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from common.domain.exceptions import Conflict
from payments.domain.value_objects import InvoiceStatus, Money, PaymentStatus, RefundStatus

if TYPE_CHECKING:
    from uuid import UUID


@dataclass
class LineItem:
    id: UUID
    description: str
    quantity: int
    unit_price: Money
    total: Money


@dataclass
class Invoice:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str
    status: InvoiceStatus
    subtotal: Money
    tax: Money
    total: Money
    due_date: date
    paid_at: datetime | None
    description: str
    line_items: list[LineItem]
    created_at: datetime
    updated_at: datetime

    def can_pay(self) -> bool:
        return self.status in (InvoiceStatus.DRAFT, InvoiceStatus.PENDING)

    def can_refund(self) -> bool:
        return self.status == InvoiceStatus.PAID

    def mark_paid(self, when: datetime) -> None:
        if self.status != InvoiceStatus.PENDING:
            raise Conflict("Invoice is not pending payment", details={"status": self.status.value})
        self.status = InvoiceStatus.PAID
        self.paid_at = when
        self.updated_at = when

    def mark_failed(self) -> None:
        if self.status not in (InvoiceStatus.PENDING, InvoiceStatus.DRAFT):
            raise Conflict(
                "Invoice cannot transition to failed",
                details={"status": self.status.value},
            )
        self.status = InvoiceStatus.FAILED
        self.updated_at = datetime.now(UTC)

    def mark_refunded(self, when: datetime) -> None:
        if self.status != InvoiceStatus.PAID:
            raise Conflict(
                "Only paid invoices can be refunded",
                details={"status": self.status.value},
            )
        self.status = InvoiceStatus.REFUNDED
        self.updated_at = when


@dataclass
class Payment:
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    amount: Money
    status: PaymentStatus
    razorpay_payment_id: str | None
    razorpay_payment_link_id: str | None
    idempotency_key: str | None
    captured_at: datetime | None
    created_at: datetime

    def mark_captured(self, when: datetime) -> None:
        if self.status != PaymentStatus.PENDING:
            raise Conflict(
                "Payment cannot transition to captured",
                details={"status": self.status.value},
            )
        self.status = PaymentStatus.CAPTURED
        self.captured_at = when


@dataclass
class Refund:
    id: UUID
    tenant_id: UUID
    payment_id: UUID
    amount: Money
    status: RefundStatus
    razorpay_refund_id: str | None
    reason: str
    created_at: datetime


@dataclass
class TenantPaymentConfig:
    tenant_id: UUID
    razorpay_account_id: str | None
    default_currency: str
    created_at: datetime
    updated_at: datetime
