# Quick Wins Round 1 — Security, DB, PWA, Frontend Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 9 still-open "quick win" findings from `docs/FINDINGS_ROADMAP.md` (F-04, F-20, F-27, F-28, F-29, F-30, F-31, F-38, F-39). The other 5 (F-06, F-09, F-22, F-23, F-24) are already done from the 2026-08-11 catch-up commit.

**Architecture:** Small, independent fixes. Each task touches one concern. Most are <1 day of work. Tasks 1 and 2 (DB migrations) should land first so the test suite stays green.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic; React 19 + Vite 5 + Tailwind 4; Postgres 16.

## Global Constraints

- Coverage targets per `docs/01-vision/overview.md`: domain ≥95%, services ≥90%, API ≥80%.
- Conventional commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:`).
- All FK constraints must have explicit `name="..."` per F-22.
- Alembic migrations are forward-only; never edit an applied migration.
- No new top-level dependencies without an ADR update.
- Branch from `main`. Commit directly to main is acceptable for S-effort fixes (user preference); M-effort F-04 should land as a single PR-equivalent commit.

---

## Task Order

| # | Finding | Title | Effort |
|---|---|---|---|
| 1 | F-28 | Composite time-range index on bookings | S |
| 2 | F-20 | FK on `customer.tenant_id` | S |
| 3 | F-27 | Vite manual chunks (bundle ≤ 250 KB) | S |
| 4 | F-30 | iOS meta tags + touch icon sizes | S |
| 5 | F-29 | React ErrorBoundary | S |
| 6 | F-31 | Mobile user menu accessible in TopBar | S |
| 7 | F-38 | Backend container runs as non-root user | S |
| 8 | F-39 | Doc-code drift sync for module docs | S |
| 9 | F-04 | JWT RS256: remove HS256 fallback from production path | M |

Tasks 1–8 can run in parallel (no shared files). Task 9 is last because it touches auth wiring + settings + tests.

---

### Task 1: F-28 — Composite time-range index on bookings

**Files:**
- Create: `apps/backend/alembic/versions/20260812_0001_bookings_resource_window_index.py`
- Modify: `apps/backend/src/booking/infrastructure/models.py:17-20`

**Context:** Booking list queries (`WHERE tenant_id = ? AND resource_id = ? AND start_at BETWEEN ? AND ?`) currently seq-scan. The composite index covers this exact access pattern and will also satisfy the existing `test_booking_service.py:252` race-condition test.

**Acceptance criteria:**
- New index `ix_bookings_resource_window` exists on `(tenant_id, resource_id, start_at)`.
- Migration applies cleanly on a fresh DB and on a DB that already has the `bookings` table.
- `EXPLAIN SELECT … FROM bookings WHERE tenant_id = … AND resource_id = … AND start_at BETWEEN …` shows an index scan.

- [ ] **Step 1: Add the index to the model**

Edit `apps/backend/src/booking/infrastructure/models.py:17-20`:

```python
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_bookings_window_valid"),
        CheckConstraint("price_cents >= 0", name="ck_bookings_price_non_negative"),
        Index(
            "ix_bookings_resource_window",
            "tenant_id", "resource_id", "start_at",
        ),
    )
```

Add `Index` to the imports on line 7:

```python
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint
```

- [ ] **Step 2: Create the alembic migration**

Create `apps/backend/alembic/versions/20260812_0001_bookings_resource_window_index.py`:

```python
"""add composite time-range index on bookings (F-28)

Revision ID: 20260812_0001
Revises: 20260811_0007
Create Date: 2026-08-12 00:00:00
"""
from __future__ import annotations

from alembic import op


revision = "20260812_0001"
down_revision = "20260811_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_bookings_resource_window",
        "bookings",
        ["tenant_id", "resource_id", "start_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bookings_resource_window", table_name="bookings")
```

- [ ] **Step 3: Apply migration locally**

Run:
```bash
cd apps/backend && alembic upgrade head
```

Expected: `20260812_0001` listed in `alembic_version` table; `\d bookings` in psql shows the new index.

- [ ] **Step 4: Commit**

```bash
git add apps/backend/alembic/versions/20260812_0001_bookings_resource_window_index.py apps/backend/src/booking/infrastructure/models.py
git commit -m "perf(booking): composite (tenant,resource,start_at) index for time-range queries (F-28)"
```

---

### Task 2: F-20 — FK on `customer.tenant_id`

**Files:**
- Create: `apps/backend/alembic/versions/20260812_0002_customer_tenant_fk.py`
- Modify: `apps/backend/src/customer/infrastructure/models.py:20-22`

**Context:** Every other business table has `tenant_id` as a plain indexed UUID. The payments module already verified RLS works via DB FK checks. Add the same FK to customers so an orphan tenant_id cannot be inserted.

**Acceptance criteria:**
- `customers.tenant_id` has `ForeignKey("tenants.id", ondelete="CASCADE", name="fk_customers_tenant_id")`.
- Inserting a customer with unknown tenant fails at DB level.
- Migration applies; existing data passes the FK (it already does — every customer has a valid tenant_id).

- [ ] **Step 1: Update the customer model**

Edit `apps/backend/src/customer/infrastructure/models.py:20-22`:

```python
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_customers_tenant_id"),
        index=True,
        nullable=False,
    )
```

- [ ] **Step 2: Create the migration**

Create `apps/backend/alembic/versions/20260812_0002_customer_tenant_fk.py`:

```python
"""add FK on customers.tenant_id (F-20)

Revision ID: 20260812_0002
Revises: 20260812_0001
Create Date: 2026-08-12 00:00:01
"""
from __future__ import annotations

from alembic import op


revision = "20260812_0002"
down_revision = "20260812_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_customers_tenant_id",
        "customers",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_customers_tenant_id", "customers", type_="foreignkey")
```

- [ ] **Step 3: Apply migration**

```bash
cd apps/backend && alembic upgrade head
```

Expected: FK visible in `\d customers`.

- [ ] **Step 4: Commit**

```bash
git add apps/backend/alembic/versions/20260812_0002_customer_tenant_fk.py apps/backend/src/customer/infrastructure/models.py
git commit -m "fix(customer): FK from customers.tenant_id to tenants.id (F-20)"
```

---

### Task 3: F-27 — Vite manual chunks (bundle ≤ 250 KB)

**Files:**
- Modify: `apps/web-pwa/vite.config.ts:7-60`

**Context:** The handbook's `docs/16-quality-gates/performance-gates.md` says `index.js ≤ 250 KB`. Current build is 365 KB. The fix is one config change — split vendor code into separate chunks so the app code is what users re-download when it changes.

**Acceptance criteria:**
- `build.rollupOptions.output.manualChunks` separates `react-vendor`, `query-vendor`, `ui-kit`, `icons`.
- After `pnpm build`, the main entry chunk (`assets/index-*.js`) is ≤ 250 KB.
- `chunkSizeWarningLimit` raised to 600 to silence vendor-chunk warnings.

- [ ] **Step 1: Add build config to vite.config.ts**

Replace `apps/web-pwa/vite.config.ts:7-60` with:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
import path from "node:path";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "Splashh",
        short_name: "Splashh",
        description: "Manage your sports club",
        theme_color: "#CCFF00",
        background_color: "#0a0a0b",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
        shortcuts: [
          { name: "My bookings", url: "/book/bookings", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
          { name: "Browse facilities", url: "/book", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,woff2}"],
        runtimeCaching: [
          {
            urlPattern: /^\/v1\//,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              networkTimeoutSeconds: 10,
              expiration: { maxEntries: 100, maxAgeSeconds: 86400 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|webp|avif|gif)$/,
            handler: "CacheFirst",
            options: { cacheName: "image-cache", expiration: { maxEntries: 200, maxAgeSeconds: 2592000 } },
          },
        ],
      },
    }),
  ],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/v1": { target: "http://127.0.0.1:8765", changeOrigin: false } },
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("react-dom") || id.includes("/react/") || id.includes("scheduler")) return "react-vendor";
          if (id.includes("@tanstack")) return "query-vendor";
          if (id.includes("@splashh/ui")) return "ui-kit";
          if (id.includes("lucide-react") || id.includes("/icons/")) return "icons";
          return "vendor";
        },
      },
    },
  },
  test: { environment: "happy-dom", globals: true, setupFiles: ["./test-setup.ts"] },
});
```

- [ ] **Step 2: Build and verify chunk sizes**

```bash
cd apps/web-pwa && pnpm build
ls -lh apps/web-pwa/dist/assets/index-*.js
```

Expected: `index-*.js` ≤ 250 KB. Vendor chunks (`react-vendor-*.js`, `query-vendor-*.js`, `ui-kit-*.js`, `icons-*.js`) exist and are ≥ 250 KB each.

- [ ] **Step 3: Commit**

```bash
git add apps/web-pwa/vite.config.ts
git commit -m "perf(web-pwa): manual vendor chunks, main bundle under 250KB (F-27)"
```

---

### Task 4: F-30 — iOS meta tags + touch icon sizes

**Files:**
- Modify: `apps/web-pwa/index.html:1-20`
- Modify: `apps/web-pwa/vite.config.ts:22-25` (icon array)

**Context:** The audit found missing iOS PWA install support. iOS Safari uses `apple-mobile-web-app-capable` (not the standard `display: standalone`) and a separate `apple-touch-icon` link. We also need 152/180 sizes for retina iPads and iPhones.

**Acceptance criteria:**
- `index.html` has `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, `apple-touch-icon` (3 sizes).
- `vite.config.ts` manifest references 144, 152, 180, 384 size entries (assumes the PNG files exist at `/public/icons/`).

- [ ] **Step 1: Update index.html**

Replace `apps/web-pwa/index.html` with:

```html
<!doctype html>
<html lang="en" class="">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#0a0a0b" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="Splashh" />
    <link rel="apple-touch-icon" href="/icons/icon-192.png" />
    <link rel="apple-touch-icon" sizes="152x152" href="/icons/icon-192.png" />
    <link rel="apple-touch-icon" sizes="180x180" href="/icons/icon-192.png" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap"
      rel="stylesheet"
    />
    <title>Splashh</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Add the missing icon sizes to vite.config.ts manifest**

Replace the icons array (around line 22-25) with:

```ts
        icons: [
          { src: "/icons/icon-144.png", sizes: "144x144", type: "image/png" },
          { src: "/icons/icon-152.png", sizes: "152x152", type: "image/png" },
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-180.png", sizes: "180x180", type: "image/png" },
          { src: "/icons/icon-384.png", sizes: "384x384", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
```

(If `icon-144.png`/`icon-152.png`/`icon-180.png`/`icon-384.png` are not yet present in `apps/web-pwa/public/icons/`, generate them from `icon-192.png` with sharp or imagemagick before merging. This plan assumes the assets team has produced them or will produce them in a follow-up — if absent, leave the manifest referencing the 192 file for now and file a follow-up.)

- [ ] **Step 3: Build and inspect**

```bash
cd apps/web-pwa && pnpm build
grep -i 'apple-mobile' dist/index.html
```

Expected: meta tags present.

- [ ] **Step 4: Commit**

```bash
git add apps/web-pwa/index.html apps/web-pwa/vite.config.ts
git commit -m "feat(web-pwa): iOS PWA meta tags and manifest icon sizes (F-30)"
```

---

### Task 5: F-29 — React ErrorBoundary

**Files:**
- Create: `apps/web-pwa/src/components/ErrorBoundary.tsx`
- Modify: `apps/web-pwa/src/App.tsx:8-18`

**Context:** Any uncaught render error today whitescreens the app. A class component `ErrorBoundary` that catches, logs, and shows a fallback is the canonical fix.

**Acceptance criteria:**
- `<ErrorBoundary>` wraps `<AppRouter />` in `App.tsx`.
- A thrown error from any descendant shows a fallback panel with a "Reload" button.
- Boundary calls `console.error` (replace with Sentry/Datadog later — out of scope here).

- [ ] **Step 1: Create the component**

Create `apps/web-pwa/src/components/ErrorBoundary.tsx`:

```tsx
import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string }) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught", error, info.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    if (this.props.fallback) return this.props.fallback(error, this.reset);
    return (
      <div
        role="alert"
        className="min-h-screen flex flex-col items-center justify-center p-6 bg-background text-foreground"
      >
        <h1 className="text-xl font-semibold mb-2">Something went wrong</h1>
        <p className="text-sm text-muted-foreground mb-4 max-w-md text-center">
          {error.message || "An unexpected error occurred."}
        </p>
        <button
          type="button"
          onClick={this.reset}
          className="px-4 py-2 rounded-none bg-primary text-primary-foreground text-sm font-medium hover:opacity-90"
        >
          Try again
        </button>
      </div>
    );
  }
}
```

- [ ] **Step 2: Wrap `<AppRouter />` in App.tsx**

Replace `apps/web-pwa/src/App.tsx` with:

```tsx
import { BrowserRouter } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { NoIndexOnAdmin } from "./components/NoIndexOnAdmin";
import { UpdateBanner } from "./components/UpdateBanner";
import { PWAInstallPrompt } from "./components/PWAInstallPrompt";
import { OfflineBanner } from "./components/OfflineBanner";
import { AppRouter } from "./routes";

export default function App() {
  return (
    <BrowserRouter>
      <NoIndexOnAdmin />
      <UpdateBanner />
      <ErrorBoundary>
        <AppRouter />
      </ErrorBoundary>
      <PWAInstallPrompt />
      <OfflineBanner />
    </BrowserRouter>
  );
}
```

- [ ] **Step 3: Type-check**

```bash
cd apps/web-pwa && pnpm tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web-pwa/src/components/ErrorBoundary.tsx apps/web-pwa/src/App.tsx
git commit -m "feat(web-pwa): React ErrorBoundary around router (F-29)"
```

---

### Task 6: F-31 — Mobile user menu accessible

**Files:**
- Modify: `apps/web-pwa/src/components/TopBar.tsx:14-48`
- Modify: `apps/web-pwa/src/components/Sidebar.tsx:93-95`

**Context:** On viewports < 768 px, the user menu is anchored to the bottom of the sidebar drawer. When the drawer is closed, the user has no way to reach the menu. The fix is to also render `<UserMenu />` in the TopBar on small viewports, and keep it in the sidebar on md+.

**Acceptance criteria:**
- UserMenu is reachable from the top bar on viewports < 768 px without opening the drawer.
- Sidebar still shows UserMenu on md+ viewports.
- Existing UserMenu keyboard / accessibility behaviour preserved.

- [ ] **Step 1: Add UserMenu to TopBar (mobile only)**

Replace `apps/web-pwa/src/components/TopBar.tsx` with:

```tsx
import { useLocation } from "react-router-dom";
import { cn, Menu, Waves } from "@splashh/ui";
import { titleForPath } from "@/lib/page-titles";
import { UserMenu } from "./UserMenu";

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
    <header
      className={cn(
        "h-14 bg-card border-b border-border flex items-center px-3 md:px-6 gap-3",
        "transition-colors duration-250 ease-swim",
        mobileOpen ? "relative z-30" : "relative",
      )}
    >
      <button
        type="button"
        aria-label="Toggle navigation"
        aria-expanded={mobileOpen}
        aria-controls="primary-nav"
        onClick={onToggleSidebar}
        className={cn(
          "md:hidden p-2 rounded-none transition-all duration-250 ease-swim",
          "hover:bg-secondary active:scale-95",
        )}
      >
        <Menu className="w-5 h-5 text-foreground" />
      </button>
      <h2
        key={pathname}
        className="text-base font-semibold text-foreground truncate animate-rise-up motion-reduce:animate-none"
      >
        {title}
      </h2>
      <div className="ml-auto flex items-center gap-2">
        <Waves
          aria-hidden="true"
          className="hidden md:block w-4 h-4 text-primary/40 animate-wave-drift motion-reduce:animate-none"
        />
        <div className="md:hidden">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Hide the sidebar copy on mobile (md+)**

Edit `apps/web-pwa/src/components/Sidebar.tsx:93-95`:

```tsx
      <div className="hidden md:block absolute bottom-0 left-0 right-0 p-2 border-t border-border bg-card">
        <UserMenu />
      </div>
```

(Add `hidden md:block` so the sidebar UserMenu only shows on ≥768 px viewports, where it's the only place it lives.)

- [ ] **Step 3: Type-check**

```bash
cd apps/web-pwa && pnpm tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add apps/web-pwa/src/components/TopBar.tsx apps/web-pwa/src/components/Sidebar.tsx
git commit -m "feat(web-pwa): user menu in top bar on mobile, sidebar on desktop (F-31)"
```

---

### Task 7: F-38 — Backend container runs as non-root

**Files:**
- Modify: `apps/backend/Dockerfile:1-39`

**Context:** The Dockerfile currently runs as root (`uid 0`). Best practice for any production container is to drop privileges.

**Acceptance criteria:**
- Container runs as a non-root user (`appuser`, uid 1000).
- All existing backend functionality still works in the dev compose stack.
- The user is created in the build stage; `/app` is owned by them.

- [ ] **Step 1: Add non-root user + USER directive**

Replace `apps/backend/Dockerfile` with:

```dockerfile
# Multi-stage build for the Splashh backend.
# Final image runs as non-root with distroless-style base.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user for runtime
RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser

WORKDIR /app

# Copy workspace config + backend package
COPY pyproject.toml uv.lock* ./
COPY apps/backend/pyproject.toml apps/backend/
COPY apps/backend/src apps/backend/src
COPY apps/backend/alembic apps/backend/alembic
COPY apps/backend/alembic.ini apps/backend/

# Install dependencies
RUN cd apps/backend && uv sync --frozen --no-dev || uv sync --no-dev

ENV PATH="/app/apps/backend/.venv/bin:$PATH"

WORKDIR /app/apps/backend

# Hand ownership of the app tree to the non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "common.interfaces.http.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Rebuild and verify uid**

```bash
docker build -t splashh-backend:test apps/backend
docker run --rm splashh-backend:test id
```

Expected output: `uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)`.

- [ ] **Step 3: Commit**

```bash
git add apps/backend/Dockerfile
git commit -m "chore(backend): Dockerfile runs as non-root user appuser (F-38)"
```

---

### Task 8: F-39 — Doc-code drift sync for module docs

**Files:**
- Modify: `docs/18-modules/membership.md` (verify "not yet implemented" banner)
- Modify: `docs/18-modules/notifications.md` (verify "not yet implemented" banner)
- Modify: `docs/18-modules/analytics.md` (verify "not yet implemented" banner)
- Modify: `docs/18-modules/README.md:65-78` (update status column if needed)

**Context:** Recent git log shows `3d63abe docs(membership): mark module as not yet implemented`. The audit's claim that docs claim shipped modules that aren't shipped is now fixed for membership. Confirm the other two and add a status column to the README table.

**Acceptance criteria:**
- Each of the three docs has a clear "Status: not yet implemented" banner at the top.
- The README table has a `Status` column reflecting reality for every module.

- [ ] **Step 1: Read each module doc and verify status banner**

```bash
head -20 docs/18-modules/membership.md
head -20 docs/18-modules/notifications.md
head -20 docs/18-modules/analytics.md
```

If a doc lacks a `> Status: not yet implemented` (or equivalent) line near the top, add one.

- [ ] **Step 2: Add status banners where missing**

For any doc missing the status banner, prepend this after the H1:

```markdown
> **Status:** Not yet implemented — scheduled for Phase 1/2 per `docs/FINDINGS_ROADMAP.md`.
```

- [ ] **Step 3: Add Status column to README table**

Edit `docs/18-modules/README.md:65-78`. Replace the table with:

```markdown
| Module | Purpose | Owner | Status |
|---|---|---|---|
| [auth](./auth.md) | Identity, authentication, sessions | Security | ✅ Shipped |
| [customer](./customer.md) | Member profiles, guardians, waivers | Customer Team | ✅ Shipped |
| [membership](./membership.md) | Plans, subscriptions, renewals | Billing Team | ⏳ Not yet implemented |
| [facility](./facility.md) | Courts, pools, resources, availability | Operations Team | ✅ Shipped |
| [booking](./booking.md) | Reservations, slots, check-in | Operations Team | ✅ Shipped (admin view in progress) |
| [payments](./payments.md) | Invoices, payments, refunds | Billing Team | ✅ Shipped (Razorpay) |
| [notifications](./notifications.md) | Email, SMS, push notifications | Platform Team | ⏳ Not yet implemented |
| [analytics](./analytics.md) | Reports, dashboards, exports | Product Team | ⏳ Not yet implemented |
| [common](./common.md) | Shared utilities, base classes | All | ✅ Shipped |
```

- [ ] **Step 4: Commit**

```bash
git add docs/18-modules/
git commit -m "docs(modules): explicit status banners and README status column (F-39)"
```

---

### Task 9: F-04 — JWT RS256: remove HS256 fallback from production path

**Files:**
- Modify: `apps/backend/src/auth/infrastructure/token_service.py:291-299` (remove `build_token_service`)
- Modify: `apps/backend/src/auth/interfaces/http/dependencies.py:43-77` (remove HS256 fallback; require RS256 keys)
- Modify: `apps/backend/src/auth/application/auth_service.py:301-339` (drop the `elif jwt_algorithm == "HS256"` branch; raise in production if RS256 keys missing)
- Modify: `apps/backend/src/common/infrastructure/settings.py:44-49` (default `jwt_algorithm` to `"RS256"`, document)
- Modify: `.env.prod.example:23-31` (verify RS256 keys documented; remove any HS256 references)
- Modify: `apps/backend/src/common/application/events.py` (out of scope here — listed only for awareness)

**Context:** The audit flagged: "RS256 is not implemented at all" — outdated. It IS implemented (RS256TokenService exists, dependencies.py uses JWT_PUBLIC_KEY_PATH). The remaining cleanup: remove HS256 fallback from the production path. HS256 must remain available for tests (some tests use ephemeral HS256 keys), but the application factory must never let HS256 reach a production environment.

**Acceptance criteria:**
- `auth_service.py` always returns an `RS256TokenService` (no HS256 branch in production).
- If `settings.environment == "production"` and JWT keys are missing, startup raises `RuntimeError`.
- `dependencies.py` rejects `JWT_ALGORITHM=HS256` outside dev/test environments.
- Tests using HS256 fixtures still work (test fixtures construct HS256TokenService directly, not via the factory).
- Existing integration tests in `tests/api/test_auth_endpoints.py` pass.

- [ ] **Step 1: Update settings.py defaults**

Replace `apps/backend/src/common/infrastructure/settings.py:44-49`:

```python
    # ---- JWT ----
    jwt_algorithm: Literal["RS256", "HS256"] = Field(
        default="RS256",
        description="Production must use RS256. HS256 is for tests only.",
    )
    jwt_private_key_path: Path = Field(default=Path("./secrets/jwt_private.pem"))
    jwt_public_key_path: Path = Field(default=Path("./secrets/jwt_public.pem"))
    jwt_access_token_ttl_seconds: int = 300
    jwt_refresh_token_ttl_seconds: int = 30 * 24 * 3600
```

- [ ] **Step 2: Remove the `build_token_service` HS256 factory**

In `apps/backend/src/auth/infrastructure/token_service.py`, delete lines 291-299 (the `build_token_service` function). It is a leftover HS256 factory that the application no longer uses.

- [ ] **Step 3: Drop the HS256 branch from auth_service.py**

Edit `apps/backend/src/auth/application/auth_service.py:301-339`. Replace the entire `if settings.jwt_algorithm == "RS256": … elif settings.jwt_algorithm == "HS256": … else:` block with:

```python
    import datetime as dt

    if settings.jwt_algorithm == "RS256":
        key_paths = RS256TokenService.get_secret(settings.environment)
        if key_paths is None and settings.environment in {"development", "test"}:
            private_pem, public_pem = RS256TokenService.generate_ephemeral_keypair()
        elif key_paths is None:
            msg = (
                "JWT keys not configured for production. "
                "Set JWT_PRIVATE_KEY_PATH and JWT_PUBLIC_KEY_PATH."
            )
            raise RuntimeError(msg)
        else:
            private_pem, public_pem = _read_keypair(key_paths)
        token_service = RS256TokenService(
            private_key_pem=private_pem,
            public_key_pem=public_pem,
            access_ttl=dt.timedelta(seconds=settings.jwt_access_token_ttl_seconds),
            refresh_ttl=dt.timedelta(seconds=settings.jwt_refresh_token_ttl_seconds),
        )
    elif settings.jwt_algorithm == "HS256":
        if settings.environment not in {"development", "test"}:
            msg = "HS256 is forbidden in production. Use RS256."
            raise RuntimeError(msg)
        import os
        secret = os.environ.get("JWT_SECRET")
        if not secret or len(secret) < 32:
            msg = "JWT_SECRET must be set and ≥32 chars in HS256 dev/test mode"
            raise RuntimeError(msg)
        from auth.infrastructure.token_service import HS256TokenService
        token_service = HS256TokenService(
            secret=secret,
            access_ttl=dt.timedelta(seconds=settings.jwt_access_token_ttl_seconds),
            refresh_ttl=dt.timedelta(seconds=settings.jwt_refresh_token_ttl_seconds),
        )
    else:
        msg = f"Unsupported JWT algorithm: {settings.jwt_algorithm}"
        raise NotImplementedError(msg)
```

Also add a small helper near the top of the function (or as a module-level private helper):

```python
def _read_keypair(key_paths: "RS256KeyPaths") -> tuple[str, str]:
    return (
        Path(key_paths.private_key_path).read_text(encoding="utf-8").strip(),
        Path(key_paths.public_key_path).read_text(encoding="utf-8").strip(),
    )
```

(Adjust indentation / imports as needed by the actual file.)

- [ ] **Step 4: Tighten dependencies.py — RS256 required in production, HS256 dev-only with explicit secret**

Edit `apps/backend/src/auth/interfaces/http/dependencies.py:43-77`. Replace `_get_jwt_algorithm` and `_get_public_key` with:

```python
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
```

- [ ] **Step 5: Verify .env.prod.example**

Confirm `.env.prod.example:23-31` only documents RS256. The current file already does (`JWT_ALGORITHM=RS256`). No change needed unless stray HS256 references remain.

- [ ] **Step 6: Run the auth test suite**

```bash
cd apps/backend && pytest tests/unit/test_rs256_token_service.py tests/api/test_auth_endpoints.py -v
```

Expected: all pass. (If `test_rs256_token_service.py` does not exist, run only `test_auth_endpoints.py` and note that the unit test is a separate follow-up.)

- [ ] **Step 7: Commit**

```bash
git add apps/backend/src/auth/infrastructure/token_service.py \
        apps/backend/src/auth/interfaces/http/dependencies.py \
        apps/backend/src/auth/application/auth_service.py \
        apps/backend/src/common/infrastructure/settings.py \
        .env.prod.example
git commit -m "fix(auth): remove HS256 fallback from production JWT path (F-04)"
```

---

## Verification (after all tasks land)

- [ ] `cd apps/backend && pytest` — full suite green
- [ ] `cd apps/web-pwa && pnpm tsc --noEmit && pnpm build && pnpm test` — type-check + build + tests green
- [ ] Bundle size: `ls -lh apps/web-pwa/dist/assets/index-*.js` ≤ 250 KB
- [ ] `docker build -t splashh-backend:test apps/backend && docker run --rm splashh-backend:test id` shows `uid=1000`
- [ ] Manual smoke: log in as customer, browse facilities, complete a booking flow
- [ ] Re-audit: update `docs/CODEBASE_REVIEW.md` to mark F-04, F-20, F-27, F-28, F-29, F-30, F-31, F-38, F-39 as resolved

## Out of scope for this plan

- F-02 (RBAC decorator across all routers) — its own focused plan
- F-03 (Postgres RLS on remaining tables) — its own focused plan
- F-11 (Redis Streams event bus) — M effort, Phase 0/1
- F-12 (OpenAPI codegen) — its own focused plan
- F-14/F-15 (tenant-isolation tests) — depends on F-03