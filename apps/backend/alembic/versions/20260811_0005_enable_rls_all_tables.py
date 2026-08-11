"""enable_rls_all_tables

Revision ID: 0005_enable_rls_all_tables
Revises: 0004_payments
Create Date: 2026-08-11 00:00:00

This migration enables Row-Level Security (RLS) on all tenant-scoped business tables
that were created before RLS was implemented in the payments module.

Tables requiring RLS (8 total):
- users, refresh_tokens (auth module)
- customers (customer module)
- facilities, resources, availability_rules (facility module)
- bookings (booking module)

The payments module already has RLS enabled (payments_invoices, payments_payments,
payments_refunds, payments_idempotency_keys) - those are left untouched.

RLS Policy: tenant_isolation
- USING: tenant_id::text = current_setting('app.tenant_id', true)
- WITH CHECK: Same as USING (prevents cross-tenant INSERT/UPDATE)

Note: RLS requires the application to set app.tenant_id for each session.
The db.py session factory should be configured to set this on connect.
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "0005_enable_rls_all_tables"
down_revision: Union[str, None] = "0004_payments"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


# All tenant-scoped tables that need RLS (excluding payments which already has it)
TENANT_SCOPED_TABLES = [
    "users",
    "refresh_tokens",
    "customers",
    "facilities",
    "resources",
    "availability_rules",
    "bookings",
]


def upgrade() -> None:
    """Enable RLS on all tenant-scoped tables and create tenant_isolation policies."""
    for table in TENANT_SCOPED_TABLES:
        # Enable RLS on the table
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Create the tenant isolation policy
        # Uses the same pattern as payments module:
        # - USING: filters rows based on tenant_id match
        # - WITH CHECK: prevents cross-tenant INSERT/UPDATE
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
        """)


def downgrade() -> None:
    """Drop tenant_isolation policies and disable RLS on all tables."""
    for table in reversed(TENANT_SCOPED_TABLES):
        # Drop the tenant isolation policy
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

        # Disable RLS on the table
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
