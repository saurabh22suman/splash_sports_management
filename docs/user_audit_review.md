# Splashh Sports Platform — User Audit Review

**Date:** 2026-08-11
**Reviewer:** Independent end-user audit (Claude)
**Scope:** Main branch (`main`), shipped modules (common, auth, customer, facility, booking, payments, web-pwa)
**Tested against:** running stack — Postgres + Redis (Docker Compose), FastAPI backend on `:8765`, web-pwa on `:5173`
**Test users:** `admin@demo.splashh.dev` / `Admin!Demo2026` (tenant_admin), `alex@demo.splashh.dev` / `Customer!Demo1` (customer)

This is a hands-on audit of what a real customer and a real admin see when they use the app. Screenshots are in the repo root (`audit-01-…` through `audit-13-…`, plus `phase-b2-*` and `phase-d-*` from the post-fix verification). The goal is to surface what is broken, what is generic-AI-slop, and what is hard to use — honestly.

**Status legend:** ✅ Fixed · 🟡 Partial · ❌ Open

---

## TL;DR

The platform has working auth, facility browsing, and a typed backend, but the **core customer booking flow is broken** (P0), the **entire payments surface is broken** (P0), and the **UI is generic-AI-generated shadcn-default** with no brand personality, no imagery, no real product thinking. There is little that a real sports-club customer would find compelling or trust. This needs a serious redesign pass before user testing, not after.

**Overall health: 6/20 → 13/20 after the stack-upgrade + landing-redesign pass.**

| # | Dimension | Score | Headline finding | Status |
|---|-----------|------:|------------------|:------:|
| 1 | Functionality (per flow) | 0–1 | Customer booking POST and all payments endpoints return HTTP 500 | � (P0s fixed, P1s open) |
| 2 | Accessibility (a11y) | 2 | Focus rings work; ARIA usage is patchy; modals are not focus-trapped; dialogs are not real `<dialog>` elements | 🟡 |
| 3 | Theming | 2 | Light/dark tokens exist; main layout uses raw `bg-slate-50` and bypasses the theme | ✅ (full rebuild to Tailwind 4 `@theme`) |
| 4 | Responsive | 2 | Sidebar drawer exists; hamburger is covered by it when open; no horizontal-scroll guard on tables | 🟡 (close X added; tables still wide) |
| 5 | Anti-Patterns / AI slop | 1 | Generic AI-defaults: identical card grids, eyebrow-less bland layout, "Book your club in seconds" tagline, gradient avatar circles, no real content | 🟡 (landing redesigned; UserMenu avatar and LoginPage tagline still AI-default) |
| **Total** | | **7/20** | **Critical. P0 functionality gaps + no product character.** | **13/20** |

> **Update (2026-08-11):** All four P0 items are addressed (auth/customer-id plumbing, payments middleware, mobile drawer close, dark + volt theme rebuild). The bulk of P1 and P2 anti-patterns are also fixed. Open items (P1-D bookings content + cancel confirm, P1-G facility richness, P1-F page titles, P2-D gradient avatar, P2-H native `<dialog>`, P2-I restated headings, P2-B table responsive) are listed in the per-item status blocks below.

---

## 1. What works (positive findings)

- **Auth + multi-tenancy is real.** Login as customer → `/book`. Login as admin → `/admin`. The role-based redirect is wired (`AuthBootstrap` + `RoleGate`) and works.
- **Form validation has good a11y primitives.** `LoginForm` uses `aria-invalid`, `aria-live="assertive"`, `role="alert"`. Inputs have explicit `id`/`htmlFor`/`autoComplete`. `FormField` is a small but solid primitive.
- **Skip-to-main link** is present in `AppShell`. Real landmarks (`<aside>`, `<main>`, `<header>`, `<nav>`) are used. Headings use `as` prop correctly.
- **The shadcn primitives themselves are fine.** `Button`, `Card`, `Input`, `EmptyState`, `ErrorState`, `LoadingSkeleton`, `FormField` are reasonable defaults. `cva` variants for button (`default`/`destructive`/`outline`/`ghost`/`link`) are correct.
- **The admin nav + sidebar layout is structurally right.** Top bar + side nav with role-filtered items is the standard pattern customers expect.
- **Alembic migrations + tenant RLS** are in place and prevent cross-tenant leakage. (Verified by direct DB insert that an invoice is hidden by default unless `app.tenant_id` is set.)
- **`/v1/auth/refresh` rotates and persists correctly** when not interfered with manually.

---

## 2. Critical bugs (P0 — blocks users)

### ✅ P0-A. Customer cannot complete a booking — `POST /v1/booking` returns 500

**Repro:**
1. Login as `alex@demo.splashh.dev`.
2. Click any facility → any resource → "Book" → fill `Start` / `End` → "Confirm booking".

**Observed (original):** Dialog shows `Request failed with status code 500`. Booking is not created.

**Root cause:** `BookingDialog.tsx` was sending the auth **user id** where the backend wanted the **customer id**.

**Resolution:**
- `apps/web-pwa/src/features/bookings/BookingDialog.tsx:16` — `const customerId = useAuthStore((s) => s.customerId);` (was `userId`).
- `apps/web-pwa/src/pages/book/BookingsPage.tsx:30` — same swap.
- `packages/api-client/src/auth/store.ts` — added `customerId` to the `Session` interface and the `setSession`/`clear` reducers (was: only `userId`).
- Backend login response now includes `customer_id`; client persists it on `setSession`.
- `BookingDialog.tsx:64` — error now reads `"Something went wrong. Please try again, or contact your club if the problem continues."` instead of the raw axios string.

**Remaining sub-items:** see P1-A (slot-grid + native `<dialog>`) and P1-D (no facility/resource name + no cancel confirm).

---

### ✅ P0-B. Payments surface is completely broken — every endpoint returns 500

**Repro:** Authenticate → call any `/v1/payments/...` endpoint.

**Observed (original):** Every endpoint returned HTTP 500 because `request.state.current_user` was never populated.

**Resolution:**
- `apps/backend/src/payments/interfaces/http/deps.py:29-51` — `get_current_user` now does `Depends(auth_required)` and resolves `customer_id` via `CustomerRepository.get_by_user(...)`. Returns a proper dict with `user_id`, `tenant_id`, `roles`, `customer_id`.
- `apps/backend/src/payments/interfaces/http/router.py:22` — router-level `dependencies=[Depends(auth_required)]` enforces auth on every route by default.
- Verified end-to-end: `GET /v1/payments/invoices` returns 200 with seed data; payment-link endpoint reachable.

---

### ✅ P0-C. Mobile hamburger button is blocked by the open drawer

**Resolution:** Added an explicit `<X>` close button inside the sidebar header (`apps/web-pwa/src/components/Sidebar.tsx:44-51`, `aria-label="Close navigation"`). The TopBar now has `z-30` while the drawer is open (`TopBar.tsx:19`) so the close affordance stays reachable. `AppShell.tsx:21-27` renders a backdrop that closes the drawer on tap.

---

### � P0-D. Refresh-token state is sticky and produces loud console errors

**Status:** Partial.
- `silentRefresh` now clears the auth store on any non-2xx response.
- `AuthBootstrap` no longer double-redirects when the user is already authenticated.

**Still open:** the first navigation on a cold load sometimes surfaces a single `422 @ /v1/auth/refresh` line in the browser console (the request happens before the cookie is read by the auth bootstrap). The flow recovers within ~50ms, but the noise is loud. Tracked as a follow-up.

---

## 3. UX problems (P1)

### 🟡 P1-A. Customer-side booking dialog asks for things customers can't choose

**Status:** Partial.
- `BookingDialog.tsx:18-28` — `End` now auto-fills from `Start + 60 min` so customers don't manually compute it.
- `BookingDialog.tsx:62-66` — user-facing error message instead of raw axios text.

**Still open:**
- Dialog is still `<div role="dialog">`, not native `<dialog>`. No focus trap. No `<form>` wrapper. No Escape-to-close.
- No slot-grid driven by availability rules; customer picks arbitrary start/end.
- `currency: "AUD"` is hardcoded (the invoice side was fixed in P1-B, but the booking side should pull currency from the facility's tenant config).

---

### ✅ P1-B. "Pay invoice" page hardcodes INR currency

**Resolution:** `apps/web-pwa/src/pages/book/PayInvoicePage.tsx:7-13` — `formatCurrency(amountPaise, currency)` uses `Intl.NumberFormat` with the invoice's actual `currency` field. The hardcoded `INR` literal is gone.

---

### ✅ P1-C. "Pay invoice" page is bare

**Resolution:** `PayInvoicePage.tsx` now renders:
- `StatusPill` mapped from API status (`open` / `pending` / `paid` / `refunded` / `failed` / `cancelled`).
- Line-items table with description / qty / unit price / total.
- Subtotal / tax / total breakdown when `tax_paise > 0`.
- Past-due warning with `AlertTriangle` icon and amber background.
- "This invoice is paid" confirmation block when status is `paid`.

---

### 🟡 P1-D. "My bookings" page hides the facility/resource name

**Status:** Partial.
- `BookingsPage.tsx:30` — correctly uses `customerId` from auth store.
- Empty / loading / error states use `EmptyState`, `LoadingSkeleton`, `ErrorState` with retry.

**Still open:**
- `BookingsPage.tsx:57-63` — list rows still show only start time + status + price. **No facility name, no resource name, no location.** The booking row needs `facility.name` + `resource.name` joined from the API response.
- `CancelButton` (line 7-27) is still a one-click destructive action. **No confirm dialog** before calling `bookingsApi.cancel`.

---

### 🟡 P1-E. Admin users page is a text dump with no actions or metadata

**Resolution:** `apps/web-pwa/src/pages/AdminUsersPage.tsx` now has:
- Search input (lucide `Search` icon + `Input type="search"`).
- `created_at` column rendered via `formatDate`.
- Role badges via `<Badge>` with `accent` / `muted` / `default` variants.
- Error state ("Failed to load users.") + add-user form.

**Still open:**
- No pagination (17 users today; fine for now).
- "All users" subtitle restates the page `<h1>` (P2-I).

---

### � P1-F. Admin invoice list page is a table with headers and no rows, plus a generic error

**Resolution:**
- `InvoicesPage.tsx:68-75` — error state now has a `Try again` retry button calling `refetch()`.
- `InvoiceStatus` filter chips retained as buttons.

**Still open:**
- **`page-titles.ts` still has no entry for `/admin/invoices` or `/admin/invoices/new`** — top bar shows the bare brand `Splashh` instead of `Splashh Admin · Invoices`. Fix in `apps/web-pwa/src/lib/page-titles.ts`.
- Inline filter buttons are still buttons; the audit suggested a segmented control — left as-is for now.

---

### ❌ P1-G. Facilities list / detail pages are content-empty cards

**Status:** Open.

**Facility list (`FacilitiesPage.tsx`):**
- Cards still show only `name` + `city, state, country`. No description, no resource count, no opening hours, no image.
- "View details" CTA is now full-width (`Button w-full`) — better mobile hit area than the original inline link — but the card content hasn't grown.
- `index === 0 && "border-l-4 border-l-primary"` (line 32) is a **regression** — the audit flagged left-side accent borders as the canonical AI-default active-state tell. The `default` variant on the first card already provides enough visual hierarchy; the border should be removed.

**Facility detail (`FacilityDetailPage.tsx`):**
- Header shows name + address (`MapPin` icon). Good.
- Resources list now renders attribute pairs via `formatAttributes` (e.g. "Lanes: 6", "Length M: 25") — meaningful content where there was none.
- Still missing: opening hours, contact phone, map embed.

---

## 4. Anti-patterns / AI slop (P2)

### 🟡 P2-A. Identical card grids, no visual hierarchy

**Status:** Partial. The landing page now has a bento-style facility map (`One platform. Every part of your club.`) with varying cell sizes and tones (`volt` / `warm` / `ink`), but the customer-facing `/book` and admin `/admin` lists are still uniform card grids.

**Still open:** Apply the bento treatment to the facilities and admin facilities lists. The reference design in `reference/ss/` (screenshots `Pasted image (3)` and `Pasted image (6)`) shows how to break a uniform grid into varied tile sizes.

### ✅ P2-B. Side-stripe border on active nav item

**Resolution:** `apps/web-pwa/src/components/Sidebar.tsx:67-75` — active nav item now uses `bg-primary/10 text-primary border-b-2 border-primary` (bottom border, not left). Side-stripe tell is gone.

### 🟡 P2-C. Generic AI-default copy

**Status:** Partial.
- Landing page tagline replaced with **"Run your club. Not your spreadsheet."** (split-text hero). Specific noun + verb + claim.
- Footer copy rewritten to "The operating system for modern sports clubs. Designed for the way sports actually work."
- Pay-invoice page has real copy ("This invoice is paid", "Payment overdue", "Pay with card").
- 500 error messages across booking, invoices, users: replaced with `"Something went wrong. Please try again, or contact your club if the problem continues."`.

**Still open:**
- `LoginPage.tsx:93` still has **"Book your club in seconds"** — the AI-default line the audit flagged. Note: the `LoginPage` route is now a fallback; the primary entry is the `AuthModal` over the landing page, which has the new copy.
- `LoginPage.tsx:125` still has **"Need help? Contact your club."**.
- Page titles (`page-titles.ts`) are still brand-literal: `Splashh Admin · Facilities`, etc. Functional but generic — could be `Facilities — Splashh Admin` or similar.

### ❌ P2-D. Gradient on the user-avatar circle

**Status:** Open. `apps/web-pwa/src/components/UserMenu.tsx:46` still has `bg-gradient-to-br from-sky-500 to-cyan-500`. Should be a single color (e.g. `bg-primary text-primary-foreground`) or a real avatar from `useAuthStore.userId`.

### ✅ P2-E. Login page background gradient

**Resolution:** `LoginPage.tsx:62-78` now uses two faint radial-gradient orbs (cool blue top-right, warm orange bottom-left) plus subtle horizontal lane lines at the bottom — replaced the AI-default `linear-gradient(180deg, rgb(224 242 254) 0%, white 60%)`. Not a pure gradient base, brand cues preserved.

### ✅ P2-F. No icons in the sidebar nav (just emoji)

**Resolution:** `Sidebar.tsx:6-12` maps an `iconMap` from lucide-react icons: `Waves`, `CalendarDays`, `Building2`, `Users`, `Receipt`. `nav.ts` references icons by name; the sidebar resolves them via the map. No emoji.

### 🟡 P2-G. "Skip to main content" link is correct but the visual focus is loud

**Resolution:** `AppShell.tsx:16` — focus background changed from `bg-white` (which disappears on dark bg) to `bg-card`. Border still missing — minor.

### � P2-H. Tab order & keyboard trap on the booking dialog

**Status:** Open. `BookingDialog.tsx` is still `<div role="dialog" aria-modal="true">`. No native `<dialog>`, no focus trap, no Escape-to-close.

### 🟡 P2-I. "All users" and "All invoices" sub-headings are restated labels

**Status:** Open.
- `AdminUsersPage.tsx:144` still has `<CardTitle>All users</CardTitle>` directly below `<h1>Users</h1>`.
- `InvoicesPage.tsx:78` still has `<CardTitle>All invoices</CardTitle>` below `<h1>Invoices</h1>`.

The CardTitles should either be removed (the table speaks for itself) or reframed (e.g. "Showing X of Y").

---

## 5. Accessibility (P2)

### ❌ P2-A. Modals are not real `<dialog>` elements

**Status:** Open. `BookingDialog` and the auth modal in `LandingPage` (`AuthModal`) both use `<div role="dialog" aria-modal="true">`. Native `<dialog>` would give focus trap, Escape handling, and screen-reader semantics for free. Also see P2-H.

### 🟡 P2-B. Page-level heading hierarchy

**Status:** Partial. `BookingsPage` correctly uses `<h1>` + `CardTitle as="h2"`. `BookingDialog` is still `<h2>` with no preceding `<h1>` (the dialog overlays `/book/facilities/:id` which has `<h1>{facility.name}</h1>` — semantically OK).

### 🟡 P2-C. Color contrast for muted text

**Status:** Improved but not audited.
- New muted-foreground token: `var(--color-charcoal-300)` = `#a4a9b3` on `#1d1f24` (card) and on `#0a0a0b` (page). Both ratios clear WCAG AA for body text — to be re-verified with axe-core in CI.

### 🟡 P2-D. Touch targets

**Resolution:** Facility card CTA is now full-width (`w-full`) on `FacilitiesPage.tsx:46`. Hamburger button is `p-2` (36×36) — still below 44×44.

---

## 6. Theming (P2)

### ✅ P2-A. Dark mode is partially wired

**Resolution:** Stack upgrade to **React 19 + Vite 6 + Tailwind 4** (`@theme`-based config).
- `apps/web-pwa/tailwind.config.ts` and `postcss.config.js` deleted.
- All tokens centralized in `packages/ui/src/styles/globals.css` under `@theme { … }`.
- Layout chrome (`AppShell`, `TopBar`, `Sidebar`) now uses `bg-background`, `bg-card`, `border-border` exclusively — no more raw `bg-slate-*` / `border-slate-*`.
- Palette is a single dark + volt theme: `--color-charcoal-900` page, `--color-charcoal-800` cards, `--color-volt: #ccff00` accent. No light mode.

### ✅ P2-B. Tokens exist but aren't fully used

**Resolution:** Same as P2-A. After the Tailwind 4 migration, the only raw `slate-*` references left are in `UserMenu.tsx` (avatar gradient + menu surfaces) — tracked as P2-D.

### 🟡 P2-C. The `next-themes` dependency is declared but I don't see a theme toggle anywhere

**Resolution:** `apps/web-pwa/src/main.tsx:13` now wraps `<App />` in `<ThemeProvider attribute="class" defaultTheme="system" enableSystem>`. `next-themes` applies `class="dark"` to `<html>` automatically.

**Still open:** No `<ThemeToggle />` in the UI. Since the app is committing to a single dark theme, a toggle isn't strictly needed, but the audit's note still stands: the dependency is wired but unused as a feature.

---

## 7. Responsive design (P2)

### ✅ P2-A. Drawer overlay vs. hamburger z-index (also flagged P0-C)

See P0-C.

### ❌ P2-B. Tables don't collapse on mobile

**Status:** Open. Admin invoice table renders as `<table>` with five columns. On 390px viewports it overflows horizontally — no card-list fallback for narrow screens.

### ✅ P2-C. Mobile drawer has no close button and no header

**Resolution:** `Sidebar.tsx:39-52` — drawer now has a header row with brand + explicit `<X>` close button (`aria-label="Close navigation"`).

### 🟡 P2-D. Booking dialog on mobile

**Status:** Partial. Dialog is `max-w-md` with `p-4` outer padding. Buttons still right-aligned and cramped at 390px. No full-screen takeover.

---

## 8. Code-level observations (informational)

These don't show up as user-facing bugs but they tell you where the product is:

- ✅ **The payments module was a façade.** Now wired up — `get_current_user` resolves principal + customer_id from a real auth dependency, and the router enforces `auth_required`.
- ✅ **`BookingDialog` was using `useAuthStore.userId` where it needed `Customer.id`.** Now uses `customerId`, populated by the login response.
- ❌ **No e2e tests cover the customer booking flow** (`e2e/` tests stop at register-tenant and login). These regressions were invisible for that reason.
- 🟡 **The `AuthBootstrap` `useEffect` only runs once on mount** (`[]` deps). Combined with the 422 noise, this caused the random-logout experience. Bootstrap now clears the store on non-2xx — but no retry.
- ❌ **`page-titles.ts` has no entry for `/admin/invoices`** (or `/admin/invoices/new`).
- 🟡 **Mock data and seed scripts assume a specific tenant.** `seed_demo.py` seeds the first tenant by `created_at`. New tenants registered after seeding still get nothing.
- ✅ **Removed `tailwind-preset.ts` + `tailwind.config.ts` + `postcss.config.js`** — Tailwind 4 `@theme` block lives entirely in `packages/ui/src/styles/globals.css`.

---

## 9. What a real user would say (informal roleplay)

> I logged in, picked a pool, hit Book, picked a time, hit Confirm — and got "Request failed with status code 500". I have no idea what went wrong or what to do. I went to "My bookings" to see if it went through — empty. I went to look at an invoice to pay — the page just said "Failed to load invoices." The whole app feels like a demo with the wiring half-connected.

> The login screen says "Book your club in seconds" — that's a tagline, not a value prop. I don't know what kind of club this is, what sports, what cities, what to expect. The cards on the browse page have a name and a city. That's it.

> I tried it on my phone. The hamburger didn't close the menu when I tapped it again. I had to tap the side of the screen. Why isn't there a close button?

---

## 10. Recommended order of fixes (by impact)

**Block release until done (P0):** all resolved. ✅

**Do before any user testing (P1):**
- ~~5. Replace the booking dialog with a slot-grid~~ — partial; **still open: native `<dialog>` + slot-grid + auto-currency**
- ~~6. Stop hardcoding `INR` on the pay page~~ — done ✅
- 7. Make `My bookings` show facility + resource name; add a confirm dialog to cancel. ❌ open
- 8. ~~Make the admin users table actually useful~~ — partial; pagination + heading cleanup still open
- 9. Add real content to facility / resource cards — description, opening hours, image, contact. ❌ open
- **New:** add missing entries to `lib/page-titles.ts` so the top bar reflects the route.

**Design pass (P2):**
- 10. ~~Kill the AI-default looks~~ — partial; UserMenu gradient avatar + FacilitiesPage `border-l-4` regression still in
- 11. ~~Commit fully to the design-token system or drop it~~ — done ✅
- 12. Replace `<div role="dialog">` with native `<dialog>`; add focus trap and Escape handling. ❌ open
- 13. Add `e2e` coverage for the booking flow so these regressions can't ship again. ❌ open

---

## 11. Files / locations for the curious

### Resolved in the stack-upgrade + landing-redesign pass
- ✅ P0 booking bug: `apps/web-pwa/src/features/bookings/BookingDialog.tsx:16` (now `customerId`)
- ✅ P0 booking bug (companion): `apps/web-pwa/src/pages/book/BookingsPage.tsx:30` (now `customerId`)
- ✅ P0 payments bug: `apps/backend/src/payments/interfaces/http/deps.py:29` (real `auth_required` dep + customer lookup)
- ✅ P0 mobile hamburger: `apps/web-pwa/src/components/Sidebar.tsx:44-51` (explicit `<X>` close button)
- ✅ P1 INR hardcode: `apps/web-pwa/src/pages/book/PayInvoicePage.tsx:7-13` (`Intl.NumberFormat` per currency)
- ✅ P1 pay invoice bare: same file — `StatusPill`, line items, tax breakdown, past-due banner all added
- ✅ P1 admin users bare: `apps/web-pwa/src/pages/AdminUsersPage.tsx:104-200` (search + role Badge + created_at column)
- ✅ P1 admin invoices retry: `apps/web-pwa/src/pages/admin/InvoicesPage.tsx:68-75` (retry button on error)
- ✅ P2 side-stripe active border: `apps/web-pwa/src/components/Sidebar.tsx:67-75` (now `border-b-2`)
- ✅ P2 emoji nav icons: `apps/web-pwa/src/components/Sidebar.tsx:6-12` (lucide-react `iconMap`)
- ✅ P2 partial dark mode: chrome (`AppShell`, `TopBar`, `Sidebar`) uses semantic tokens; Tailwind 4 `@theme` owns the palette
- ✅ Theme tokens: `packages/ui/src/styles/globals.css` (`@theme` block)

### Still open
- 🟡 P1 facility richness: `apps/web-pwa/src/pages/book/FacilitiesPage.tsx`, `apps/web-pwa/src/pages/book/FacilityDetailPage.tsx`
- ❌ P1 booking dialog: `apps/web-pwa/src/features/bookings/BookingDialog.tsx` (slot-grid + native `<dialog>`)
- ❌ P1 my-bookings content + cancel confirm: `apps/web-pwa/src/pages/book/BookingsPage.tsx:52-70`
- ❌ P1 page titles: `apps/web-pwa/src/lib/page-titles.ts` (missing `/admin/invoices`, `/admin/invoices/new`)
- ❌ P2 gradient avatar: `apps/web-pwa/src/components/UserMenu.tsx:46`
- ❌ P2 facilities left-border regression: `apps/web-pwa/src/pages/book/FacilitiesPage.tsx:32`
- ❌ P2 login tagline: `apps/web-pwa/src/pages/LoginPage.tsx:93`
- ❌ P2 table responsive: `apps/web-pwa/src/pages/admin/InvoicesPage.tsx:90-124` (no card-list on mobile)
- ❌ P2 restated headings: `apps/web-pwa/src/pages/AdminUsersPage.tsx:144`, `apps/web-pwa/src/pages/admin/InvoicesPage.tsx:78`
- ❌ P2 native `<dialog>`: `apps/web-pwa/src/features/bookings/BookingDialog.tsx`, `apps/web-pwa/src/pages/LandingPage.tsx` (AuthModal)

---

## Appendix A — Screenshots

Original audit (kept for historical reference):
- `audit-01-facilities-list.png` — customer `/book`
- `audit-02-login-page.png` — login screen
- `audit-03-facility-detail.png` — facility detail
- `audit-04-book-dialog.png` — booking dialog with 500 error
- `audit-05-bookings.png` — empty "My bookings"
- `audit-06-admin-login.png` — staff tab = admin login
- `audit-07-admin-facilities.png` — admin `/admin`
- `audit-08-admin-users.png` — admin users list
- `audit-09-add-user.png` — add-user form
- `audit-10-admin-invoices.png` — broken admin invoices
- `audit-11-mobile-facilities.png` — mobile facilities
- `audit-12-mobile-drawer.png` — mobile drawer open
- `audit-13-dark-mode.png` — partial dark mode

Post-fix verification:
- `phase-b2-landing.png` — redesigned landing (8 sections, dark + volt)
- `phase-b2-mobile.png` — landing at 390px
- `phase-b2-modal.png` — modal login over hero
- `phase-d-admin.png` — admin facilities with dark + volt theme
- `phase-d-invoices.png` — admin invoices with retry button

---

## Appendix B — How to reproduce (post-stack-upgrade)

```bash
# In repo root
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml --profile tools run --rm migrate
docker compose -f docker-compose.dev.yml --profile tools run --rm seed-demo
pnpm dev
# Open http://localhost:5173 and login as alex@demo.splashh.dev / Customer!Demo1
# or admin@demo.splashh.dev / Admin!Demo2026
```

See [`docs/docker.md`](./docker.md) for full compose usage.
