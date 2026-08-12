"""FastAPI application factory.

Usage:
    uvicorn common.interfaces.http.app:create_app --factory

The factory pattern lets tests create isolated app instances with overridden
dependencies.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import payments models to register them with Base.metadata
from payments.infrastructure import models as _payments_models  # noqa: F401

from common.infrastructure.db import dispose_engine, init_engine
from common.infrastructure.logging import configure_logging, get_logger
from common.infrastructure.middleware import RequestContextMiddleware
from common.infrastructure.settings import get_settings
from common.interfaces.http.errors import register_error_handlers
from common.interfaces.http.health import router as health_router

_logger = get_logger(__name__)


def _create_openapi_metadata() -> dict[str, object]:
    return {
        "title": "Splashh Sports Platform API",
        "version": "0.1.0",
        "description": (
            "Multi-tenant Sports Club Management Platform API. "
            "All endpoints require authentication unless explicitly marked public."
        ),
        "contact": {"name": "Platform Engineering", "email": "platform@splashh.dev"},
        "license_info": {"name": "Proprietary"},
    }


def create_app() -> FastAPI:
    """Build a FastAPI app with all infrastructure wired up."""
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.environment != "development")
    _logger.info("app_starting", environment=settings.environment, debug=settings.debug)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Initialize database engine
        await init_engine(settings)
        _logger.info("engine_initialised")

        # --- Startup-time validation for dev payment simulator ---
        if settings.dev_payment_simulator_enabled:
            if settings.environment == "production":
                raise RuntimeError(
                    "DEV_PAYMENT_SIMULATOR_ENABLED must be False when ENVIRONMENT=production"
                )
            if (
                settings.environment != "development"
                and settings.dev_state_secret == "dev-state-secret-change-me"
            ):
                raise RuntimeError(
                    "DEV_STATE_SECRET must be set (not the default) when "
                    "DEV_PAYMENT_SIMULATOR_ENABLED=true and ENVIRONMENT != development"
                )
            if (
                settings.environment == "development"
                and settings.dev_state_secret == "dev-state-secret-change-me"
            ):
                _logger.warning("dev_state_secret_using_default")

        # Initialize payment provider and event bus
        from common.application.events import InProcessEventPublisher
        from payments.application.devsim_adapter import DevSimAdapter
        from payments.application.provider import RazorpayAdapter

        app.state.event_bus = InProcessEventPublisher()
        if settings.dev_payment_simulator_enabled:
            app.state.payment_provider = DevSimAdapter(
                app_url=settings.app_url,
                dev_state_secret=settings.dev_state_secret,
                webhook_secret=settings.razorpay_webhook_secret,
            )
            _logger.warning(
                "payment_simulator_active",
                provider="devsim",
                environment=settings.environment,
            )
        else:
            app.state.payment_provider = RazorpayAdapter(
                key_id=settings.razorpay_key_id,
                key_secret=settings.razorpay_key_secret,
                webhook_secret=settings.razorpay_webhook_secret,
            )
        _logger.info("payment_provider_initialised", provider=type(app.state.payment_provider).__name__)

        try:
            yield
        finally:
            # Dispose database engine
            await dispose_engine()
            _logger.info("engine_disposed")

    app = FastAPI(
        **_create_openapi_metadata(),
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
    )

    # Middleware (order matters: outermost first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_error_handlers(app)
    app.include_router(health_router)

    _register_module_routers(app)

    _logger.info("app_ready")
    return app


def _register_module_routers(app: FastAPI) -> None:
    """Mount each module's HTTP router under `/v1/<module>`.

    Each module's router owns its own resource-relative paths (`""`, `/{id}`,
    `/{id}/cancel`, etc.) — the shared prefix adds the module namespace.
    This keeps URLs like `/v1/bookings/{id}/cancel` while letting each module
    router stay self-contained. We import lazily so a broken module doesn't
    prevent the app from booting.
    """
    settings = get_settings()
    for module_name in ("auth", "customer", "facility", "booking", "payments"):
        try:
            module = __import__(module_name, fromlist=["interfaces"])
            router = getattr(module.interfaces, "router", None)  # type: ignore[attr-defined]
        except (ImportError, AttributeError):
            continue
        if router is None:
            continue
        app.include_router(router, prefix=f"/v1/{module_name}", tags=[module_name])

    # Dev payment simulator (gated by env flag, never mounted in prod).
    if settings.dev_payment_simulator_enabled:
        try:
            from payments.interfaces.http.devsim_router import router as devsim_router

            # Mount WITHOUT additional prefix - router already has prefix="/dev/mock-checkout"
            app.include_router(devsim_router)
        except ImportError:
            _logger.warning("devsim_router_unavailable")
