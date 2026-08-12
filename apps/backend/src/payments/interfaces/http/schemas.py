"""Pydantic schemas for payments HTTP endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LineItemInput(BaseModel):
    """Input schema for a line item on an invoice."""

    description: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(..., gt=0)
    unit_price_paise: int = Field(..., ge=0)


class LineItemResponse(BaseModel):
    """Response schema for a line item on an invoice."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    quantity: int
    unit_price_paise: int
    total_paise: int


class InvoiceCreateRequest(BaseModel):
    """Request schema for creating an invoice."""

    customer_id: UUID
    line_items: list[LineItemInput] = Field(..., min_length=1)
    description: str = ""
    due_date: date


class InvoiceResponse(BaseModel):
    """Response schema for an invoice."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str
    status: Literal["draft", "pending", "paid", "failed", "cancelled", "refunded"]
    subtotal_paise: int
    tax_paise: int
    total_paise: int
    currency: str
    due_date: date
    paid_at: datetime | None
    description: str
    line_items: list[LineItemResponse]
    created_at: datetime
    updated_at: datetime


class PaymentLinkResponse(BaseModel):
    """Response schema for a payment link."""

    short_url: str
    razorpay_payment_link_id: str
    expires_at: datetime | None


class RefundRequest(BaseModel):
    """Request schema for requesting a refund."""

    reason: str = Field(..., min_length=1, max_length=500)


class RefundResponse(BaseModel):
    """Response schema for a refund."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    amount_paise: int
    currency: str
    status: Literal["pending", "completed", "failed"]
    reason: str
    razorpay_refund_id: str | None
    created_at: datetime
