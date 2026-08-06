"""HTTP router for auth endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.auth_service import AuthService, build_auth_service
from auth.interfaces.http.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterTenantRequest,
    RegisterTenantResponse,
    TokenResponse,
)
from common.domain.exceptions import Unauthorized
from common.infrastructure.db import get_session

router = APIRouter()


def _auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    from common.infrastructure.settings import get_settings

    return build_auth_service(session, get_settings())


def _to_token_response(result) -> TokenResponse:  # type: ignore[no-untyped-def]
    import datetime as _dt

    access_in = int((result.access_expires_at - _dt.datetime.now(_dt.timezone.utc)).total_seconds())
    refresh_in = int((result.refresh_expires_at - _dt.datetime.now(_dt.timezone.utc)).total_seconds())
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=max(access_in, 0),
        refresh_expires_in=max(refresh_in, 0),
        user_id=result.user_id,
        tenant_id=result.tenant_id,
    )


@router.post(
    "/register-tenant",
    response_model=RegisterTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_tenant(
    payload: RegisterTenantRequest,
    svc: AuthService = Depends(_auth_service),
) -> RegisterTenantResponse:
    tenant, admin = await svc.register_tenant(
        tenant_name=payload.tenant_name,
        tenant_slug=payload.tenant_slug,
        primary_contact_email=payload.primary_contact_email,
        admin_email=payload.admin_email,
        admin_password=payload.admin_password,
        admin_full_name=payload.admin_full_name,
    )
    return RegisterTenantResponse(
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        admin_user_id=admin.id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    svc: AuthService = Depends(_auth_service),
) -> TokenResponse:
    result = await svc.login(email=payload.email, password=payload.password)
    return _to_token_response(result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    svc: AuthService = Depends(_auth_service),
) -> TokenResponse:
    result = await svc.refresh(refresh_token=payload.refresh_token)
    return _to_token_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    svc: AuthService = Depends(_auth_service),
) -> None:
    await svc.logout(refresh_token=payload.refresh_token)
    return None
