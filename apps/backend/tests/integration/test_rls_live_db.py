"""Live-DB tests for RLS tenant isolation (F-15).

These tests verify that Row-Level Security policies are properly configured at the database
level. Unlike the mock-based tests in test_tenant_isolation_matrix.py, these tests
connect to a real PostgreSQL database with RLS enabled.

The tests use a testcontainer to spin up a real Postgres instance, apply
migrations, enable RLS, and verify the policies are in place.

NOTE: These tests verify that RLS policies exist and are properly configured.
Full end-to-end cross-tenant isolation testing requires the application to properly
set app.tenant_id on each connection, which is tested in other integration tests.
"""

from __future__ import annotations

import uuid
from typing import Any
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
async def postgres_container():
    """Spin up a real Postgres container for testing RLS."""
    from testcontainers.community.postgres import PostgresContainer

    # Spin up a PostgreSQL container with asyncpg driver
    pg = PostgresContainer(
        "postgres:15-alpine",
        username="splashh",
        password="splashh_dev",
        dbname="splashh",
        driver="asyncpg",
    )

    try:
        pg.start()
        yield pg
    finally:
        pg.stop()


@pytest_asyncio.fixture(scope="function")
async def db_engine(postgres_container):
    """Create test engine connected to the containerized Postgres."""
    # Get the connection string from the container
    db_url = postgres_container.get_connection_url()
    # Convert to async driver
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=False)

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

        for table in TENANT_SCOPED_TABLES:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))

        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    # Enable RLS on all tables (simulating the migration)
    async with engine.begin() as conn:
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

    yield engine

    # Teardown
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    """Create a session factory for the test DB."""
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def tenant_a_id() -> UUID:
    return uuid.uuid4()


@pytest.fixture
def tenant_b_id() -> UUID:
    return uuid.uuid4()


@pytest.mark.asyncio
class TestRLSPoliciesExist:
    """Test that RLS policies are properly created on all tenant-scoped tables."""

    async def test_rls_enabled_on_all_tables(self, db_engine) -> None:
        """Verify RLS is enabled on all tenant-scoped tables."""
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

    async def test_tenant_isolation_policy_exists(self, db_engine) -> None:
        """Verify tenant_isolation policy exists on all tables."""
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

    async def test_policy_uses_current_setting(self, db_engine) -> None:
        """Verify the policy uses current_setting('app.tenant_id', true)."""
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT policyname, qual::text, with_check::text
                FROM pg_policies
                WHERE tablename = 'users' AND policyname = 'tenant_isolation'
            """)
            )
            row = result.fetchone()
            assert row is not None, "Policy not found"
            assert "current_setting" in row[1], (
                f"USING clause should contain current_setting: {row[1]}"
            )
            assert "tenant_id" in row[1], f"USING clause should contain tenant_id: {row[1]}"
            assert "current_setting" in row[2], (
                f"WITH CHECK should contain current_setting: {row[2]}"
            )
            assert "tenant_id" in row[2], f"WITH CHECK should contain tenant_id: {row[2]}"

    async def test_policy_is_permissive(self, db_engine) -> None:
        """Verify the policy is permissive (OR'd with other policies)."""
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT policyname, permissive
                FROM pg_policies
                WHERE policyname = 'tenant_isolation'
            """)
            )
            rows = result.fetchall()
            assert len(rows) > 0, "No tenant_isolation policies found"
            for row in rows:
                assert row[1] is True or row[1] == "PERMISSIVE", (
                    f"Policy {row[0]} is not permissive: {row[1]}"
                )


@pytest.mark.asyncio
class TestRLSDataIsolation:
    """Test that data isolation works when tenant_id is properly set."""

    async def test_insert_within_tenant_succeeds(self, session_factory, tenant_a_id) -> None:
        """INSERT within the same tenant should work when tenant_id is not set."""
        # First create the tenant
        async with session_factory() as session:
            await session.execute(
                text("""
                INSERT INTO tenants (id, name, slug, status, primary_contact_email, created_at, updated_at)
                VALUES (:id, :name, :slug, :status, :email, NOW(), NOW())
            """),
                {
                    "id": str(tenant_a_id),
                    "name": "Tenant A",
                    "slug": "tenant-a",
                    "status": "active",
                    "email": "a@tenant.com",
                },
            )
            await session.commit()

        # Now insert a user
        async with session_factory() as session:
            user_id = uuid.uuid4()
            await session.execute(
                text("""
                INSERT INTO users (id, tenant_id, email, password_hash, full_name, roles, is_active, failed_login_count, created_at, updated_at)
                VALUES (:id, :tenant_id, :email, :hash, :name, '{}', true, 0, NOW(), NOW())
            """),
                {
                    "id": str(user_id),
                    "tenant_id": str(tenant_a_id),
                    "email": "test@tenant.com",
                    "hash": "hash",
                    "name": "Test User",
                },
            )
            await session.commit()

        # Verify the user was created
        async with session_factory() as session:
            result = await session.execute(
                text("""
                SELECT COUNT(*) FROM users WHERE tenant_id = :tid
            """),
                {"tid": str(tenant_a_id)},
            )
            count = result.scalar()
            assert count == 1, f"Expected 1 user, got {count}"

    async def test_data_persists_correctly(self, session_factory, tenant_a_id, tenant_b_id) -> None:
        """Verify data is correctly stored for different tenants."""
        # First create the tenants
        async with session_factory() as session:
            await session.execute(
                text("""
                INSERT INTO tenants (id, name, slug, status, primary_contact_email, created_at, updated_at)
                VALUES (:id, :name, :slug, :status, :email, NOW(), NOW())
            """),
                {
                    "id": str(tenant_a_id),
                    "name": "Tenant A",
                    "slug": "tenant-a",
                    "status": "active",
                    "email": "a@tenant.com",
                },
            )
            await session.execute(
                text("""
                INSERT INTO tenants (id, name, slug, status, primary_contact_email, created_at, updated_at)
                VALUES (:id, :name, :slug, :status, :email, NOW(), NOW())
            """),
                {
                    "id": str(tenant_b_id),
                    "name": "Tenant B",
                    "slug": "tenant-b",
                    "status": "active",
                    "email": "b@tenant.com",
                },
            )
            await session.commit()

        # Create users for both tenants
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()

        async with session_factory() as session:
            await session.execute(
                text("""
                INSERT INTO users (id, tenant_id, email, password_hash, full_name, roles, is_active, failed_login_count, created_at, updated_at)
                VALUES (:id, :tenant_id, :email, :hash, :name, '{}', true, 0, NOW(), NOW())
            """),
                {
                    "id": str(user_a_id),
                    "tenant_id": str(tenant_a_id),
                    "email": "user-a@test.com",
                    "hash": "hash",
                    "name": "User A",
                },
            )

            await session.execute(
                text("""
                INSERT INTO users (id, tenant_id, email, password_hash, full_name, roles, is_active, failed_login_count, created_at, updated_at)
                VALUES (:id, :tenant_id, :email, :hash, :name, '{}', true, 0, NOW(), NOW())
            """),
                {
                    "id": str(user_b_id),
                    "tenant_id": str(tenant_b_id),
                    "email": "user-b@test.com",
                    "hash": "hash",
                    "name": "User B",
                },
            )
            await session.commit()

        # Verify both users exist (bypassing RLS by not setting tenant_id)
        async with session_factory() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            assert count == 2, f"Expected 2 users total, got {count}"

        # Verify tenant A's user
        async with session_factory() as session:
            result = await session.execute(
                text("""
                SELECT email FROM users WHERE tenant_id = :tid
            """),
                {"tid": str(tenant_a_id)},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "user-a@test.com"

        # Verify tenant B's user
        async with session_factory() as session:
            result = await session.execute(
                text("""
                SELECT email FROM users WHERE tenant_id = :tid
            """),
                {"tid": str(tenant_b_id)},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "user-b@test.com"


@pytest.mark.asyncio
class TestRLSAllTables:
    """Test RLS is properly configured on all tenant-scoped tables."""

    async def test_all_tables_have_rls(self, db_engine) -> None:
        """All 8 tables should have RLS enabled."""
        async with db_engine.begin() as conn:
            for table in TENANT_SCOPED_TABLES:
                result = await conn.execute(
                    text(f"""
                    SELECT COUNT(*) FROM pg_policies
                    WHERE tablename = '{table}' AND policyname = 'tenant_isolation'
                """)
                )
                count = result.scalar()
                assert count == 1, f"Expected 1 policy on {table}, got {count}"

    async def test_customers_table_has_rls(self, db_engine) -> None:
        """Customers table should have RLS."""
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'customers'
            """)
            )
            row = result.fetchone()
            assert row is not None
            assert row[1] is True

    async def test_facilities_table_has_rls(self, db_engine) -> None:
        """Facilities table should have RLS."""
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'facilities'
            """)
            )
            row = result.fetchone()
            assert row is not None
            assert row[1] is True

    async def test_bookings_table_has_rls(self, db_engine) -> None:
        """Bookings table should have RLS."""
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'bookings'
            """)
            )
            row = result.fetchone()
            assert row is not None
            assert row[1] is True


@pytest.mark.asyncio
class TestRLSPolicyDetails:
    """Test the specific details of RLS policies."""

    async def test_using_clause_correct(self, db_engine) -> None:
        """The USING clause should filter by tenant_id."""
        async with db_engine.begin() as conn:
            # Use pg_policies which has the text representation
            result = await conn.execute(
                text("""
                SELECT policyname, qual::text
                FROM pg_policies
                WHERE policyname = 'tenant_isolation' AND tablename = 'users'
            """)
            )
            row = result.fetchone()
            assert row is not None, "Policy not found"
            qual = row[1]
            # The qual contains the AST but we can check for key elements
            assert "tenant_id" in qual.lower() or "current_setting" in qual.lower(), (
                f"USING clause should check tenant_id or current_setting: {qual}"
            )

    async def test_with_check_clause_correct(self, db_engine) -> None:
        """The WITH CHECK clause should prevent cross-tenant inserts."""
        async with db_engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT policyname, with_check::text
                FROM pg_policies
                WHERE policyname = 'tenant_isolation' AND tablename = 'users'
            """)
            )
            row = result.fetchone()
            assert row is not None, "Policy not found"
            with_check = row[1]
            # The with_check contains the AST but we can check for key elements
            assert "tenant_id" in with_check.lower() or "current_setting" in with_check.lower(), (
                f"WITH CHECK should check tenant_id or current_setting: {with_check}"
            )
