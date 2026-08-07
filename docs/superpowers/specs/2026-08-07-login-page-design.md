# Login Page & App Shell Redesign — Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Splashh web-pwa login page and add a persistent sidebar+top-bar app shell on every protected route, with a working logout flow.

**Architecture:** A new `AppShell` component wraps the existing protected routes (`<RoleGate>` children) in `apps/web-pwa/src/routes/index.tsx`. The shell is composed of three sibling components — `Sidebar`, `TopBar`, `UserMenu` — fed by a role-aware nav config. The login page is redesigned to a centered card on a soft gradient, with a Customer/Staff tab toggle that replaces the two separate routes. Logout is a React Query mutation that posts to `/v1/auth/logout`, clears the auth store, and navigates home.

**Tech Stack:** React 19, react-router-dom, @tanstack/react-query, Tailwind CSS, zustand (auth store), vitest + @testing-library/react. No new dependencies; no new `@splashh/ui` primitives.

## Global Constraints

- Brand primary color: `sky-500` (`#0EA5E9`) — already declared in the PWA manifest and used by `@splashh/ui` tokens. Do not introduce a new color.
- Avatar gradient: `sky-500` → `cyan-500` (`#0EA5E9` → `#06B6D4`).
- Type: system font stack via Tailwind defaults. No custom font load.
- Radii: `rounded-2xl` for the login card, `rounded-lg` for sidebar items, `rounded-full` for the avatar.
- Shadows: `shadow-sm` for sidebar, `shadow-md` for the login card, `shadow-xl` for popover.
- All four existing demo accounts must continue to log in successfully: `admin@demo.splashh.dev` (Staff), `alex@demo.splashh.dev` / `priya@demo.splashh.dev` / `jordan@demo.splashh.dev` (Customer).
- Logout must succeed even if `POST /v1/auth/logout` returns 401 or network-fails (graceful degradation; the local store is the source of truth for UI).
- `/admin/login` must continue to work as a deep-link and pre-select the Staff tab.
- Admin pages must remain `noindex` (existing `useNoIndex` hook, unchanged).
- The existing `AuthBootstrap`, `ProtectedRoute`, `RoleGate`, `RoleBasedRedirect`, and `api` axios interceptor (401 → silentRefresh) remain untouched.
- E2E flow is covered by the existing `e2e/admin-user-creation.spec.ts` and friends; this design does not add new e2e tests.

## File Structure

**Files created (5):**
- `apps/web-pwa/src/components/AppShell.tsx`
- `apps/web-pwa/src/components/Sidebar.tsx`
- `apps/web-pwa/src/components/TopBar.tsx`
- `apps/web-pwa/src/components/UserMenu.tsx`
- `apps/web-pwa/src/features/auth/useLogout.ts`

**Test files created (5):**
- `apps/web-pwa/test/login-page.test.tsx`
- `apps/web-pwa/test/app-shell.test.tsx`
- `apps/web-pwa/test/sidebar.test.tsx`
- `apps/web-pwa/test/topbar.test.tsx`
- `apps/web-pwa/test/use-logout.test.ts`

**Files modified (3):**
- `apps/web-pwa/src/pages/LoginPage.tsx` — redesign; add tabs; accept `?role=staff`
- `apps/web-pwa/src/pages/AdminLoginPage.tsx` — becomes a redirect to `/login?role=staff`
- `apps/web-pwa/src/routes/index.tsx` — wrap `<RoleGate>` children with `<AppShell>`

**No new `@splashh/ui` primitives. No new npm dependencies.**

---

## Architecture

### `AppShell`

Receives `children` (the page content), reads `useAuthStore` for `roles` and `userId`, derives the nav config from `NAV_BY_ROLE`, and renders `<Sidebar>` + `<TopBar>` + `<main>{children}</main>`.

```ts
// apps/web-pwa/src/components/AppShell.tsx
export function AppShell({ children }: { children: React.ReactNode }) {
  const roles = useAuthStore((s) => s.roles);
  const items = useMemo(() => navForRoles(roles), [roles]);
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <div className="flex min-h-screen bg-slate-50">
      <a href="#main" className="sr-only focus:not-sr-only ...">Skip to main content</a>
      <Sidebar items={items} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      {mobileOpen && <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={() => setMobileOpen(false)} aria-hidden />}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar mobileOpen={mobileOpen} onToggleSidebar={() => setMobileOpen((v) => !v)} />
        <main id="main" className="flex-1 p-4 md:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
```

### `Sidebar`

```ts
// apps/web-pwa/src/components/Sidebar.tsx
export interface NavItem { to: string; label: string; icon: string; }
export function Sidebar({ items, mobileOpen, onClose }: { items: NavItem[]; mobileOpen: boolean; onClose: () => void; }) {
  return (
    <aside className={cn(
      "fixed md:static inset-y-0 left-0 z-40 w-60 bg-white border-r border-slate-200 shadow-sm",
      "transform transition-transform duration-200 ease-out md:transform-none",
      mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
    )} aria-label="Primary">
      <div className="px-4 py-4 font-bold text-sky-900">Splashh</div>
      <nav aria-label="Primary"><ul role="list" className="px-2 space-y-1">
        {items.map((item) => <SidebarItem key={item.to} item={item} onNavigate={onClose} />)}
      </ul></nav>
      <div className="absolute bottom-0 left-0 right-0 p-2 border-t border-slate-200">
        <UserMenu />
      </div>
    </aside>
  );
}
```

`SidebarItem` is an internal subcomponent. It uses `NavLink` from `react-router-dom` and applies active styling (sky-50 bg, sky-700 text, 2px left border sky-500) when the current path matches `item.to`. On mobile, clicking an item calls `onNavigate()` to close the drawer.

### `TopBar`

```ts
// apps/web-pwa/src/components/TopBar.tsx
export function TopBar({ mobileOpen, onToggleSidebar }: { mobileOpen: boolean; onToggleSidebar: () => void }) {
  const { pathname } = useLocation();
  const title = titleForPath(pathname);
  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center px-3 md:px-6 gap-3">
      <button
        type="button"
        aria-label="Toggle navigation"
        aria-expanded={mobileOpen}
        aria-controls="primary-nav"
        onClick={onToggleSidebar}
        className="md:hidden p-2 rounded hover:bg-slate-100"
      >☰</button>
      <h1 className="text-base font-semibold text-slate-900 truncate">{title}</h1>
      <div className="ml-auto" />
    </header>
  );
}
```

`titleForPath` already exists in `apps/web-pwa/src/lib/page-titles.ts` and is reused. The hamburger button's `aria-expanded` is wired to the same `mobileOpen` state owned by `AppShell`; `AppShell` passes the boolean and the toggle callback to `TopBar`.

### `UserMenu`

```ts
// apps/web-pwa/src/components/UserMenu.tsx
export function UserMenu() {
  const userId = useAuthStore((s) => s.userId);
  const initials = (userId ?? "?").slice(0, 1).toUpperCase();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));
  useEscapeKey(() => setOpen(false));
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 p-2 rounded hover:bg-slate-100"
      >
        <span aria-hidden className="w-7 h-7 rounded-full bg-gradient-to-br from-sky-500 to-cyan-500 text-white text-xs font-semibold flex items-center justify-center">{initials}</span>
        <span className="text-sm text-slate-700">Account</span>
      </button>
      {open && (
        <div role="menu" className="absolute bottom-full left-0 mb-1 w-44 bg-white rounded-lg shadow-xl border border-slate-200 py-1">
          <button
            role="menuitem"
            type="button"
            onClick={() => { setOpen(false); /* useLogout.mutate() */ }}
            className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50"
          >Log out</button>
        </div>
      )}
    </div>
  );
}
```

`useClickOutside` and `useEscapeKey` are tiny local hooks (≤ 10 lines each) defined in the same file. They use `mousedown` and `keydown` listeners on `document`.

### `useLogout`

```ts
// apps/web-pwa/src/features/auth/useLogout.ts
export function useLogout() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: async () => {
      try {
        await api.post("/auth/logout");
      } catch {
        // swallow — local logout still proceeds
      }
    },
    onSettled: () => {
      useAuthStore.getState().clear();
      navigate("/", { replace: true });
    },
  });
}
```

### Nav config

```ts
// apps/web-pwa/src/components/nav.ts
export const NAV_BY_ROLE: Record<string, NavItem[]> = {
  customer: [
    { to: "/book", label: "Browse", icon: "🏊" },
    { to: "/book/bookings", label: "My bookings", icon: "📅" },
  ],
  tenant_admin: [
    { to: "/admin", label: "Facilities", icon: "🏢" },
    { to: "/admin/users", label: "Users", icon: "👥" },
  ],
};

export function navForRoles(roles: string[]): NavItem[] {
  for (const r of roles) {
    if (NAV_BY_ROLE[r]) return NAV_BY_ROLE[r];
  }
  return [];
}
```

Order: customer takes precedence for shared logins (a user with both roles sees customer nav in v1; a "Switch to admin" link is deferred — YAGNI).

---

## Login Page Redesign

```ts
// apps/web-pwa/src/pages/LoginPage.tsx
export function LoginPage() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);
  const [search] = useSearchParams();
  const initialMode: "customer" | "staff" = search.get("role") === "staff" ? "staff" : "customer";
  const [mode, setMode] = useState<"customer" | "staff">(initialMode);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  useEffect(() => { emailRef.current?.focus(); }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4"
          style={{ background: "linear-gradient(180deg, rgb(224 242 254) 0%, white 60%)" }}>
      <div className="mb-6 text-center">
        <div className="text-3xl font-bold text-sky-900">Splashh</div>
        <div className="text-sm text-slate-500">Book your club in seconds</div>
      </div>
      <Card className="w-full max-w-sm rounded-2xl shadow-md">
        <CardHeader>
          <div role="tablist" aria-label="Login type" className="flex border-b border-slate-200">
            <Tab id="customer" selected={mode === "customer"} onSelect={() => setMode("customer")}>Customer</Tab>
            <Tab id="staff"    selected={mode === "staff"}    onSelect={() => setMode("staff")}>Staff</Tab>
          </div>
        </CardHeader>
        <CardContent>
          <LoginForm mode={mode} headingLevel="h2" emailRef={emailRef}
                     onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })} />
        </CardContent>
      </Card>
      <p className="mt-6 text-xs text-slate-500">Need help? Contact your club.</p>
    </main>
  );
}
```

`Tab` is a local subcomponent (≤ 20 lines) handling `role="tab"`, `aria-selected`, and arrow-key navigation between the two tabs. `LoginForm` is unchanged — it already accepts `mode` and `headingLevel` props.

`AdminLoginPage.tsx` becomes:

```ts
// apps/web-pwa/src/pages/AdminLoginPage.tsx
import { Navigate } from "react-router-dom";
export function AdminLoginPage() { return <Navigate to="/login?role=staff" replace />; }
```

---

## Data Flow

### Login

1. User on `/login` (or `/login?role=staff`) submits the form.
2. `useLogin` mutation → `POST /v1/auth/login` with `{ email, password, mode }`.
3. On 200: `useAuthStore.setSession({ accessToken, userId, tenantId, roles })`.
4. `onSuccess(roles)` → `navigate(homeForRoles(roles), { replace: true })`.
5. `ProtectedRoute` sees `isAuthenticated` and renders the new `<AppShell>` wrapping the role-gated child.

### Logout

1. User clicks the sidebar footer avatar → `UserMenu` opens.
2. User clicks "Log out" → `useLogout.mutate()`.
3. `mutationFn` calls `api.post("/auth/logout")`; on any error (401, network, etc.) the error is swallowed.
4. `onSettled` runs unconditionally: `useAuthStore.getState().clear()` then `navigate("/", { replace: true })`.
5. The user lands on `HomePage` (`/`) showing the "Customer login" / "Admin login" entry points.

### Role routing (unchanged)

- `ProtectedRoute` redirects unauthenticated users to `/login`.
- `RoleGate` redirects users with the wrong role to `/redirect`, which is handled by `RoleBasedRedirect` to their correct home.
- After login, the `homeForRoles(roles)` helper picks the first matching route. For `customer` → `/book`; for `tenant_admin` → `/admin`.

### Mobile sidebar state

Owned by `AppShell` (`mobileOpen: boolean`). Passed down to `Sidebar` (controls slide-in class) and `TopBar` (controls `aria-expanded` on the hamburger button, via an `onToggleSidebar` callback that flips the same state).

---

## Error Handling

- **Login errors:** existing `useLogin` surfaces backend `detail` (e.g. "Invalid credentials") in the `role="alert"` region. No change.
- **Logout errors:** swallowed by design (see Logout flow). The local store is the source of truth for UI, so the user appears logged out regardless of what the server says.
- **Network down during login:** existing `api` interceptor propagates the error to `useLogin.error`, which the form already renders.
- **Network down during logout:** `mutationFn` catches; `onSettled` still clears and navigates.
- **Token expiry after the page has been open for >5 min:** the `api` interceptor's 401 handler calls `silentRefresh`. If refresh fails, it calls `useAuthStore.getState().clear()` and the user is bounced to `/login` (existing behavior, unchanged).

---

## Testing

Test stack: `vitest` + `@testing-library/react` + `@testing-library/user-event` + `happy-dom`. Wrapper pattern: `QueryClient` + `QueryClientProvider` + `MemoryRouter`. Mock `@splashh/api-client` and stub `api.post` per test (mirrors the pattern in `test/login.test.tsx`).

### `test/login-page.test.tsx`
- Tabs render with Customer selected by default
- Clicking Staff switches the active tab and updates the form's `mode` prop
- URL `?role=staff` pre-selects Staff on first render
- Submitting the Customer tab calls `api.post("/auth/login", { ..., mode: "customer" })`
- Submitting the Staff tab calls `api.post("/auth/login", { ..., mode: "staff" })`
- After successful login, navigates to `homeForRoles(roles)` (mock `useNavigate`)
- Validation errors on empty fields (carry-over from existing `LoginForm` tests)

### `test/app-shell.test.tsx`
- Renders `<Sidebar>` + `<TopBar>` + children
- Shows the customer nav items when `roles = ["customer"]`
- Shows the admin nav items when `roles = ["tenant_admin"]`
- TopBar shows the page title from the current route
- Clicking the avatar in the sidebar footer opens `UserMenu`; clicking "Log out" calls `useLogout`
- Mobile sidebar is hidden by default; clicking the hamburger button opens it

### `test/sidebar.test.tsx`
- Renders nav items as `NavLink`s with their labels
- The current route's item has the active styling (sky-50 background, etc.)
- The footer avatar shows the first character of `userId` uppercased

### `test/topbar.test.tsx`
- Renders the page title from the `pathname` prop
- Renders the hamburger button on viewports < 768px
- Does not render the hamburger on viewports ≥ 768px
- Clicking the hamburger calls `onToggleSidebar`
- `aria-expanded` on the hamburger button reflects the `mobileOpen` prop

### `test/use-logout.test.ts`
- Calls `api.post("/auth/logout")` on mutate
- On success: clears the auth store and navigates to `/`
- On API error (e.g., 401): still clears the auth store and navigates to `/` (graceful degradation)
- After a successful call, the store `isAuthenticated` is `false`

### Not tested (YAGNI)
- E2E flow (existing `e2e/*.spec.ts`)
- Animations / transitions
- Popover positioning details
- `AuthBootstrap` rehydration (covered by existing tests)
- `RoleGate` / `ProtectedRoute` (covered by existing tests)
- Visual regressions

---

## Out of Scope (deferred)

- A real `Avatar` primitive (image uploads) — v1 uses initials-on-gradient.
- A real user name display — v1 derives initials from `userId` and labels the menu row "Account".
- "Switch to admin" for users with both roles.
- Profile / Settings / Help menu items (YAGNI per design decision).
- Dark mode.
- Internationalization.
- Persistent collapsed/expanded sidebar preference.
- Keyboard shortcut to open the user menu (e.g., `g` then `u`).

## Spec self-review

- ✅ No placeholders or TBDs.
- ✅ Internal consistency: every section references the same file names, the same color tokens, the same component breakdown.
- ✅ Scope: one design, one app surface, no decomposition needed.
- ✅ No ambiguous requirements — every value (color, radius, font stack, endpoint) is explicit.
