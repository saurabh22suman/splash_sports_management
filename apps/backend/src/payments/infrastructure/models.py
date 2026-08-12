from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TEXT, TypeDecorator

from common.infrastructure.db import Base
from common.infrastructure.mixins import TimestampMixin


class JsonColumn(TypeDecorator):
    """A JSON column that uses JSONB for PostgreSQL and JSON for other dialects (e.g., SQLite)."""

    impl = TEXT
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        # For SQLite, convert to JSON string
        import json

        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        # For SQLite, parse JSON string
        import json

        return json.loads(value)


class TenantPaymentConfigModel(Base, TimestampMixin):
    __tablename__ = "payments_tenant_config"

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        # use_alter defers FK constraint creation to avoid SQLite issues
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
            use_alter=True,
            name="fk_payments_tenant_config_tenant_id",
        ),
        primary_key=True,
    )
    razorpay_account_id: Mapped[str | None] = mapped_column(
        Text
    )  # NULL in v1 (single platform account)
    default_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="INR")


class InvoiceModel(Base, TimestampMixin):
    __tablename__ = "payments_invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="payments_invoices_number_uniq"),
        Index("payments_invoices_tenant_customer_idx", "tenant_id", "customer_id"),
        Index("payments_invoices_tenant_status_idx", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    invoice_number: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    subtotal_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="INR")
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JsonColumn, nullable=False, server_default="{}"
    )

    line_items: Mapped[list[InvoiceLineItemModel]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )


class InvoiceLineItemModel(Base):
    __tablename__ = "payments_invoice_line_items"
    __table_args__ = (Index("payments_line_items_invoice_idx", "invoice_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "payments_invoices.id",
            ondelete="CASCADE",
            name="fk_payments_invoice_line_items_invoice_id",
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    invoice: Mapped[InvoiceModel] = relationship(back_populates="line_items")


class PaymentModel(Base, TimestampMixin):
    __tablename__ = "payments_payments"
    __table_args__ = (
        Index(
            "payments_payments_rzp_payment_uniq", "tenant_id", "razorpay_payment_id", unique=True
        ),
        Index(
            "payments_payments_rzp_link_uniq", "tenant_id", "razorpay_payment_link_id", unique=True
        ),
        Index("payments_payments_idempotency_uniq", "tenant_id", "idempotency_key", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "payments_invoices.id", ondelete="RESTRICT", name="fk_payments_payments_invoice_id"
        ),
        nullable=False,
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="INR")
    status: Mapped[str] = mapped_column(Text, nullable=False)
    razorpay_payment_id: Mapped[str | None] = mapped_column(Text)
    razorpay_payment_link_id: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefundModel(Base, TimestampMixin):
    __tablename__ = "payments_refunds"
    __table_args__ = (
        Index("payments_refunds_rzp_uniq", "tenant_id", "razorpay_refund_id", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    payment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "payments_payments.id", ondelete="RESTRICT", name="fk_payments_refunds_payment_id"
        ),
        nullable=False,
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="INR")
    status: Mapped[str] = mapped_column(Text, nullable=False)
    razorpay_refund_id: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False, server_default="")


class ProcessedRazorpayEventModel(Base):
    __tablename__ = "payments_processed_razorpay_events"
    __table_args__ = (Index("payments_processed_events_processed_at_idx", "processed_at"),)

    razorpay_event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True)
    )  # nullable: test events lack tenant context
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyKeyModel(Base):
    __tablename__ = "payments_idempotency_keys"
    __table_args__ = (Index("payments_idempotency_keys_expires_at_idx", "expires_at"),)

    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    request_hash: Mapped[str] = mapped_column(Text, nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict] = mapped_column(JsonColumn, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
