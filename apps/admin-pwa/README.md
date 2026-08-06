# admin-pwa

Operator-facing PWA for the Splashh Sports Platform. Manage facilities,
resources, and availability rules; view and update today's bookings.

## Dev

```bash
pnpm --filter admin-pwa dev
# http://127.0.0.1:5173
```

The dev server proxies `/v1` to the backend at `http://127.0.0.1:8765`.

## Build

```bash
pnpm --filter admin-pwa build
```

## Test

```bash
pnpm --filter admin-pwa test
pnpm test:e2e -- --project=admin
```

## Stack

Same as `customer-pwa`: Vite + React 18 + TypeScript + shadcn/ui (via
`@splashh/ui`) + TanStack Query + React Router v6 + React Hook Form + Zod +
Zustand (via `@splashh/api-client`) + vite-plugin-pwa.
