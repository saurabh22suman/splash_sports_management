from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from common.application.events import DomainEvent

if TYPE_CHECKING:
    from uuid import UUID


@dataclass(frozen=True)
class InvoiceCreated(DomainEvent):
    invoice_id: UUID | None = field(default=None)
    customer_id: UUID | None = field(default=None)
    total_paise: int = 0
    currency: str = "INR"


@dataclass(frozen=True)
class InvoicePaid(DomainEvent):
    invoice_id: UUID | None = field(default=None)
    payment_id: UUID | None = field(default=None)
    customer_id: UUID | None = field(default=None)
    amount_paise: int = 0
    currency: str = "INR"


@dataclass(frozen=True)
class PaymentFailed(DomainEvent):
    invoice_id: UUID | None = field(default=None)
    payment_id: UUID | None = field(default=None)
    customer_id: UUID | None = field(default=None)
    reason: str = ""


@dataclass(frozen=True)
class RefundIssued(DomainEvent):
    invoice_id: UUID | None = field(default=None)
    payment_id: UUID | None = field(default=None)
    refund_id: UUID | None = field(default=None)
    customer_id: UUID | None = field(default=None)
    amount_paise: int = 0
    currency: str = "INR"
