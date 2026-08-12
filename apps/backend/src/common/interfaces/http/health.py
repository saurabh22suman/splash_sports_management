"""Health and readiness endpoints.

* `/healthz` — liveness; always 200 if the process is up.
* `/readyz` — readiness; checks DB + Redis connectivity.

These are unauthenticated by design so load balancers and orchestrators can
probe them.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import text

from common.infrastructure.db import get_session_factory

router = APIRouter(tags=["health"])


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness() -> dict[str, object]:
    checks: dict[str, str] = {}
    overall_ok = True

    # DB
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        overall_ok = False
        checks["database"] = f"error: {exc.__class__.__name__}"

    return {
        "status": "ok" if overall_ok else "degraded",
        "checks": checks,
    }
