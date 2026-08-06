# web-pwa

Single PWA for the Splashh Sports Platform with role-based routing.
After login, users are redirected to a role-specific home page.

## Two login routes

- `/login` — Customer login (book facilities, manage bookings)
- `/admin/login` — Admin login (manage facilities, resources, users)

## Role-based home

After login, users are redirected based on their role:

- `customer` → `/book` (facilities, bookings)
- `admin` → `/admin/facilities` (facility management)
- `admin` with user-management permission → `/admin/users` (user management)

## Dev

```bash
pnpm --filter web-pwa dev
# http://127.0.0.1:5173 (PWA)
# http://127.0.0.1:8765 (backend API)
```

The dev server proxies `/v1` to the backend at `http://127.0.0.1:8765`.

## Build

```bash
pnpm --filter web-pwa build
```

## Test

```bash
pnpm --filter web-pwa test
pnpm test:e2e
```

## Stack

Vite + React 18 + TypeScript + shadcn/ui (via `@splashh/ui`) + TanStack Query +
React Router v6 + React Hook Form + Zod + Zustand (via `@splashh/api-client`) +
vite-plugin-pwa.
