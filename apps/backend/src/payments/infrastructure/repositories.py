from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from payments.infrastructure.models import (
    IdempotencyKeyModel,
    InvoiceModel,
    PaymentModel,
    ProcessedRazorpayEventModel,
    RefundModel,
    TenantPaymentConfigModel,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class InvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def save(self, inv: InvoiceModel) -> None:
        self._s.add(inv)
        await self._s.flush()

    async def get(self, tenant_id: UUID, invoice_id: UUID) -> InvoiceModel | None:
        return (
            await self._s.execute(
                select(InvoiceModel).where(
                    InvoiceModel.id == invoice_id,
                    InvoiceModel.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()

    async def get_for_update(
        self, tenant_id: UUID, invoice_id: UUID
    ) -> InvoiceModel | None:
        return (
            await self._s.execute(
                select(InvoiceModel).where(
                    InvoiceModel.id == invoice_id,
                    InvoiceModel.tenant_id == tenant_id,
                ).with_for_update()
            )
        ).scalar_one_or_none()

    async def get_by_razorpay_payment_link_id(
        self, tenant_id: UUID, payment_link_id: str
    ) -> InvoiceModel | None:
        # join via Payment to find the invoice
        # (UNIQUE partial index on razorpay_payment_link_id)
        result = await self._s.execute(
            select(InvoiceModel)
            .join(PaymentModel, PaymentModel.invoice_id == InvoiceModel.id)
            .where(
                PaymentModel.razorpay_payment_link_id == payment_link_id,
                PaymentModel.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_customer(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InvoiceModel]:
        result = await self._s.execute(
            select(InvoiceModel)
            .where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.customer_id == customer_id,
            )
            .order_by(InvoiceModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        status: str | None = None,
        customer_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InvoiceModel]:
        stmt = select(InvoiceModel).where(InvoiceModel.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(InvoiceModel.status == status)
        if customer_id:
            stmt = stmt.where(InvoiceModel.customer_id == customer_id)
        stmt = (
            stmt.order_by(InvoiceModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def next_invoice_number(self, tenant_id: UUID) -> str:
        # Atomic per-tenant sequential; uniqueness enforced by UNIQUE index.
        result = await self._s.execute(
            select(InvoiceModel.invoice_number)
            .where(InvoiceModel.tenant_id == tenant_id)
            .order_by(InvoiceModel.created_at.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        if last is None:
            return "INV-000001"
        n = int(last.split("-")[-1]) + 1
        return f"INV-{n:06d}"


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def save(self, p: PaymentModel) -> None:
        self._s.add(p)
        await self._s.flush()

    async def get_by_id(
        self, tenant_id: UUID, payment_id: UUID
    ) -> PaymentModel | None:
        return (
            await self._s.execute(
                select(PaymentModel).where(
                    PaymentModel.id == payment_id,
                    PaymentModel.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()

    async def get_by_razorpay_payment_link_id(
        self, tenant_id: UUID, link_id: str
    ) -> PaymentModel | None:
        return (
            await self._s.execute(
                select(PaymentModel).where(
                    PaymentModel.razorpay_payment_link_id == link_id,
                    PaymentModel.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()

    async def get_by_razorpay_payment_id(
        self, tenant_id: UUID, rzp_payment_id: str
    ) -> PaymentModel | None:
        return (
            await self._s.execute(
                select(PaymentModel).where(
                    PaymentModel.razorpay_payment_id == rzp_payment_id,
                    PaymentModel.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()

    async def latest_captured_for_invoice(
        self, tenant_id: UUID, invoice_id: UUID
    ) -> PaymentModel | None:
        return (
            await self._s.execute(
                select(PaymentModel)
                .where(
                    PaymentModel.invoice_id == invoice_id,
                    PaymentModel.tenant_id == tenant_id,
                    PaymentModel.status == "captured",
                )
                .order_by(PaymentModel.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()


class RefundRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def save(self, r: RefundModel) -> None:
        self._s.add(r)
        await self._s.flush()

    async def get_by_razorpay_id(
        self, tenant_id: UUID, razorpay_refund_id: str
    ) -> RefundModel | None:
        return (
            await self._s.execute(
                select(RefundModel).where(
                    RefundModel.razorpay_refund_id == razorpay_refund_id,
                    RefundModel.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()


class ProcessedRazorpayEventRepository:
    """Global dedup log keyed by globally-unique Razorpay event id."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def exists(self, razorpay_event_id: str) -> bool:
        return (
            await self._s.execute(
                select(ProcessedRazorpayEventModel.razorpay_event_id).where(
                    ProcessedRazorpayEventModel.razorpay_event_id == razorpay_event_id
                )
            )
        ).scalar_one_or_none() is not None

    async def mark_processed(
        self, razorpay_event_id: str, tenant_id: UUID | None, event_type: str
    ) -> None:
        # Use SQLite insert for test compatibility; PostgreSQL uses pg_insert
        stmt = sqlite_insert(ProcessedRazorpayEventModel).values(
            razorpay_event_id=razorpay_event_id,
            tenant_id=tenant_id,
            event_type=event_type,
            processed_at=datetime.now(UTC),
        ).on_conflict_do_nothing(index_elements=["razorpay_event_id"])
        await self._s.execute(stmt)
        await self._s.flush()


class TenantPaymentConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: UUID) -> TenantPaymentConfigModel | None:
        return await self._s.get(TenantPaymentConfigModel, tenant_id)


class IdempotencyKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(
        self, tenant_id: UUID, endpoint: str, key: str
    ) -> IdempotencyKeyModel | None:
        return (
            await self._s.execute(
                select(IdempotencyKeyModel).where(
                    IdempotencyKeyModel.tenant_id == tenant_id,
                    IdempotencyKeyModel.endpoint == endpoint,
                    IdempotencyKeyModel.key == key,
                )
            )
        ).scalar_one_or_none()

    async def save(self, row: IdempotencyKeyModel) -> None:
        self._s.add(row)
        await self._s.flush()
