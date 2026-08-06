"""Alembic environment configuration.

Uses our async engine and reads the URL from settings. All ORM models that
subclass `Base` are auto-imported so `alembic revision --autogenerate` can
detect schema drift.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

# Ensure backend package is importable when running `alembic` from repo root
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from common.infrastructure.db import Base  # noqa: E402
from common.infrastructure.settings import get_settings  # noqa: E402

# Import all modules so their models register on Base.metadata
from auth.infrastructure import models as _auth_models  # noqa: E402, F401
from customer.infrastructure import models as _customer_models  # noqa: E402, F401
from facility.infrastructure import models as _facility_models  # noqa: E402, F401
from booking.infrastructure import models as _booking_models  # noqa: E402, F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a DB connection (emit SQL)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations using a sync connection under the hood."""
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
