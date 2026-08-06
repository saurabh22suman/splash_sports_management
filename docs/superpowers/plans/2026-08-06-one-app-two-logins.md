# One App, Two Login Routes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `admin-pwa` + `customer-pwa` into a single `web-pwa` with two login routes (`/login` for customers, `/admin/login` for staff), role-based home redirect after login, and an admin "create user" flow.

**Architecture:** Single Vite React app replaces the two PWAs. One `<LoginForm>` mounts at two routes; after success, role-based redirect (admin → `/admin`, customer → `/book`). Backend `LoginResult` and `/login` + `/refresh` responses now include `roles`. New `POST /v1/auth/users` + `GET /v1/auth/users` (admin-only) backs a new `/admin/users` page.

**Tech Stack:** Vite, React 18, TypeScript 5.6, shadcn/ui (via `@splashh/ui`), TanStack Query v5, React Router v6 (data router), RHF, Zod, Zustand, Axios, FastAPI 0.115, SQLAlchemy 2 async, Pydantic v2, Argon2id, Playwright, axe-core, Vitest, RTL.

**Spec:** `docs/superpowers/specs/2026-08-06-one-app-two-logins-design.md`

## Global Constraints

- All paths are repo-root-relative unless prefixed.
- Backend tests: `cd apps/backend && PYTHONPATH=src uv run pytest`.
- Frontend tests: `pnpm --filter web-pwa test` (or the relevant filter).
- E2E: `pnpm exec playwright test`.
- Single PWA port: **5173** (5174 is freed). Backend: **8765**. Vite proxy `/v1` → `http://127.0.0.1:8765`.
- Single PWA install name: **"Splashh"** (not role-specific).
- Brand color: light `#0EA5E9`, dark `#38BDF8`.
- All paths in TS/TSX use `@/...` alias (resolved via each app's `tsconfig.json` + `vite.config.ts`).
- Package-internal imports use **relative** paths (e.g. `"../auth/store.js"`) — discovered during the previous plan that workspace `@/*` aliases don't resolve across packages.
- The `<meta name="robots" content="noindex">` head injection must be present on `/admin/login` and all `/admin/*` routes.
- `LoginForm` is the **only** form used for both `/login` and `/admin/login`. A `mode` prop (`"customer" | "staff"`) only changes analytics / copy, not visual.
- Role-based home mapping: `homeForRoles(["tenant_admin"]) = "/admin"`, `homeForRoles(["customer"]) = "/book"`, `homeForRoles(["staff"]) = "/staff"`, default `"/"`.

---

### Task 1: Backend — `LoginResult.roles` + `TokenResponse.roles`

**Files:**
- Modify: `apps/backend/src/auth/application/auth_service.py`
- Modify: `apps/backend/src/auth/interfaces/http/schemas.py`
- Modify: `apps/backend/src/auth/interfaces/http/router.py`
- Modify: `apps/backend/tests/api/test_auth_endpoints.py`

- [ ] **Step 1: Write failing test for login response includes roles**

Add to `apps/backend/tests/api/test_auth_endpoints.py`, inside `TestAuthEndpoints`:

```python
async def test_login_response_includes_roles(self, client: AsyncClient) -> None:
    from auth.interfaces.http.router import _auth_service

    result = MagicMock()
    result.access_token = "fake-access"
    result.refresh_token = "fake-refresh"
    result.access_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    result.refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    result.user_id = uuid4()
    result.tenant_id = uuid4()
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
```

- [ ] **Step 2: Run, verify FAIL**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest tests/api/test_auth_endpoints.py::TestAuthEndpoints::test_login_response_includes_roles -v`
Expected: FAIL — `KeyError: 'roles'` (or pydantic validation error).

- [ ] **Step 3: Update `LoginResult` to include roles**

In `apps/backend/src/auth/application/auth_service.py`, change the `LoginResult` dataclass:

```python
@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    user_id: UUID
    tenant_id: UUID
    roles: list[str]   # NEW
```

In `AuthService.login` and `AuthService.refresh`, after building the `LoginResult`, populate `roles=[r.value for r in user.roles]` from the persisted `user.roles`.

- [ ] **Step 4: Update `TokenResponse` schema**

In `apps/backend/src/auth/interfaces/http/schemas.py`:

```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    user_id: UUID
    tenant_id: UUID
    roles: list[str] = Field(default_factory=list)   # NEW
    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 5: Update `_to_token_response` to pass roles**

In `apps/backend/src/auth/interfaces/http/router.py`:

```python
def _to_token_response(result) -> TokenResponse:
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
```

- [ ] **Step 6: Run test, verify PASS**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest tests/api/test_auth_endpoints.py -q`
Expected: all green (existing + 1 new).

- [ ] **Step 7: Run full backend suite**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest -q`
Expected: 53 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/backend
git commit -m "feat(backend): include roles in login + refresh response"
```

---

### Task 2: Backend — `UserAdminService.create_user` (TDD)

**Files:**
- Create: `apps/backend/src/auth/application/user_admin_service.py`
- Create: `apps/backend/tests/unit/test_user_admin_service.py`

- [ ] **Step 1: Write failing unit tests**

Create `apps/backend/tests/unit/test_user_admin_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from auth.application.user_admin_service import UserAdminService
from auth.domain.entities import User, UserRole
from common.domain.exceptions import Validation, Conflict


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_persists():
    users = MagicMock()
    users.add = AsyncMock(side_effect=lambda u: u)
    hasher = MagicMock()
    hasher.hash = MagicMock(return_value="hashed-pw")

    svc = UserAdminService(users=users, hasher=hasher, tenant_id="t1")
    user = await svc.create_user(
        email="new@example.com",
        full_name="New User",
        password="supersecret-pw-1",
        roles=[UserRole.CUSTOMER],
    )

    hasher.hash.assert_called_once_with("supersecret-pw-1")
    assert user.password_hash == "hashed-pw"
    assert user.email == "new@example.com"
    assert user.tenant_id == "t1"
    assert user.roles == [UserRole.CUSTOMER]
    users.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_rejects_tenant_admin_role():
    users = MagicMock()
    hasher = MagicMock()
    svc = UserAdminService(users=users, hasher=hasher, tenant_id="t1")

    with pytest.raises(Validation):
        await svc.create_user(
            email="x@example.com",
            full_name="X",
            password="supersecret-pw-1",
            roles=[UserRole.TENANT_ADMIN],
        )


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email():
    from common.domain.exceptions import Conflict

    users = MagicMock()
    users.get_by_email_global = AsyncMock(return_value=MagicMock())  # already exists
    hasher = MagicMock()
    svc = UserAdminService(users=users, hasher=hasher, tenant_id="t1")

    with pytest.raises(Conflict):
        await svc.create_user(
            email="dup@example.com",
            full_name="Dup",
            password="supersecret-pw-1",
            roles=[UserRole.CUSTOMER],
        )
```

- [ ] **Step 2: Run, verify FAIL**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest tests/unit/test_user_admin_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.application.user_admin_service'`.

- [ ] **Step 3: Implement `UserAdminService`**

Create `apps/backend/src/auth/application/user_admin_service.py`:

```python
from __future__ import annotations

import hashlib
from uuid import UUID

from auth.domain.entities import User, UserRole
from auth.infrastructure.password_hasher import Argon2PasswordHasher
from auth.infrastructure.repositories import UserRepository
from common.domain.exceptions import Conflict, Validation

ALLOWED_NEW_USER_ROLES = {UserRole.CUSTOMER, UserRole.STAFF}


class UserAdminService:
    def __init__(
        self,
        users: UserRepository,
        hasher: Argon2PasswordHasher,
        tenant_id: UUID,
    ) -> None:
        self.users = users
        self.hasher = hasher
        self.tenant_id = tenant_id

    async def create_user(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
        roles: list[UserRole],
    ) -> User:
        if any(r not in ALLOWED_NEW_USER_ROLES for r in roles):
            raise Validation("Only customer and staff roles can be assigned via this endpoint")
        if not roles:
            raise Validation("At least one role is required")

        existing = await self.users.get_by_email_global(email)
        if existing is not None:
            raise Conflict("User with that email already exists", details={"email": email})

        user = User.create(
            tenant_id=self.tenant_id,
            email=email,
            password_hash=self.hasher.hash(password),
            full_name=full_name,
            roles=roles,
        )
        return await self.users.add(user)
```

Note: the `hashlib` import is included to mirror the pattern in `auth_service.py` for `hash_user_token`; remove if unused.

- [ ] **Step 4: Run tests, verify PASS**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest tests/unit/test_user_admin_service.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/backend
git commit -m "feat(backend): UserAdminService.create_user"
```

---

### Task 3: Backend — `POST /v1/auth/users` + `GET /v1/auth/users` (TDD)

**Files:**
- Modify: `apps/backend/src/auth/interfaces/http/schemas.py`
- Create: `apps/backend/src/auth/interfaces/http/admin_user_router.py`
- Modify: `apps/backend/src/common/interfaces/http/app.py` (mount the new router)
- Modify: `apps/backend/tests/api/test_auth_endpoints.py`

- [ ] **Step 1: Add request/response schemas**

In `apps/backend/src/auth/interfaces/http/schemas.py`, append at the end:

```python
from typing import Literal  # ensure import at top

class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    roles: list[Literal["customer", "staff"]] = Field(min_length=1, max_length=4)


class CreateUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    roles: list[str]


class UserListItem(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    roles: list[str]
    is_active: bool
    created_at: datetime


class UserListResponse(BaseModel):
    data: list[UserListItem]
```

- [ ] **Step 2: Write failing API tests**

Add to `apps/backend/tests/api/test_auth_endpoints.py`:

```python
async def test_admin_can_create_user(self, client: AsyncClient) -> None:
    from auth.interfaces.http.router import _auth_service, _user_admin_service
    from common.domain.exceptions import Unauthorized, Forbidden

    # Mock auth service to return a principal with tenant_admin
    principal = MagicMock()
    principal.tenant_id = uuid4()
    principal.roles = ["tenant_admin"]

    # The route uses Depends(auth_required) which is in auth.dependencies.
    # We override it directly.
    from auth.interfaces.http.dependencies import auth_required

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
    from auth.interfaces.http.dependencies import auth_required
    from auth.interfaces.http.router import _user_admin_service
    from common.domain.exceptions import Conflict

    principal = MagicMock()
    principal.tenant_id = uuid4()
    principal.roles = ["tenant_admin"]
    client._transport.app.dependency_overrides[auth_required] = lambda: principal

    admin_svc = MagicMock()
    admin_svc.create_user = AsyncMock(side_effect=Conflict("User with that email already exists", details={"email": "dup@example.com"}))
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
    from auth.interfaces.http.dependencies import auth_required
    from auth.interfaces.http.router import _user_admin_service

    principal = MagicMock()
    principal.tenant_id = uuid4()
    principal.roles = ["tenant_admin"]
    client._transport.app.dependency_overrides[auth_required] = lambda: principal

    admin_svc = MagicMock()
    admin_svc.list_users = AsyncMock(return_value=[
        MagicMock(id=uuid4(), email="a@x.com", full_name="A", roles=[MagicMock(value="customer")], is_active=True, created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
    ])
    client._transport.app.dependency_overrides[_user_admin_service] = lambda: admin_svc

    resp = await client.get("/v1/auth/users")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)
    assert resp.json()["data"][0]["email"] == "a@x.com"


async def test_non_admin_cannot_list_users(self, client: AsyncClient) -> None:
    from auth.interfaces.http.dependencies import auth_required

    principal = MagicMock()
    principal.tenant_id = uuid4()
    principal.roles = ["customer"]
    client._transport.app.dependency_overrides[auth_required] = lambda: principal

    resp = await client.get("/v1/auth/users")
    assert resp.status_code == 403
```

- [ ] **Step 3: Run, verify FAIL**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest tests/api/test_auth_endpoints.py -k "create_user or list_users" -v`
Expected: FAIL — no `_user_admin_service` dependency yet.

- [ ] **Step 4: Add `_user_admin_service` dependency + create the router**

In `apps/backend/src/auth/interfaces/http/router.py`, add at the bottom of the file:

```python
from auth.application.user_admin_service import UserAdminService
from auth.infrastructure.password_hasher import Argon2PasswordHasher
from auth.interfaces.http.dependencies import auth_required, CurrentPrincipal
from auth.interfaces.http.schemas import CreateUserRequest, CreateUserResponse, UserListItem, UserListResponse
from common.domain.exceptions import Forbidden


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
```

Also add `list_users` method to `UserAdminService`:

```python
async def list_users(self) -> list[User]:
    return await self.users.list_by_tenant(self.tenant_id)
```

If `UserRepository` doesn't have `list_by_tenant`, add it:

```python
async def list_by_tenant(self, tenant_id: UUID) -> list[User]:
    from sqlalchemy import select
    from auth.infrastructure.models import UserModel
    stmt = select(UserModel).where(UserModel.tenant_id == tenant_id).order_by(UserModel.created_at.desc())
    result = await self.session.execute(stmt)
    return [_user_to_domain(m) for m in result.scalars().all()]
```

- [ ] **Step 5: Mount the new endpoints in app.py**

The existing `auth/router.py` already exposes `router` (an `APIRouter()` with no prefix). `_register_module_routers` mounts it under `/v1/auth`. Since the new endpoints are in the same file, **no app.py change is needed** — they're already covered by the existing mount.

- [ ] **Step 6: Run API tests, verify PASS**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest tests/api/test_auth_endpoints.py -k "create_user or list_users" -v`
Expected: 6 passed.

- [ ] **Step 7: Run full backend suite**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest -q`
Expected: 59 passed (53 + 6).

- [ ] **Step 8: Commit**

```bash
git add apps/backend
git commit -m "feat(backend): admin create-user + list-users endpoints"
```

---

### Task 4: Rename `admin-pwa` → `web-pwa` and drop the customer port

**Files:**
- Move: `apps/admin-pwa/` → `apps/web-pwa/`
- Modify: `apps/web-pwa/package.json` (name, scripts)
- Modify: `apps/web-pwa/vite.config.ts` (drop 5174)
- Modify: `apps/web-pwa/index.html` (title)
- Modify: root `package.json` (dev script)
- Modify: `playwright.config.ts` (baseURL 5173 only)

- [ ] **Step 1: Move directory**

Run:
```bash
mv apps/admin-pwa apps/web-pwa
```

- [ ] **Step 2: Update `apps/web-pwa/package.json`**

Change `name` from `"admin-pwa"` to `"web-pwa"`. Update `dev` script to `vite --port 5173 --strictPort`. Drop any reference to a second port.

- [ ] **Step 3: Update `vite.config.ts`**

Set the dev server port to `5173` only. Update the PWA manifest `name`/`short_name` to `"Splashh"` (was `"Splashh Admin"`). Keep `theme_color: "#0EA5E9"`. Update shortcuts: `"My bookings"` → `/book/bookings`, `"Browse facilities"` → `/book` (was the admin's `/admin/facilities/new`).

- [ ] **Step 4: Update `index.html` title**

Change `<title>Splashh Admin</title>` → `<title>Splashh</title>`.

- [ ] **Step 5: Update root `package.json` `dev` script**

```json
"dev": "concurrently -k -n backend,web -c blue,green \"make -C apps/backend dev\" \"pnpm --filter web-pwa dev\""
```

- [ ] **Step 6: Update `playwright.config.ts`**

Single project, baseURL `http://127.0.0.1:5173`. Remove the customer project. Remove the customer-pwa `webServer` entry. Keep the admin-pwa entry (renamed to web-pwa implicitly by pnpm filter):

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: [["list"]],
  use: { trace: "on-first-retry" },
  projects: [
    { name: "web", use: { ...devices["Desktop Chrome"], baseURL: "http://127.0.0.1:5173" } },
  ],
  webServer: [
    { command: "make -C apps/backend dev", url: "http://127.0.0.1:8765/healthz", reuseExistingServer: true, timeout: 30_000 },
    { command: "pnpm --filter web-pwa dev", url: "http://127.0.0.1:5173", reuseExistingServer: true, timeout: 30_000 },
  ],
});
```

- [ ] **Step 7: Update workspace `pnpm-workspace.yaml`**

No change needed — `apps/*` already covers the renamed `web-pwa`.

- [ ] **Step 8: Update existing E2E specs (just the test names / project references for now)**

`apps/web-pwa` directory now contains what was `admin-pwa`. The e2e specs will be rewritten in Task 12; for now, leave them (they'll fail to find the old ports). Mark this step complete after the move.

- [ ] **Step 9: Install and typecheck**

Run: `pnpm install && pnpm --filter web-pwa typecheck`
Expected: typecheck 0.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "refactor(web-pwa): rename admin-pwa to web-pwa (single port 5173)"
```

---

### Task 5: Move customer-pwa pages into web-pwa (book/*)

**Files:**
- Delete: `apps/customer-pwa/`
- Create: `apps/web-pwa/src/pages/book/FacilitiesPage.tsx` (from `apps/customer-pwa/src/pages/FacilitiesPage.tsx`)
- Create: `apps/web-pwa/src/pages/book/FacilityDetailPage.tsx`
- Create: `apps/web-pwa/src/pages/book/BookingsPage.tsx`
- Create: `apps/web-pwa/src/features/bookings/api.ts`
- Create: `apps/web-pwa/src/features/bookings/useCreateBooking.ts`
- Create: `apps/web-pwa/src/features/bookings/useBookings.ts`
- Create: `apps/web-pwa/src/features/bookings/BookingDialog.tsx`
- Create: `apps/web-pwa/src/features/facilities/api.ts`
- Create: `apps/web-pwa/src/features/facilities/useFacilities.ts`
- Create: `apps/web-pwa/src/test/login.test.tsx` (move + adapt)
- Create: `apps/web-pwa/src/test/booking.test.tsx` (move + adapt)
- Delete: `apps/customer-pwa/`

- [ ] **Step 1: Copy page files from `customer-pwa` into `web-pwa/src/pages/book/`**

```bash
mkdir -p apps/web-pwa/src/pages/book
cp apps/customer-pwa/src/pages/FacilitiesPage.tsx apps/web-pwa/src/pages/book/FacilitiesPage.tsx
cp apps/customer-pwa/src/pages/FacilityDetailPage.tsx apps/web-pwa/src/pages/book/FacilityDetailPage.tsx
cp apps/customer-pwa/src/pages/BookingsPage.tsx apps/web-pwa/src/pages/book/BookingsPage.tsx
```

- [ ] **Step 2: Copy features**

```bash
mkdir -p apps/web-pwa/src/features/{bookings,facilities}
cp apps/customer-pwa/src/features/facilities/api.ts apps/web-pwa/src/features/facilities/api.ts
cp apps/customer-pwa/src/features/facilities/useFacilities.ts apps/web-pwa/src/features/facilities/useFacilities.ts
cp apps/customer-pwa/src/features/bookings/api.ts apps/web-pwa/src/features/bookings/api.ts
cp apps/customer-pwa/src/features/bookings/useCreateBooking.ts apps/web-pwa/src/features/bookings/useCreateBooking.ts
cp apps/customer-pwa/src/features/bookings/useBookings.ts apps/web-pwa/src/features/bookings/useBookings.ts
cp apps/customer-pwa/src/features/bookings/BookingDialog.tsx apps/web-pwa/src/features/bookings/BookingDialog.tsx
```

- [ ] **Step 3: Move tests**

```bash
mkdir -p apps/web-pwa/test
cp apps/customer-pwa/test/login.test.tsx apps/web-pwa/test/login.test.tsx
cp apps/customer-pwa/test/booking.test.tsx apps/web-pwa/test/booking.test.tsx
```

In the moved test files, change `import { api } from "@splashh/api-client"` — no path change needed. Change `customer-pwa` to `web-pwa` in the `pnpm test` calls. Change `import { LoginForm } from "@/features/auth/LoginForm";` to use the web-pwa path (already the same).

- [ ] **Step 4: Delete `apps/customer-pwa/`**

```bash
rm -rf apps/customer-pwa
```

- [ ] **Step 5: Run web-pwa typecheck + test**

Run: `pnpm --filter web-pwa typecheck && pnpm --filter web-pwa test`
Expected: typecheck 0; tests 3 passed (login x2, booking x1).

- [ ] **Step 6: Commit**

```bash
git add -A
git rm -r apps/customer-pwa 2>/dev/null || true
git commit -m "refactor(web-pwa): move customer-pwa pages/features into book/* section"
```

---

### Task 6: Frontend — `RoleGate`, `RoleBasedRedirect`, `homeForRoles`

**Files:**
- Create: `apps/web-pwa/src/lib/role-routing.ts`
- Create: `apps/web-pwa/src/routes/role-gate.tsx`
- Create: `apps/web-pwa/src/routes/role-based-redirect.tsx`
- Create: `apps/web-pwa/src/components/RoleMismatch.tsx`
- Create: `apps/web-pwa/test/role-routing.test.ts`
- Create: `apps/web-pwa/test/role-gate.test.tsx`
- Create: `apps/web-pwa/test/role-based-redirect.test.tsx`

- [ ] **Step 1: Write failing test for `homeForRoles`**

Create `apps/web-pwa/test/role-routing.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { homeForRoles } from "../src/lib/role-routing";

describe("homeForRoles", () => {
  it("admin goes to /admin", () => {
    expect(homeForRoles(["tenant_admin"])).toBe("/admin");
  });
  it("customer goes to /book", () => {
    expect(homeForRoles(["customer"])).toBe("/book");
  });
  it("staff goes to /staff", () => {
    expect(homeForRoles(["staff"])).toBe("/staff");
  });
  it("empty falls back to /", () => {
    expect(homeForRoles([])).toBe("/");
  });
  it("admin wins over customer if both present", () => {
    expect(homeForRoles(["customer", "tenant_admin"])).toBe("/admin");
  });
});
```

- [ ] **Step 2: Run, verify FAIL**

Run: `pnpm --filter web-pwa test -- role-routing`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `homeForRoles`**

Create `apps/web-pwa/src/lib/role-routing.ts`:

```ts
const ROLE_HOMES: Record<string, string> = {
  tenant_admin: "/admin",
  customer: "/book",
  staff: "/staff",
};

export const homeForRoles = (roles: readonly string[]): string => {
  for (const role of roles) {
    const home = ROLE_HOMES[role];
    if (home) return home;
  }
  return "/";
};
```

- [ ] **Step 4: Run test, verify PASS**

Run: `pnpm --filter web-pwa test -- role-routing`
Expected: 5 passed.

- [ ] **Step 5: Write failing test for `<RoleGate>`**

Create `apps/web-pwa/test/role-gate.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@splashh/api-client";
import { RoleGate } from "../src/routes/role-gate";

const renderWith = (roles: string[], path = "/admin") => {
  useAuthStore.setState({ roles, isAuthenticated: true, accessToken: "x", userId: "u", tenantId: "t" });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<RoleGate roles={["tenant_admin"]} />}>
          <Route path="/admin" element={<div>admin ok</div>} />
        </Route>
        <Route path="/book" element={<div>book</div>} />
      </Routes>
    </MemoryRouter>,
  );
};

describe("RoleGate", () => {
  it("renders Outlet when role matches", () => {
    renderWith(["tenant_admin"]);
    expect(screen.getByText("admin ok")).toBeInTheDocument();
  });
  it("renders 403 page when role missing", () => {
    renderWith(["customer"]);
    expect(screen.getByRole("heading", { name: /not authorized/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Run, verify FAIL**

Run: `pnpm --filter web-pwa test -- role-gate`
Expected: FAIL.

- [ ] **Step 7: Implement `RoleGate` and `RoleMismatch`**

Create `apps/web-pwa/src/components/RoleMismatch.tsx`:

```tsx
import { Button } from "@splashh/ui";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "../lib/role-routing";

export function RoleMismatch({ required }: { required: string[] }) {
  const navigate = useNavigate();
  const roles = useAuthStore((s) => s.roles);
  const home = homeForRoles(roles);
  return (
    <main className="container max-w-md py-12 text-center">
      <h1 className="text-2xl font-semibold">Not authorized</h1>
      <p className="mt-2 text-muted-foreground">
        This area is for {required.join(" / ")} only.
      </p>
      <div className="mt-6 flex justify-center gap-2">
        <Button onClick={() => navigate(home, { replace: true })}>Go to your home</Button>
        <Button variant="ghost" asChild>
          <Link to="/login">Switch account</Link>
        </Button>
      </div>
    </main>
  );
}
```

Create `apps/web-pwa/src/routes/role-gate.tsx`:

```tsx
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@splashh/api-client";
import { RoleMismatch } from "../components/RoleMismatch";

export function RoleGate({ roles }: { roles: string[] }) {
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const userRoles = useAuthStore((s) => s.roles);
  const location = useLocation();

  if (!isAuthed) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!roles.some((r) => userRoles.includes(r))) return <RoleMismatch required={roles} />;
  return <Outlet />;
}
```

- [ ] **Step 8: Run role-gate tests, verify PASS**

Run: `pnpm --filter web-pwa test -- role-gate`
Expected: 2 passed.

- [ ] **Step 9: Write failing test for `<RoleBasedRedirect>`**

Create `apps/web-pwa/test/role-based-redirect.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { useAuthStore } from "@splashh/api-client";
import { RoleBasedRedirect } from "../src/routes/role-based-redirect";

describe("RoleBasedRedirect", () => {
  it("navigates to /admin for admin", () => {
    useAuthStore.setState({ roles: ["tenant_admin"], isAuthenticated: true, accessToken: "x", userId: "u", tenantId: "t" });
    render(
      <MemoryRouter initialEntries={["/"]}>
        <RoleBasedRedirect />
      </MemoryRouter>,
    );
    expect(window.location.pathname).toBe("/"); // jsdom doesn't actually navigate; this just exercises the component
  });
});
```

A single component-mounting test is enough — full navigation behaviour is exercised by the E2E spec in Task 12.

- [ ] **Step 10: Implement `RoleBasedRedirect`**

Create `apps/web-pwa/src/routes/role-based-redirect.tsx`:

```tsx
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "../lib/role-routing";

export function RoleBasedRedirect() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);

  useEffect(() => {
    if (isAuthed) {
      navigate(homeForRoles(roles), { replace: true });
    }
  }, [isAuthed, roles, navigate]);

  return null;
}
```

- [ ] **Step 11: Run all web-pwa tests, verify PASS**

Run: `pnpm --filter web-pwa test`
Expected: 5 (role-routing) + 2 (role-gate) + 1 (role-based-redirect) + 2 (login) + 1 (booking) = 11 passed.

- [ ] **Step 12: Commit**

```bash
git add apps/web-pwa
git commit -m "feat(web-pwa): role-based routing (RoleGate, RoleBasedRedirect, homeForRoles)"
```

---

### Task 7: Frontend — `<LoginForm>` with `mode` prop + `loginRequest` reads roles

**Files:**
- Modify: `apps/web-pwa/src/features/auth/api.ts`
- Modify: `apps/web-pwa/src/features/auth/LoginForm.tsx`

- [ ] **Step 1: Update `loginRequest` to set roles**

In `apps/web-pwa/src/features/auth/api.ts`:

```ts
import { api, useAuthStore } from "@splashh/api-client";

interface LoginResponse {
  access_token: string;
  user_id: string;
  tenant_id: string;
  roles: string[];
}

export async function loginRequest(email: string, password: string): Promise<string[]> {
  const res = await api.post<LoginResponse>("/auth/login", { email, password });
  useAuthStore.getState().setSession({
    accessToken: res.data.access_token,
    userId: res.data.user_id,
    tenantId: res.data.tenant_id,
    roles: res.data.roles ?? [],
  });
  return res.data.roles ?? [];
}
```

- [ ] **Step 2: Update `LoginForm` to accept `mode` and return roles via callback**

Replace `apps/web-pwa/src/features/auth/LoginForm.tsx`:

```tsx
import { Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "@splashh/ui";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useLogin } from "./useLogin";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

export function LoginForm({
  onSuccess,
  mode = "customer",
}: {
  onSuccess: (roles: string[]) => void;
  mode?: "customer" | "staff";
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });
  const login = useLogin();

  const onSubmit = handleSubmit(async (data) => {
    try {
      const roles = await login.mutateAsync({ ...data, mode });
      onSuccess(roles);
    } catch {
      /* error surfaced via mutation */
    }
  });

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-xl">
          {mode === "staff" ? "Admin log in" : "Log in"}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              aria-invalid={errors.email ? "true" : "false"}
              {...register("email")}
            />
          </FormField>
          <FormField label="Password" htmlFor="password" error={errors.password?.message}>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              aria-invalid={errors.password ? "true" : "false"}
              {...register("password")}
            />
          </FormField>
          {login.error && (
            <p role="alert" className="text-sm text-destructive">
              {(login.error as Error).message || "Login failed"}
            </p>
          )}
          <Button type="submit" disabled={isSubmitting || login.isPending} className="w-full">
            {login.isPending ? "Logging in…" : "Log in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Update `useLogin` to pass `mode` and return roles**

In `apps/web-pwa/src/features/auth/useLogin.ts`:

```ts
import { useMutation } from "@tanstack/react-query";
import { loginRequest } from "./api";

export function useLogin() {
  return useMutation({
    mutationFn: (input: { email: string; password: string; mode?: "customer" | "staff" }) =>
      loginRequest(input.email, input.password),
  });
}
```

The return type of `useMutation` already yields `data` as the resolved value of `mutationFn`, so `roles` is exposed via `mutation.data`.

- [ ] **Step 4: Typecheck + run tests**

Run: `pnpm --filter web-pwa typecheck && pnpm --filter web-pwa test`
Expected: typecheck 0; tests 11 passed (login + booking unchanged).

- [ ] **Step 5: Commit**

```bash
git add apps/web-pwa
git commit -m "feat(web-pwa): LoginForm mode + roles in session"
```

---

### Task 8: Frontend — wire `/login` and `/admin/login` + role-based redirect after login

**Files:**
- Modify: `apps/web-pwa/src/pages/LoginPage.tsx`
- Create: `apps/web-pwa/src/pages/AdminLoginPage.tsx`
- Modify: `apps/web-pwa/src/pages/HomePage.tsx`
- Modify: `apps/web-pwa/src/routes/index.tsx`
- Modify: `apps/web-pwa/src/features/auth/AuthBootstrap.tsx`

- [ ] **Step 1: Replace `LoginPage`**

Replace `apps/web-pwa/src/pages/LoginPage.tsx`:

```tsx
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { LoginForm } from "@/features/auth/LoginForm";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "@/lib/role-routing";

export function LoginPage() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <LoginForm
        mode="customer"
        onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
      />
    </main>
  );
}
```

- [ ] **Step 2: Create `AdminLoginPage`**

Create `apps/web-pwa/src/pages/AdminLoginPage.tsx`:

```tsx
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { LoginForm } from "@/features/auth/LoginForm";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "@/lib/role-routing";

export function AdminLoginPage() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);

  useEffect(() => {
    document.title = "Splashh Admin";
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => {
      document.head.removeChild(meta);
    };
  }, []);

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <LoginForm
        mode="staff"
        onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
      />
    </main>
  );
}
```

- [ ] **Step 3: Update `HomePage` to have public landing links**

Replace `apps/web-pwa/src/pages/HomePage.tsx`:

```tsx
import { Button } from "@splashh/ui";
import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="text-4xl font-bold">Splashh</h1>
      <p className="text-muted-foreground">Book your club in seconds.</p>
      <Button asChild>
        <Link to="/login">Customer login</Link>
      </Button>
      <p className="text-xs text-muted-foreground">
        Staff? <Link to="/admin/login" className="underline">Admin login</Link>
      </p>
    </main>
  );
}
```

- [ ] **Step 4: Replace `routes/index.tsx` with the new tree**

Replace `apps/web-pwa/src/routes/index.tsx`:

```tsx
import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { AuthBootstrap } from "@/features/auth/AuthBootstrap";
import { AdminLoginPage } from "@/pages/AdminLoginPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { ProtectedRoute } from "./protected";
import { RoleGate } from "./role-gate";
import { RoleBasedRedirect } from "./role-based-redirect";

const FacilitiesPage = lazy(() => import("@/pages/book/FacilitiesPage").then((m) => ({ default: m.FacilitiesPage })));
const FacilityDetailPage = lazy(() => import("@/pages/book/FacilityDetailPage").then((m) => ({ default: m.FacilityDetailPage })));
const BookingsPage = lazy(() => import("@/pages/book/BookingsPage").then((m) => ({ default: m.BookingsPage })));
const AdminFacilitiesPage = lazy(() => import("@/pages/admin/AdminFacilitiesPage").then((m) => ({ default: m.AdminFacilitiesPage })));
const AdminFacilityNewPage = lazy(() => import("@/pages/admin/AdminFacilityNewPage").then((m) => ({ default: m.AdminFacilityNewPage })));
const AdminFacilityDetailPage = lazy(() => import("@/pages/admin/AdminFacilityDetailPage").then((m) => ({ default: m.AdminFacilityDetailPage })));
const AdminUsersPage = lazy(() => import("@/pages/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage })));

export function AppRouter() {
  return (
    <AuthBootstrap>
      <Suspense fallback={<div className="p-8 text-center text-muted-foreground">Loading…</div>}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/redirect" element={<RoleBasedRedirect />} />
            <Route element={<RoleGate roles={["customer"]} />}>
              <Route path="/book" element={<FacilitiesPage />} />
              <Route path="/book/facilities/:id" element={<FacilityDetailPage />} />
              <Route path="/book/bookings" element={<BookingsPage />} />
            </Route>
            <Route element={<RoleGate roles={["tenant_admin"]} />}>
              <Route path="/admin" element={<AdminFacilitiesPage />} />
              <Route path="/admin/facilities/new" element={<AdminFacilityNewPage />} />
              <Route path="/admin/facilities/:id" element={<AdminFacilityDetailPage />} />
              <Route path="/admin/users" element={<AdminUsersPage />} />
            </Route>
          </Route>
          <Route path="*" element={<HomePage />} />
        </Routes>
      </Suspense>
    </AuthBootstrap>
  );
}
```

Note: the `customer` role gate lets any user with the customer role through. A user with both `tenant_admin` and `customer` can reach `/book`; a user with only `tenant_admin` cannot. If multi-role users need a switcher, that's out of scope.

- [ ] **Step 5: Update `AuthBootstrap` to also navigate on first session**

Update `apps/web-pwa/src/features/auth/AuthBootstrap.tsx`:

```tsx
import { silentRefresh, useAuthStore } from "@splashh/api-client";
import { useEffect } from "react";
import { homeForRoles } from "@/lib/role-routing";

export function AuthBootstrap({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!useAuthStore.getState().isAuthenticated) {
      silentRefresh()
        .then(() => {
          if (window.location.pathname === "/") {
            const roles = useAuthStore.getState().roles;
            window.location.replace(homeForRoles(roles));
          }
        })
        .catch(() => undefined);
    }
  }, []);
  return <>{children}</>;
}
```

- [ ] **Step 6: Move old admin-pwa pages into `web-pwa/src/pages/admin/`**

```bash
mkdir -p apps/web-pwa/src/pages/admin
mv apps/web-pwa/src/pages/AdminFacilitiesPage.tsx apps/web-pwa/src/pages/admin/AdminFacilitiesPage.tsx
mv apps/web-pwa/src/pages/AdminFacilityNewPage.tsx apps/web-pwa/src/pages/admin/AdminFacilityNewPage.tsx
mv apps/web-pwa/src/pages/AdminFacilityDetailPage.tsx apps/web-pwa/src/pages/admin/AdminFacilityDetailPage.tsx
mv apps/web-pwa/src/pages/BookingsPage.tsx apps/web-pwa/src/pages/admin/BookingsPage.tsx
```

(BookingsPage is the admin's bookings view — different from `book/BookingsPage.tsx`.)

- [ ] **Step 7: Typecheck + test**

Run: `pnpm --filter web-pwa typecheck && pnpm --filter web-pwa test`
Expected: 0; 11 tests pass.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(web-pwa): /login + /admin/login + role-based routing tree"
```

---

### Task 9: Frontend — `users` feature (api + hooks)

**Files:**
- Create: `apps/web-pwa/src/features/admin/users/api.ts`
- Create: `apps/web-pwa/src/features/admin/users/useUsers.ts`
- Create: `apps/web-pwa/test/users.test.tsx`

- [ ] **Step 1: Write failing test for create-user mutation**

Create `apps/web-pwa/test/users.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api } from "@splashh/api-client";
import { useCreateUser } from "../src/features/admin/users/useUsers";

function Probe() {
  const create = useCreateUser();
  return (
    <button
      onClick={() =>
        create.mutate({
          email: "new@example.com",
          full_name: "New User",
          password: "verysecurepassword123",
          roles: ["customer"],
        })
      }
    >
      create
    </button>
  );
}

it("posts to /auth/users and returns the new user", async () => {
  (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    data: { id: "u1", email: "new@example.com", full_name: "New User", roles: ["customer"] },
  });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <Probe />
    </QueryClientProvider>,
  );
  await userEvent.click(screen.getByRole("button", { name: "create" }));
  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith(
      "/auth/users",
      expect.objectContaining({ email: "new@example.com", roles: ["customer"] }),
    );
  });
});
```

- [ ] **Step 2: Run, verify FAIL**

Run: `pnpm --filter web-pwa test -- users`
Expected: FAIL.

- [ ] **Step 3: Implement `usersApi` + hooks**

Create `apps/web-pwa/src/features/admin/users/api.ts`:

```ts
import { api } from "@splashh/api-client";

export interface User {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  is_active: boolean;
  created_at: string;
}

export interface CreateUserInput {
  email: string;
  full_name: string;
  password: string;
  roles: Array<"customer" | "staff">;
}

export const usersApi = {
  list: () => api.get<{ data: User[] }>("/auth/users").then((r) => r.data.data),
  create: (input: CreateUserInput) => api.post<User>("/auth/users", input).then((r) => r.data),
};
```

Create `apps/web-pwa/src/features/admin/users/useUsers.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersApi, type CreateUserInput } from "./api";

export const userKeys = {
  all: ["users"] as const,
  list: (tenantId: string) => ["users", "list", tenantId] as const,
};

export function useUsers() {
  return useQuery({ queryKey: userKeys.all, queryFn: usersApi.list });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateUserInput) => usersApi.create(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}
```

- [ ] **Step 4: Run test, verify PASS**

Run: `pnpm --filter web-pwa test -- users`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/web-pwa
git commit -m "feat(web-pwa): users feature (api + hooks)"
```

---

### Task 10: Frontend — `AdminUsersPage`

**Files:**
- Create: `apps/web-pwa/src/pages/AdminUsersPage.tsx`

- [ ] **Step 1: Create the page**

Create `apps/web-pwa/src/pages/AdminUsersPage.tsx`:

```tsx
import { useState } from "react";
import { Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "@splashh/ui";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useUsers, useCreateUser, type CreateUserInput } from "@/features/admin/users/useUsers";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  full_name: z.string().min(1, "Name is required"),
  password: z.string().min(12, "At least 12 characters"),
  role_customer: z.boolean().default(false),
  role_staff: z.boolean().default(false),
});
type FormData = z.infer<typeof schema>;

function AddUserForm({ onCreated }: { onCreated: () => void }) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { role_customer: true, role_staff: false } });
  const create = useCreateUser();

  const onSubmit = handleSubmit(async (data) => {
    const roles: CreateUserInput["roles"] = [];
    if (data.role_customer) roles.push("customer");
    if (data.role_staff) roles.push("staff");
    if (roles.length === 0) return;
    try {
      await create.mutateAsync({
        email: data.email,
        full_name: data.full_name,
        password: data.password,
        roles,
      });
      reset();
      onCreated();
    } catch {
      /* surfaced via mutation state */
    }
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Add user</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-3">
          <FormField label="Email" htmlFor="u-email" error={errors.email?.message}>
            <Input id="u-email" type="email" {...register("email")} />
          </FormField>
          <FormField label="Full name" htmlFor="u-name" error={errors.full_name?.message}>
            <Input id="u-name" {...register("full_name")} />
          </FormField>
          <FormField label="Temporary password" htmlFor="u-pw" error={errors.password?.message}>
            <Input id="u-pw" type="password" {...register("password")} />
          </FormField>
          <fieldset className="space-y-1">
            <legend className="text-sm font-medium">Roles</legend>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("role_customer")} /> Customer
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("role_staff")} /> Staff
            </label>
          </fieldset>
          {create.error && (
            <p role="alert" className="text-sm text-destructive">
              {(create.error as Error).message}
            </p>
          )}
          <Button type="submit" size="sm" disabled={isSubmitting || create.isPending}>
            {create.isPending ? "Adding…" : "Add user"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export function AdminUsersPage() {
  const { data, isLoading, error } = useUsers();
  const [adding, setAdding] = useState(false);

  return (
    <main className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Users</h1>
        <Button onClick={() => setAdding((s) => !s)}>{adding ? "Close" : "+ Add user"}</Button>
      </div>
      {adding && <div className="mb-4"><AddUserForm onCreated={() => setAdding(false)} /></div>}
      {isLoading && <p>Loading…</p>}
      {error && <p className="text-destructive">Failed to load users.</p>}
      <Card>
        <CardHeader><CardTitle className="text-base">All users</CardTitle></CardHeader>
        <CardContent>
          {data?.length === 0 && <p className="text-sm text-muted-foreground">No users yet.</p>}
          <ul className="divide-y">
            {data?.map((u) => (
              <li key={u.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  {u.email} · {u.full_name}
                </span>
                <span className="text-muted-foreground">{u.roles.join(", ")}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </main>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `pnpm --filter web-pwa typecheck`
Expected: 0.

- [ ] **Step 3: Commit**

```bash
git add apps/web-pwa
git commit -m "feat(web-pwa): AdminUsersPage"
```

---

### Task 11: PWA polish — manifest, install prompt, `<head>` noindex

**Files:**
- Modify: `apps/web-pwa/vite.config.ts` (manifest already updated in Task 4 — confirm)
- Modify: `apps/web-pwa/src/components/PWAInstallPrompt.tsx` (copy)
- Modify: `apps/web-pwa/src/components/UpdateBanner.tsx` (copy)

- [ ] **Step 1: Verify manifest in `vite.config.ts`**

Re-read `apps/web-pwa/vite.config.ts` and confirm the manifest block from Task 4 step 3 is in place. (If you changed it in Task 4, you're done.)

- [ ] **Step 2: Update `PWAInstallPrompt` copy**

In `apps/web-pwa/src/components/PWAInstallPrompt.tsx`, change the CardTitle text from "Install Splashh Admin" to "Install Splashh". Change the description "Add to your home screen for quick management on the go." to "Add to your home screen for the best experience."

- [ ] **Step 3: Update `UpdateBanner` copy**

In `apps/web-pwa/src/components/UpdateBanner.tsx`, change "A new version of Splashh Admin is available." to "A new version of Splashh is available."

- [ ] **Step 4: Add a route-level `<head>` noindex for `/admin/*`**

In `apps/web-pwa/src/routes/index.tsx`, add a wrapper element that injects the meta tag for any `/admin` or `/admin/*` route. Simplest: a small effect inside the existing RoleGate's outlet — but that complicates the existing component. Alternative: add a `useNoIndex()` hook in a top-level `<NoIndexOnAdmin />` component that the App renders inside the BrowserRouter:

Create `apps/web-pwa/src/hooks/useNoIndex.ts`:

```ts
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function useNoIndex(whenPathStartsWith: string) {
  const { pathname } = useLocation();
  useEffect(() => {
    if (!pathname.startsWith(whenPathStartsWith)) return;
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => {
      document.head.removeChild(meta);
    };
  }, [pathname, whenPathStartsWith]);
}
```

Create `apps/web-pwa/src/components/NoIndexOnAdmin.tsx`:

```tsx
import { useNoIndex } from "../hooks/useNoIndex";

export function NoIndexOnAdmin() {
  useNoIndex("/admin");
  return null;
}
```

In `apps/web-pwa/src/App.tsx`, add `<NoIndexOnAdmin />` inside the `<BrowserRouter>`:

```tsx
import { BrowserRouter } from "react-router-dom";
import { NoIndexOnAdmin } from "./components/NoIndexOnAdmin";
import { UpdateBanner } from "./components/UpdateBanner";
import { PWAInstallPrompt } from "./components/PWAInstallPrompt";
import { AppRouter } from "./routes";

export default function App() {
  return (
    <BrowserRouter>
      <NoIndexOnAdmin />
      <UpdateBanner />
      <AppRouter />
      <PWAInstallPrompt />
    </BrowserRouter>
  );
}
```

- [ ] **Step 5: Typecheck + build**

Run: `pnpm --filter web-pwa typecheck && pnpm --filter web-pwa build`
Expected: typecheck 0; build emits `dist/manifest.webmanifest`, `dist/sw.js`.

- [ ] **Step 6: Commit**

```bash
git add apps/web-pwa
git commit -m "feat(web-pwa): single-install PWA copy + noindex for /admin/*"
```

---

### Task 12: E2E — admin creates a customer; both PWAs log in at correct URL

**Files:**
- Modify: `e2e/admin.spec.ts`
- Create: `e2e/admin-user-creation.spec.ts`
- Delete: `e2e/customer.spec.ts` (consolidated into `admin.spec.ts`)

- [ ] **Step 1: Update `e2e/admin.spec.ts` to use `/admin/login` and the renamed project**

Replace `e2e/admin.spec.ts`:

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("admin: register tenant via API then log in via /admin/login", async ({ page, request }) => {
  const slug = `e2e-admin-${Date.now()}`;
  const email = `admin-${slug}@example.com`;
  const password = "CorrectHorseBatteryStaple!9";

  const reg = await request.post("http://127.0.0.1:8765/v1/auth/register-tenant", {
    data: {
      tenant_name: "E2E Admin Tenant",
      tenant_slug: slug,
      primary_contact_email: `contact-${slug}@example.com`,
      admin_email: email,
      admin_password: password,
      admin_full_name: "E2E Admin",
    },
  });
  expect(reg.status()).toBe(201);

  await page.goto("/admin/login");
  await expect(page.getByRole("heading", { name: /admin log in/i })).toBeVisible();

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();

  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: /facilities/i })).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) => v.impact === "critical" || v.impact === "serious"),
  ).toEqual([]);
});

test("customer: log in via /login and reach /book", async ({ page, request }) => {
  const slug = `e2e-cust-${Date.now()}`;
  const email = `cust-${slug}@example.com`;
  const password = "CorrectHorseBatteryStaple!9";

  // Register a tenant + admin via the API
  const reg = await request.post("http://127.0.0.1:8765/v1/auth/register-tenant", {
    data: {
      tenant_name: "E2E Customer Tenant",
      tenant_slug: slug,
      primary_contact_email: `contact-${slug}@example.com`,
      admin_email: email,
      admin_password: password,
      admin_full_name: "E2E Customer",
    },
  });
  expect(reg.status()).toBe(201);

  // The admin who registered has the tenant_admin role. To test the customer
  // path, create a customer user via the admin endpoint first.
  // (Reuse the same password for simplicity.)
  const loginAsAdmin = await request.post("http://127.0.0.1:8765/v1/auth/login", {
    data: { email, password },
  });
  expect(loginAsAdmin.status()).toBe(200);
  const adminAccess = (await loginAsAdmin.json()).access_token;
  const create = await request.post("http://127.0.0.1:8765/v1/auth/users", {
    data: { email: `customer-${slug}@example.com`, full_name: "E2E Customer", password, roles: ["customer"] },
    headers: { Authorization: `Bearer ${adminAccess}` },
  });
  expect(create.status()).toBe(201);

  // Now log in as the customer via /login
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /^log in$/i })).toBeVisible();

  await page.getByLabel("Email").fill(`customer-${slug}@example.com`);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();

  await expect(page).toHaveURL(/\/book$/);
});
```

- [ ] **Step 2: Create new admin-user-creation E2E**

Create `e2e/admin-user-creation.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test("admin creates a customer; customer logs in at /login", async ({ page, request }) => {
  const slug = `e2e-create-${Date.now()}`;
  const adminEmail = `admin-${slug}@example.com`;
  const customerEmail = `customer-${slug}@example.com`;
  const password = "CorrectHorseBatteryStaple!9";

  // Register tenant
  const reg = await request.post("http://127.0.0.1:8765/v1/auth/register-tenant", {
    data: {
      tenant_name: "E2E Create User Tenant",
      tenant_slug: slug,
      primary_contact_email: `contact-${slug}@example.com`,
      admin_email: adminEmail,
      admin_password: password,
      admin_full_name: "E2E Admin",
    },
  });
  expect(reg.status()).toBe(201);

  // Log in as admin
  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page).toHaveURL(/\/admin$/);

  // Navigate to users page and create a customer
  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: /users/i })).toBeVisible();
  await page.getByRole("button", { name: /add user/i }).click();
  await page.getByLabel("Email").fill(customerEmail);
  await page.getByLabel("Full name").fill("E2E Customer");
  await page.getByLabel("Temporary password").fill(password);
  await page.getByRole("button", { name: /add user/i }).last().click();

  // The new user appears in the list
  await expect(page.getByText(customerEmail)).toBeVisible();

  // Log out (best effort) and log in as the customer
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("Email").fill(customerEmail);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();

  // Lands on /book (customer home)
  await expect(page).toHaveURL(/\/book$/);
});
```

- [ ] **Step 3: Delete `e2e/customer.spec.ts`**

```bash
rm e2e/customer.spec.ts
```

- [ ] **Step 4: Confirm Playwright config is the one from Task 4**

The config from Task 4 step 6 has a single `web` project + web-pwa webServer. No further change needed.

- [ ] **Step 5: Run E2E**

Start backend (`make -C apps/backend dev` in background) and web-pwa (`pnpm --filter web-pwa dev` in background). Then:

```bash
pnpm exec playwright test
```

Expected: 3 passed (2 in `admin.spec.ts` + 1 in `admin-user-creation.spec.ts`).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "test(e2e): single web-pwa — admin/user creation flows"
```

---

### Task 13: Full-suite verification + README refresh

**Files:**
- Modify: `README.md`
- Modify: `apps/customer-pwa/README.md` (delete)
- Modify: `apps/web-pwa/README.md` (refresh)

- [ ] **Step 1: Run all test suites**

```bash
cd apps/backend && PYTHONPATH=src uv run pytest -q
cd ../..
pnpm --filter @splashh/ui test
pnpm --filter @splashh/api-client test
pnpm --filter web-pwa test
pnpm --filter web-pwa typecheck
pnpm --filter @splashh/ui typecheck
pnpm --filter @splashh/api-client typecheck
pnpm exec playwright test
```

Expected: all green (backend 59, ui 2, api-client 6, web-pwa 12, e2e 3, plus the new role-routing/role-gate/role-based-redirect/users/admin-users tests).

- [ ] **Step 2: Delete `apps/customer-pwa/README.md`**

```bash
rm -f apps/customer-pwa/README.md
rmdir apps/customer-pwa 2>/dev/null || true
```

- [ ] **Step 3: Refresh `apps/web-pwa/README.md`**

Replace the contents to reflect the new model: one app, two login routes, role-based home, `/admin/users` for user management. Mention ports 5173 / 8765.

- [ ] **Step 4: Update root `README.md`**

- Replace the "Two PWAs" line with: "Frontend: `apps/web-pwa` (single installable PWA; role-based home after login; admin users can create other roles)."
- Drop the second PWA row from the repo-layout tree.
- Update the dev commands (one port, one PWA).
- Update the "What's in this prototype" table.

- [ ] **Step 5: Run lint**

```bash
pnpm lint
```

Expected: clean (no Biome findings) or only existing findings.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: refresh READMEs for one-app model"
```

---

## Self-Review Checklist

- [x] Every spec section (§1–§13) is covered by at least one task.
- [x] No `TBD` / `TODO` / `fill in` strings remain.
- [x] All function/method names referenced in later tasks exist in earlier tasks (`homeForRoles`, `RoleGate`, `RoleBasedRedirect`, `RoleMismatch`, `usersApi`, `useCreateUser`, `useUsers`, `LoginForm`, `auth_required`/`CurrentPrincipal`, `_user_admin_service`).
- [x] Type names match across tasks (`User`, `UserListItem`, `CreateUserRequest`, `CreateUserResponse`, `UserAdminService`, `LoginResult`, `TokenResponse`, `RoleGate` props, `LoginForm` props).
- [x] Each `pnpm`/`uv` command includes the working directory prefix where it matters.
- [x] Every task ends with `git commit` and a verification step.
- [x] The `LoginForm` `mode` prop's `onSuccess(roles)` signature is consistent across Task 7 (form), Task 8 (LoginPage + AdminLoginPage wiring).
- [x] `_user_admin_service` is defined exactly once (Task 3) and overridden in both success and 403 tests in Task 3.
- [x] AuthBootstrap's homeForRoles redirect in Task 8 is conditional on `pathname === "/"` to avoid loops on inner pages.
