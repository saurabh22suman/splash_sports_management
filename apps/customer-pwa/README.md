# customer-pwa

Customer-facing PWA for the Splashh Sports Platform. Installable, offline-capable
shell, with the booking flow (browse facilities → book a slot → my bookings).

## Dev

```bash
pnpm --filter customer-pwa dev
# http://127.0.0.1:5174
```

The dev server proxies `/v1` to the backend at `http://127.0.0.1:8765`.

## Build

```bash
pnpm --filter customer-pwa build
# Outputs to dist/ with manifest.webmanifest and sw.js
```

## Test

```bash
pnpm --filter customer-pwa test        # vitest unit + component
pnpm test:e2e -- --project=customer     # Playwright E2E
```

## Stack

Vite + React 18 + TypeScript + shadcn/ui (via `@splashh/ui`) + TanStack Query
+ React Router v6 + React Hook Form + Zod + Zustand (via `@splashh/api-client`)
+ vite-plugin-pwa.
