from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from common.domain.exceptions import Conflict, NotFound, Validation
from payments.application.events import InvoiceCreated, InvoicePaid, PaymentFailed, RefundIssued
from payments.domain.entities import Invoice, InvoiceStatus, LineItem
from payments.domain.value_objects import Money, PaymentStatus
from payments.infrastructure.models import InvoiceLineItemModel, InvoiceModel, PaymentModel
from payments.infrastructure.repositories import (  # noqa: F401
    InvoiceRepository,
    TenantPaymentConfigRepository,
)

if TYPE_CHECKING:
    from common.application.events import EventPublisher
    from payments.application.provider import PaymentLinkResult, PaymentProvider
    from payments.infrastructure.repositories import (  # noqa: F401
        IdempotencyKeyRepository,
        PaymentRepository,
        ProcessedRazorpayEventRepository,
        RefundRepository,
    )


class PaymentService:
    def __init__(
        self, *, session, invoice_repo, payment_repo, refund_repo,
        processed_event_repo, idempotency, tenant_config_repo,
        events: EventPublisher, provider: PaymentProvider, settings,
    ) -> None:
        self._session = session
        self._invoices = invoice_repo
        self._payments = payment_repo
        self._refunds = refund_repo
        self._processed_events = processed_event_repo
        self._idem = idempotency
        self._tenant_cfg = tenant_config_repo
        self._events = events
        self._provider = provider
        self._settings = settings

    async def create_invoice(
        self, *, tenant_id: UUID, customer_id: UUID,
        line_items: list[dict], description: str, due_date: date,
        idempotency_key: str | None = None,  # noqa: ARG002
    ) -> Invoice:
        # Note: idempotency_key is reserved for future use
        # Validate line items
        for li in line_items:
            if li["quantity"] <= 0:
                raise Validation("Line item quantity must be positive", details={"item": li})
            if li["unit_price_paise"] < 0:
                raise Validation("Line item unit price must be non-negative", details={"item": li})
        if not line_items:
            raise Validation("At least one line item required")

        # Get tenant config for currency
        cfg = await self._tenant_cfg.get(tenant_id)
        currency = cfg.default_currency if cfg else "INR"

        # Compute subtotal
        subtotal = sum(li["quantity"] * li["unit_price_paise"] for li in line_items)

        # Get next invoice number
        invoice_number = await self._invoices.next_invoice_number(tenant_id)
        now = datetime.now(UTC)

        # Create the invoice model
        inv = InvoiceModel(
            id=uuid4(), tenant_id=tenant_id, customer_id=customer_id,
            invoice_number=invoice_number, status="pending",
            subtotal_paise=subtotal, tax_paise=0, total_paise=subtotal,
            currency=currency, due_date=due_date, paid_at=None,
            description=description, metadata_={},
            created_at=now, updated_at=now,
        )

        # Add line items to the model
        for li in line_items:
            total = li["quantity"] * li["unit_price_paise"]
            inv.line_items.append(InvoiceLineItemModel(
                id=uuid4(), invoice_id=inv.id, description=li["description"],
                quantity=li["quantity"], unit_price_paise=li["unit_price_paise"], total_paise=total,
            ))

        # Persist the invoice (cascade saves line items)
        await self._invoices.save(inv)

        # Publish InvoiceCreated event
        await self._events.publish(InvoiceCreated(
            tenant_id=tenant_id,
            invoice_id=inv.id,
            customer_id=customer_id,
            total_paise=subtotal,
            currency=currency,
        ))

        # Build and return Invoice entity
        entity_line_items = []
        for model_li in inv.line_items:
            entity_line_items.append(LineItem(
                id=model_li.id,
                description=model_li.description,
                quantity=model_li.quantity,
                unit_price=Money(amount_paise=model_li.unit_price_paise, currency=currency),
                total=Money(amount_paise=model_li.total_paise, currency=currency),
            ))

        return Invoice(
            id=inv.id,
            tenant_id=inv.tenant_id,
            customer_id=inv.customer_id,
            invoice_number=inv.invoice_number,
            status=InvoiceStatus.PENDING,
            subtotal=Money(amount_paise=inv.subtotal_paise, currency=inv.currency),
            tax=Money(amount_paise=inv.tax_paise, currency=inv.currency),
            total=Money(amount_paise=inv.total_paise, currency=inv.currency),
            due_date=inv.due_date,
            paid_at=inv.paid_at,
            description=inv.description,
            line_items=entity_line_items,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    async def create_payment_link(
        self, *, tenant_id: UUID, customer_id: UUID, invoice_id: UUID, idempotency_key: str,
    ) -> PaymentLinkResult:
        inv = await self._invoices.get_for_update(tenant_id, invoice_id)
        if inv is None:
            raise NotFound("Invoice not found", details={"invoice_id": str(invoice_id)})
        if inv.customer_id != customer_id:
            # 404 to avoid leaking
            raise NotFound("Invoice not found", details={"invoice_id": str(invoice_id)})
        if not (inv.status == "pending"):
            raise Conflict("Invoice is not payable", details={"status": inv.status})

        payment = PaymentModel(
            id=uuid4(), tenant_id=tenant_id, invoice_id=invoice_id,
            amount_paise=inv.total_paise, currency=inv.currency,
            status=PaymentStatus.PENDING.value,
            razorpay_payment_id=None, razorpay_payment_link_id=None,
            idempotency_key=idempotency_key, captured_at=None,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        await self._payments.save(payment)

        inv_dict = {
            "id": inv.id, "tenant_id": tenant_id, "customer_id": inv.customer_id,
            "line_items": [{"description": li.description, "quantity": li.quantity,
                            "unit_price_paise": li.unit_price_paise, "total_paise": li.total_paise}
                           for li in inv.line_items],
            "currency": inv.currency,
        }
        app_url = self._settings.app_url
        result = await self._provider.create_payment_link(
            invoice=inv_dict, payment_id=payment.id, idempotency_key=idempotency_key,
            success_url=f"{app_url}/book/pay/{invoice_id}/return?payment_link_id={{PAYMENT_LINK_ID}}",
            cancel_url=f"{app_url}/book/pay/{invoice_id}",
            customer={"id": str(inv.customer_id)},
        )
        payment.razorpay_payment_link_id = result.razorpay_payment_link_id
        await self._payments.save(payment)
        return result

    async def handle_webhook(self, *, raw_payload: bytes, signature: str) -> None:
        # Verify webhook signature (sync call)
        try:
            event = self._provider.verify_webhook(raw_payload, signature)
        except Exception as e:
            raise Validation("Invalid webhook signature", details={"error": str(e)}) from e

        # Dedup check
        if await self._processed_events.exists(event["id"]):
            return  # Already processed

        etype = event.get("event")
        payload = event.get("payload", {})

        if etype == "payment.captured":
            ent = payload.get("payment", {}).get("entity", {})
            notes = ent.get("notes", {}) or {}
            payment_id = UUID(notes["payment_id"])
            tenant_id = UUID(notes["tenant_id"])
            invoice_id = UUID(notes["invoice_id"])

            payment = await self._payments.get_by_id(tenant_id, payment_id)
            if payment is None:
                await self._processed_events.mark_processed(event["id"], tenant_id, etype)
                return

            inv = await self._invoices.get_for_update(tenant_id, invoice_id)
            now = datetime.now(UTC)
            payment.razorpay_payment_id = ent.get("id") or payment.razorpay_payment_id
            payment.status = "captured"
            payment.captured_at = now
            inv.status = "paid"
            inv.paid_at = now
            await self._payments.save(payment)
            await self._invoices.save(inv)
            await self._processed_events.mark_processed(event["id"], tenant_id, etype)

            await self._events.publish(InvoicePaid(
                tenant_id=tenant_id,
                invoice_id=inv.id,
                payment_id=payment.id,
                customer_id=inv.customer_id,
                amount_paise=inv.total_paise,
                currency=inv.currency,
            ))

        elif etype == "payment.failed":
            ent = payload.get("payment", {}).get("entity", {})
            notes = ent.get("notes", {}) or {}
            payment_id = UUID(notes["payment_id"])
            tenant_id = UUID(notes["tenant_id"])
            invoice_id = UUID(notes["invoice_id"])
            reason = ent.get("error_code") or ent.get("error_description") or "payment_failed"

            payment = await self._payments.get_by_id(tenant_id, payment_id)
            if payment is None:
                await self._processed_events.mark_processed(event["id"], tenant_id, etype)
                return

            inv = await self._invoices.get_for_update(tenant_id, invoice_id)
            payment.status = "failed"
            inv.status = "failed"
            await self._payments.save(payment)
            await self._invoices.save(inv)
            await self._processed_events.mark_processed(event["id"], tenant_id, etype)

            await self._events.publish(PaymentFailed(
                tenant_id=tenant_id,
                invoice_id=inv.id,
                payment_id=payment.id,
                customer_id=inv.customer_id,
                reason=reason,
            ))

        elif etype == "refund.processed":
            ent = payload.get("refund", {}).get("entity", {})
            razorpay_refund_id = ent.get("id")

            refund = await self._refunds.get_by_razorpay_refund_id_any_tenant(razorpay_refund_id)
            if refund is None:
                await self._processed_events.mark_processed(event["id"], uuid4(), etype)
                return

            tenant_id = refund.tenant_id
            payment = await self._payments.get_by_id(tenant_id, refund.payment_id)
            inv = await self._invoices.get_for_update(tenant_id, payment.invoice_id)
            now = datetime.now(UTC)
            refund.status = "completed"
            inv.status = "refunded"
            await self._refunds.save(refund)
            await self._invoices.save(inv)
            await self._processed_events.mark_processed(event["id"], tenant_id, etype)

            await self._events.publish(RefundIssued(
                tenant_id=tenant_id,
                invoice_id=inv.id,
                payment_id=payment.id,
                refund_id=refund.id,
                customer_id=inv.customer_id,
                amount_paise=refund.amount_paise,
                currency=refund.currency,
            ))

        else:
            # Unknown event type - mark processed and move on
            await self._processed_events.mark_processed(event["id"], uuid4(), etype)
