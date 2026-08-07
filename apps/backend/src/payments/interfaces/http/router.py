"""FastAPI router for payments endpoints."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from payments.application.payment_service import PaymentService
from payments.interfaces.http.deps import get_current_user, get_payment_service, idempotency_key
from payments.interfaces.http.schemas import (
    InvoiceCreateRequest,
    InvoiceResponse,
    LineItemResponse,
    PaymentLinkResponse,
    RefundRequest,
    RefundResponse,
)

router = APIRouter(tags=["payments"])

if TYPE_CHECKING:
    from payments.domain.entities import Invoice


def _invoice_to_response(inv: Invoice) -> InvoiceResponse:
    """Convert a domain Invoice entity to InvoiceResponse."""
    return InvoiceResponse(
        id=inv.id,
        tenant_id=inv.tenant_id,
        customer_id=inv.customer_id,
        invoice_number=inv.invoice_number,
        status=inv.status.value,
        subtotal_paise=inv.subtotal.amount_paise,
        tax_paise=inv.tax.amount_paise,
        total_paise=inv.total.amount_paise,
        currency=inv.total.currency,
        due_date=inv.due_date,
        paid_at=inv.paid_at,
        description=inv.description,
        line_items=[
            LineItemResponse(
                id=li.id,
                description=li.description,
                quantity=li.quantity,
                unit_price_paise=li.unit_price.amount_paise,
                total_paise=li.total.amount_paise,
            )
            for li in inv.line_items
        ],
        created_at=inv.created_at,
        updated_at=inv.updated_at,
    )


@router.post("/payments/invoices", status_code=201, response_model=InvoiceResponse)
async def create_invoice(
    body: InvoiceCreateRequest,
    user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
    idem_key: str | None = Depends(idempotency_key),
) -> InvoiceResponse:
    """Create a new invoice (tenant_admin only)."""
    inv = await service.create_invoice(
        tenant_id=user["tenant_id"],
        customer_id=body.customer_id,
        line_items=[li.model_dump() for li in body.line_items],
        description=body.description,
        due_date=body.due_date,
        idempotency_key=idem_key,
    )
    return _invoice_to_response(inv)


@router.get("/payments/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> list[InvoiceResponse]:
    """List invoices, filtered by status and/or customer_id.

    Customers see only their own invoices. Admins see all.
    """
    viewer_cust = user["customer_id"] if "customer" in user["roles"] else None
    invoices = await service.list_invoices(
        tenant_id=user["tenant_id"],
        viewer_customer_id=viewer_cust,
        status=status_filter,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )
    return [InvoiceResponse.model_validate(i) for i in invoices]


@router.get("/payments/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> InvoiceResponse:
    """Get a single invoice by ID.

    Returns 404 to avoid leaking existence of invoices to unauthorized users.
    """
    viewer_cust = user["customer_id"] if "customer" in user["roles"] else None
    inv = await service.get_invoice(
        tenant_id=user["tenant_id"],
        invoice_id=invoice_id,
        viewer_customer_id=viewer_cust,
    )
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceResponse.model_validate(inv)


@router.post(
    "/payments/invoices/{invoice_id}/payment-link",
    status_code=200,
    response_model=PaymentLinkResponse,
)
async def create_payment_link(
    invoice_id: UUID,
    user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
    idem_key: str | None = Depends(idempotency_key),
) -> PaymentLinkResponse:
    """Create a payment link for an invoice (customer only, requires idempotency key)."""
    if "customer" not in user["roles"]:
        raise HTTPException(status_code=403, detail="Only customers can pay invoices")
    if idem_key is None:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")

    try:
        result = await service.create_payment_link(
            tenant_id=user["tenant_id"],
            customer_id=user["customer_id"],
            invoice_id=invoice_id,
            idempotency_key=idem_key,
        )
    except Exception:
        # Re-raise service exceptions (NotFound, Conflict, etc.)
        raise

    return PaymentLinkResponse(
        short_url=result.short_url,
        razorpay_payment_link_id=result.razorpay_payment_link_id,
        expires_at=result.expires_at,
    )


@router.post(
    "/payments/invoices/{invoice_id}/refund",
    status_code=200,
    response_model=RefundResponse,
)
async def refund_invoice(
    invoice_id: UUID,
    body: RefundRequest,
    user: dict = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
    idem_key: str | None = Depends(idempotency_key),
) -> RefundResponse:
    """Refund a paid invoice (tenant_admin only, requires idempotency key)."""
    if "tenant_admin" not in user["roles"]:
        raise HTTPException(status_code=403, detail="Only tenant_admin can refund")
    if idem_key is None:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")

    refund = await service.refund_invoice(
        tenant_id=user["tenant_id"],
        invoice_id=invoice_id,
        reason=body.reason,
        idempotency_key=idem_key,
    )
    return RefundResponse.model_validate(refund)
