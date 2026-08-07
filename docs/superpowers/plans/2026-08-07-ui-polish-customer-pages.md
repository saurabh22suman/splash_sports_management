# Customer-Facing UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the four customer-facing pages of the Splashh PWA so each
passes axe-core with 0 violations, has real loading/empty/error states,
works comfortably on a phone, and has light + dark mode parity.

**Architecture:** Page-by-page pass that introduces three shared state
components (`EmptyState`, `LoadingSkeleton`, `ErrorState`) in
`packages/ui/`. Task 2 introduces the three components and uses them on
`/book/bookings`. Tasks 3 and 4 consume those components. Task 1 is form
polish on `/login` and does not depend on the shared components.

**Tech Stack:** React 18, TypeScript, Tailwind CSS 3, shadcn/ui-style
primitives in `packages/ui/`, Vitest + Testing Library, Playwright + axe-core.

**Parallelization:** Tasks 1 and 2 are independent (different files) and
can run in parallel. Tasks 3 and 4 are independent of each other but both
depend on Task 2's shared components — execute them in parallel after
Task 2 lands.

## Global Constraints

These apply to every task. Exact values below are copied from the spec.

- **4 customer-facing pages in scope:** `/login`, `/book`,
  `/book/facilities/:id`, `/book/bookings`.
- **No new dependencies** added to any `package.json`.
- **No new tokens** in `packages/ui/src/tokens.ts` — the existing HSL CSS
  vars (`--background`, `--primary`, `--ring`, etc.) cover what's needed.
- **Reuse existing primitives:** `Card`, `CardContent`, `CardHeader`,
  `CardTitle`, `CardFooter`, `Button`, `Input`, `Label`, `FormField` from
  `@splashh/ui`. Promotion of new state components to `packages/ui/` from
  day one.
- **A11y:** proper `<main>` landmark, h1 → h2 → h3 hierarchy,
  `aria-label` on icon-only buttons, `role="alert"` on errors, axe-core
  clean (0 violations) in light + dark.
- **Mobile:** Single-column ≤640px, touch targets ≥44px, inputs ≥16px
  font (iOS-safe — prevents zoom on focus), no horizontal scroll.
- **Form validation:** inline error under each input via `FormField`'s
  existing `error` prop (already wired to `role="alert"`); submit error
  shown with `role="alert"` and `aria-live="assertive"`.
- **Visual:** consistent spacing on Tailwind scale, visible focus rings
  (already on Button via `focus-visible:ring-2`), hover states, dark-mode
  parity, subtle fade transition (`transition-opacity`) for state changes.
- **iOS safe-area:** keep page padding at `p-4` (existing) + `pb-[env(safe-area-inset-bottom)]` for the bottom padding when there's a sticky action.
- **Tests:** axe-core 0 violations via `@axe-core/playwright` in light + dark, unit tests for each polished page, existing tests must still pass.
- **Existing tests must stay green:** `pnpm --filter web-pwa test` (currently 24 passing) and `pnpm test:e2e`.

## Component Contracts (used by Tasks 2, 3, 4)

```typescript
// packages/ui/src/components/EmptyState.tsx
export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void } | { label: string; to: string };
}
export function EmptyState(props: EmptyStateProps): JSX.Element;

// packages/ui/src/components/LoadingSkeleton.tsx
export interface LoadingSkeletonProps {
  lines?: number;       // default 3
  withCard?: boolean;    // default false
}
export function LoadingSkeleton(props: LoadingSkeletonProps): JSX.Element;

// packages/ui/src/components/ErrorState.tsx
export interface ErrorStateProps {
  title?: string;       // default "Something went wrong"
  description?: string;
  onRetry?: () => void;
}
export function ErrorState(props: ErrorStateProps): JSX.Element;
```

All three accept and forward `className` and `data-testid` for the
overriding tests.

---

## Task 1: Polish `/login`

**Files:**
- Modify: `apps/web-pwa/src/pages/LoginPage.tsx`
- Modify: `apps/web-pwa/src/features/auth/LoginForm.tsx`
- Test: `apps/web-pwa/test/login.test.tsx`
- New: `e2e/login-polish.spec.ts`

**Goal:** Add a proper page shell, prevent iOS auto-zoom on the inputs,
add `aria-live` to the submit error, auto-focus the email field on mount,
and verify axe-core 0 violations.

**Interfaces (consumed):**
- `LoginForm` from `@/features/auth/LoginForm` (already exists)
- `Card`, `CardContent`, `CardHeader`, `CardTitle`, `Button`, `FormField`, `Input` from `@splashh/ui`

**Interfaces (produced for later tasks):**
- None — Task 1 is self-contained.

- [ ] **Step 1: Write failing tests for the polished login page**

Append to `apps/web-pwa/test/login.test.tsx`:

```tsx
import { LoginPage } from "@/pages/LoginPage";

// ... existing imports

describe("LoginPage", () => {
  it("renders a <main> landmark with an h1 visible to assistive tech", () => {
    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <LoginPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: /log in/i })).toBeInTheDocument();
  });

  it("puts the error message in an aria-live=assertive region", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("Invalid credentials"));
    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <LoginPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/email/i), "u@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "wrongpwd");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveTextContent(/invalid credentials/i);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/web-pwa && pnpm test test/login.test.tsx`
Expected: 2 failures — "unable to find role=main", "no h1 with level=1",
"element does not have aria-live=assertive".

- [ ] **Step 3: Add an h1 and aria-live to LoginForm**

In `apps/web-pwa/src/features/auth/LoginForm.tsx`, change the `<CardTitle>` to
include an `<h1>` semantics via the existing `CardTitle` (which renders
`<h3>` by default). Replace the title with a heading semantic that gives
`<h1>` level on the login page when used in `LoginPage`.

Add a `headingLevel` prop (default 3) to `CardTitle` in
`packages/ui/src/components/ui/card.tsx` that maps to the underlying
heading element:

```tsx
export const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement> & { as?: "h1" | "h2" | "h3" }
>(({ className, as: Comp = "h3", ...props }, ref) => (
  <Comp ref={ref} className={cn("text-2xl font-semibold leading-none tracking-tight", className)} {...props} />
));
```

In `LoginForm`, change the inline error `<p>` to:

```tsx
{login.error && (
  <p role="alert" aria-live="assertive" className="text-sm text-destructive">
    {(login.error as Error).message || "Login failed"}
  </p>
)}
```

Also add `text-base` (16px) to both `<Input>`s to prevent iOS zoom:

```tsx
<Input id="email" type="email" autoComplete="email" className="text-base" ... />
<Input id="password" type="password" autoComplete="current-password" className="text-base" ... />
```

- [ ] **Step 4: Polish LoginPage**

Replace `apps/web-pwa/src/pages/LoginPage.tsx` with:

```tsx
import { useNavigate } from "react-router-dom";
import { useEffect, useRef } from "react";
import { LoginForm } from "@/features/auth/LoginForm";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "@/lib/role-routing";

export function LoginPage() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  useEffect(() => {
    emailRef.current?.focus();
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center p-4 pb-[env(safe-area-inset-bottom)]">
      <LoginForm
        mode="customer"
        emailRef={emailRef}
        onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
      />
    </main>
  );
}
```

Add an `emailRef` prop to `LoginForm`:

```tsx
export function LoginForm({
  onSuccess,
  mode = "customer",
  emailRef,
}: {
  onSuccess: (roles: string[]) => void;
  mode?: "customer" | "staff";
  emailRef?: React.Ref<HTMLInputElement>;
}) {
  // ...
  <Input
    id="email"
    type="email"
    autoComplete="email"
    ref={emailRef}
    className="text-base"
    aria-invalid={errors.email ? "true" : "false"}
    {...register("email")}
  />
  // ...
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd apps/web-pwa && pnpm test test/login.test.tsx`
Expected: 4 tests passing (2 existing + 2 new).

- [ ] **Step 6: Add an axe-core e2e test for /login**

Create `e2e/login-polish.spec.ts`:

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("/login passes axe-core (light)", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { level: 1, name: /log in/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/login passes axe-core (dark)", async ({ page, browser }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/login");
  await expect(page.getByRole("heading", { level: 1, name: /log in/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

- [ ] **Step 7: Run e2e test (manually) to verify axe passes**

Run: `pnpm test:e2e e2e/login-polish.spec.ts`
Expected: 2 tests, 0 violations.

- [ ] **Step 8: Commit**

```bash
git add apps/web-pwa/src/pages/LoginPage.tsx \
        apps/web-pwa/src/features/auth/LoginForm.tsx \
        packages/ui/src/components/ui/card.tsx \
        apps/web-pwa/test/login.test.tsx \
        e2e/login-polish.spec.ts
git commit -m "feat(web-pwa): polish /login — h1, aria-live, focus, iOS-safe"
```

---

## Task 2: Polish `/book/bookings` + introduce shared state components

**Files:**
- New: `packages/ui/src/components/EmptyState.tsx`
- New: `packages/ui/src/components/LoadingSkeleton.tsx`
- New: `packages/ui/src/components/ErrorState.tsx`
- Modify: `packages/ui/src/index.ts`
- Modify: `apps/web-pwa/src/pages/book/BookingsPage.tsx`
- New: `apps/web-pwa/test/bookings-page.test.tsx`
- New: `e2e/bookings-polish.spec.ts`

**Goal:** Introduce the three shared state components in `packages/ui/`,
hook them into the BookingsPage, and add the visual states + a11y. This
is the page Tasks 3 and 4 will reuse.

**Interfaces (consumed):**
- `useBookingsByCustomer(customerId)` from `@/features/bookings/useBookings`
- `Card`, `CardContent`, `CardHeader`, `CardTitle`, `Button` from `@splashh/ui`

**Interfaces (produced for later tasks):**
- `EmptyState`, `LoadingSkeleton`, `ErrorState` exported from `@splashh/ui`

- [ ] **Step 1: Write failing tests for the three shared components**

Create `packages/ui/src/components/EmptyState.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(<EmptyState title="Nothing here" description="Try again later" />);
    expect(screen.getByRole("heading", { name: /nothing here/i })).toBeInTheDocument();
    expect(screen.getByText(/try again later/i)).toBeInTheDocument();
  });

  it("renders an onClick action as a button", () => {
    const onClick = vi.fn();
    render(<EmptyState title="Empty" action={{ label: "Refresh", onClick }} />);
    screen.getByRole("button", { name: /refresh/i }).click();
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("renders a `to` action as a link", () => {
    render(<EmptyState title="Empty" action={{ label: "Browse", to: "/book" }} />);
    const link = screen.getByRole("link", { name: /browse/i });
    expect(link).toHaveAttribute("href", "/book");
  });
});
```

Create `packages/ui/src/components/LoadingSkeleton.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import "@testing-library/jest-dom/vitest";
import { LoadingSkeleton } from "./LoadingSkeleton";

describe("LoadingSkeleton", () => {
  it("renders a polite live region with screen-reader text", () => {
    render(<LoadingSkeleton />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveTextContent(/loading/i);
  });

  it("renders the requested number of lines", () => {
    const { container } = render(<LoadingSkeleton lines={5} />);
    expect(container.querySelectorAll("[data-skeleton-line]")).toHaveLength(5);
  });

  it("renders a card-shaped skeleton when withCard is true", () => {
    const { container } = render(<LoadingSkeleton withCard />);
    expect(container.querySelector("[data-skeleton-card]")).toBeInTheDocument();
  });
});
```

Create `packages/ui/src/components/ErrorState.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  it("renders an alert role with default title", () => {
    render(<ErrorState />);
    expect(screen.getByRole("alert")).toHaveTextContent(/something went wrong/i);
  });

  it("renders a retry button when onRetry is provided", () => {
    const onRetry = vi.fn();
    render(<ErrorState onRetry={onRetry} />);
    screen.getByRole("button", { name: /retry/i }).click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("uses a custom title and description when provided", () => {
    render(<ErrorState title="Could not load" description="Network error" />);
    expect(screen.getByRole("alert")).toHaveTextContent(/could not load/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/network error/i);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/ui && pnpm test 2>/dev/null || pnpm --filter @splashh/ui test`
Expected: 3 failures — "Cannot find module './EmptyState'", etc.

- [ ] **Step 3: Implement EmptyState**

Create `packages/ui/src/components/EmptyState.tsx`:

```tsx
import * as React from "react";
import { cn } from "../lib/cn.js";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?:
    | { label: string; onClick: () => void }
    | { label: string; to: string };
  className?: string;
  "data-testid"?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  ...rest
}: EmptyStateProps) {
  return (
    <div
      data-testid={rest["data-testid"]}
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-4 py-12 text-center",
        className,
      )}
    >
      {icon && <div className="text-muted-foreground">{icon}</div>}
      <h2 className="text-lg font-semibold">{title}</h2>
      {description && (
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {action && "to" in action ? (
        <a
          href={action.to}
          className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          {action.label}
        </a>
      ) : (
        action && (
          <button
            type="button"
            onClick={action.onClick}
            className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {action.label}
          </button>
        )
      )}
    </div>
  );
}
```

- [ ] **Step 4: Implement LoadingSkeleton**

Create `packages/ui/src/components/LoadingSkeleton.tsx`:

```tsx
import * as React from "react";
import { cn } from "../lib/cn.js";

export interface LoadingSkeletonProps {
  lines?: number;
  withCard?: boolean;
  className?: string;
  "data-testid"?: string;
}

export function LoadingSkeleton({
  lines = 3,
  withCard = false,
  className,
  ...rest
}: LoadingSkeletonProps) {
  const arr = Array.from({ length: lines });
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-testid={rest["data-testid"]}
      className={cn("w-full space-y-3", className)}
    >
      <span className="sr-only">Loading…</span>
      {withCard && (
        <div
          data-skeleton-card
          className="rounded-lg border bg-card p-6 shadow-sm"
        >
          <div className="h-4 w-1/3 animate-pulse rounded bg-muted" />
          <div className="mt-3 h-3 w-1/2 animate-pulse rounded bg-muted" />
        </div>
      )}
      {arr.map((_, i) => (
        <div
          key={i}
          data-skeleton-line
          className={cn(
            "h-3 animate-pulse rounded bg-muted",
            i === arr.length - 1 ? "w-2/3" : "w-full",
          )}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Implement ErrorState**

Create `packages/ui/src/components/ErrorState.tsx`:

```tsx
import * as React from "react";
import { cn } from "../lib/cn.js";

export interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
  "data-testid"?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
  className,
  ...rest
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      data-testid={rest["data-testid"]}
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-4 py-12 text-center",
        className,
      )}
    >
      <h2 className="text-lg font-semibold">{title}</h2>
      {description && (
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          Retry
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Re-export from packages/ui**

Modify `packages/ui/src/index.ts`:

```ts
export * from "./components/ui/button";
export * from "./components/ui/card";
export * from "./components/ui/input";
export * from "./components/ui/label";
export * from "./components/forms/form-field";
export * from "./components/EmptyState";
export * from "./components/LoadingSkeleton";
export * from "./components/ErrorState";
export * from "./lib/cn";
export { brand } from "./tokens";
```

- [ ] **Step 7: Run shared component tests to verify they pass**

Run: `cd packages/ui && pnpm test 2>/dev/null || pnpm --filter @splashh/ui test`
Expected: All EmptyState/LoadingSkeleton/ErrorState tests passing.

- [ ] **Step 8: Write failing test for BookingsPage states**

Create `apps/web-pwa/test/bookings-page.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>(
    "@splashh/api-client",
  );
  return { ...actual, useAuthStore: vi.fn(() => ({ userId: "u1" })) };
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useAuthStore } from "@splashh/api-client";
import { BookingsPage } from "@/pages/book/BookingsPage";

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <BookingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("BookingsPage", () => {
  it("renders a polite live region while loading", () => {
    renderPage();
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("renders an alert region on error with a retry button", async () => {
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({ userId: "u1" });
    renderPage();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("renders an h1 and an empty state when there are no bookings", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { level: 1, name: /my bookings/i })).toBeInTheDocument();
    expect(screen.getByText(/no bookings yet/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 9: Run tests to verify they fail**

Run: `cd apps/web-pwa && pnpm test test/bookings-page.test.tsx`
Expected: 3 failures — expected role=status, role=alert, h1.

- [ ] **Step 10: Polish BookingsPage**

Replace `apps/web-pwa/src/pages/book/BookingsPage.tsx` with:

```tsx
import { Button, Card, CardContent, CardHeader, CardTitle, EmptyState, ErrorState, LoadingSkeleton } from "@splashh/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@splashh/api-client";
import { bookingsApi } from "@/features/bookings/api";
import { useBookingsByCustomer } from "@/features/bookings/useBookings";

function CancelButton({ id }: { id: string }) {
  const qc = useQueryClient();
  const cancel = useMutation({
    mutationFn: () => bookingsApi.cancel(id, "customer_request"),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["bookings"] });
    },
  });
  return (
    <Button size="sm" variant="destructive" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
      {cancel.isPending ? "Cancelling…" : "Cancel"}
    </Button>
  );
}

export function BookingsPage() {
  const userId = useAuthStore((s) => s.userId);
  const { data, isLoading, error, refetch } = useBookingsByCustomer(userId);

  return (
    <main className="container py-6">
      <h1 className="mb-4 text-2xl font-semibold">My bookings</h1>
      {isLoading && <LoadingSkeleton withCard lines={3} />}
      {error && (
        <ErrorState
          title="Could not load your bookings"
          description="Try again in a moment."
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !error && data?.length === 0 && (
        <EmptyState
          title="No bookings yet"
          description="Browse facilities and book your first slot."
          action={{ label: "Browse facilities", to: "/book" }}
        />
      )}
      {!isLoading && !error && (data?.length ?? 0) > 0 && (
        <ul className="space-y-3">
          {data!.map((b) => (
            <li key={b.id}>
              <Card>
                <CardHeader>
                  <CardTitle as="h2" className="text-base">
                    {new Date(b.start_at).toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Status: {b.status} · {b.price_cents / 100} {b.currency}
                </CardContent>
                {b.status === "confirmed" && (
                  <CardContent>
                    <CancelButton id={b.id} />
                  </CardContent>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
```

- [ ] **Step 11: Run bookings tests to verify they pass**

Run: `cd apps/web-pwa && pnpm test test/bookings-page.test.tsx`
Expected: 3 tests passing.

- [ ] **Step 12: Add axe-core e2e for /book/bookings**

Create `e2e/bookings-polish.spec.ts`:

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("/book/bookings passes axe-core (light)", async ({ page }) => {
  // assumes a logged-in customer via existing seed; see admin-user-creation.spec.ts
  await page.goto("/book/bookings");
  await expect(page.getByRole("heading", { level: 1, name: /my bookings/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/book/bookings passes axe-core (dark)", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/book/bookings");
  await expect(page.getByRole("heading", { level: 1, name: /my bookings/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

- [ ] **Step 13: Commit**

```bash
git add packages/ui/src/components/EmptyState.tsx \
        packages/ui/src/components/LoadingSkeleton.tsx \
        packages/ui/src/components/ErrorState.tsx \
        packages/ui/src/components/EmptyState.test.tsx \
        packages/ui/src/components/LoadingSkeleton.test.tsx \
        packages/ui/src/components/ErrorState.test.tsx \
        packages/ui/src/index.ts \
        apps/web-pwa/src/pages/book/BookingsPage.tsx \
        apps/web-pwa/test/bookings-page.test.tsx \
        e2e/bookings-polish.spec.ts
git commit -m "feat(ui): EmptyState/LoadingSkeleton/ErrorState + polish /book/bookings"
```

---

## Task 3: Polish `/book` (Facilities list)

**Files:**
- Modify: `apps/web-pwa/src/pages/book/FacilitiesPage.tsx`
- Modify: `apps/web-pwa/test/facilities-page.test.tsx`
- New: `e2e/facilities-polish.spec.ts`

**Goal:** Replace the raw "Loading…", "Failed to load facilities.", and
"No facilities yet." markup with the shared state components. Add
`text-base` to the page-level layout (no inputs here, but iOS-safe
heading sizing), ensure h1 → h2 hierarchy with the cards as h2.

**Interfaces (consumed):**
- `EmptyState`, `LoadingSkeleton`, `ErrorState` from `@splashh/ui` (from Task 2)
- `useFacilities()` from `@/features/facilities/useFacilities`

**Interfaces (produced for later tasks):**
- None — Task 3 is self-contained.

- [ ] **Step 1: Write failing tests for the polished FacilitiesPage**

Append to `apps/web-pwa/test/facilities-page.test.tsx`:

```tsx
import { useAuthStore } from "@splashh/api-client";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

// existing render fn below ...

describe("FacilitiesPage (polish)", () => {
  it("renders a polite live region while loading", () => {
    render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><FacilitiesPage /></QueryClientProvider></MemoryRouter>);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("renders an h1 inside <main>", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: { data: [] } });
    render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><FacilitiesPage /></QueryClientProvider></MemoryRouter>);
    expect(await screen.findByRole("heading", { level: 1, name: /facilities/i })).toBeInTheDocument();
  });

  it("renders the empty state with a Browse action when there are no facilities", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: { data: [] } });
    render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><FacilitiesPage /></QueryClientProvider></MemoryRouter>);
    expect(await screen.findByText(/no facilities yet/i)).toBeInTheDocument();
  });

  it("renders an alert region on error and a retry button", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("boom"));
    render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><FacilitiesPage /></QueryClientProvider></MemoryRouter>);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/web-pwa && pnpm test test/facilities-page.test.tsx`
Expected: 3 failures — role=status, role=alert, h1.

- [ ] **Step 3: Polish FacilitiesPage**

Replace `apps/web-pwa/src/pages/book/FacilitiesPage.tsx` with:

```tsx
import { Card, CardContent, CardFooter, CardHeader, CardTitle, EmptyState, ErrorState, LoadingSkeleton } from "@splashh/ui";
import { Link } from "react-router-dom";
import { useFacilities } from "@/features/facilities/useFacilities";

export function FacilitiesPage() {
  const { data, isLoading, error, refetch } = useFacilities();

  return (
    <main className="container py-6">
      <h1 className="mb-4 text-2xl font-semibold">Facilities</h1>
      {isLoading && <LoadingSkeleton withCard lines={3} />}
      {error && (
        <ErrorState
          title="Could not load facilities"
          description="Try again in a moment."
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !error && data?.length === 0 && (
        <EmptyState
          title="No facilities yet"
          description="When your club adds facilities, they'll show up here."
        />
      )}
      {!isLoading && !error && (data?.length ?? 0) > 0 && (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data!.map((f) => (
            <li key={f.id}>
              <Card className="h-full">
                <CardHeader>
                  <CardTitle as="h2" className="text-lg">{f.name}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {f.city}, {f.state}
                </CardContent>
                <CardFooter>
                  <Link
                    to={`/book/facilities/${f.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    View details →
                  </Link>
                </CardFooter>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/web-pwa && pnpm test test/facilities-page.test.tsx`
Expected: All tests pass (existing + 4 new).

- [ ] **Step 5: Add axe-core e2e for /book**

Create `e2e/facilities-polish.spec.ts`:

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("/book passes axe-core (light)", async ({ page }) => {
  await page.goto("/book");
  await expect(page.getByRole("heading", { level: 1, name: /facilities/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/book passes axe-core (dark)", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/book");
  await expect(page.getByRole("heading", { level: 1, name: /facilities/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

- [ ] **Step 6: Commit**

```bash
git add apps/web-pwa/src/pages/book/FacilitiesPage.tsx \
        apps/web-pwa/test/facilities-page.test.tsx \
        e2e/facilities-polish.spec.ts
git commit -m "feat(web-pwa): polish /book — shared state components, h1, a11y"
```

---

## Task 4: Polish `/book/facilities/:id` (detail)

**Files:**
- Modify: `apps/web-pwa/src/pages/book/FacilityDetailPage.tsx`
- New: `apps/web-pwa/test/facility-detail-page.test.tsx`
- New: `e2e/facility-detail-polish.spec.ts`

**Goal:** Replace the raw `Loading…` / `Failed to load facility.` markup
with the shared components. Distinguish 404 (not found) from network
errors so the user gets actionable feedback. Promote the card titles
and the "Resources" header to h2 for a proper h1 → h2 → h3 hierarchy.

**Interfaces (consumed):**
- `EmptyState`, `LoadingSkeleton`, `ErrorState` from `@splashh/ui` (from Task 2)
- `useFacility(id)`, `useResources(id)` from `@/features/facilities/useFacilities`

**Interfaces (produced for later tasks):**
- None — Task 4 is the final task.

- [ ] **Step 1: Write failing tests for the polished FacilityDetailPage**

Create `apps/web-pwa/test/facility-detail-page.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>(
    "@splashh/api-client",
  );
  return { ...actual, api: { get: vi.fn() } };
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api } from "@splashh/api-client";
import { FacilityDetailPage } from "@/pages/book/FacilityDetailPage";

function renderAt(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/book/facilities/${id}`]}>
      <QueryClientProvider client={new QueryClient()}>
        <Routes>
          <Route path="/book/facilities/:id" element={<FacilityDetailPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("FacilityDetailPage", () => {
  it("renders a polite live region while loading", () => {
    renderAt("fac-123");
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("renders the facility name as h1 inside <main>", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { data: { id: "fac-123", name: "Sydney Aquatic Centre", address_line1: "1 Driver Ave", city: "Sydney", state: "NSW" } },
    });
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: { data: [] } });
    renderAt("fac-123");
    expect(
      await screen.findByRole("heading", { level: 1, name: /sydney aquatic centre/i }),
    ).toBeInTheDocument();
  });

  it("renders a 404 empty state when the facility is not found", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: { data: null } });
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: { data: [] } });
    renderAt("missing");
    expect(await screen.findByText(/not found/i)).toBeInTheDocument();
  });

  it("renders an alert region on error with a retry button", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("boom"));
    renderAt("fac-123");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/web-pwa && pnpm test test/facility-detail-page.test.tsx`
Expected: 4 failures.

- [ ] **Step 3: Polish FacilityDetailPage**

Replace `apps/web-pwa/src/pages/book/FacilityDetailPage.tsx` with:

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, EmptyState, ErrorState, LoadingSkeleton } from "@splashh/ui";
import { useFacility, useResources } from "@/features/facilities/useFacilities";
import { BookingDialog } from "@/features/bookings/BookingDialog";

export function FacilityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const facility = useFacility(id);
  const resources = useResources(id);
  const [bookingResource, setBookingResource] = useState<string | null>(null);

  if (facility.isLoading) {
    return (
      <main className="container py-6">
        <LoadingSkeleton withCard lines={3} />
      </main>
    );
  }

  if (facility.error) {
    return (
      <main className="container py-6">
        <ErrorState
          title="Could not load facility"
          description="Try again in a moment."
          onRetry={() => facility.refetch()}
        />
      </main>
    );
  }

  if (!facility.data) {
    return (
      <main className="container py-6">
        <EmptyState
          title="Facility not found"
          description="It may have been removed. Try browsing all facilities."
          action={{ label: "Browse facilities", to: "/book" }}
        />
      </main>
    );
  }

  const f = facility.data;
  return (
    <main className="container py-6">
      <h1 className="text-2xl font-semibold">{f.name}</h1>
      <p className="text-sm text-muted-foreground">
        {f.address_line1}, {f.city} {f.state}
      </p>
      <h2 className="mt-6 text-lg font-medium">Resources</h2>
      {resources.isLoading && <LoadingSkeleton />}
      {resources.error && (
        <ErrorState
          title="Could not load resources"
          onRetry={() => resources.refetch()}
        />
      )}
      {!resources.isLoading && !resources.error && resources.data?.length === 0 && (
        <EmptyState title="No resources yet" description="This facility has no bookable resources." />
      )}
      {!resources.isLoading && !resources.error && (resources.data?.length ?? 0) > 0 && (
        <ul className="mt-2 grid gap-3 sm:grid-cols-2">
          {resources.data!.map((r) => (
            <li key={r.id}>
              <Card>
                <CardHeader>
                  <CardTitle as="h3" className="text-base">{r.name}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Type: {r.resource_type} · Capacity: {r.capacity}
                </CardContent>
                <CardContent>
                  <Button onClick={() => setBookingResource(r.id)}>Book</Button>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
      {bookingResource && (
        <BookingDialog resourceId={bookingResource} onClose={() => setBookingResource(null)} />
      )}
    </main>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/web-pwa && pnpm test test/facility-detail-page.test.tsx`
Expected: 4 tests passing.

- [ ] **Step 5: Add axe-core e2e for /book/facilities/:id**

Create `e2e/facility-detail-polish.spec.ts`:

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("/book/facilities/:id passes axe-core (light)", async ({ page }) => {
  // seed has splash-sports-club facility; assumes migration ran
  await page.goto("/book/facilities/splash-sports-club");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/book/facilities/:id passes axe-core (dark)", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/book/facilities/splash-sports-club");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/book/facilities/:id shows the not-found state for an unknown id", async ({ page }) => {
  await page.goto("/book/facilities/does-not-exist");
  await expect(page.getByText(/not found/i)).toBeVisible();
  await page.getByRole("link", { name: /browse facilities/i }).click();
  await expect(page).toHaveURL(/\/book$/);
});
```

- [ ] **Step 6: Commit**

```bash
git add apps/web-pwa/src/pages/book/FacilityDetailPage.tsx \
        apps/web-pwa/test/facility-detail-page.test.tsx \
        e2e/facility-detail-polish.spec.ts
git commit -m "feat(web-pwa): polish /book/facilities/:id — 404, shared states, a11y"
```

---

## Whole-spec done criteria

After all 4 tasks land:

- [ ] All 4 pages pass 0 axe-core violations in light + dark
- [ ] `packages/ui/` exports `EmptyState`, `LoadingSkeleton`, `ErrorState`
- [ ] `pnpm --filter web-pwa test` green (24 + new tests)
- [ ] `pnpm test:e2e` green (existing + new polish specs)
- [ ] `pnpm typecheck` green
- [ ] `pnpm -r build` green
- [ ] Visual regression baseline saved at `e2e/screenshots/polish-baseline/` (8 PNGs: 4 pages × 2 modes) — captured manually after all tasks land

## Self-review checklist

- [x] Spec coverage: every page in the spec has a task; every done criterion is addressed.
- [x] Placeholder scan: no "TBD", "TODO", "implement later", "fill in details".
- [x] Type consistency: `EmptyState`, `LoadingSkeleton`, `ErrorState` defined in Task 2; `Btn`. `Button` only used; `CardTitle as="h2"`/`"h3"` tasked; same component contracts used across Tasks 2, 3, 4.
- [x] No new dependencies added.
- [x] Existing tests preserved (login.test.tsx, facilities-page.test.tsx keep current tests; new tests append).
- [x] axe-core 0 violations is the gate — codified as e2e test per page.
- [x] Mobile: iOS-safe `text-base` on inputs (Task 1); responsive grids already exist (Tasks 2-4).
- [x] Form validation: `FormField` already renders `role="alert"`; submit error is `aria-live="assertive"` (Task 1).
- [x] Dark mode: `omitBackground`/parity comes free from existing CSS vars; verified by axe-core in dark mode.
