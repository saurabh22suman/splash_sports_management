# Login Page & App Shell Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Splashh web-pwa login page to a centered card on a soft gradient with Customer/Staff tabs, and add a persistent sidebar+top-bar app shell on every protected route with a working logout flow.

**Architecture:** A new `AppShell` component wraps the existing protected routes in `apps/web-pwa/src/routes/index.tsx`. The shell is composed of three sibling components — `Sidebar`, `TopBar`, `UserMenu` — fed by a role-aware nav config in `components/nav.ts`. The login page is redesigned to a centered card on a soft gradient, with a Customer/Staff tab toggle that replaces the two separate routes. Logout is a React Query mutation that posts to `/v1/auth/logout`, clears the auth store, and navigates home.

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
- E2E flow is covered by the existing `e2e/*.spec.ts`; this plan adds no new e2e tests.
- All commands below assume the repo root `/home/soloengine/Github/splash_sports_management` as the working directory.

---

## Task 1: `useLogout` hook

**Files:**
- Create: `apps/web-pwa/src/features/auth/useLogout.ts`
- Test: `apps/web-pwa/test/use-logout.test.ts`

**Interfaces:**
- Consumes: `api` from `@splashh/api-client`; `useAuthStore` from `@splashh/api-client`; `useNavigate` from `react-router-dom`; `useMutation` from `@tanstack/react-query`.
- Produces: `useLogout()` returning a `UseMutationResult` whose `mutate()` posts to `/v1/auth/logout`, then on settle calls `useAuthStore.getState().clear()` and `navigate("/", { replace: true })`.

- [ ] **Step 1: Write the failing test**

Create `apps/web-pwa/test/use-logout.test.ts`:

```ts
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: vi.fn() };
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api, useAuthStore } from "@splashh/api-client";
import { useNavigate } from "react-router-dom";
import { useLogout } from "@/features/auth/useLogout";

const setup = () => {
  const qc = new QueryClient();
  const navigate = vi.fn();
  (useNavigate as ReturnType<typeof vi.fn>).mockReturnValue(navigate);
  useAuthStore.setState({
    accessToken: "t",
    userId: "u1",
    tenantId: "ten1",
    roles: ["customer"],
    isAuthenticated: true,
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return { navigate, wrapper };
};

describe("useLogout", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({
      accessToken: null, userId: null, tenantId: null, roles: [], isAuthenticated: false,
    });
  });

  it("calls POST /auth/logout on mutate", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: {} });
    const { wrapper } = setup();
    useAuthStore.setState({ accessToken: "t", isAuthenticated: true });
    const { result } = renderHook(() => useLogout(), { wrapper });
    await act(async () => { result.current.mutate(); });
    expect(api.post).toHaveBeenCalledWith("/auth/logout");
  });

  it("clears the auth store and navigates to / on success", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: {} });
    const { navigate, wrapper } = setup();
    useAuthStore.setState({ accessToken: "t", isAuthenticated: true });
    const { result } = renderHook(() => useLogout(), { wrapper });
    await act(async () => { result.current.mutate(); });
    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(navigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("still clears and navigates on API error (graceful degradation)", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("network down"));
    const { navigate, wrapper } = setup();
    useAuthStore.setState({ accessToken: "t", isAuthenticated: true });
    const { result } = renderHook(() => useLogout(), { wrapper });
    await act(async () => { result.current.mutate(); });
    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(navigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web-pwa && pnpm test -- use-logout`
Expected: FAIL — `useLogout` does not exist (module not found).

- [ ] **Step 3: Write the implementation**

Create `apps/web-pwa/src/features/auth/useLogout.ts`:

```ts
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, useAuthStore } from "@splashh/api-client";

export function useLogout() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: async () => {
      try {
        await api.post("/auth/logout");
      } catch {
        // swallow: local logout still proceeds
      }
    },
    onSettled: () => {
      useAuthStore.getState().clear();
      navigate("/", { replace: true });
    },
  });
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/web-pwa && pnpm test -- use-logout`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web-pwa/src/features/auth/useLogout.ts apps/web-pwa/test/use-logout.test.ts
git commit -m "feat(web-pwa): add useLogout hook with graceful API-failure handling"
```

---

## Task 2: `UserMenu` component

**Files:**
- Create: `apps/web-pwa/src/components/UserMenu.tsx`
- Test: `apps/web-pwa/test/user-menu.test.tsx`

**Interfaces:**
- Consumes: `useAuthStore` (userId for initials), `useLogout` from `@/features/auth/useLogout`. Local hooks: `useClickOutside`, `useEscapeKey` (defined in the same file).
- Produces: `<UserMenu />` — a self-contained avatar button + popover. Clicking the avatar opens a menu with a single "Log out" item that triggers `useLogout().mutate()`. Closes on click-outside, Esc, or after the logout click.

- [ ] **Step 1: Write the failing test**

Create `apps/web-pwa/test/user-menu.test.tsx`:

```ts
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useAuthStore } from "@splashh/api-client";
import { UserMenu } from "@/components/UserMenu";

const setup = () => {
  const qc = new QueryClient();
  useAuthStore.setState({ userId: "alex-123", accessToken: "t", isAuthenticated: true });
  return {
    qc,
    rerender: () => undefined as void,
  };
};

const renderMenu = () => {
  setup();
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <UserMenu />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("UserMenu", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({
      accessToken: null, userId: null, tenantId: null, roles: [], isAuthenticated: false,
    });
  });

  it("renders an avatar button with the user's first initial", () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    expect(screen.getByRole("button", { name: /open account menu/i })).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("falls back to ? when no userId is set", () => {
    renderMenu();
    expect(screen.getByText("?")).toBeInTheDocument();
  });

  it("does not show the menu items until the avatar is clicked", () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: /log out/i })).not.toBeInTheDocument();
  });

  it("opens the menu and shows Log out after clicking the avatar", async () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    await userEvent.click(screen.getByRole("button", { name: /open account menu/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /log out/i })).toBeInTheDocument();
  });

  it("closes the menu when the avatar is clicked a second time", async () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    const trigger = screen.getByRole("button", { name: /open account menu/i });
    await userEvent.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    await userEvent.click(trigger);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes the menu on Escape", async () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    await userEvent.click(screen.getByRole("button", { name: /open account menu/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web-pwa && pnpm test -- user-menu`
Expected: FAIL — `UserMenu` does not exist.

- [ ] **Step 3: Write the implementation**

Create `apps/web-pwa/src/components/UserMenu.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@splashh/api-client";
import { useLogout } from "@/features/auth/useLogout";

function useClickOutside(ref: React.RefObject<HTMLElement>, onClose: () => void) {
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [ref, onClose]);
}

function useEscapeKey(onClose: () => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);
}

export function UserMenu() {
  const userId = useAuthStore((s) => s.userId);
  const initials = (userId ?? "?").slice(0, 1).toUpperCase();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));
  useEscapeKey(() => setOpen(false));
  const logout = useLogout();

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Open account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 p-2 rounded hover:bg-slate-100"
      >
        <span
          aria-hidden
          className="w-7 h-7 rounded-full bg-gradient-to-br from-sky-500 to-cyan-500 text-white text-xs font-semibold flex items-center justify-center"
        >
          {initials}
        </span>
        <span className="text-sm text-slate-700">Account</span>
      </button>
      {open && (
        <div
          role="menu"
          className="absolute bottom-full left-0 mb-1 w-44 bg-white rounded-lg shadow-xl border border-slate-200 py-1"
        >
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false);
              logout.mutate();
            }}
            className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50"
          >
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/web-pwa && pnpm test -- user-menu`
Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web-pwa/src/components/UserMenu.tsx apps/web-pwa/test/user-menu.test.tsx
git commit -m "feat(web-pwa): add UserMenu component with avatar + logout popover"
```

---

## Task 3: `Sidebar` component

**Files:**
- Create: `apps/web-pwa/src/components/Sidebar.tsx`
- Test: `apps/web-pwa/test/sidebar.test.tsx`

**Interfaces:**
- Consumes: `NavItem` (defined inline in the file: `{ to: string; label: string; icon: string }`); `UserMenu` from `@/components/UserMenu`; `NavLink` from `react-router-dom`; `cn` from `@splashh/ui`.
- Produces: `<Sidebar items mobileOpen onClose>` — fixed left rail. Renders the Splashh wordmark, a `<nav>` of `NavLink`s for the given items, and a footer containing `<UserMenu />`. Slides in on mobile when `mobileOpen` is true; always visible on `md+` viewports.

- [ ] **Step 1: Write the failing test**

Create `apps/web-pwa/test/sidebar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/components/UserMenu", () => ({ UserMenu: () => <div data-testid="user-menu" /> }));

import { Sidebar } from "@/components/Sidebar";

const items = [
  { to: "/book", label: "Browse", icon: "🏊" },
  { to: "/book/bookings", label: "My bookings", icon: "📅" },
];

const renderSidebar = (path: string = "/book") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Sidebar items={items} mobileOpen={false} onClose={vi.fn()} />
    </MemoryRouter>,
  );

describe("Sidebar", () => {
  it("renders the Splashh wordmark", () => {
    renderSidebar();
    expect(screen.getByText("Splashh")).toBeInTheDocument();
  });

  it("renders a nav element with aria-label='Primary'", () => {
    renderSidebar();
    expect(screen.getByRole("navigation", { name: /primary/i })).toBeInTheDocument();
  });

  it("renders a NavLink for each item with the label and icon", () => {
    renderSidebar();
    expect(screen.getByRole("link", { name: /🏊.*Browse/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /📅.*My bookings/ })).toBeInTheDocument();
  });

  it("marks the current route's link as active (sky-50 background)", () => {
    renderSidebar("/book");
    const browse = screen.getByRole("link", { name: /🏊.*Browse/ });
    expect(browse.className).toMatch(/bg-sky-50/);
  });

  it("renders the UserMenu in the footer", () => {
    renderSidebar();
    expect(screen.getByTestId("user-menu")).toBeInTheDocument();
  });

  it("calls onClose when a nav item is clicked", async () => {
    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar items={items} mobileOpen={true} onClose={onClose} />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("link", { name: /Browse/ }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web-pwa && pnpm test -- sidebar`
Expected: FAIL — `Sidebar` does not exist.

- [ ] **Step 3: Write the implementation**

Create `apps/web-pwa/src/components/Sidebar.tsx`:

```tsx
import { cn } from "@splashh/ui";
import { NavLink } from "react-router-dom";
import { UserMenu } from "./UserMenu";

export interface NavItem {
  to: string;
  label: string;
  icon: string;
}

export function Sidebar({
  items,
  mobileOpen,
  onClose,
}: {
  items: NavItem[];
  mobileOpen: boolean;
  onClose: () => void;
}) {
  return (
    <aside
      aria-label="Primary"
      id="primary-nav"
      className={cn(
        "fixed md:static inset-y-0 left-0 z-40 w-60 bg-white border-r border-slate-200 shadow-sm",
        "transform transition-transform duration-200 ease-out md:transform-none",
        mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
      )}
    >
      <div className="px-4 py-4 font-bold text-sky-900">Splashh</div>
      <nav aria-label="Primary">
        <ul role="list" className="px-2 space-y-1">
          {items.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                onClick={onClose}
                end={item.to === "/admin" || item.to === "/book"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg text-sm",
                    isActive
                      ? "bg-sky-50 text-sky-700 border-l-2 border-sky-500"
                      : "text-slate-700 hover:bg-slate-50",
                  )
                }
              >
                <span aria-hidden>{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="absolute bottom-0 left-0 right-0 p-2 border-t border-slate-200">
        <UserMenu />
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/web-pwa && pnpm test -- sidebar`
Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web-pwa/src/components/Sidebar.tsx apps/web-pwa/test/sidebar.test.tsx
git commit -m "feat(web-pwa): add Sidebar with role-aware nav and mobile drawer"
```

---

## Task 4: `TopBar` component

**Files:**
- Create: `apps/web-pwa/src/components/TopBar.tsx`
- Test: `apps/web-pwa/test/topbar.test.tsx`

**Interfaces:**
- Consumes: `useLocation` from `react-router-dom`; `titleForPath` from `@/lib/page-titles`.
- Produces: `<TopBar mobileOpen onToggleSidebar>` — sticky top bar. Shows a hamburger button on viewports `< md`, hidden on `md+`. Always shows the current page title (from `titleForPath`).

- [ ] **Step 1: Write the failing test**

Create `apps/web-pwa/test/topbar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/lib/page-titles", () => ({
  titleForPath: (p: string) => (p.startsWith("/admin") ? "Admin" : "Browse"),
}));

import { TopBar } from "@/components/TopBar";

const renderBar = (pathname: string, mobileOpen = false) => {
  const onToggle = vi.fn();
  const result = render(
    <MemoryRouter initialEntries={[pathname]}>
      <TopBar mobileOpen={mobileOpen} onToggleSidebar={onToggle} />
    </MemoryRouter>,
  );
  return { onToggle, ...result };
};

describe("TopBar", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it("renders the page title from the current route", () => {
    renderBar("/book");
    expect(screen.getByRole("heading", { level: 1, name: "Browse" })).toBeInTheDocument();
  });

  it("renders the hamburger button with aria-label", () => {
    renderBar("/book");
    expect(screen.getByRole("button", { name: /toggle navigation/i })).toBeInTheDocument();
  });

  it("calls onToggleSidebar when the hamburger is clicked", async () => {
    const { onToggle } = renderBar("/book");
    await userEvent.click(screen.getByRole("button", { name: /toggle navigation/i }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("reflects the mobileOpen prop in aria-expanded", () => {
    renderBar("/book", true);
    expect(screen.getByRole("button", { name: /toggle navigation/i })).toHaveAttribute("aria-expanded", "true");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web-pwa && pnpm test -- topbar`
Expected: FAIL — `TopBar` does not exist.

- [ ] **Step 3: Write the implementation**

Create `apps/web-pwa/src/components/TopBar.tsx`:

```tsx
import { useLocation } from "react-router-dom";
import { titleForPath } from "@/lib/page-titles";

export function TopBar({
  mobileOpen,
  onToggleSidebar,
}: {
  mobileOpen: boolean;
  onToggleSidebar: () => void;
}) {
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
      >
        ☰
      </button>
      <h1 className="text-base font-semibold text-slate-900 truncate">{title}</h1>
      <div className="ml-auto" />
    </header>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/web-pwa && pnpm test -- topbar`
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web-pwa/src/components/TopBar.tsx apps/web-pwa/test/topbar.test.tsx
git commit -m "feat(web-pwa): add TopBar with page title and mobile hamburger"
```

---

## Task 5: `AppShell` + nav config

**Files:**
- Create: `apps/web-pwa/src/components/AppShell.tsx`
- Create: `apps/web-pwa/src/components/nav.ts`
- Test: `apps/web-pwa/test/app-shell.test.tsx`

**Interfaces:**
- Consumes: `useAuthStore` (for `roles`); `Sidebar` and `TopBar` from sibling files; `NAV_BY_ROLE` and `navForRoles` from `@/components/nav`.
- Produces: `<AppShell>{children}</AppShell>` — full-bleed layout. Owns the `mobileOpen` state and passes it + the toggle callback to `TopBar` and `Sidebar`. Renders a skip link, a backdrop on mobile when open, and a `<main id="main">` for the page content.

- [ ] **Step 1: Write the failing test**

Create `apps/web-pwa/test/app-shell.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

vi.mock("@/components/Sidebar", () => ({
  Sidebar: ({ items, mobileOpen, onClose }: any) => (
    <div data-testid="sidebar" data-mobile-open={mobileOpen ? "true" : "false"}>
      {items.map((it: any) => (
        <a key={it.to} href={it.to} onClick={onClose}>{it.label}</a>
      ))}
    </div>
  ),
}));

vi.mock("@/components/TopBar", () => ({
  TopBar: ({ mobileOpen, onToggleSidebar }: any) => (
    <div>
      <button data-testid="hamburger" aria-expanded={mobileOpen} onClick={onToggleSidebar}>☰</button>
    </div>
  ),
}));

vi.mock("@/components/UserMenu", () => ({ UserMenu: () => <div data-testid="user-menu" /> }));

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useAuthStore } from "@splashh/api-client";
import { AppShell } from "@/components/AppShell";
import { NAV_BY_ROLE, navForRoles } from "@/components/nav";

const renderShell = (path: string, roles: string[]) => {
  useAuthStore.setState({ roles, isAuthenticated: true });
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <AppShell>
          <div data-testid="content">Page content</div>
        </AppShell>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("navForRoles", () => {
  it("returns customer nav for the customer role", () => {
    expect(navForRoles(["customer"])).toEqual(NAV_BY_ROLE.customer);
  });
  it("returns admin nav for the tenant_admin role", () => {
    expect(navForRoles(["tenant_admin"])).toEqual(NAV_BY_ROLE.tenant_admin);
  });
  it("returns an empty array for an unknown role", () => {
    expect(navForRoles(["unknown"])).toEqual([]);
  });
});

describe("AppShell", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null, userId: null, tenantId: null, roles: [], isAuthenticated: false,
    });
  });

  it("renders the Sidebar and TopBar with the children content", () => {
    renderShell("/book", ["customer"]);
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("hamburger")).toBeInTheDocument();
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });

  it("shows customer nav items when the user is a customer", () => {
    renderShell("/book", ["customer"]);
    expect(screen.getByRole("link", { name: "Browse" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "My bookings" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });

  it("shows admin nav items when the user is a tenant_admin", () => {
    renderShell("/admin", ["tenant_admin"]);
    expect(screen.getByRole("link", { name: "Facilities" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Users" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Browse" })).not.toBeInTheDocument();
  });

  it("renders a Skip to main content link as the first focusable element", () => {
    renderShell("/book", ["customer"]);
    const skip = screen.getByRole("link", { name: /skip to main content/i });
    expect(skip).toHaveAttribute("href", "#main");
  });

  it("opens the mobile sidebar when the hamburger is clicked", async () => {
    renderShell("/book", ["customer"]);
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toHaveAttribute("data-mobile-open", "false");
    await userEvent.click(screen.getByTestId("hamburger"));
    expect(sidebar).toHaveAttribute("data-mobile-open", "true");
  });

  it("renders a <main id='main'> landmark for the children", () => {
    renderShell("/book", ["customer"]);
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main");
    expect(main).toContainElement(screen.getByTestId("content"));
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web-pwa && pnpm test -- app-shell`
Expected: FAIL — `AppShell` and `nav` modules do not exist.

- [ ] **Step 3: Write the implementations**

Create `apps/web-pwa/src/components/nav.ts`:

```ts
import type { NavItem } from "./Sidebar";

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

Create `apps/web-pwa/src/components/AppShell.tsx`:

```tsx
import { useMemo, useState } from "react";
import { useAuthStore } from "@splashh/api-client";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { navForRoles } from "./nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const roles = useAuthStore((s) => s.roles);
  const items = useMemo(() => navForRoles(roles), [roles]);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-50">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-white focus:px-3 focus:py-2 focus:rounded focus:shadow"
      >
        Skip to main content
      </a>
      <Sidebar items={items} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar
          mobileOpen={mobileOpen}
          onToggleSidebar={() => setMobileOpen((v) => !v)}
        />
        <main id="main" className="flex-1 p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd apps/web-pwa && pnpm test -- app-shell`
Expected: 9 tests pass (3 navForRoles + 6 AppShell).

- [ ] **Step 5: Commit**

```bash
git add apps/web-pwa/src/components/AppShell.tsx apps/web-pwa/src/components/nav.ts apps/web-pwa/test/app-shell.test.tsx
git commit -m "feat(web-pwa): add AppShell with role-aware nav and mobile drawer state"
```

---

## Task 6: `LoginPage` redesign with tabs, `AdminLoginPage` redirect, and route wiring

**Files:**
- Modify: `apps/web-pwa/src/pages/LoginPage.tsx`
- Modify: `apps/web-pwa/src/pages/AdminLoginPage.tsx`
- Modify: `apps/web-pwa/src/routes/index.tsx`
- Test: `apps/web-pwa/test/login-page.test.tsx`

**Interfaces:**
- Consumes: `LoginForm` from `@/features/auth/LoginForm` (existing — already supports `mode` and `headingLevel` props); `useAuthStore` from `@splashh/api-client`; `useSearchParams` and `useNavigate` from `react-router-dom`; `homeForRoles` from `@/lib/role-routing`; `Card`, `CardHeader`, `CardContent` from `@splashh/ui`; `AppShell` from `@/components/AppShell`.
- Produces: `/login` (Customer/Staff tabbed login); `/admin/login` (redirects to `/login?role=staff`); all `<RoleGate>` children wrapped in `<AppShell>`.

- [ ] **Step 1: Delete the now-superseded test cases for the old LoginPage**

The existing `apps/web-pwa/test/login.test.tsx` contains a `describe("LoginPage", …)` block (lines 53–86 in the current file) that asserts the old behavior (single `h1` heading "Log in"). Read the file, then remove that `describe` block only — keep the `LoginForm` cases untouched.

Run: `cd apps/web-pwa && pnpm test -- login` to confirm the existing LoginForm tests still pass after the deletion. Expected: 3 tests pass (was 5; we removed 2 cases).

- [ ] **Step 2: Write the new failing tests**

Create `apps/web-pwa/test/login-page.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: vi.fn() };
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api, useAuthStore } from "@splashh/api-client";
import { useNavigate } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { AdminLoginPage } from "@/pages/AdminLoginPage";

const renderLogin = (initialPath: string = "/login") => {
  const navigate = vi.fn();
  (useNavigate as ReturnType<typeof vi.fn>).mockReturnValue(navigate);
  return {
    navigate,
    ...render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/login?role=staff" element={<LoginPage />} />
            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route path="/admin" element={<div>admin home</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({
      accessToken: null, userId: null, tenantId: null, roles: [], isAuthenticated: false,
    });
  });

  it("renders a Customer and Staff tab with Customer selected by default", () => {
    renderLogin("/login");
    const customer = screen.getByRole("tab", { name: "Customer" });
    const staff = screen.getByRole("tab", { name: "Staff" });
    expect(customer).toHaveAttribute("aria-selected", "true");
    expect(staff).toHaveAttribute("aria-selected", "false");
  });

  it("pre-selects the Staff tab when ?role=staff is in the URL", () => {
    renderLogin("/login?role=staff");
    expect(screen.getByRole("tab", { name: "Customer" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tab", { name: "Staff" })).toHaveAttribute("aria-selected", "true");
  });

  it("switches the active tab on click", async () => {
    renderLogin("/login");
    await userEvent.click(screen.getByRole("tab", { name: "Staff" }));
    expect(screen.getByRole("tab", { name: "Staff" })).toHaveAttribute("aria-selected", "true");
  });

  it("shows the Splashh wordmark and tagline above the card", () => {
    renderLogin();
    expect(screen.getByText("Splashh")).toBeInTheDocument();
    expect(screen.getByText(/book your club in seconds/i)).toBeInTheDocument();
  });

  it("submits the Customer tab with mode='customer' on success", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { access_token: "t", user_id: "u1", tenant_id: "ten1" },
    });
    renderLogin("/login");
    await userEvent.type(screen.getByLabelText(/email/i), "alex@demo.splashh.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "Customer!Demo1");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(api.post).toHaveBeenCalledWith(
      "/auth/login",
      expect.objectContaining({ mode: "customer" }),
    );
  });

  it("submits the Staff tab with mode='staff'", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { access_token: "t", user_id: "u1", tenant_id: "ten1" },
    });
    renderLogin("/login?role=staff");
    await userEvent.type(screen.getByLabelText(/email/i), "admin@demo.splashh.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "Admin!Demo2026");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(api.post).toHaveBeenCalledWith(
      "/auth/login",
      expect.objectContaining({ mode: "staff" }),
    );
  });
});

describe("AdminLoginPage", () => {
  it("renders a Navigate that sends the user to /login?role=staff", () => {
    renderLogin("/admin/login");
    expect(screen.getByText(/log in/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Staff" })).toHaveAttribute("aria-selected", "true");
  });
});
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `cd apps/web-pwa && pnpm test -- login-page`
Expected: FAIL — `LoginPage` still renders the old single-heading layout, and `AdminLoginPage` is not a `<Navigate>`.

- [ ] **Step 4: Replace `LoginPage.tsx`**

Edit `apps/web-pwa/src/pages/LoginPage.tsx` — replace the entire file with:

```tsx
import { useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader } from "@splashh/ui";
import { LoginForm } from "@/features/auth/LoginForm";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "@/lib/role-routing";

type Mode = "customer" | "staff";

function Tab({
  id,
  selected,
  onSelect,
  children,
}: {
  id: string;
  selected: boolean;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      id={`tab-${id}`}
      aria-selected={selected}
      aria-controls="login-panel"
      onClick={onSelect}
      className={
        "flex-1 px-3 py-2 text-sm font-medium border-b-2 -mb-px " +
        (selected
          ? "border-sky-500 text-sky-700 bg-sky-50"
          : "border-transparent text-slate-500 hover:text-slate-700")
      }
    >
      {children}
    </button>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);
  const initialMode: Mode = search.get("role") === "staff" ? "staff" : "customer";
  const [mode, setMode] = useState<Mode>(initialMode);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  useEffect(() => {
    emailRef.current?.focus();
  }, [mode]);

  return (
    <main
      className="min-h-screen flex flex-col items-center justify-center p-4"
      style={{ background: "linear-gradient(180deg, rgb(224 242 254) 0%, white 60%)" }}
    >
      <div className="mb-6 text-center">
        <div className="text-3xl font-bold text-sky-900">Splashh</div>
        <div className="text-sm text-slate-500">Book your club in seconds</div>
      </div>
      <Card className="w-full max-w-sm rounded-2xl shadow-md">
        <CardHeader className="p-0">
          <div role="tablist" aria-label="Login type" className="flex border-b border-slate-200">
            <Tab id="customer" selected={mode === "customer"} onSelect={() => setMode("customer")}>
              Customer
            </Tab>
            <Tab id="staff" selected={mode === "staff"} onSelect={() => setMode("staff")}>
              Staff
            </Tab>
          </div>
        </CardHeader>
        <CardContent>
          <div id="login-panel" role="tabpanel" aria-labelledby={`tab-${mode}`}>
            <LoginForm
              mode={mode}
              headingLevel="h2"
              emailRef={emailRef}
              onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
            />
          </div>
        </CardContent>
      </Card>
      <p className="mt-6 text-xs text-slate-500">Need help? Contact your club.</p>
    </main>
  );
}
```

- [ ] **Step 5: Replace `AdminLoginPage.tsx`**

Edit `apps/web-pwa/src/pages/AdminLoginPage.tsx` — replace the entire file with:

```tsx
import { Navigate } from "react-router-dom";

export function AdminLoginPage() {
  return <Navigate to="/login?role=staff" replace />;
}
```

- [ ] **Step 6: Wire `AppShell` into the protected routes**

Edit `apps/web-pwa/src/routes/index.tsx`. In the import block, add `import { AppShell } from "@/components/AppShell";`. Then wrap the two `<RoleGate>` children blocks so each is rendered inside `<AppShell>`. The final `<Routes>` body should look like:

```tsx
<Route element={<ProtectedRoute />}>
  <Route path="/redirect" element={<RoleBasedRedirect />} />
  <Route element={<RoleGate roles={["customer"]} />}>
    <Route path="/book" element={<AppShell><FacilitiesPage /></AppShell>} />
    <Route path="/book/facilities/:id" element={<AppShell><FacilityDetailPage /></AppShell>} />
    <Route path="/book/bookings" element={<AppShell><BookingsPage /></AppShell>} />
  </Route>
  <Route element={<RoleGate roles={["tenant_admin"]} />}>
    <Route path="/admin/users" element={<AppShell><AdminUsersPage /></AppShell>} />
    <Route path="/admin/facilities/new" element={<AppShell><AdminFacilityNewPage /></AppShell>} />
    <Route path="/admin/facilities/:id" element={<AppShell><AdminFacilityDetailPage /></AppShell>} />
    <Route path="/admin" element={<AppShell><AdminFacilitiesPage /></AppShell>} />
  </Route>
</Route>
```

Do not change `<LoginPage />` or `<AdminLoginPage />` — they must remain outside the shell.

- [ ] **Step 7: Run the new tests to verify they pass**

Run: `cd apps/web-pwa && pnpm test -- login-page`
Expected: 8 tests pass (7 LoginPage + 1 AdminLoginPage).

- [ ] **Step 8: Run the full web-pwa suite to confirm no regressions**

Run: `cd apps/web-pwa && pnpm test`
Expected: all suites green — `app-shell`, `booking`, `facilities-page`, `facility-detail-page`, `login`, `login-page`, `role-based-redirect`, `role-gate`, `role-routing`, `sidebar`, `topbar`, `user-menu`, `use-logout`, `users`, `page-titles`. About 50+ tests total.

If any pre-existing test fails (most likely the `bookings-page.test.tsx` or `facilities-page.test.tsx` because they render their pages directly without a router context, and now those pages expect to be wrapped in `<AppShell>`), wrap them in a `<MemoryRouter>` in the test or in a thin test helper. Do not change the page component to compensate.

- [ ] **Step 9: Run the typecheck**

Run: `cd apps/web-pwa && pnpm typecheck`
Expected: passes (no type errors).

- [ ] **Step 10: Commit**

```bash
git add apps/web-pwa/src/pages/LoginPage.tsx apps/web-pwa/src/pages/AdminLoginPage.tsx apps/web-pwa/src/routes/index.tsx apps/web-pwa/test/login.test.tsx apps/web-pwa/test/login-page.test.tsx
git commit -m "feat(web-pwa): redesign login page with tabs, redirect admin login, wire AppShell into protected routes"
```

---

## Self-Review

**1. Spec coverage:**
- Login centered card on soft gradient → Task 6 ✓
- Customer/Staff tab toggle → Task 6 ✓
- `?role=staff` deep-link → Task 6 ✓
- `AdminLoginPage` redirect → Task 6 ✓
- Sidebar (logo, nav, user menu footer) → Task 3 ✓
- TopBar (page title, hamburger) → Task 4 ✓
- AppShell (wraps both, owns mobileOpen, skip link) → Task 5 ✓
- Role-aware nav config → Task 5 (`nav.ts`) ✓
- Logout via popover → Task 2 ✓
- `useLogout` graceful degradation → Task 1 ✓
- All 4 demo accounts still work — covered by the e2e tests (untouched) and verified by the new unit tests for `mode: "customer"` and `mode: "staff"` in Task 6
- Skip link, ARIA tabs, `aria-expanded` on hamburger — wired in Tasks 2, 5, 6 ✓
- `noindex` for admin pages — unchanged, out of scope ✓
- `useNoIndex` still works on `/admin/*` (the route entry points are unchanged) ✓
- No new dependencies, no new `@splashh/ui` primitives ✓

**2. Placeholder scan:** No "TBD", "TODO", "implement later" in any task. Every code block is complete.

**3. Type consistency:**
- `NavItem` is defined in `Sidebar.tsx` and re-exported/imported in `nav.ts` — consistent.
- `Sidebar` props: `{ items: NavItem[]; mobileOpen: boolean; onClose: () => void }` — used identically in `AppShell.tsx` and all tests.
- `TopBar` props: `{ mobileOpen: boolean; onToggleSidebar: () => void }` — used identically in `AppShell.tsx` and all tests.
- `useLogout` returns the React Query mutation result; tests import and call `result.current.mutate()`.
- `useAuthStore` shape (`accessToken`, `userId`, `tenantId`, `roles`, `isAuthenticated`, `setSession`, `setAccessToken`, `clear`) is used consistently in every test.
- `LoginForm` props (`mode`, `headingLevel`, `emailRef`, `onSuccess`) match the existing component.
- `homeForRoles` and `titleForPath` are imported from the existing `@/lib/role-routing` and `@/lib/page-titles` respectively.

No type inconsistencies found.
