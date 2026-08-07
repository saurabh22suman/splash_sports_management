from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from common.domain.exceptions import Validation
from payments.application.events import InvoiceCreated
from payments.domain.entities import Invoice, InvoiceStatus, LineItem
from payments.domain.value_objects import Money
from payments.infrastructure.models import InvoiceLineItemModel, InvoiceModel
from payments.infrastructure.repositories import (  # noqa: F401
    InvoiceRepository,
    TenantPaymentConfigRepository,
)

if TYPE_CHECKING:
    from common.application.events import EventPublisher
    from payments.application.provider import PaymentProvider
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
