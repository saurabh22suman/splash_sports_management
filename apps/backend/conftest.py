"""Pytest fixtures shared across all test types.

Test isolation: each test gets its own DB transaction that rolls back at the
end. We use testcontainers for Postgres + Redis in CI; locally you can also
point at a running docker-compose stack via the environment variables below.

The fixture layer hides infrastructure details so individual tests can be
written against the high-level API of each module.
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio

# Ensure the test config is in place before importing the app
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "")

# When HS256 is selected we need a symmetric secret
os.environ.setdefault("JWT_SECRET", "test-secret-key-only-for-unit-tests-do-not-use-in-prod")
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_PRIVATE_KEY_PATH"] = ""
os.environ["JWT_PUBLIC_KEY_PATH"] = ""

from common.infrastructure.settings import get_settings, reset_settings_cache  # noqa: E402

reset_settings_cache()


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _reset_settings() -> Iterator[None]:
    """Force fresh settings per-test when env vars change."""
    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest_asyncio.fixture
async def settings() -> Any:
    return get_settings()


@pytest_asyncio.fixture
async def app():
    """Build a FastAPI app for API tests."""
    from common.interfaces.http.app import create_app

    return create_app()
