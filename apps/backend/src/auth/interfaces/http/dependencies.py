"""HTTP-layer dependencies for authentication.

* [`auth_required`] — extracts and validates the Bearer access token, then
  binds the request context (tenant_id, user_id) so downstream dependencies
  like [`common.application.context.require_tenant_id`] can read it.

This is the bridge between the stateless JWT in the `Authorization` header
and the contextvars-based request context used by services. Without it, the
contextvar is empty for every authenticated request and service-layer guards
like `require_tenant_id` raise "Tenant context required".
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import Header, status
from fastapi.exceptions import HTTPException

from common.application.context import RequestContext, bind_context
from common.domain.types import TenantId, UserId


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    """The authenticated caller extracted from the access token.

    Returned by [`auth_required`] so route handlers can inspect the caller
    without reaching into contextvars themselves.
    """

    user_id: UserId
    tenant_id: TenantId
    roles: tuple[str, ...]
    jti: str


def _decode_access_token(token: str) -> CurrentPrincipal:
    """Decode + validate a JWT access token.

    Raises HTTP 401 on any failure (missing/invalid/expired/wrong type).
    The signing secret is taken from `JWT_SECRET` to match the dev fallback
    in [`auth.application.auth_service.build_auth_service`].
    """
    secret = os.environ.get(
        "JWT_SECRET", "dev-only-jwt-secret-change-me-in-prod-please-32chars"
    )
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc

    if claims.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not an access token",
        )

    try:
        user_id = UserId(claims["sub"])
        tenant_id = TenantId(claims["tenant_id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed access token claims",
        ) from exc

    roles_raw = claims.get("roles") or []
    if not isinstance(roles_raw, list):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed access token claims",
        )

    jti = str(claims.get("jti") or "")
    return CurrentPrincipal(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=tuple(str(r) for r in roles_raw),
        jti=jti,
    )


def auth_required(
    authorization: str | None = Header(default=None),
) -> CurrentPrincipal:
    """FastAPI dependency: require a valid Bearer access token.

    Sets `tenant_id` and `user_id` on the request context so any service
    code that calls `require_tenant_id()` / `require_user_id()` works
    without further plumbing.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    principal = _decode_access_token(token)

    # Bind to context so require_tenant_id / require_user_id work downstream.
    bind_context(
        RequestContext(
            request_id="",  # filled in by RequestContextMiddleware at start
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
        )
    )
    return principal


def auth_tenant(
    principal: CurrentPrincipal = __import__("fastapi").Depends(auth_required),
):
    """FastAPI dependency: authenticated tenant id.

    Wraps [`auth_required`] so FastAPI's dependency resolver runs the
    token validation FIRST, then returns the tenant id. Using this in
    route signatures is preferred over `Depends(require_tenant_id)`
    because the latter reads from a contextvar and could race against
    the bind performed by `auth_required`.

    For convenience this also returns the principal via a side-channel
    so other deps in the same request share it.
    """
    return principal.tenant_id
