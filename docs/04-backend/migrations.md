# Migrations

> This document covers Alembic migration patterns, naming conventions, safe migration strategies, and online migration techniques.

## Overview

We use **Alembic** for database schema migrations. Migrations are version-controlled, testable, and designed for safe execution in production.

## Alembic Setup

```python
# alembic/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from common.config import get_settings
from database import Base

# Import all models to register them with Base
from booking.infrastructure.models import BookingModel
from customer.infrastructure.models import CustomerModel
from membership.infrastructure.models import MembershipModel
from facility.infrastructure.models import FacilityModel

config = context.config
settings = get_settings()

# Set SQLAlchemy URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## Naming Convention

> **Rule** — Migration filenames follow `<timestamp>_<operation>_<table>.py` format.

```
alembic/
├── env.py
├── script.py.mako
└── versions/
    ├── 2024_01_15_0001_create_bookings_table.py
    ├── 2024_01_15_0002_add_customer_id_to_bookings.py
    ├── 2024_01_16_0001_add_booking_status_index.py
    └── 2024_01_20_0001_create_memberships_table.py
```

## Migration Template

```python
"""Add booking status column

Revision ID: 2024_01_15_0002
Revises: 2024_01_15_0001
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '2024_01_15_0002'
down_revision: Union[str, None] = '2024_01_15_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status column to bookings table."""
    op.add_column(
        'bookings',
        sa.Column('status', sa.String(20), nullable=False, server_default='pending')
    )

    # Add index for status queries
    op.create_index(
        'idx_bookings_status',
        'bookings',
        ['status'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade() -> None:
    """Remove status column from bookings table."""
    op.drop_index('idx_bookings_status', 'bookings')
    op.drop_column('bookings', 'status')
```

## Safe Online Migrations

### Add Nullable Column

```python
def upgrade() -> None:
    # Step 1: Add nullable column
    op.add_column(
        'bookings',
        sa.Column('notes', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('bookings', 'notes')
```

### Add Column with Default

```python
def upgrade() -> None:
    # Step 1: Add nullable column first
    op.add_column(
        'bookings',
        sa.Column('version', sa.Integer(), nullable=True)
    )

    # Step 2: Backfill existing rows in batches
    # This should be done via a separate script for large tables
    # Or use op.execute() with caution
    op.execute("""
        UPDATE bookings
        SET version = 1
        WHERE version IS NULL
    """)

    # Step 3: Alter to NOT NULL
    op.alter_column('bookings', 'version', nullable=False)


def downgrade() -> None:
    op.drop_column('bookings', 'version')
```

### Add Foreign Key

```python
def upgrade() -> None:
    # Add nullable FK first
    op.add_column(
        'bookings',
        sa.Column('facility_id', sa.UUID(), nullable=True)
    )

    # Backfill
    op.execute("""
        UPDATE bookings b
        SET facility_id = f.id
        FROM facilities f
        WHERE b.facility_name = f.name
    """)

    # Add NOT NULL constraint
    op.alter_column('bookings', 'facility_id', nullable=False)

    # Add FK constraint
    op.create_foreign_key(
        'fk_bookings_facility_id',
        'bookings', 'facilities',
        ['facility_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_bookings_facility_id', 'bookings')
    op.drop_column('bookings', 'facility_id')
```

### Rename Table

```python
def upgrade() -> None:
    # Rename table
    op.rename_table('bookings', 'reservations')

    # Update all references in the codebase FIRST
    # Then add alias for backward compatibility
    op.create_table(
        'bookings',
        op.create_table('reservations').select()
    )


def downgrade() -> None:
    op.drop_table('bookings')
    op.rename_table('reservations', 'bookings')
```

### Concurrent Index Creation

```python
def upgrade() -> None:
    # Don't lock the table with a regular index
    op.create_index(
        'idx_bookings_customer_date',
        'bookings',
        ['customer_id', 'slot_date'],
        postgresql_concurrently=True  # Requires PostgreSQL 12+
    )


def downgrade() -> None:
    op.drop_index(
        'idx_bookings_customer_date',
        'bookings',
        postgresql_concurrently=True
    )
```

### Rename Column

```python
def upgrade() -> None:
    # Add new column
    op.add_column(
        'bookings',
        sa.Column('facility_id', sa.UUID(), nullable=True)
    )

    # Copy data
    op.execute("""
        UPDATE bookings
        SET facility_id = old_facility_id
    """)

    # Drop old column
    op.drop_column('bookings', 'old_facility_id')


def downgrade() -> None:
    # Reverse the process
    pass
```

## Migration Testing

```python
# tests/alembic/test_migrations.py
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text


def test_migration_up_down(tmp_path):
    """Test that migration can go up and down."""
    # Create test database
    engine = create_engine("sqlite:///:memory:")

    # Get Alembic config
    alembic_cfg = Config("alembic.ini")

    # Run upgrade
    command.upgrade(alembic_cfg, "+1")

    # Verify tables exist
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        assert "bookings" in tables

    # Run downgrade
    command.downgrade(alembic_cfg, "-1")

    # Verify tables are gone
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        assert "bookings" not in tables
```

## Migration Best Practices

> **Rule** — Never destructive in production without a clear plan.

| Scenario | Strategy |
|----------|----------|
| Add column | Nullable first, backfill, NOT NULL |
| Remove column | Deprecate in code, wait 1 release, remove |
| Rename table | Create new, copy data, switch, drop old |
| Drop table | Archive data first, confirm no refs |
| Large data migration | Run in batches during low traffic |
| Locking operations | Use `CONCURRENTLY` for PostgreSQL |

## Long-Running Migration Strategy

For migrations that take > 30 seconds:

1. **Plan** — Document in ticket, estimate time
2. **Schedule** — Run during low-traffic window
3. **Test** — Run on staging first with production-like data
4. **Monitor** — Watch query performance
5. **Rollback** — Have downgrade ready

```python
# Example: Large table backfill
def upgrade() -> None:
    # Use batched updates to avoid long locks
    BATCH_SIZE = 1000

    while True:
        result = op.execute(f"""
            UPDATE bookings
            SET version = 1
            WHERE version IS NULL
            LIMIT {BATCH_SIZE}
        """)
        if result.rowcount < BATCH_SIZE:
            break
```

## CI/CD Integration

```yaml
# .github/workflows/ci.yml
- name: Run migrations
  run: |
    alembic upgrade head
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

## Related Documents

- [Database Migrations](../06-database/migrations.md)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Online DDL](https://www.postgresql.org/docs/current/sql-altertable.html)
