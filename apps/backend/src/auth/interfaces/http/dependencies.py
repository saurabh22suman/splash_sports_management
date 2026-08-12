"""HTTP-layer dependencies for authentication.

* [`auth_required`] — extracts and validates the Bearer access token, then
  binds the request context (tenant_id, user_id) so downstream dependencies
  like [`common.application.context.require_tenant_id`] can read it.

This is the bridge between the stateless JWT in the `Authorization` header
and the contextvars-based request context used by services. Without it, the
contextvar is empty for every authenticated request and service-layer guards
like `require_tenant_id` raise "Tenant context required".

For RS256: uses public key from JWT_PUBLIC_KEY_PATH env var (or file).
For HS256 (dev only): uses JWT_SECRET env var.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import jwt
from fastapi import Depends, Header, status
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


def _get_jwt_algorithm() -> str:
    """JWT algorithm from env, defaulting to RS256."""
    return os.environ.get("JWT_ALGORITHM", "RS256")


def _get_public_key() -> str:
    """Return the key/secret used to verify incoming access tokens.

    Production: RS256 only. Requires `JWT_PUBLIC_KEY_PATH`.
    Dev/test:   RS256 (file or ephemeral) or HS256 (requires `JWT_SECRET`,
                ≥32 chars). HS256 is forbidden in production.
    """
    algorithm = _get_jwt_algorithm()
    environment = os.environ.get("ENVIRONMENT", "development")

    if algorithm == "RS256":
        public_key_path = os.environ.get("JWT_PUBLIC_KEY_PATH")
        if public_key_path:
            path = Path(public_key_path)
            if path.is_file():
                return path.read_text(encoding="utf-8").strip()
        if environment == "production":
            msg = "JWT public key not configured. Set JWT_PUBLIC_KEY_PATH."
            raise RuntimeError(msg)
        # Dev/test: ephemeral RS256 keypair per process
        from auth.infrastructure.token_service import RS256TokenService

        _, public_pem = RS256TokenService.generate_ephemeral_keypair()
        return public_pem

    # algorithm == "HS256"
    if environment == "production":
        msg = "HS256 is forbidden in production. Use RS256 with JWT keys."
        raise RuntimeError(msg)
    secret = os.environ.get("JWT_SECRET")
    if not secret or len(secret) < 32:
        msg = "JWT_SECRET must be set and ≥32 chars when JWT_ALGORITHM=HS256"
        raise RuntimeError(msg)
    return secret


def _decode_access_token(token: str) -> CurrentPrincipal:
    """Decode + validate a JWT access token.

    Raises HTTP 401 on any failure (missing/invalid/expired/wrong type).
    Uses RS256 with public key file (production) or HS256 with JWT_SECRET (dev).
    """
    algorithm = _get_jwt_algorithm()
    secret = _get_public_key()
    algorithms = [algorithm]

    try:
        claims = jwt.decode(token, secret, algorithms=algorithms)
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


def requires_role(*allowed_roles: str):
    """FastAPI dependency factory: enforce role-based access control.

    Returns a dependency that checks if the authenticated principal has at least
    one of the specified roles. Raises HTTP 403 if the principal lacks permission.

    Usage:
        @router.post("/invoices", dependencies=[Depends(requires_role("tenant_admin"))])
        async def create_invoice(...):
            ...

    Or as a parameter dependency:
        @router.post("/invoices")
        async def create_invoice(
            principal: CurrentPrincipal = Depends(requires_role("tenant_admin"))
        ):
            ...

    Args:
        *allowed_roles: Role names that are permitted to access the endpoint.

    Returns:
        A FastAPI dependency that enforces role-based authorization.

    Raises:
        HTTPException: 403 if the principal's roles don't include any allowed role.
    """

    def role_checker(
        principal: CurrentPrincipal = Depends(auth_required),
    ) -> CurrentPrincipal:
        """Dependency that validates the principal has an allowed role."""
        principal_has_role = any(role in principal.roles for role in allowed_roles)
        if not principal_has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return principal

    return role_checker
