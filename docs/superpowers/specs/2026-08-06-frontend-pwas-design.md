# Frontend PWAs — Design Spec

**Date:** 2026-08-06
**Status:** Draft — pending user review
**Scope:** Initial scaffold of `admin-pwa`, `customer-pwa`, and a shared UI package, plus a small backend addition for httpOnly refresh-token cookies. Targets a demonstrable thin slice in both apps against the live backend.

---

## 1. Goals & Non-Goals

**Goals**

- Two installable PWAs that share a single source of UI primitives and a single typed API client.
- A demonstrable thin slice in each app: customer can log in, browse facilities, book a slot, cancel; admin can log in, create a facility + resource, see today's bookings.
- Cookie-based silent refresh on top of the existing JWT auth flow, so access tokens never touch `localStorage`.
- Type-safe API layer generated from the backend's OpenAPI.
- pnpm workspace with source-linked packages so we don't duplicate UI primitives or API plumbing.

**Non-Goals (deferred)**

- Push notifications (VAPID + backend endpoint + service-worker handler).
- Multi-tenant white-labelling and per-tenant theme overrides.
- Realtime updates (WebSocket / SSE) — current design polls via TanStack Query.
- Internationalization (English only).
- Payments (Stripe / etc.).
- Mobile native shells (Capacitor / Tauri).
- Production deploy / CI-CD / hosting configuration.
- Broad E2E coverage — only thin-slice smoke specs in v1.

---

## 2. Decisions Locked In (from brainstorm)

| Decision | Choice |
|---|---|
| v1 scope | Both PWAs + shared UI package |
| Auth storage | Access token in memory; refresh in httpOnly cookie set by backend |
| Thin slice | Both PWAs ship a usable thin slice in v1 |
| Brand | Sports-blue (`#0EA5E9` light / `#38BDF8` dark); light + dark mode via `next-themes` |
| Monorepo shape | pnpm workspace, 3 packages: `admin-pwa`, `customer-pwa`, `packages/ui` (+ `api-client`, `config`) |
| Stack | Vite + React 18 + TypeScript 5.6 + shadcn/ui + Tailwind + vite-plugin-pwa + TanStack Query v5 + React Router v6 (data router) + React Hook Form + Zod + Zustand + Biome |

---

## 3. Repo Layout

```
splash_sports_management/
  apps/
    backend/                # already exists
    admin-pwa/              # NEW — port 5173 in dev, role=tenant_admin / staff
    customer-pwa/           # NEW — port 5174 in dev, role=customer
  packages/
    ui/                     # NEW — @splashh/ui, shadcn primitives + brand tokens + composites
    api-client/             # NEW — @splashh/api-client, typed fetch + auth interceptor + query keys
    config/                 # NEW — @splashh/config, shared tsconfig + biome + vitest presets
  pnpm-workspace.yaml
  package.json              # root scripts: dev, build, lint, test, typecheck
  tsconfig.base.json
  .npmrc                    # node-linker=hoisted (Vite resolves workspace symlinks)
  biome.json
```

**Workspace packages:**

| Package | Exports | Consumed by |
|---|---|---|
| `@splashh/config` | tsconfig presets, vitest config preset, biome config preset | both PWAs, both libs |
| `@splashh/ui` | components, hooks, lib, styles, tokens | both PWAs |
| `@splashh/api-client` | `api` (axios instance), `queryKeys`, `types`, `authStore` | both PWAs |

**Why a separate API client:** the silent-refresh interceptor, request queueing, type generation, and query-key constants are non-trivial. Putting them in a shared package keeps the two apps in lock-step — if the refresh logic changes, both apps get the fix.

**Why `config`:** both PWAs would otherwise duplicate tsconfig settings, vitest setup, and ESLint/Biome config. Centralizing prevents drift.

---

## 4. Shared UI Package (`@splashh/ui`)

```
packages/ui/
  src/
    components/
      ui/                   # shadcn primitives (shadcn CLI-generated, brand-themed)
        Button.tsx
        Card.tsx
        Dialog.tsx
        Input.tsx
        Label.tsx
        Select.tsx
        Skeleton.tsx
        Alert.tsx
        Badge.tsx
        Tabs.tsx
        Table.tsx
        Toast.tsx           # sonner
        ...
      forms/                # composites that wrap primitives + RHF bindings
        FormField.tsx       # label + control + error + description
        DatePicker.tsx      # react-day-picker themed
        TimePicker.tsx
        SelectField.tsx
        SubmitButton.tsx    # isPending-aware
      data/
        DataTable.tsx       # generic, TanStack Table headless
        EmptyState.tsx
        StatCard.tsx
      feedback/
        ConfirmDialog.tsx
        ErrorBoundary.tsx
        LoadingScreen.tsx
      layout/
        AppShell.tsx        # header + sidebar + main; role-specific shells live in apps
        PageHeader.tsx
        SectionCard.tsx
    hooks/                  # generic only
      useMediaQuery.ts
      useDebounce.ts
      useDisclosure.ts
    lib/
      cn.ts                 # tailwind-merge + clsx
      formatters.ts         # currency, date, time
    styles/
      globals.css           # tailwind base + shadcn theme variables (light/dark)
    tokens.ts               # brand color constants for non-Tailwind contexts
  package.json              # exports . for consumers
  tailwind.config.ts        # preset extending shadcn; brand color injected
  components.json           # shadcn CLI config: "ui" base dir = src/components/ui
```

**Rules:**

- No feature logic. No API calls. No router imports. Pure presentational.
- Every primitive accepts `className` and forwards refs so consumers can compose.
- Strict TypeScript: `strict`, `noUncheckedIndexedAccess: true`.
- Barrel export: `index.ts` re-exports everything.

**Theme:**

- shadcn's CSS-variable theme system.
- `globals.css` defines `:root` and `.dark` overrides for `--primary`, `--background`, `--foreground`, `--muted`, `--border`, etc.
- Brand color: light `#0EA5E9` (sky-500), dark `#38BDF8` (sky-400).
- `next-themes` toggles `.dark` on `<html>`, persisted to localStorage as `theme`, system-default on first load.

---

## 5. API Client (`@splashh/api-client`)

```
packages/api-client/
  src/
    api/
      client.ts             # axios instance with baseURL='/v1'
      interceptors.ts       # request: attach Bearer; response: 401 → silent refresh
      refresh.ts            # single-flight refresh promise; queue concurrent requests
    auth/
      store.ts              # Zustand: accessToken, user, tenantId, isAuthenticated
      bootstrap.tsx         # <AuthBootstrap /> — on mount, try /v1/auth/refresh once
      permissions.ts        # hasRole(user, role) helpers
    query/
      keys.ts               # typed query-key factory (per-resource + per-filter)
      client.ts             # TanStack QueryClient with sensible defaults
    types/
      api.gen.ts            # generated from backend openapi.json (openapi-typescript)
      domain.ts             # hand-written domain types re-exported from generated types
    openapi.config.ts       # openapi-typescript config; reads backend /openapi.json
  scripts/
    generate-types.sh       # curl backend, run openapi-typescript, write to types/api.gen.ts
  package.json
```

**Auth interceptor (single-flight):**

```
async function refreshAccessToken() {
  // Returns a single in-flight promise.
  // Subsequent calls during refresh reuse the same promise.
  if (inflight) return inflight;
  inflight = axios.post("/v1/auth/refresh", null, { withCredentials: true })
    .then(r => { store.setAccessToken(r.data.access_token); return r.data.access_token; })
    .catch(err => { store.clear(); throw err; })
    .finally(() => { inflight = null; });
  return inflight;
}

// On 401:
//   1. if no concurrent refresh, start one and remember the request
//   2. if refresh succeeds, retry original request with new token
//   3. if refresh fails, clear store and emit "unauthorized" event (router redirects)
```

**Query keys:**

```
export const queryKeys = {
  facilities: {
    all: ["facilities"] as const,
    list: (tenantId: string) => ["facilities", "list", tenantId] as const,
    detail: (id: string) => ["facilities", "detail", id] as const,
  },
  bookings: {
    listByResource: (resourceId: string) => ["bookings", "by-resource", resourceId] as const,
    listByCustomer: (customerId: string) => ["bookings", "by-customer", customerId] as const,
    detail: (id: string) => ["bookings", "detail", id] as const,
  },
  customers: {
    list: (tenantId: string) => ["customers", "list", tenantId] as const,
    detail: (id: string) => ["customers", "detail", id] as const,
  },
};
```

---

## 6. Backend Cookie Addition

Small additive change to the existing auth flow. Both modes (JSON-body refresh + cookie refresh) work; the existing server-to-server / CLI path is unaffected.

**New settings** (`common/infrastructure/settings.py` or `auth/.../settings.py`):

```
auth_refresh_cookie_name: str = "refresh_token"
auth_refresh_cookie_secure: bool = True            # False in dev
auth_refresh_cookie_samesite: str = "lax"
auth_refresh_cookie_max_age_seconds: int = 2_592_000  # 30 days
```

**`POST /v1/auth/login`** (existing):

- On success, in addition to the JSON body, set `Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/v1/auth; Max-Age=2592000`.
- Existing JSON body unchanged.

**`POST /v1/auth/refresh`** (existing):

- Read refresh from cookie first (`request.cookies.get("refresh_token")`); fall back to JSON body if cookie absent.
- Validate the JWT exactly as today.
- On rotation success: set new `Set-Cookie` with the rotated token.
- On reuse detection / expiry: clear the cookie (`Set-Cookie: refresh_token=; Max-Age=0`).

**`POST /v1/auth/logout`** (existing):

- On success, clear the cookie. Idempotent — invalid refresh tokens still 204 and clear.

**Cookie attributes:**

| Attribute | Value | Rationale |
|---|---|---|
| `HttpOnly` | yes | JS cannot exfiltrate the refresh token |
| `Secure` | yes in prod, no in dev | HTTPS-only in production |
| `SameSite` | `Lax` | Allows top-level navigations from email links; blocks cross-site POST |
| `Path` | `/v1/auth` | Cookie only sent to auth endpoints — minimizes blast radius |
| `Max-Age` | 30 days | Matches refresh-token TTL |

**Why Path is scoped to `/v1/auth`:** if a future XSS in another surface (e.g. user-generated content in admin-pwa) somehow exfiltrates cookies, the attacker only gets refresh tokens, which are rotation-locked and short-lived.

**Access-token TTL:** shorten from 15min → 5min in dev/prod settings since silent refresh is now reliable. No breaking change for the JSON-body mode (it just refreshes more often).

**Tests:**

- `tests/api/test_auth_endpoints.py`: add `test_login_sets_refresh_cookie`, `test_refresh_via_cookie`, `test_logout_clears_cookie`, `test_refresh_reuse_clears_cookie`.
- Integration: confirm existing body-mode refresh still works (server-to-server).

---

## 7. Routing & Guards (both PWAs)

React Router v6 **data router** (`createBrowserRouter`, not `<Routes>`). Both PWAs share the same shape:

```
/                          → public landing / role-based redirect
/login                     → public
/register-tenant           → public (admin-pwa only; gated by env flag in customer-pwa)
/                          → protected shell (AppShell + <Outlet />)
  /dashboard               → role-dependent landing
  /facilities              → list (admin: manage; customer: browse)
  /facilities/:id          → detail
  /bookings                → list
  /bookings/new            → wizard (customer-pwa only)
  /bookings/:id            → detail (cancel / checkin actions per role)
  /profile                 → self
/                          → admin-only shell (admin-pwa)
  /admin/facilities/new
  /admin/facilities/:id/resources
  /admin/facilities/:id/availability
  /admin/customers
  /admin/reports
```

**Guards:**

- `<ProtectedRoute requires="auth">`: data-router loader reads Zustand store via `useAuthStore.getState()`; redirects to `/login?next=<path>` if no access token and the silent-refresh bootstrap hasn't yet succeeded.
- `<RoleGate roles={["tenant_admin"]}>`: wraps admin-only segments. If the user's roles don't include any of the required, renders a friendly 403 page.
- Both run as loaders so unauthorized navigation never flashes content.

**Code splitting:** every route's component is `React.lazy(() => import(...))`. Initial bundle = shell + auth + TanStack Query + landing only. Each feature lands as its own chunk.

**Auth bootstrap:**

```
<AuthBootstrap />   // rendered once at app root
  useEffect(() => {
    if (!store.accessToken) {
      api.post("/v1/auth/refresh", null, { withCredentials: true })
        .then(r => store.setSession(r.data))
        .catch(() => {/* not logged in; stay on landing */});
    }
  }, []);
```

---

## 8. State Management

| State type | Tool | Example |
|---|---|---|
| Server (queries) | TanStack Query v5 | facility list, booking detail |
| Server (mutations) | TanStack Query `useMutation` + optimistic updates | create booking, cancel booking |
| Auth (singleton) | Zustand store, hydrated by `AuthBootstrap` | access token, current user |
| UI (theme, sidebar open) | `next-themes` + Zustand | dark/light, drawer state |
| Form | React Hook Form + Zod resolver | all forms |
| URL | React Router search params | filters, pagination |

**Optimistic updates for the booking flow:**

- `createBooking` — `onMutate` cancels `queryKeys.bookings.listByResource(id)`, snapshots, prepends a `pending` booking; `onError` rolls back from snapshot; `onSettled` invalidates the relevant keys.
- `cancelBooking` — optimistic status flip to `cancelled` on both detail and list queries; rollback on error.

**Cache invalidation discipline:** every mutation's `onSettled` calls `qc.invalidateQueries({ queryKey: ... })` with the smallest key set. The `queryKeys` factory in `@splashh/api-client` ensures the strings can't drift.

---

## 9. PWA Features

`vite-plugin-pwa` with `generateSW` (Workbox) for both apps. Distinct manifests:

| Field | admin-pwa | customer-pwa |
|---|---|---|
| `name` | "Splashh Admin" | "Splashh Sports" |
| `short_name` | "Splashh Admin" | "Splashh" |
| `theme_color` | `#0EA5E9` | `#0EA5E9` |
| `categories` | business, productivity | sports, lifestyle |
| `shortcuts` | Today's Bookings, New Facility | My Bookings, Book a Court |

**Service worker strategies** (Workbox `runtimeCaching`):

| Pattern | Strategy | Cache name | Expiry |
|---|---|---|---|
| App shell (`**/*.{js,css,html,woff2}`) | `CacheFirst` | `app-shell` | 30 days |
| `/v1/*` API | `NetworkFirst` (10s timeout) | `api-cache` | 24h, only `CacheableResponsePlugin` 200/0 |
| Images (`*.{png,jpg,svg,webp,avif,gif}`) | `CacheFirst` | `image-cache` | 30 days, 200 entries |
| Fonts (`/fonts/*.woff2`) | `CacheFirst` | `font-cache` | 1 year, 20 entries |

**Install prompt:** `<PWAInstallPrompt />` listens for `beforeinstallprompt`, defers it, surfaces a bottom-left card on the **third** visit (persisted in localStorage as `install_dismissed_at`). Dismissal lasts 7 days.

**Update flow:** `useRegisterSW` from `virtual:pwa-register/react`. When `needRefresh` flips true, a top banner says "New version available — refresh". On accept, `updateServiceWorker(true)` reloads.

**Push notifications:** deferred. Hooks in place (`requestNotificationPermission`, `subscribeToPush`) but no VAPID / backend endpoint / SW handler.

**Offline support:** app shell + last-viewed bookings (TanStack Query persistence via `@tanstack/query-sync-storage-persister` to IndexedDB). **Outbox for offline create-booking is out of scope** — show a banner if the user attempts to mutate while offline.

---

## 10. Testing

| Level | Tool | Scope |
|---|---|---|
| Unit / component | Vitest + React Testing Library + happy-dom | Co-located `*.test.ts(x)` |
| Coverage gate | Vitest `--coverage` | `packages/ui` ≥ 80%, `packages/api-client` ≥ 80%, app code ≥ 60% |
| E2E | Playwright | Two projects (`admin-pwa`, `customer-pwa`); one smoke spec each |
| Mocking | MSW | For local component tests; NOT used in E2E |
| Accessibility | `@axe-core/playwright` | Runs on every E2E spec; CI fails on serious/critical violations |

**E2E smoke specs (Playwright):**

- `admin-pwa`: login → create facility → add resource → assert visible in list.
- `customer-pwa`: login → browse facilities → open facility → attempt booking → assert booking appears in "My bookings".

Both run against the live backend (started in CI via docker-compose). Locally they run against `uv run uvicorn` on port 8765 with Vite dev server proxying `/v1`.

---

## 11. Tooling

- **Package manager:** pnpm 9.x with `node-linker=hoisted` so Vite resolves workspace symlinks without extra plugins.
- **TypeScript:** 5.6, strict mode, project references rooted at `packages/config/tsconfig.base.json`.
- **Lint/format:** Biome (single tool — faster than eslint+prettier, fewer deps). One `biome.json` at root.
- **Husky + lint-staged:** pre-commit runs `biome check --write` on staged files only.
- **shadcn CLI:** `pnpm ui:add <name>` proxies to `pnpm --filter @splashh/ui dlx shadcn@latest add <name>`.

**Root scripts:**

| Script | Effect |
|---|---|
| `pnpm dev` | `concurrently -k -n backend,admin,customer "make -C apps/backend dev" "pnpm --filter admin-pwa dev" "pnpm --filter customer-pwa dev"` |
| `pnpm build` | `pnpm -r build` |
| `pnpm typecheck` | `pnpm -r typecheck` |
| `pnpm lint` | `biome check .` |
| `pnpm test` | `pnpm -r test` |
| `pnpm test:e2e` | `playwright test` |
| `pnpm ui:add <name>` | shadcn add scoped to `packages/ui` |

**Why `make -C apps/backend dev`:** the backend is a Python project managed by `uv`, not a pnpm package. A Makefile target in `apps/backend/Makefile` (or `scripts/backend-dev.sh`) wraps `uv run uvicorn ...` so the root `pnpm dev` can orchestrate all three processes uniformly.

---

## 12. Thin Slice — What "Done" Means in v1

**customer-pwa:**

1. `/login` form with email + password (RHF + Zod). On submit, login → redirect to `/facilities`.
2. `/facilities` list page: TanStack Query `useQuery` against `/v1/facility`; renders facility cards.
3. `/facilities/:id` detail: shows facility info + list of resources; each resource has a "Book" button.
4. Booking modal (or `/bookings/new`): date picker, time picker, confirm → optimistic create → success toast.
5. `/bookings` list: shows current user's bookings (filter by upcoming/past); cancel button with confirmation dialog → optimistic status flip.
6. PWA: installable; install prompt banner; update banner on new SW.

**admin-pwa:**

1. `/login` (same shape).
2. `/admin/facilities` list: read-only view of all facilities in tenant.
3. `/admin/facilities/new`: form (name, slug, address, timezone) → create → redirect to detail.
4. `/admin/facilities/:id`: detail page with tabs (Info / Resources / Availability / Bookings).
5. Add Resource form, Add Availability Rule form — both under tabs.
6. `/bookings` (cross-tenant view): list all today's bookings with check-in / complete actions.
7. PWA: installable; install + update banners.

**Backend:**

- Cookie-based refresh endpoint + tests as described in §6.

---

## 13. Open Questions for Implementation Phase

These are explicitly deferred to the implementation plan / writing-plans phase:

- Exact copy for empty states, error states, toast wording.
- Icon set (lucide vs heroicons vs custom) — lucide is the shadcn default; assumed.
- Date / time library — `react-day-picker` is the assumption; revisit if the booking time-slot picker needs more.
- Whether `next-themes` is the right theme lib given it's Next.js-named — it works in Vite; if friction arises, swap to a tiny `useDarkMode` hook.
- Cypress vs Playwright — Playwright chosen; revisit if E2E pain emerges.

---

## 14. Trade-offs

| Decision | Gain | Give up |
|---|---|---|
| pnpm workspace + 3 packages | No UI duplication, single API client source | More upfront setup, project references to maintain |
| httpOnly refresh cookie | XSS-resistant refresh | Requires backend change; cookie-based auth is harder to debug |
| Source-linked UI package | Both apps see updates instantly | One app's broken primitive breaks the other (mitigated by tests) |
| TanStack Query for all server state | Caching + invalidation + optimistic updates for free | Bundle size (~13kB gz) |
| `generateSW` (Workbox) over custom SW | Battle-tested offline + cache strategies | Less control over edge cases |
| Biome over ESLint + Prettier | Single tool, faster, fewer deps | Less mature plugin ecosystem (rarely needed) |
| Vite dev proxy | No CORS in dev | Prod deploy must preserve same-origin or set CORS carefully |

---

## 15. Related Documents

- `docs/05-frontend/pwa-strategy.md` — PWA patterns this builds on
- `docs/05-frontend/folder-structure.md` — vertical-slice conventions
- `docs/05-frontend/state-management.md` — TanStack Query + RHF + Zustand patterns
- `docs/05-frontend/caching.md` — cache-time / stale-time / invalidation
- `docs/05-frontend/component-design.md`, `forms.md`, `hooks.md` — design conventions
- `docs/09-security/` — refresh-token rotation, CSRF posture
