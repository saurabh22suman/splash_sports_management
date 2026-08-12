"""Per-request context.

We use [`contextvars`](https://docs.python.org/3/library/contextvars.html) so that
async tasks spawned by a request inherit tenant_id, request_id, and user_id without
threading them through every function signature.

> **Why contextvars?** FastAPI/Starlette runs each request in its own asyncio task.
> Module-level context variables let domain code ask "who is calling me?" without
> polluting signatures. Tests can override context via [`set_test_context`].
"""
from __future__ import annotations

import secrets
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Self

from common.domain.types import TenantId, UserId


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Immutable per-request context.

    Attributes:
        request_id: ULID-ish unique id for the request. Logged with every record.
        tenant_id: The tenant the request belongs to. None for unauthenticated routes.
        user_id: The authenticated user. None for public routes.
        trace_id: OpenTelemetry trace id if OTel is enabled.
    """

    request_id: str
    tenant_id: TenantId | None = None
    user_id: UserId | None = None
    trace_id: str | None = None

    @classmethod
    def new(cls, *, tenant_id: TenantId | None = None, user_id: UserId | None = None) -> Self:
        return cls(
            request_id=secrets.token_urlsafe(12),
            tenant_id=tenant_id,
            user_id=user_id,
        )


_request_ctx: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def get_context() -> RequestContext | None:
    return _request_ctx.get()


def require_context() -> RequestContext:
    ctx = _request_ctx.get()
    if ctx is None:
        msg = "No request context bound. Did you forget the middleware?"
        raise RuntimeError(msg)
    return ctx


def require_tenant_id() -> TenantId:
    ctx = require_context()
    if ctx.tenant_id is None:
        from common.domain.exceptions import Unauthorized

        raise Unauthorized("Tenant context required")
    return ctx.tenant_id


def require_user_id() -> UserId:
    ctx = require_context()
    if ctx.user_id is None:
        from common.domain.exceptions import Unauthorized

        raise Unauthorized("Authentication required")
    return ctx.user_id


def bind_context(ctx: RequestContext) -> None:
    """Set the current request context. Called by middleware."""
    _request_ctx.set(ctx)


def reset_context() -> None:
    _request_ctx.set(None)


def new_request_id() -> str:
    """Generate a fresh request id. Used by middleware at request start."""
    return uuid.uuid4().hex
