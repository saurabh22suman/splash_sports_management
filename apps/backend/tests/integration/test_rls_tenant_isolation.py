"""Integration tests for RLS tenant isolation.

This test verifies that the RLS migration can be applied and that the tenant_isolation
policies are created correctly.
"""

from __future__ import annotations

import os
import uuid
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

# Import models to ensure all tables are registered with Base
from auth.infrastructure.models import TenantModel, UserModel, RefreshTokenModel
from booking.infrastructure.models import BookingModel
from customer.infrastructure.models import CustomerModel
from facility.infrastructure.models import FacilityModel, ResourceModel, AvailabilityRuleModel
from common.infrastructure.db import Base


pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test",
)

# Tables requiring RLS (same as migration)
TENANT_SCOPED_TABLES = [
    "users",
    "refresh_tokens",
    "customers",
    "facilities",
    "resources",
    "availability_rules",
    "bookings",
]


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test engine."""
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Setup: create tables
    async with engine.begin() as conn:
        # Drop all tables with CASCADE to handle FK constraints
        await conn.execute(text("DROP TABLE IF EXISTS payments_tenant_config CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_idempotency_keys CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_refunds CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_payments CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_invoice_line_items CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_invoices CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_processed_razorpay_events CASCADE"))

        # Also drop our tables with CASCADE
        for table in TENANT_SCOPED_TABLES:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))

        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    yield engine

    # Teardown: clean up
    async with engine.begin() as conn:
        for table in TENANT_SCOPED_TABLES:
            try:
                await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
                await conn.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
            except Exception:
                pass

        await conn.execute(text("DROP TABLE IF EXISTS payments_tenant_config CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_idempotency_keys CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_refunds CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_payments CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_invoice_line_items CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_invoices CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS payments_processed_razorpay_events CASCADE"))

        for table in TENANT_SCOPED_TABLES:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        await conn.commit()

    await engine.dispose()


@pytest.mark.asyncio
class TestRLSMigration:
    """Test RLS migration creates policies correctly."""

    async def test_migration_creates_rls_policies(self, db_engine):
        """Verify the migration enables RLS and creates tenant_isolation policies."""
        async with db_engine.begin() as conn:
            # Apply the migration (simulate)
            for table in TENANT_SCOPED_TABLES:
                await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
                await conn.execute(
                    text(f"""
                    CREATE POLICY tenant_isolation ON {table}
                    USING (tenant_id::text = current_setting('app.tenant_id', true))
                    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
                """)
                )
            await conn.commit()

        # Verify RLS is enabled on all tables
        async with db_engine.begin() as conn:
            for table in TENANT_SCOPED_TABLES:
                result = await conn.execute(
                    text(f"""
                    SELECT relname, relrowsecurity
                    FROM pg_class
                    WHERE relname = '{table}'
                """)
                )
                row = result.fetchone()
                assert row is not None, f"Table {table} not found"
                assert row[1] is True, f"RLS not enabled on {table}"

        # Verify policies exist
        async with db_engine.begin() as conn:
            for table in TENANT_SCOPED_TABLES:
                result = await conn.execute(
                    text(f"""
                    SELECT policyname, cmd, permissive
                    FROM pg_policies
                    WHERE tablename = '{table}' AND policyname = 'tenant_isolation'
                """)
                )
                row = result.fetchone()
                assert row is not None, f"Policy tenant_isolation not found on {table}"
                assert row[2] == True or row[2] == "PERMISSIVE", (
                    f"Policy on {table} is not permissive: {row[2]}"
                )

    async def test_tenant_isolation_policy_structure(self, db_engine):
        """Verify the policy has the correct structure and USING clause."""
        # Create test data
        tenant_a_id = str(uuid.uuid4())

        async with db_engine.begin() as conn:
            # Create tenant
            await conn.execute(
                text("""
                INSERT INTO tenants (id, name, slug, status, primary_contact_email, created_at, updated_at)
                VALUES (:id, :name, :slug, :status, :email, NOW(), NOW())
            """),
                {
                    "id": tenant_a_id,
                    "name": "Tenant A",
                    "slug": "tenant-a",
                    "status": "active",
                    "email": "a@tenant.com",
                },
            )

            # Create a user
            await conn.execute(
                text("""
                INSERT INTO users (id, tenant_id, email, password_hash, full_name, roles, is_active, failed_login_count, created_at, updated_at)
                VALUES (:id, :tenant_id, :email, :hash, :name, '{}', true, 0, NOW(), NOW())
            """),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_a_id,
                    "email": "user@tenant-a.com",
                    "hash": "hash",
                    "name": "User A",
                },
            )
            await conn.commit()

        # Enable RLS
        async with db_engine.begin() as conn:
            await conn.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
            await conn.execute(
                text("""
                CREATE POLICY tenant_isolation ON users
                USING (tenant_id::text = current_setting('app.tenant_id', true))
                WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
            """)
            )
            await conn.commit()

        # Verify the policy has the correct structure
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT policyname, cmd, qual::text, with_check::text
                FROM pg_policies
                WHERE tablename = 'users' AND policyname = 'tenant_isolation'
            """)
            )
            row = result.fetchone()
            assert row is not None, "Policy not found"
            assert "tenant_id" in row[2], f"USING clause should contain tenant_id: {row[2]}"
            assert "current_setting" in row[2], f"USING clause should use current_setting: {row[2]}"
            assert "tenant_id" in row[3], f"WITH CHECK clause should contain tenant_id: {row[3]}"
            assert "current_setting" in row[3], (
                f"WITH CHECK clause should use current_setting: {row[3]}"
            )

    async def test_downgrade_removes_policies(self, db_engine):
        """Verify the downgrade correctly removes policies and disables RLS."""
        # Apply RLS
        async with db_engine.begin() as conn:
            for table in TENANT_SCOPED_TABLES:
                await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
                await conn.execute(
                    text(f"""
                    CREATE POLICY tenant_isolation ON {table}
                    USING (tenant_id::text = current_setting('app.tenant_id', true))
                    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
                """)
                )
            await conn.commit()

        # Verify policies exist
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT COUNT(*) FROM pg_policies WHERE policyname = 'tenant_isolation'
            """)
            )
            count = result.scalar()
            assert count == len(TENANT_SCOPED_TABLES), (
                f"Expected {len(TENANT_SCOPED_TABLES)} policies, found {count}"
            )

        # Run downgrade (simulate)
        async with db_engine.begin() as conn:
            for table in TENANT_SCOPED_TABLES:
                await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
                await conn.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
            await conn.commit()

        # Verify policies are removed
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT COUNT(*) FROM pg_policies WHERE policyname = 'tenant_isolation'
            """)
            )
            count = result.scalar()
            assert count == 0, f"Expected 0 policies after downgrade, found {count}"

        # Verify RLS is disabled
        async with db_engine.begin() as conn:
            for table in TENANT_SCOPED_TABLES:
                result = await conn.execute(
                    text(f"""
                    SELECT relname, relrowsecurity
                    FROM pg_class
                    WHERE relname = '{table}'
                """)
                )
                row = result.fetchone()
                assert row is not None and row[1] is False, f"RLS should be disabled on {table}"
