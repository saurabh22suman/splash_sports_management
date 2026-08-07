# Customer-Facing UI Polish — design

**Date:** 2026-08-07
**Status:** approved
**Owner:** soloengine

## Goal

Make the four customer-facing pages of the Splashh PWA feel finished and
accessible. After this pass, every page passes axe-core with 0 violations,
has real loading/empty/error states (not "Loading…" text), works
comfortably on a phone, and shares a consistent visual rhythm with light
+ dark mode parity.

## Scope

**In scope (4 customer-facing pages):**
- `/login` — `apps/web-pwa/src/pages/LoginPage.tsx`
- `/book` — `apps/web-pwa/src/pages/book/FacilitiesPage.tsx`
- `/book/facilities/:id` — `apps/web-pwa/src/pages/book/FacilityDetailPage.tsx`
- `/book/bookings` — `apps/web-pwa/src/pages/book/BookingsPage.tsx`

**In scope (shared primitives):**
- `packages/ui/src/components/EmptyState.tsx`
- `packages/ui/src/components/LoadingSkeleton.tsx`
- `packages/ui/src/components/ErrorState.tsx`
- Re-export from `packages/ui/src/index.ts`

**Out of scope (deferred):**
- Admin pages (`/admin/login`, `/admin`, `/admin/users`, `/admin/facilities/*`, `/admin/bookings`)
- `HomePage` (`/`) — public landing; not in customer-flow scope
- New features (dark-mode toggle UI, password reset, profile page)
- Performance optimization
- i18n / RTL

## Approach: page-by-page

Four tasks, one per page, in complexity order. The shared components
(`EmptyState`, `LoadingSkeleton`, `ErrorState`) are introduced by Task 2
in `packages/ui/` so Tasks 3 and 4 can compose them directly.

1. **Task 1 — `/login`** — form-heavy, no data fetching; introduces the
   form-validation feedback pattern (inline error under input,
   `role="alert"` on submit error, focus management on mount).
2. **Task 2 — `/book/bookings`** — first data-fetching page polished.
   Introduces `EmptyState`, `LoadingSkeleton`, `ErrorState` in
   `packages/ui/src/components/` and exports them from
   `packages/ui/src/index.ts`. Replaces the existing "Loading…",
   "Failed to load bookings.", and "No bookings yet." raw markup.
3. **Task 3 — `/book`** — reuses the three shared components from Task 2.
   Cards on a responsive grid (already has `sm:grid-cols-2 lg:grid-cols-3`).
4. **Task 4 — `/book/facilities/:id`** — reuses the three shared
   components. Adds error state distinguishing 404 from network failure.

## Per-page work (all four dimensions per page)

| Dimension | Concrete deliverable |
|---|---|
| **A11y** | Proper landmarks (`<main>`, `<nav>` if any), heading hierarchy (h1 → h2 → h3), `aria-label`s on icon-only buttons, `role="alert"` for errors, keyboard focus on mount, axe-core clean (0 violations) |
| **UX states** | Loading skeleton matching eventual content, empty state with helpful copy + optional CTA, error state with retry button, form-validation feedback (inline) |
| **Mobile** | Single-column ≤640px, touch targets ≥44px, inputs ≥16px font (iOS-safe — prevents zoom on focus), no horizontal scroll, mobile screenshot at 375×812 |
| **Visual** | Consistent spacing on the Tailwind scale, visible focus rings, hover states, dark-mode parity, subtle motion for state transitions (fade/slide) |

## Cross-cutting decisions

- **Shared components live in `packages/ui/src/components/`**, not in
  `apps/web-pwa/src/components/`. Promotion from day one so admin pages
  can reuse immediately when their polish pass comes.
- **No new tokens in `@splashh/ui/tokens.ts`** for this pass — the existing
  HSL CSS vars (`--background`, `--primary`, etc.) cover what's needed.
- **Form components in `packages/ui/src/components/forms/form-field.tsx`**
  are reused by Task 1 for the login form.
- **No new dependencies** added to `package.json`.

## File structure

```
packages/ui/src/components/
├── EmptyState.tsx          # new
├── LoadingSkeleton.tsx     # new
├── ErrorState.tsx          # new
└── ui/                     # existing primitives (button, card, input, label)
└── forms/                  # existing form primitives
packages/ui/src/index.ts    # modified: export the 3 new components

apps/web-pwa/src/pages/LoginPage.tsx                # polished (Task 1)
apps/web-pwa/src/pages/book/BookingsPage.tsx        # polished (Task 2)
apps/web-pwa/src/pages/book/FacilitiesPage.tsx      # polished (Task 3)
apps/web-pwa/src/pages/book/FacilityDetailPage.tsx  # polished (Task 4)

apps/web-pwa/test/bookings-page.test.tsx            # new (Task 2)
apps/web-pwa/test/facilities-page.test.tsx          # extended (Task 3)
apps/web-pwa/test/facility-detail-page.test.tsx     # new (Task 4)

e2e/screenshots/polish-baseline/                    # new (visual regression)
├── login-desktop-light.png
├── login-desktop-dark.png
├── login-mobile-light.png
├── login-mobile-dark.png
└── ... (× 4 pages)
```

## Component contracts

**`EmptyState`** (used when a list/data is empty):
- Props: `icon?: ReactNode`, `title: string`, `description?: string`, `action?: { label: string; onClick: () => void } | { label: string; to: string }`
- Renders centered, with appropriate vertical spacing
- No role needed; just heading + text + button

**`LoadingSkeleton`** (used during data fetch):
- Props: `lines?: number` (default 3), `withCard?: boolean` (default false)
- Renders `role="status"` with `aria-live="polite"`, screen-reader text "Loading…"
- Animated pulse using existing Tailwind `animate-pulse`

**`ErrorState`** (used on data-fetch failure):
- Props: `title?: string` (default "Something went wrong"), `description?: string`, `onRetry?: () => void`
- Renders `role="alert"` so screen readers announce
- Retry button is the primary action if `onRetry` provided

## Testing strategy (per page)

1. **axe-core** via `@axe-core/playwright` — 0 violations in light + dark.
2. **Keyboard nav walkthrough** — tab through the page, hit Enter on
   the primary action, ensure focus is visible at every stop.
3. **Mobile screenshot** at 375×812 (iPhone 13) — full-page.
4. **Desktop screenshot** at 1280×800 — full-page.
5. **Both screenshots in both modes** (light + dark).
6. **Existing tests still green** — `pnpm --filter web-pwa test`
   (currently 24 passing).
7. **Existing e2e tests still green** — `pnpm test:e2e`.

## Done criteria

**Per-page (each task):**
- [ ] 0 axe-core violations in light + dark
- [ ] Keyboard nav works end-to-end
- [ ] Mobile screenshot inspected
- [ ] Desktop screenshot inspected
- [ ] Existing unit + e2e tests still green
- [ ] At least one new component-usage test added to `apps/web-pwa/test/`

**Whole-spec (after all 4 tasks):**
- [ ] All 4 pages pass per-page criteria
- [ ] `packages/ui/` exports `EmptyState`, `LoadingSkeleton`, `ErrorState`
- [ ] Visual regression baseline saved at `e2e/screenshots/polish-baseline/`
      (8 PNGs: 4 pages × 2 modes)

## Why this approach

- **Page-by-page** lets each task ship a finished unit for review; the
  reviewer sees one polished page, not partial changes across four.
- **Shared primitives in `packages/ui/` from day one** avoids needing to
  migrate later when admin pages reuse them.
- **Tasks 1 and 2 are independent** (different files) and can run in
  parallel; **Tasks 3 and 4 are independent of each other** (different
  files) and both depend on Task 2's shared components. This gives a
  2 + 2 parallel structure for implementation.
- **axe-core is the gate** — it surfaces the same kinds of issues
  Playwright testing found earlier (color contrast, heading order) and
  prevents regressions.

## Open follow-ups (not part of this spec)

- Admin pages polish (separate pass).
- HomePage polish (separate pass).
- Performance pass (image optimization, code splitting per route).
- Add a dark-mode toggle in the UI (currently just respects system
  preference via `next-themes`).
- i18n / RTL support.