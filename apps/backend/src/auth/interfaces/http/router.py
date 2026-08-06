"""HTTP router for auth endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.auth_service import AuthService, build_auth_service
from auth.application.user_admin_service import UserAdminService
from auth.infrastructure.password_hasher import Argon2PasswordHasher
from auth.infrastructure.repositories import UserRepository
from auth.interfaces.http.dependencies import auth_required, CurrentPrincipal
from auth.interfaces.http.schemas import (
    CreateUserRequest,
    CreateUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterTenantRequest,
    RegisterTenantResponse,
    TokenResponse,
    UserListItem,
    UserListResponse,
)
from common.domain.exceptions import Forbidden, Unauthorized
from common.infrastructure.db import get_session
from common.infrastructure.settings import get_settings

router = APIRouter()


def _auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
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
        roles=getattr(result, "roles", []),
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Attach the refresh token as an httpOnly cookie scoped to /v1/auth."""
    s = get_settings()
    response.set_cookie(
        key=s.auth_refresh_cookie_name,
        value=token,
        max_age=s.auth_refresh_cookie_max_age_seconds,
        path=s.auth_refresh_cookie_path,
        secure=s.auth_refresh_cookie_secure,
        httponly=True,
        samesite=s.auth_refresh_cookie_samesite,
    )


def _extract_refresh(request: Request, body: RefreshRequest | None) -> str:
    """Read the refresh token from cookie (preferred) or JSON body."""
    s = get_settings()
    cookie_token = request.cookies.get(s.auth_refresh_cookie_name)
    if cookie_token:
        return cookie_token
    if body and body.refresh_token:
        return body.refresh_token
    raise HTTPException(status_code=422, detail="Missing refresh token")


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
    response: Response,
    svc: AuthService = Depends(_auth_service),
) -> TokenResponse:
    result = await svc.login(email=payload.email, password=payload.password)
    _set_refresh_cookie(response, result.refresh_token)
    return _to_token_response(result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = Body(default=None),
    svc: AuthService = Depends(_auth_service),
) -> TokenResponse:
    token = _extract_refresh(request, payload)
    result = await svc.refresh(refresh_token=token)
    _set_refresh_cookie(response, result.refresh_token)
    return _to_token_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    payload: LogoutRequest | None = Body(default=None),
    svc: AuthService = Depends(_auth_service),
) -> None:
    s = get_settings()
    cookie_token = request.cookies.get(s.auth_refresh_cookie_name)
    body_token = payload.refresh_token if payload else None
    token = cookie_token or body_token
    if token:
        await svc.logout(refresh_token=token)
    response.delete_cookie(key=s.auth_refresh_cookie_name, path=s.auth_refresh_cookie_path)
    return None


def _user_admin_service(
    session: AsyncSession = Depends(get_session),
    principal: CurrentPrincipal = Depends(auth_required),
) -> UserAdminService:
    return UserAdminService(
        users=UserRepository(session),
        hasher=Argon2PasswordHasher(),
        tenant_id=principal.tenant_id,
    )


@router.post("/users", response_model=CreateUserResponse, status_code=201)
async def create_user(
    payload: CreateUserRequest,
    principal: CurrentPrincipal = Depends(auth_required),
    svc: UserAdminService = Depends(_user_admin_service),
) -> CreateUserResponse:
    if "tenant_admin" not in principal.roles:
        raise Forbidden("Only tenant admins can create users")
    from auth.domain.entities import UserRole

    user = await svc.create_user(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        roles=[UserRole(r) for r in payload.roles],
    )
    return CreateUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=[r.value for r in user.roles],
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    principal: CurrentPrincipal = Depends(auth_required),
    svc: UserAdminService = Depends(_user_admin_service),
) -> UserListResponse:
    if "tenant_admin" not in principal.roles:
        raise Forbidden("Only tenant admins can list users")
    users = await svc.list_users()
    return UserListResponse(
        data=[
            UserListItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                roles=[r.value for r in u.roles],
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in users
        ]
    )


