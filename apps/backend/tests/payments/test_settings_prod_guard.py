"""Startup-time validation: dev simulator must never run in production, and
must never use the default secret outside development.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI


def test_prod_env_with_simulator_enabled_raises_on_app_creation(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_PAYMENT_SIMULATOR_ENABLED", "true")
    monkeypatch.setenv("DEV_STATE_SECRET", "any-real-secret-32chars-or-more-xxx")

    from common.infrastructure.settings import reset_settings_cache, get_settings

    reset_settings_cache()
    settings = get_settings()
    assert settings.environment == "production"
    assert settings.dev_payment_simulator_enabled is True

    from common.interfaces.http.app import create_app

    app = create_app()

    # Trigger lifespan manually - this runs the startup validation
    with pytest.raises(RuntimeError, match="DEV_PAYMENT_SIMULATOR_ENABLED must be False"):
        asyncio.run(_run_lifespan(app))


def test_non_dev_env_with_simulator_enabled_and_default_secret_raises(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DEV_PAYMENT_SIMULATOR_ENABLED", "true")
    monkeypatch.setenv("DEV_STATE_SECRET", "dev-state-secret-change-me")

    from common.infrastructure.settings import reset_settings_cache

    reset_settings_cache()

    from common.interfaces.http.app import create_app

    app = create_app()

    # Trigger lifespan manually - this runs the startup validation
    with pytest.raises(RuntimeError, match="DEV_STATE_SECRET must be set"):
        asyncio.run(_run_lifespan(app))


def test_dev_env_with_simulator_and_default_secret_does_not_raise(monkeypatch):
    """Sanity check: dev + simulator + default secret is allowed (with warning)."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_PAYMENT_SIMULATOR_ENABLED", "true")
    monkeypatch.setenv("DEV_STATE_SECRET", "dev-state-secret-change-me")

    from common.infrastructure.settings import reset_settings_cache

    reset_settings_cache()

    from common.interfaces.http.app import create_app

    app = create_app()

    # Trigger lifespan - should not raise
    asyncio.run(_run_lifespan(app))

    # The devsim router should be mounted - check via original_router
    devsim_mounted = False
    for route in app.routes:
        if hasattr(route, "original_router"):
            orig = route.original_router
            if hasattr(orig, "routes"):
                for r in orig.routes:
                    if hasattr(r, "path") and "/dev/mock-checkout" in r.path:
                        devsim_mounted = True
                        break
        if devsim_mounted:
            break

    assert devsim_mounted, "Expected /dev/mock-checkout route to be mounted"


def test_devsim_routes_not_mounted_when_flag_false(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_PAYMENT_SIMULATOR_ENABLED", "false")

    from common.infrastructure.settings import reset_settings_cache

    reset_settings_cache()

    from common.interfaces.http.app import create_app

    app = create_app()

    # The devsim router should NOT be mounted
    devsim_mounted = False
    for route in app.routes:
        if hasattr(route, "original_router"):
            orig = route.original_router
            if hasattr(orig, "routes"):
                for r in orig.routes:
                    if hasattr(r, "path") and "/dev/mock-checkout" in r.path:
                        devsim_mounted = True
                        break
        if devsim_mounted:
            break

    assert not devsim_mounted, "Expected no /dev/mock-checkout route when flag is false"


async def _run_lifespan(app: FastAPI) -> None:
    """Run the app's lifespan context to trigger startup validation."""
    async with app.router.lifespan_context(app):
        pass
