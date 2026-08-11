"""add FK on customers.tenant_id (F-20)

Revision ID: 20260812_0002
Revises: 20260812_0001
Create Date: 2026-08-12 00:00:01
"""
from __future__ import annotations

from alembic import op


revision = "20260812_0002"
down_revision = "20260812_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_customers_tenant_id",
        "customers",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_customers_tenant_id", "customers", type_="foreignkey")
