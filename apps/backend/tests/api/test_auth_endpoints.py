"""API tests for auth endpoints.

Hits the FastAPI app via httpx.AsyncClient. Uses an isolated in-memory SQLite
session for HTTP-layer tests so we don't require a live Postgres. (Real
backend integration tests live in `tests/integration/`.)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_session() -> MagicMock:
    s = MagicMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.get = AsyncMock()
    s.execute = AsyncMock()
    s.delete = AsyncMock()
    s.commit = AsyncMock()
    s.rollback = AsyncMock()
    return s


@pytest_asyncio.fixture
async def client(mock_session) -> AsyncIterator[AsyncClient]:
    """Build the FastAPI app and provide an httpx client.

    We patch the auth service to return controlled results so we can exercise
    the HTTP layer in isolation.
    """
    from auth.interfaces.http import router as auth_router

    # Use the actual app, but override DB dependency to return mock session
    from common.interfaces.http.app import create_app
    from common.infrastructure import db as db_module

    async def override_get_session() -> AsyncIterator[MagicMock]:
        yield mock_session

    app = create_app()
    app.dependency_overrides[db_module.get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
@pytest.mark.api
class TestAuthEndpoints:
    async def test_register_tenant_success(self, client: AsyncClient) -> None:
        # Mock the auth_service to return a controlled result
        from uuid import uuid4

        from common.interfaces.http import app as app_module

        fake_tenant = MagicMock()
        fake_tenant.id = uuid4()
        fake_tenant.slug = "splashh"
        fake_admin = MagicMock()
        fake_admin.id = uuid4()

        mock_svc = MagicMock()
        mock_svc.register_tenant = AsyncMock(return_value=(fake_tenant, fake_admin))

        # Override the dependency for auth_service
        from auth.interfaces.http.router import _auth_service

        app_module.create_app  # ensure module imported
        client._transport.app.dependency_overrides[_auth_service] = lambda: mock_svc

        resp = await client.post(
            "/v1/auth/register-tenant",
            json={
                "tenant_name": "Splashh Sports",
                "tenant_slug": "splashh",
                "primary_contact_email": "contact@splashh.dev",
                "admin_email": "admin@splashh.dev",
                "admin_password": "verysecurepassword123",
                "admin_full_name": "Admin User",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["tenant_slug"] == "splashh"
        assert "tenant_id" in body
        assert "admin_user_id" in body

    async def test_register_tenant_validation_error(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/v1/auth/register-tenant",
            json={
                "tenant_name": "X",  # too short
                "tenant_slug": "BAD_SLUG",
                "primary_contact_email": "not-an-email",
                "admin_email": "also-not-an-email",
                "admin_password": "short",
                "admin_full_name": "",
            },
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "validation_error"
        assert "errors" in body

    async def test_login_returns_token(self, client: AsyncClient) -> None:
        from datetime import datetime, timedelta, timezone
        from uuid import uuid4

        from common.interfaces.http import app as app_module
        from auth.interfaces.http.router import _auth_service

        result = MagicMock()
        result.access_token = "fake-access"
        result.refresh_token = "fake-refresh"
        result.access_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        result.refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        result.user_id = uuid4()
        result.tenant_id = uuid4()
        result.expires_in = 900  # 15 minutes in seconds
        result.refresh_expires_in = 2592000  # 30 days in seconds
        result.customer_id = uuid4()
        result.roles = ["tenant_admin"]

        mock_svc = MagicMock()
        mock_svc.login = AsyncMock(return_value=result)
        client._transport.app.dependency_overrides[_auth_service] = lambda: mock_svc

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "admin@splashh.dev", "password": "verysecurepassword123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "fake-access"
        assert body["refresh_token"] == "fake-refresh"
        assert body["token_type"] == "bearer"

    async def test_login_sets_refresh_cookie(self, client: AsyncClient) -> None:
        from datetime import datetime, timedelta, timezone
        from uuid import uuid4

        from auth.interfaces.http.router import _auth_service

        result = MagicMock()
        result.access_token = "fake-access"
        result.refresh_token = "fake-refresh-jwt"
        result.access_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        result.refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        result.user_id = uuid4()
        result.tenant_id = uuid4()
        result.expires_in = 900
        result.refresh_expires_in = 2592000
        result.customer_id = uuid4()
        result.roles = ["tenant_admin"]

        mock_svc = MagicMock()
        mock_svc.login = AsyncMock(return_value=result)
        client._transport.app.dependency_overrides[_auth_service] = lambda: mock_svc

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "admin@splashh.dev", "password": "verysecurepassword123"},
        )
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        assert "refresh_token=fake-refresh-jwt" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie or "SameSite=Lax" in set_cookie
        assert "Path=/v1/auth" in set_cookie

    async def test_refresh_via_cookie(self, client: AsyncClient) -> None:
        from datetime import datetime, timedelta, timezone
        from uuid import uuid4

        from auth.interfaces.http.router import _auth_service

        result = MagicMock()
        result.access_token = "new-access"
        result.refresh_token = "new-refresh-jwt"
        result.access_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        result.refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        result.user_id = uuid4()
        result.tenant_id = uuid4()
        result.expires_in = 900
        result.refresh_expires_in = 2592000
        result.customer_id = uuid4()
        result.roles = ["tenant_admin"]

        mock_svc = MagicMock()
        mock_svc.refresh = AsyncMock(return_value=result)
        client._transport.app.dependency_overrides[_auth_service] = lambda: mock_svc

        resp = await client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": "cookie-jwt-value"},
        )
        assert resp.status_code == 200
        # The cookie was used as the refresh source
        mock_svc.refresh.assert_awaited_once_with(refresh_token="cookie-jwt-value")
        # And a new cookie was set
        assert "refresh_token=new-refresh-jwt" in resp.headers.get("set-cookie", "")

    async def test_refresh_via_body_still_works(self, client: AsyncClient) -> None:
        from datetime import datetime, timedelta, timezone
        from uuid import uuid4

        from auth.interfaces.http.router import _auth_service

        result = MagicMock()
        result.access_token = "new-access"
        result.refresh_token = "new-refresh-jwt"
        result.access_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        result.refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        result.user_id = uuid4()
        result.tenant_id = uuid4()
        result.expires_in = 900
        result.refresh_expires_in = 2592000
        result.customer_id = uuid4()
        result.roles = ["tenant_admin"]

        mock_svc = MagicMock()
        mock_svc.refresh = AsyncMock(return_value=result)
        client._transport.app.dependency_overrides[_auth_service] = lambda: mock_svc

        resp = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "body-jwt-value"},
        )
        assert resp.status_code == 200
        mock_svc.refresh.assert_awaited_once_with(refresh_token="body-jwt-value")

    async def test_logout_clears_cookie(self, client: AsyncClient) -> None:
        from auth.interfaces.http.router import _auth_service

        mock_svc = MagicMock()
        mock_svc.logout = AsyncMock()
        client._transport.app.dependency_overrides[_auth_service] = lambda: mock_svc

        resp = await client.post(
            "/v1/auth/logout",
            cookies={"refresh_token": "to-revoke"},
        )
        assert resp.status_code == 204
        mock_svc.logout.assert_awaited_once_with(refresh_token="to-revoke")
        set_cookie = resp.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie
        assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()

    async def test_login_invalid_credentials_returns_401(self, client: AsyncClient) -> None:
        from common.interfaces.http import app as app_module
        from auth.interfaces.http.router import _auth_service
        from common.domain.exceptions import Unauthorized

        mock_svc = MagicMock()
        mock_svc.login = AsyncMock(side_effect=Unauthorized("Invalid credentials"))
        client._transport.app.dependency_overrides[_auth_service] = lambda: mock_svc

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "admin@splashh.dev", "password": "verysecurepassword123"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["code"] == "unauthorized"

    async def test_login_response_includes_roles(self, client: AsyncClient) -> None:
        from datetime import datetime, timedelta, timezone
        from uuid import uuid4

        from auth.interfaces.http.router import _auth_service

        result = MagicMock()
        result.access_token = "fake-access"
        result.refresh_token = "fake-refresh"
        result.access_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        result.refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        result.user_id = uuid4()
        result.tenant_id = uuid4()
        result.expires_in = 900
        result.refresh_expires_in = 2592000
        result.customer_id = uuid4()
        result.roles = ["tenant_admin", "customer"]

        mock_svc = MagicMock()
        mock_svc.login = AsyncMock(return_value=result)
        client._transport.app.dependency_overrides[_auth_service] = lambda: mock_svc

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "admin@splashh.dev", "password": "verysecurepassword123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["roles"] == ["tenant_admin", "customer"]

    async def test_healthz(self, client: AsyncClient) -> None:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_admin_can_create_user(self, client: AsyncClient) -> None:
        from uuid import uuid4

        from auth.interfaces.http.router import _auth_service, _user_admin_service
        from auth.interfaces.http.dependencies import auth_required

        # Mock auth service to return a principal with tenant_admin
        principal = MagicMock()
        principal.tenant_id = uuid4()
        principal.roles = ["tenant_admin"]

        # The route uses Depends(auth_required) which is in auth.dependencies.
        # We override it directly.
        client._transport.app.dependency_overrides[auth_required] = lambda: principal

        new_user = MagicMock()
        new_user.id = uuid4()
        new_user.email = "newuser@example.com"
        new_user.full_name = "New User"
        new_user.roles = [MagicMock(value="customer")]

        admin_svc = MagicMock()
        admin_svc.create_user = AsyncMock(return_value=new_user)
        client._transport.app.dependency_overrides[_user_admin_service] = lambda: admin_svc

        resp = await client.post(
            "/v1/auth/users",
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "verysecurepassword123",
                "roles": ["customer"],
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["email"] == "newuser@example.com"
        assert body["roles"] == ["customer"]
        admin_svc.create_user.assert_awaited_once()

    async def test_non_admin_cannot_create_user(self, client: AsyncClient) -> None:
        from uuid import uuid4

        from auth.interfaces.http.dependencies import auth_required

        principal = MagicMock()
        principal.tenant_id = uuid4()
        principal.roles = ["customer"]

        client._transport.app.dependency_overrides[auth_required] = lambda: principal

        resp = await client.post(
            "/v1/auth/users",
            json={
                "email": "x@example.com",
                "full_name": "X",
                "password": "verysecurepassword123",
                "roles": ["customer"],
            },
        )
        assert resp.status_code == 403

    async def test_create_user_validates_role(self, client: AsyncClient) -> None:
        from uuid import uuid4

        from auth.interfaces.http.dependencies import auth_required

        principal = MagicMock()
        principal.tenant_id = uuid4()
        principal.roles = ["tenant_admin"]
        client._transport.app.dependency_overrides[auth_required] = lambda: principal

        resp = await client.post(
            "/v1/auth/users",
            json={
                "email": "x@example.com",
                "full_name": "X",
                "password": "verysecurepassword123",
                "roles": ["tenant_admin"],
            },
        )
        assert resp.status_code == 422

    async def test_create_user_duplicate_email_409(self, client: AsyncClient) -> None:
        from uuid import uuid4

        from auth.interfaces.http.dependencies import auth_required
        from auth.interfaces.http.router import _user_admin_service
        from common.domain.exceptions import Conflict

        principal = MagicMock()
        principal.tenant_id = uuid4()
        principal.roles = ["tenant_admin"]
        client._transport.app.dependency_overrides[auth_required] = lambda: principal

        admin_svc = MagicMock()
        admin_svc.create_user = AsyncMock(
            side_effect=Conflict(
                "User with that email already exists", details={"email": "dup@example.com"}
            )
        )
        client._transport.app.dependency_overrides[_user_admin_service] = lambda: admin_svc

        resp = await client.post(
            "/v1/auth/users",
            json={
                "email": "dup@example.com",
                "full_name": "Dup",
                "password": "verysecurepassword123",
                "roles": ["customer"],
            },
        )
        assert resp.status_code == 409

    async def test_admin_can_list_users(self, client: AsyncClient) -> None:
        import datetime as dt

        from uuid import uuid4

        from auth.interfaces.http.dependencies import auth_required
        from auth.interfaces.http.router import _user_admin_service

        principal = MagicMock()
        principal.tenant_id = uuid4()
        principal.roles = ["tenant_admin"]
        client._transport.app.dependency_overrides[auth_required] = lambda: principal

        admin_svc = MagicMock()
        admin_svc.list_users = AsyncMock(
            return_value=[
                MagicMock(
                    id=uuid4(),
                    email="a@x.com",
                    full_name="A",
                    roles=[MagicMock(value="customer")],
                    is_active=True,
                    created_at=dt.datetime.now(dt.timezone.utc),
                ),
            ]
        )
        client._transport.app.dependency_overrides[_user_admin_service] = lambda: admin_svc

        resp = await client.get("/v1/auth/users")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)
        assert resp.json()["data"][0]["email"] == "a@x.com"

    async def test_non_admin_cannot_list_users(self, client: AsyncClient) -> None:
        from uuid import uuid4

        from auth.interfaces.http.dependencies import auth_required

        principal = MagicMock()
        principal.tenant_id = uuid4()
        principal.roles = ["customer"]

        client._transport.app.dependency_overrides[auth_required] = lambda: principal

        resp = await client.get("/v1/auth/users")
        assert resp.status_code == 403
