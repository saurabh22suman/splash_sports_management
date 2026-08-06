# One App, Two Login Routes — Design Spec

**Date:** 2026-08-06
**Status:** Draft — pending user review
**Scope:** Refactor the existing two-PWA scaffold (admin-pwa + customer-pwa) into a single app with two login routes. Add an admin "create user" flow. Update role-based home routing. Update E2E tests. No new product features beyond this.

---

## 1. Goals & Non-Goals

**Goals**

- Single installable PWA. One `apps/web-pwa/` replaces `apps/admin-pwa/` and `apps/customer-pwa/`.
- One `LoginForm` component, mounted at two routes: `/login` (public, customer) and `/admin/login` (noindex, staff).
- After successful login, the app routes by the user's first role: `tenant_admin` → `/admin`, `customer` → `/book`, `staff` → `/staff` (future).
- Admin can create new users with `customer` or `staff` roles via `POST /v1/auth/users` (admin-only).
- `LoginResult` (and the `/login` + `/refresh` JSON response) includes the user's roles, so the frontend can route without an extra round-trip.
- E2E specs and Playwright config reflect the new layout.

**Non-Goals (deferred)**

- Invite-by-email flow (admin sets a temp password and shares it manually for v1).
- Self-service password change / forgot-password.
- Multi-tenant staff (sub-admin). Only `customer` and `staff` can be created via the new endpoint.
- Two branded PWA installs (one admin, one customer). v1 ships a single "Splashh" install for all roles.
- Role-based theming (admin sees a different colour palette than customer).

---

## 2. Repo changes

| Action | Path |
|---|---|
| Delete | `apps/customer-pwa/` |
| Rename | `apps/admin-pwa/` → `apps/web-pwa/` |
| Modify | root `package.json` `dev` script (drop `--filter customer-pwa`) |
| Modify | root `package.json` `ui:add` (no change) |
| Modify | `apps/web-pwa/vite.config.ts` (drop the 5174 entry / proxy remains same) |
| Modify | `apps/web-pwa/package.json` `name: "web-pwa"` |
| Modify | `apps/web-pwa/index.html` (title → "Splashh") |
| Modify | `apps/web-pwa/src/App.tsx`, `routes/index.tsx` (new routes) |
| Modify | `apps/web-pwa/src/pages/*` (rename + re-path) |
| Create | `apps/web-pwa/src/pages/AdminUsersPage.tsx` |
| Create | `apps/web-pwa/src/routes/role-gate.tsx` |
| Create | `apps/web-pwa/src/routes/role-based-redirect.tsx` |
| Modify | `apps/web-pwa/src/components/PWAInstallPrompt.tsx` (manifest-neutral copy) |
| Modify | `apps/web-pwa/public/manifest.webmanifest` (name "Splashh") |
| Modify | `apps/web-pwa/src/features/admin/users/*` (new) |
| Modify | `e2e/admin.spec.ts` (login URL → `/admin/login`) |
| Modify | `e2e/customer.spec.ts` (login URL → `/login`) |
| Modify | `playwright.config.ts` (single project + baseURL) |
| Modify | `apps/backend/src/auth/application/auth_service.py` (add `roles` to `LoginResult`) |
| Modify | `apps/backend/src/auth/interfaces/http/router.py` (return roles in login/refresh responses) |
| Modify | `apps/backend/src/auth/interfaces/http/schemas.py` (TokenResponse adds `roles`) |
| Create | `apps/backend/src/auth/interfaces/http/admin_user_router.py` (or extend existing) |
| Create | `apps/backend/src/auth/application/user_admin_service.py` (create_user use case) |
| Modify | `apps/backend/tests/api/test_auth_endpoints.py` (login response shape, new create_user tests) |

---

## 3. Routing (frontend)

```
/                            public landing — "Customer login" → /login; small "Staff?" link → /admin/login
/login                       public customer login (mode="customer")
/admin/login                 staff login (mode="staff", noindex, not in public nav)
/                            authed shell (role-aware)
  /book                      customer home → FacilitiesPage
  /book/facilities/:id       facility detail + booking dialog
  /book/bookings             my bookings
  /admin                     admin home → AdminFacilitiesPage
  /admin/facilities/new
  /admin/facilities/:id
  /admin/users               NEW — list + create
  /profile                   self (shared)
```

**Route guards** (in `routes/`):
- `protected.tsx` (existing): redirect to `/login` (or `/admin/login` if `mode=staff` was in the `state.from` path's first segment) when not authed.
- `role-gate.tsx` (new): reads roles from `useAuthStore`; if user's roles include any of the required, render `<Outlet />`, otherwise render `<RoleMismatch />` (a 403 page that links to the user's actual home).
- `role-based-redirect.tsx` (new): renders nothing, but on mount navigates to the right home for the user's role. Used as the default child of `ProtectedRoute` when the user hits a bare `/`.

**`<meta name="robots" content="noindex">`** added to `/admin/login` (and ideally all `/admin/*`, via a parent route or a static `<head>` injection in the layout).

**Role → home mapping** (in `lib/role-routing.ts`):
```ts
export const homeForRoles = (roles: string[]): string => {
  if (roles.includes("tenant_admin")) return "/admin";
  if (roles.includes("customer")) return "/book";
  if (roles.includes("staff")) return "/staff";
  return "/";
};
```

---

## 4. Auth response shape (backend)

Currently `LoginResult` doesn't carry roles in the response body, even though the JWT has them. We fix that so the frontend can route immediately.

**`LoginResult` (auth_service.py):**
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

**`TokenResponse` (schemas.py):**
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

`_to_token_response` in the router populates `roles=[r.value for r in result.roles]` (the user passed via the service).

**`/v1/auth/refresh` response** — also returns `roles` (read from the persisted user record on rotation).

The frontend `loginRequest` and `silentRefresh` read `data.roles ?? []` and call `setSession({ accessToken, userId, tenantId, roles })`. This means a fresh page load that goes through `AuthBootstrap → silentRefresh` also gets the correct roles, and the `RoleBasedRedirect` can route to the right home.

---

## 5. Backend: `POST /v1/auth/users`

New use case `UserAdminService.create_user(...)`:
- Hashes password with `Argon2PasswordHasher`.
- Creates `User` with `roles` (validated to be in `["customer", "staff"]`; `tenant_admin` is rejected).
- Persists via `UserRepository.add`.
- Returns the created user (id, email, full_name, roles).

Endpoint in `auth/interfaces/http/admin_user_router.py` (or appended to the existing router):
```python
@router.post("/users", response_model=CreateUserResponse, status_code=201)
async def create_user(
    payload: CreateUserRequest,
    principal: CurrentPrincipal = Depends(auth_required),
    svc: UserAdminService = Depends(_user_admin_service),
) -> CreateUserResponse:
    if "tenant_admin" not in principal.roles:
        raise Forbidden("Only tenant admins can create users")
    user = await svc.create_user(
        tenant_id=principal.tenant_id,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        roles=payload.roles,
    )
    return CreateUserResponse(id=user.id, email=user.email, full_name=user.full_name, roles=[r.value for r in user.roles])
```

Schemas:
```python
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
```

The endpoint lives under the same `/v1/auth/*` prefix. The auth_required dependency returns 401 if no token, and the explicit `tenant_admin` check returns 403 otherwise. No new global dependency changes needed.

Tests (`tests/api/test_auth_endpoints.py`):
- `test_admin_can_create_user` — 201 with the new user.
- `test_non_admin_cannot_create_user` — 403.
- `test_create_user_validates_role` — `tenant_admin` in roles → 422.
- `test_create_user_rejects_invalid_email` — 422.
- `test_create_user_duplicate_email` — 409.

---

## 6. Frontend: `/admin/users` page

`apps/web-pwa/src/features/admin/users/`:
- `api.ts`: `usersApi.list()` → `GET /v1/auth/users` (new endpoint below), `usersApi.create(input)` → `POST /v1/auth/users`.
- `useUsers.ts`: `useUsers()` query + `useCreateUser()` mutation with `onSuccess` invalidation.

**Add `GET /v1/auth/users` to backend** (same role check as `POST`): returns `[{ id, email, full_name, roles, is_active, created_at }]`. Same `UserAdminService`. Test: `test_admin_can_list_users`, `test_non_admin_cannot_list_users`.

`AdminUsersPage`:
- Table: email · full_name · roles · created_at.
- "Add user" button opens a modal (or inline form) with email, full_name, password, role (multi-select chips for customer/staff).
- On submit: optimistic add, on error show inline.
- Uses existing `<FormField>`, `<Input>`, `<Button>` from `@splashh/ui`.

---

## 7. PWA changes

`apps/web-pwa/public/manifest.webmanifest`:
```json
{
  "name": "Splashh",
  "short_name": "Splashh",
  "description": "Book your club in seconds",
  "theme_color": "#0EA5E9",
  "background_color": "#ffffff",
  "display": "standalone",
  "start_url": "/",
  "icons": [/* unchanged */],
  "shortcuts": [
    { "name": "My bookings", "url": "/book/bookings", "icons": [...] },
    { "name": "Browse facilities", "url": "/book", "icons": [...] }
  ]
}
```

`index.html` `<title>` → "Splashh".

`PWAInstallPrompt` copy → "Install Splashh" (was "Install Splashh Admin").

Install banner: shown to all logged-in users (no role filter). The home after install adapts via `RoleBasedRedirect`.

---

## 8. Refactor: customer-pwa → web-pwa

Files moved (verbatim where possible) from `apps/customer-pwa/`:
- `src/features/facilities/*` → `apps/web-pwa/src/features/bookings/facilities/*` (or stay at `features/facilities` and be shared by both `/book` and `/admin` consumers).
- `src/features/bookings/*` → same.
- `src/pages/FacilitiesPage.tsx` → `src/pages/book/FacilitiesPage.tsx`.
- `src/pages/FacilityDetailPage.tsx` → `src/pages/book/FacilityDetailPage.tsx`.
- `src/pages/BookingsPage.tsx` → `src/pages/book/BookingsPage.tsx`.

Routes re-pointed. Path imports updated from `@/features/facilities/api` to the new path.

**Dev workflow** (after refactor):
- `pnpm dev` runs `make -C apps/backend dev` + `pnpm --filter web-pwa dev` (concurrently).
- Single port 5173 for the PWA.
- Backend still 8765.

**Vite proxy** unchanged: `/v1` → `http://127.0.0.1:8765`.

---

## 9. Data flow on login

```
/ or /admin/login
  └─> <LoginForm mode="customer"|"staff">
       └─> loginRequest(email, password)
            └─> POST /v1/auth/login → { access_token, refresh_token, user_id, tenant_id, roles }
                 └─> useAuthStore.setSession(...)
                      └─> navigate(homeForRoles(roles))
```

Subsequent visits:
```
/  (with refresh cookie)
  └─> AuthBootstrap
       └─> silentRefresh() → POST /v1/auth/refresh → { access_token, ..., roles }
            └─> useAuthStore.setSession(...)
                 └─> RoleBasedRedirect on first protected route → navigate(homeForRoles(roles))
```

---

## 10. Testing

| Level | What | Where |
|---|---|---|
| Backend unit | `UserAdminService.create_user` rejects `tenant_admin` role | `tests/unit/test_user_admin_service.py` (new) |
| Backend API | login/refresh response includes roles; create_user success + 403 + 409 + 422 | `tests/api/test_auth_endpoints.py` |
| Frontend unit | `RoleBasedRedirect` picks `/admin` for admin, `/book` for customer, `/` for none | `apps/web-pwa/test/role-based-redirect.test.tsx` (new) |
| Frontend unit | `AdminUsersPage` renders the user list and submits the create form | `apps/web-pwa/test/admin-users.test.tsx` (new) |
| E2E | admin can create a customer; customer can then log in at `/login` and see `/book` | `e2e/admin-user-creation.spec.ts` (new) |
| E2E | existing admin + customer specs updated to use the new login URLs | `e2e/admin.spec.ts`, `e2e/customer.spec.ts` |

---

## 11. Trade-offs

| Decision | Gain | Give up |
|---|---|---|
| One app | Shared auth, shared UI, single install, less duplication | One install name (not "Splashh Admin" / "Splashh Sports") |
| Two login routes | Customer entry is public, staff entry is hidden (not linked) | One more route to maintain (still 1 form) |
| Admin sets temp password | Simpler flow, no email infra | User experience is rough — admin shares a password out-of-band |
| Self-route by role after login | No landing page that asks "where do you want to go?" | If a user has multiple roles, we always go to the first one |
| GET /v1/auth/users added | Admin sees a list of users in the same tenant | New endpoint + tests |

---

## 12. Out of scope (deferred)

- Email-based invite flow (send magic link).
- Self-service password change / forgot-password.
- Multi-role accounts with a role-switcher in the UI.
- Per-tenant branding in the PWA.
- Two PWAs on subdomains (admin.splashh.com vs splashh.com).
- Bulk user import.
- Audit log of admin user-creation actions.

---

## 13. Related Documents

- `docs/superpowers/specs/2026-08-06-frontend-pwas-design.md` — prior spec (two PWAs, superseded by this one for the role/login story)
- `docs/05-frontend/state-management.md` — TanStack Query / RHF / Zustand patterns
- `docs/09-security/` — refresh-token rotation, role-based access
