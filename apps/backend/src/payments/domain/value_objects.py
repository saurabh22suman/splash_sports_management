from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CAPTURED = "captured"
    FAILED = "failed"


class RefundStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Money:
    amount_paise: int
    currency: str

    def __post_init__(self) -> None:
        if self.amount_paise < 0:
            raise ValueError(f"amount_paise must be >= 0, got {self.amount_paise}")
        if not isinstance(self.currency, str) or len(self.currency) != 3:
            raise ValueError(f"currency must be a 3-char ISO-4217 code, got {self.currency!r}")
