"""create payments tables

Revision ID: 0004_payments
Revises: 0003_bookings
Create Date: 2026-08-07

"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_payments"
down_revision: Union[str, None] = "0003_bookings"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    # payments_tenant_config
    op.create_table(
        "payments_tenant_config",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("razorpay_account_id", sa.Text(), nullable=True),
        sa.Column("default_currency", sa.CHAR(3), nullable=False, server_default="INR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # payments_invoices
    op.create_table(
        "payments_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("subtotal_paise", sa.BigInteger, nullable=False),
        sa.Column("tax_paise", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_paise", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="INR"),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "invoice_number", name="payments_invoices_number_uniq"),
    )
    op.create_index("payments_invoices_tenant_customer_idx", "payments_invoices", ["tenant_id", "customer_id"])
    op.create_index("payments_invoices_tenant_status_idx", "payments_invoices", ["tenant_id", "status"])

    # payments_invoice_line_items
    op.create_table(
        "payments_invoice_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price_paise", sa.BigInteger, nullable=False),
        sa.Column("total_paise", sa.BigInteger, nullable=False),
    )
    op.create_index("payments_line_items_invoice_idx", "payments_invoice_line_items", ["invoice_id"])

    # payments_payments
    op.create_table(
        "payments_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments_invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_paise", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("razorpay_payment_id", sa.Text(), nullable=True),
        sa.Column("razorpay_payment_link_id", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("payments_payments_rzp_payment_uniq", "payments_payments", ["tenant_id", "razorpay_payment_id"], unique=True, postgresql_where=sa.text("razorpay_payment_id IS NOT NULL"))
    op.create_index("payments_payments_rzp_link_uniq", "payments_payments", ["tenant_id", "razorpay_payment_link_id"], unique=True, postgresql_where=sa.text("razorpay_payment_link_id IS NOT NULL"))
    op.create_index("payments_payments_idempotency_uniq", "payments_payments", ["tenant_id", "idempotency_key"], unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))

    # payments_refunds
    op.create_table(
        "payments_refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments_payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_paise", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("razorpay_refund_id", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("payments_refunds_rzp_uniq", "payments_refunds", ["tenant_id", "razorpay_refund_id"], unique=True, postgresql_where=sa.text("razorpay_refund_id IS NOT NULL"))

    # payments_processed_razorpay_events
    op.create_table(
        "payments_processed_razorpay_events",
        sa.Column("razorpay_event_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("payments_processed_events_processed_at_idx", "payments_processed_razorpay_events", ["processed_at"])

    # payments_idempotency_keys
    op.create_table(
        "payments_idempotency_keys",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("endpoint", sa.Text(), primary_key=True),
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("response_body", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("payments_idempotency_keys_expires_at_idx", "payments_idempotency_keys", ["expires_at"])

    # RLS policies (one per business table). payments_processed_razorpay_events is NOT
    # RLS-scoped - it's a global dedup log keyed by globally-unique razorpay_event_id.
    # Note: payments_invoice_line_items has no tenant_id - it's protected via the parent invoice
    for table in ("payments_invoices", "payments_payments",
                  "payments_refunds", "payments_idempotency_keys"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING (tenant_id = current_setting('app.tenant_id', true)::uuid)")

    # Seed: one TenantPaymentConfig row per existing tenant (default currency = INR)
    op.execute("""
        INSERT INTO payments_tenant_config (tenant_id, default_currency)
        SELECT id, 'INR' FROM tenants
        ON CONFLICT (tenant_id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON payments_idempotency_keys")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON payments_refunds")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON payments_payments")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON payments_invoices")

    for table in ("payments_idempotency_keys", "payments_processed_razorpay_events",
                  "payments_refunds", "payments_payments", "payments_invoice_line_items",
                  "payments_invoices", "payments_tenant_config"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("payments_idempotency_keys_expires_at_idx", table_name="payments_idempotency_keys")
    op.drop_table("payments_idempotency_keys")

    op.drop_index("payments_processed_events_processed_at_idx", table_name="payments_processed_razorpay_events")
    op.drop_table("payments_processed_razorpay_events")

    op.drop_index("payments_refunds_rzp_uniq", table_name="payments_refunds")
    op.drop_table("payments_refunds")

    op.drop_index("payments_payments_idempotency_uniq", table_name="payments_payments")
    op.drop_index("payments_payments_rzp_link_uniq", table_name="payments_payments")
    op.drop_index("payments_payments_rzp_payment_uniq", table_name="payments_payments")
    op.drop_table("payments_payments")

    op.drop_index("payments_line_items_invoice_idx", table_name="payments_invoice_line_items")
    op.drop_table("payments_invoice_line_items")

    op.drop_index("payments_invoices_tenant_status_idx", table_name="payments_invoices")
    op.drop_index("payments_invoices_tenant_customer_idx", table_name="payments_invoices")
    op.drop_table("payments_invoices")

    op.drop_table("payments_tenant_config")
