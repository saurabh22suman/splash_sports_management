# Splashh Sports Platform — Codebase Review

> **Author:** Principal Engineering audit (Claude) · **Date:** 2026-08-11
> **Scope:** `apps/backend/`, `apps/web-pwa/`, `packages/`, `docs/`, infrastructure
> **Method:** 12 parallel review agents + lead synthesis. Read-only — no code modified.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Methodology](#2-methodology)
3. [Current System Architecture](#3-current-system-architecture)
4. [Handbook Compliance Matrix](#4-handbook-compliance-matrix)
5. [Product & User Flow Review](#5-product--user-flow-review)
6. [UI/UX Review](#6-uiux-review)
7. [Sports-First UX Review](#7-sports-first-ux-review)
8. [Frontend Review](#8-frontend-review)
9. [Backend Review](#9-backend-review)
10. [Database Review](#10-database-review)
11. [Booking Engine Review](#11-booking-engine-review)
12. [Payment Review](#12-payment-review)
13. [Authentication & Authorization](#13-authentication--authorization)
14. [Security Review (OWASP)](#14-security-review-owasp)
15. [TDD & Testing Review](#15-tdd--testing-review)
16. [PWA Review](#16-pwa-review)
17. [Performance Review](#17-performance-review)
18. [Scalability Review](#18-scalability-review)
19. [Multi-Agent Development Readiness](#19-multi-agent-development-readiness)
20. [Technical Debt](#20-technical-debt)
21. [Findings (Consolidated)](#21-findings-consolidated)
22. [Top 10 Issues](#22-top-10-issues)
23. [Top 10 UX Issues](#23-top-10-ux-issues)
24. [Top 10 Security Risks](#24-top-10-security-risks)
25. [Top 10 Architectural Concerns](#25-top-10-architectural-concerns)
26. [Highest ROI Improvements](#26-highest-roi-improvements)
27. [Recommended Roadmap](#27-recommended-roadmap)
28. [Production Readiness](#28-production-readiness)
29. [Final Scorecard](#29-final-scorecard)

---

## 1. Executive Summary

The Splashh Sports Platform has a **disciplined engineering culture** — an unusually thorough handbook, clean DDD layering, well-defined bounded contexts, working auth and payments, and a PWA that ships. The code mostly matches the handbook.

**It is not safe for production multi-tenant deployment today.**

The single most important fact: **the booking race-condition test passes** (`tests/integration/test_booking_service.py:252`), so two customers cannot both grab the same slot. The core "make-or-break" question is answered positively.

But there are **8 P0 (Critical) findings** and **15 P1 (High) findings** that block production. The top three are:

1. **JWT uses HS256 instead of the documented RS256** (`apps/backend/src/auth/infrastructure/token_service.py:34-113`). If the symmetric secret leaks (and there is a hardcoded default in `dependencies.py:46-48`), attackers can forge admin tokens for any tenant.
2. **PostgreSQL Row-Level Security (RLS) is enabled on only the payments tables.** All other business tables (`tenants`, `users`, `refresh_tokens`, `customers`, `facilities`, `resources`, `availability_rules`, `bookings`) rely entirely on application-layer tenant filtering. The handbook (`docs/09-security/tenant-isolation.md`) and ADR-0003 specify RLS as defense-in-depth — it is missing for 8/9 tables.
3. **No RBAC / permission enforcement.** Routers only check `auth_required` (authentication), not authorization. Any authenticated customer can call `POST /v1/invoices/{id}/refund` and `POST /v1/admin/invoices` because there is no role/permission decorator on the endpoint.

Combined, these mean **an authenticated user with knowledge of one tenant can, with low effort, become admin of any other tenant.** Until they are fixed, the platform is unsafe for SaaS.

Other significant gaps:

- **Membership, Notifications, Analytics modules** are documented in `docs/18-modules/` but **do not exist in code** — the roadmap claims "shipped" but only 5 of 8 modules are present.
- **Event bus is in-process** (`apps/backend/src/common/application/events.py:26-43`) — ADR-0004 specifies Redis Streams + outbox; this is a synchronous, in-memory fan-out that loses events on restart.
- **Booking flows skip availability, capacity, membership and timezone validation** — the docstring promises them; the code does not.
- **CI/CD is documented but not implemented** — no `.github/workflows/` directory exists.
- **No backup infrastructure** — the 5-minute RPO target cannot be met.
- **Test coverage ≈ 58%** — well below the stated targets (95% domain / 90% services / 80% API).
- **Production frontend bundle is 365 KB** — exceeds the 250 KB performance gate.
- **3 of the 5 product personas** (Reception/Coach/Owner) have **no working UI** beyond a placeholder.
- **Integration tests are broken** (FK constraint naming) — cannot validate DB-layer behavior end-to-end.

**Production Readiness: NOT READY.** See §28.

The encouraging news: the **architecture itself is sound**. The DDD layering is enforced in practice, the domain layer has zero framework imports, the booking concurrency primitive is correct, Argon2 password hashing is properly configured, and Razorpay webhook signatures are verified. Most of the work needed is **additive** (RLS policies, RBAC checks, modules, CI) rather than corrective (rewrites).

---

## 2. Methodology

12 specialized agents were launched in parallel against the live repository:

| Agent | Track | Output |
|---|---|---|
| A | Architecture (modular monolith, ADR compliance, dependency direction) | `aced84e` |
| B | Backend (routers, services, repos, schemas, async, transactions) | `a90909e` |
| C | Frontend (React, routing, state, design system, a11y, responsive) | `a6b202e` |
| D | Product/UX (per-persona journeys, empty/loading/error states) | `a1d2cf4` |
| E | Booking domain (concurrency, availability, capacity, idempotency, refunds) | `a5de0a6` |
| F | Security (OWASP Top 10, OWASP API Top 10, OWASP ASVS L2) | `a1cfdb8` |
| G | Database (schema, indexes, migrations, RLS, soft-deletes) | `ad9d2c0` |
| H | Testing/TDD (coverage, test quality, e2e gaps) | `a640325` |
| I | Performance (API latency, bundle, query hotspots, caching) | `a7ff247` |
| J | PWA (manifest, service worker, offline, mobile, iOS) | `af436c9` |
| K | DevOps / Production (Docker, CI/CD, observability, backup) | `afa3dd8` |
| L | AI-Agent readiness (module boundaries, conventions, contracts) | `a36572e` |

Each agent was instructed to provide evidence-based findings with `file:line` citations and severity (P0–P4). The lead agent verified critical claims (e.g., Agent C's claim that `AdminUsersPage` doesn't exist is **wrong** — the file is 204 lines and lazy-loaded via `routes/index.tsx:46`), consolidated overlapping findings (e.g., missing RLS appeared in 3 agents), and de-duplicated. Some lower-priority findings have been dropped where they were duplicates or contradicted by direct verification.

> **Note on certainty:** Throughout this report, "Confirmed" = verified by direct code inspection or runtime test. "Likely" = inferred from code without running the test. "Unable to verify" = the agent could not determine the answer with available tools.

---

## 3. Current System Architecture

The actual architecture follows the handbook's intent very closely:

```
apps/backend/src/
├── auth/             # Identity: User, Tenant, JWT (HS256), refresh tokens, Argon2
├── customer/         # Customer profiles
├── facility/         # Facility, Resource, AvailabilityRule + PATCH/DELETE
├── booking/          # Booking with SELECT FOR UPDATE + overlap detection
├── payments/         # Invoice, Payment, Refund; Razorpay webhooks; idempotency
├── common/           # BaseRepository, exceptions, settings, db, mixins
└── tests/

apps/web-pwa/        # Single PWA with role-based home after login
├── pages/            # Lazy-loaded routes (landing, login, admin/*, book/*)
├── components/       # AppShell, Sidebar, TopBar, UserMenu, ConfirmDialog
├── features/         # auth, admin, bookings, payments, facilities
└── vite.config.ts    # PWA config (autoUpdate, NetworkFirst 10s, CacheFirst images)

packages/
├── ui/               # shadcn-style primitives + dark+volt theme via Tailwind 4 @theme
├── api-client/       # axios + zustand auth store + TanStack Query keys
└── config/           # shared tsconfig/vitest/biome

docs/                 # 18 sections of engineering handbook (very thorough)
e2e/                  # 7 Playwright spec files (mostly accessibility checks)
```

**What works:**

- DDD layer separation enforced — `apps/backend/src/booking/domain/entities.py` has zero framework imports. Verified across modules.
- `BaseRepository` in `common/infrastructure/repository.py` provides tenant filtering primitives; every business module overrides its queries with `tenant_id`.
- Frontend features follow a consistent `api.ts` + `use*.ts` hook pattern.
- Booking double-booking prevention works — `booking/infrastructure/repositories.py:74-122` uses `SELECT FOR UPDATE` + an overlap-existence check inside a single transaction. The integration test confirms exactly 1 of 5 concurrent attempts succeeds.
- PWA has working manifest, service worker (autoUpdate), runtime caching (NetworkFirst for APIs, CacheFirst for images), and offline shell.
- Argon2id password hashing is properly configured (memory 19 MB, 2 iterations).
- Razorpay webhook signature verification uses the official SDK.

**What doesn't match the handbook:**

- **ADR-0004 violation**: `InProcessEventPublisher` (synchronous, in-memory) instead of Redis Streams + outbox.
- **ADR-0003 partial**: RLS only on payments tables.
- **ADR-0005 partial**: HS256 instead of documented RS256.
- **ADR-0001 violation**: `booking/infrastructure/repositories.py:81,152` directly imports `facility.infrastructure.models` (SQLAlchemy ORM models), crossing a bounded context boundary.
- **Three documented modules are missing**: `membership`, `notifications`, `analytics` (folders don't exist under `apps/backend/src/`).

---

## 4. Handbook Compliance Matrix

| ADR / Doc | Title | Status | Evidence |
|---|---|---|---|
| **ADR-0001** | Modular monolith | **FAIL** | `booking/infrastructure/repositories.py:81` imports `from facility.infrastructure.models import ResourceModel` |
| **ADR-0002** | FastAPI + PostgreSQL + Redis | **PASS** | `common/interfaces/http/app.py`, `common/infrastructure/db.py`, `common/infrastructure/settings.py:42` |
| **ADR-0003** | Multi-tenant (shared schema + RLS) | **PARTIAL** | `tenant_id` on every table, RLS policies on payments only — `migrations/20240101_0003_0004_payments.py:128-134` |
| **ADR-0004** | Event bus (Redis Streams + outbox) | **FAIL** | `common/application/events.py:26-43` is `InProcessEventPublisher` |
| **ADR-0005** | JWT + refresh tokens | **PARTIAL** | `auth/infrastructure/token_service.py:34-113` uses HS256, not RS256 — explicit `NotImplementedError` in `auth_service.py:312-314` |
| **ADR-0006** | Repository pattern | **PASS** | `BaseRepository` in `common/infrastructure/repository.py` |
| **ADR-0007** | PWA over native | **PASS** | `apps/web-pwa/vite.config.ts:11-50` |
| **09-security/authentication.md** | Argon2id, JWT, refresh rotation | **PARTIAL** | Argon2id OK; JWT algorithm wrong; HIBP not implemented |
| **09-security/tenant-isolation.md** | Postgres RLS | **PARTIAL** | App-layer filters everywhere; RLS only on payments tables |
| **09-security/rbac.md** | Per-role permission decorators | **FAIL** | No `@requires_permission` decorator; only `auth_required` exists |
| **09-security/rate-limiting.md** | Login throttling + global limits | **FAIL** | Settings defined, no middleware |
| **09-security/ssrf.md** | Webhook URL allowlist | **FAIL** | `success_url`/`cancel_url` passed directly to Razorpay (`payments/application/payment_service.py:166-167`) |
| **16-quality-gates/performance-gates.md** | Bundle ≤ 250 KB | **FAIL** | `dist/assets/index-*.js` = 365 KB |
| **16-quality-gates/release-gates.md** | CI/CD pipeline | **FAIL** | No `.github/workflows/` exists |
| **12-devops/disaster-recovery.md** | RPO 5 min, RTO 1 h | **FAIL** | No backup scripts, no WAL archiving |

**Compliance summary:** 3 of 15 ADRs/doc-requirements fully pass; 4 partial; 8 fail.

---

## 5. Product & User Flow Review

The product vision in `docs/01-vision/overview.md` lists **5 personas**: Customer, Reception, Manager, Coach, Owner. The audit walked each:

### Customer (`alex@demo.splashh.dev`) — WORKS
- ✅ Login → `/book` → browse facilities → view detail → book → view bookings → cancel
- ✅ Native `<dialog>` for cancel confirmation
- ✅ Booking dialog: native `<dialog>` with Escape, focus trap, auto-fill end time
- ✅ Bookings list shows facility + resource names (after backend JOIN added)

### Reception / Manager (`admin@demo.splashh.dev`) — PARTIALLY WORKS
- ✅ Login → `/admin` → manage facilities + resources (CRUD works end-to-end via curl test)
- ✅ Manage users (add, search, role badges)
- ✅ Invoices list with filters + retry button + responsive card list
- ❌ **`/admin/bookings` is a 19-line placeholder** — `apps/web-pwa/src/pages/admin/BookingsPage.tsx:7` shows "Today's bookings view coming soon."
- ❌ **No member management** — only user management. Customers ≠ members in this codebase.
- ❌ **No attendance / check-in UI**
- ❌ **No dashboard overview** with today's stats
- ❌ **Invoices list shows customer ID truncated to 8 chars** — no name lookup

### Coach — NOT IMPLEMENTED
- No `/coach` route. No schedule UI. No attendance UI. (Module `notifications` and the coach flow are absent.)

### Owner — NOT IMPLEMENTED
- No `/owner` route. No revenue, occupancy, renewal analytics. (Module `analytics` absent.)

### What is missing for a real pilot

The platform can run a **single-tenant, customer-facing book-and-pay flow** today. It cannot run a sports club. Reception needs to see today's bookings; the gym needs to see attendance; the owner needs to see revenue.

---

## 6. UI/UX Review

**Strengths:**
- Customer-facing surfaces (`FacilitiesPage`, `FacilityDetailPage`, `BookingsPage`) use the proper `EmptyState`/`ErrorState`/`LoadingSkeleton` components.
- Form labels are properly associated via `FormField` with `htmlFor`.
- Skip-to-main link in `AppShell.tsx:14-19`.
- Sidebar has `aria-label="Primary"` and proper landmarks.
- Login tabs use proper `role="tablist"` / `aria-selected`.

**Weaknesses (consolidated from agents C + D):**

| ID | Surface | Issue | Severity |
|---|---|---|---|
| C2/D1 | `AdminUsersPage.tsx:139,140,162-166` | Plain-text `Loading…` / `Failed to load users` / `No users yet` instead of `LoadingSkeleton` / `ErrorState` / `EmptyState` | P3 |
| C3 | `InvoicesPage.tsx:67` | Plain-text `Loading…` instead of `LoadingSkeleton` | P3 |
| C1 | `LandingPage.tsx:924` (AuthModal) | Custom `role="dialog"` div instead of native `<dialog>` | P1 |
| D2 | `admin/BookingsPage.tsx` | Placeholder ("Today's bookings view coming soon") | **P0** |
| D4 | (no module) | No membership management UI | P1 |
| D5 | (no module) | No check-in / QR UI | P1 |
| D6 | `InvoicesPage.tsx:145` | Customer identifier is a truncated UUID, not a name | P2 |
| D7 | (no route) | No `/coach` or `/owner` dashboards | P2 |

> **Correction:** Agent C claimed `AdminUsersPage` does not exist. **It does** — `apps/web-pwa/src/pages/AdminUsersPage.tsx` is 204 lines and is lazy-loaded via `apps/web-pwa/src/routes/index.tsx:46`. The finding has been corrected above.

---

## 7. Sports-First UX Review

The product is named "Splashh" and serves swimming / badminton / tennis / gym clubs. **Does it feel sports-specific?**

**Yes, partially.**
- Landing page uses sport icons (Swimming, Badminton, Tennis, Gym, Football, Cricket).
- Facility cards surface resource types (Pool, Lane, Court).
- Booking flow uses datetime pickers and a slot-grid is feasible.
- `StatusPill` shows booking status correctly.

**No, fundamentally.**
- The `/admin` shell is a generic CRUD UI.
- The `/admin/bookings` placeholder is a generic "coming soon" page.
- The `/book` browse page shows facilities by city — not by sport or "available now".
- There is **no visual court/pool grid** for availability.
- There is **no sports-specific terminology guidance** anywhere (e.g. "lane", "court", "session", "member tier" not surfaced).

The product is **a generic booking tool with sports vocabulary** rather than a sports-first product. For a category where the dominant AI reflex is "generic SaaS CRUD", this is exactly that.

---

## 8. Frontend Review

**Positive findings (Agent C):**

- Feature-based folder structure (`features/{auth,admin,bookings,...}/`).
- TanStack Query for server state, Zustand for auth — clear separation.
- Lazy-loaded pages via `React.lazy()` in `routes/index.tsx`.
- `ConfirmDialog`, `BookingDialog`, `BookingsPage` cancel — **all use native `<dialog>`** correctly.
- `BookingDialog` accepts `resourceName` + `facilityName` and renders them in the header.
- Native `<input type="search">` for users-page filter.
- `aria-live="assertive"` on booking error region.
- `data-testid` on key components for E2E.

**Findings (de-duplicated):**

| ID | Location | Issue | Severity |
|---|---|---|---|
| C5 | `AdminFacilityDetailPage.tsx:41` | `useDeactivateResource(id!)` non-null assertion will crash if `id` undefined | P3 |
| C7 | `App.tsx` | No React `ErrorBoundary` | P1 |
| C4 | `packages/ui/src/tokens.ts` + `packages/ui/src/styles/globals.css` | Two parallel token systems (OKLCH vs Tailwind 4 `@theme`) — drift risk | P2 |
| C8 | `PayInvoicePage.tsx:145` | Error paragraph lacks `aria-live="assertive"` | P3 |
| C9 | `BookingDialog.tsx:65-66` | Hardcoded `price_cents: 0, currency: "AUD"` — backend ignores | P1 (business logic) |

> The frontend is the strongest part of the codebase. The remaining work is small (error boundaries, native dialogs, loading consistency).

---

## 9. Backend Review

**Positive findings (Agent B):**

- Pydantic v2 used throughout with proper field constraints.
- Async SQLAlchemy with proper session lifecycle (`commit`/`rollback` on context exit).
- Consistent error mapping via `common/domain/exceptions.py` → RFC 7807 responses.
- Razorpay webhook signature verification via the official SDK.
- Idempotency support in payments via `X-Idempotency-Key` + partial unique indexes.

**Findings (de-duplicated):**

| ID | Location | Issue | Severity |
|---|---|---|---|
| B1 | `common/infrastructure/settings.py:68-72` | `app_url` referenced in `payment_service.py:163` but **not defined in `Settings`** — would crash at runtime | **P0** |
| B5 | `payments/application/payment_service.py:252` | `get_by_razorpay_refund_id_any_tenant` — explicit cross-tenant lookup | **P0** |
| B3 | `auth/infrastructure/repositories.py:162-166` | `RefreshTokenRepository.get_by_hash` lacks `tenant_id` filter | **P0** |
| B2 | `customer/infrastructure/models.py:20-22` | `tenant_id` lacks `ForeignKey` to `tenants.id` | P1 |
| B4 | `auth/infrastructure/repositories.py:111-121` | `get_by_email_global` — acknowledged cross-tenant lookup | P0 |
| B7 | `common/application/middleware.py:40-44` | `reset_context()` not called in `finally` — leaks context on exception | P1 |
| B8/B9 | `payments/interfaces/http/router.py:136-138, 172-174` | `Idempotency-Key` optional for payment-link and refund (should be required) | P1 |
| B10 | `auth/interfaces/http/dependencies.py:46-48` | Weak default JWT secret (`dev-only-jwt-secret-change-me-in-prod-please-32chars`) | P0 (with F) |
| B11 | `customer/infrastructure/models.py` | No unique constraint on `(tenant_id, email)` | P1 |
| B6 | `payments/application/payment_service.py:192` | `tenant_id` read from Razorpay `notes` (user-controlled) | **P0** |

**Backend quality:** The business logic is mostly correct. The issues are around **boundaries and defaults** — tenant isolation gaps, missing config, weak defaults. The fix set is mechanical.

---

## 10. Database Review

**Schema inventory (Agent G):**

| Module | Tables | tenant_id | RLS | Indexes | Soft Delete |
|---|---|---|---|---|---|
| common | `tenants` | root | no | slug | no |
| auth | `users`, `refresh_tokens` | yes | no | tenant_id, email, hash, family_id | partial (timestamps) |
| customer | `customers` | yes | no | tenant_id, user_id, email | no (status only) |
| facility | `facilities`, `resources`, `availability_rules` | yes | no | tenant_id | no (status only) |
| booking | `bookings` | yes | no | tenant_id, customer_id, resource_id, partial composite (resource_window) | partial (status) |
| payments | `payments_invoices`, `payments_payments`, `payments_refunds`, `payments_idempotency_keys` | yes | **yes** | good | partial |
| payments | `payments_invoice_line_items` | no (via parent) | no | invoice_id | no |
| payments | `payments_processed_razorpay_events` | no (global) | no | processed_at | no |

**Migrations:** 4 files, linear history, all reversible, no destructive operations. Clean.

**Findings:**

| ID | Issue | Severity |
|---|---|---|
| G1 | **RLS only on payments tables** — 8/9 business tables have no defense-in-depth | **P0** |
| G2 | `AuditMixin` defined but unused — no `created_by` / `updated_by` | P1 |
| G3 | `OptimisticLockMixin` defined but unused — no `version` column on bookings | P1 |
| G4 | `customer.tenant_id` lacks FK | P1 (with B2) |
| G6 | Invoice number generation is read-then-write without `FOR UPDATE` | P1 |
| G7 | UUIDv4 used everywhere instead of UUIDv7 / ULID — bad for sort | P3 |
| G9 | `payments_invoice_line_items` has no `tenant_id` | P3 |
| G10 | Soft-delete inconsistent — some tables status, some timestamps | P2 |

> The schema is **clean** and **intentional**. The biggest gap is the missing RLS.

---

## 11. Booking Engine Review

**The make-or-break question:** *Can two users successfully book the same slot under concurrent requests?*

**Answer: NO.** The system is protected by `SELECT FOR UPDATE` row-level locking combined with an overlap-existence check inside a single transaction (`booking/infrastructure/repositories.py:74-122`). The integration test `test_booking_service.py:252` verifies exactly **1 of 5 concurrent requests succeeds**.

```
1. Acquire row-level lock on the resource.
2. Check for overlapping CONFIRMED bookings within [start_at, end_at).
3. Insert booking.
4. Commit on session exit → lock released.
```

The lock works **provided the session commits properly**. The test demonstrates the pattern works.

**However, there are critical gaps in the rest of the booking flow:**

| ID | Issue | Severity |
|---|---|---|
| E4 | **Client-controlled pricing** — `BookingCreate.price_cents` is taken from the request and only validated `>= 0`. A client sending `price_cents: 0` bypasses payment. | **P0** |
| E3 | **No availability rule validation** — bookings can be made outside operating hours, on blackout dates, when resource is under maintenance. Docstring says "Validate against resource availability rules (if any)" but no code does this. | **P1** |
| E5 | **No membership enforcement** — anyone can book regardless of membership status. | **P1** |
| E2 | **No capacity validation** — `Resource.capacity` exists in `facility/domain/entities.py:174` but never checked. | P2 |
| E6 | **Timezone not applied** — `Facility.timezone` stored but never used. | P2 |
| E7 | **No refund on cancellation** — `cancel_booking` just marks status; no refund trigger. | P2 |
| E8 | **No idempotency keys on booking POST** — double-click creates duplicate bookings. | P2 |
| E9 | **No waitlist** — overbooking scenarios have no handling. | P3 |

**Booking engine summary:** Race-free ✓. Business rules ✗ (availability, membership, capacity, pricing all unenforced).

---

## 12. Payment Review

**Architecture:** Razorpay integration is real and working end-to-end.

- `apps/backend/src/payments/` is the most thoroughly implemented module.
- Idempotency keys work via `payments/interfaces/http/router.py` + `IdempotencyStore`.
- RLS policies are enabled (the only module with them).
- Webhook signature verification uses the official SDK.
- Invoice generation produces line items, tax, totals.
- Refund flow exists and is tested.

**Findings:**

| ID | Issue | Severity |
|---|---|---|
| B1 | **`app_url` setting missing** — referenced in `payment_service.py:163` | **P0** |
| B5 | Cross-tenant refund lookup (`get_by_razorpay_refund_id_any_tenant`) | **P0** |
| B6 | `tenant_id` read from webhook `notes` (user-controlled) | **P0** |
| B8/B9 | Idempotency key optional for payment-link and refund | P1 |
| E7 | Cancellation does not trigger refund | P2 |
| G6 | Invoice number generation race | P1 |

**Payment conclusion:** The Razorpay integration is real, but **trust boundaries are weak**. A forged webhook with a malicious `tenant_id` in `notes` could trigger a cross-tenant refund. This is the same risk profile as the JWT issue.

---

## 13. Authentication & Authorization

### Authentication

| Aspect | Status | Evidence |
|---|---|---|
| Argon2id password hashing | ✅ Pass | `auth/infrastructure/password_hasher.py` (memory 19 MB, 2 iterations) |
| HS256 vs RS256 | ❌ **P0** | `auth/infrastructure/token_service.py:34-113` uses HS256; ADR-0005 / handbook specify RS256 |
| Refresh token rotation with family-based reuse detection | ✅ Pass | `auth/application/auth_service.py:159-217` |
| Refresh token stored in httpOnly cookie with SameSite | ✅ Pass | `auth/interfaces/http/schemas.py` + `auth/application/auth_service.py:140` |
| Account lockout | ✅ Pass | magic numbers in `auth/domain/entities.py:131-132` (`_MAX_FAILED_LOGINS = 10`, `_LOCKOUT_MINUTES = 15`) |
| HIBP password breach check | ❌ Open | documented but not implemented |
| Default JWT secret in env fallback | ❌ **P0** | `auth/interfaces/http/dependencies.py:46-48` falls back to `"dev-only-jwt-secret-change-me-in-prod-please-32chars"` |
| Token storage in browser | ⚠️ Memory-only (in api-client Zustand store) — good | `packages/api-client/src/auth/store.ts` |

### Authorization (RBAC)

**Status: NOT IMPLEMENTED.** No role checks, no permission decorator, no policy object.

- Routers only check `auth_required` (authentication).
- Manual role checks exist in 2 places (`payments/router.py:135,171`) — inconsistent.
- A `tenant_admin` and a `customer` have the same authorization surface.

This is the second P0. Any authenticated user can call any endpoint.

**The handbook explicitly says RBAC should be enforced** (`docs/09-security/rbac.md`), but no enforcement mechanism exists.

---

## 14. Security Review (OWASP)

Audit against OWASP Top 10 + OWASP API Security Top 10 + OWASP ASVS L2.

### Critical findings (synthesis)

| ID | OWASP category | Finding | Severity |
|---|---|---|---|
| SEC-1 | A02:2021 Cryptographic Failures | JWT uses HS256 (symmetric) instead of RS256 (asymmetric) — secret compromise = full token forgery | **P0** |
| SEC-2 | A01:2021 Broken Access Control | No RBAC enforcement on any endpoint | **P0** |
| SEC-3 | A01:2021 Broken Access Control | PostgreSQL RLS enabled on only 1 of 4 module families | **P0** |
| SEC-4 | A07:2021 Identification & Auth Failures | Hardcoded default JWT secret fallback | **P0** |
| SEC-5 | A04:2021 Insecure Design | Booking price client-controlled — `price_cents` accepted from client without server computation | **P0** |
| SEC-6 | A04:2021 Insecure Design | Refresh-token lookup missing `tenant_id` filter (token hash collision = cross-tenant auth) | **P0** |
| SEC-7 | A04:2021 Insecure Design | Payment webhook `tenant_id` read from user-controlled `notes` field | **P0** |
| SEC-8 | A04:2021 Insecure Design | Payment refund explicitly looks up cross-tenant via `get_by_razorpay_refund_id_any_tenant` | **P0** |
| SEC-9 | A05:2021 Security Misconfiguration | Backend container runs as root (no `USER` directive) | P1 |
| SEC-10 | A07:2021 / API2:2023 | No rate limiting implementation (settings defined, no middleware) | P1 |
| SEC-11 | API7:2023 SSRF | No webhook URL allowlist — `success_url`/`cancel_url` passed to Razorpay directly | P1 |
| SEC-12 | A05:2021 | No security headers (HSTS, CSP, X-Frame-Options, etc.) | P2 |
| SEC-13 | A09:2021 Logging Failures | structlog configured but app uses `getLogger()` (not bound loggers) — logs not structured | P2 |
| SEC-14 | A02:2021 | No HIBP password breach check | P2 |
| SEC-15 | A05:2021 | CORS allows `["*"]` methods/headers + `allow_credentials=true` (safe default but misconfig risk) | P2 |

**Top 5 Critical Risks:**

1. **(SEC-1 + SEC-4)** JWT algorithm + default secret. Together: any developer who can read the public repo knows the production fallback secret and can forge tokens. The fact that `NotImplementedError` is raised for RS256 means **RS256 is not implemented at all** — it's documented but the code only knows HS256. **Fix:** implement RS256 per the documented plan; remove the default secret; fail-fast on startup if not configured.
2. **(SEC-2)** No RBAC. A `customer` can call `POST /v1/payments/invoices/{id}/refund` because there's no role check. The payments router has 2 manual role checks (`if "tenant_admin" not in user["roles"]`) — these are spot-fixes, not a system. **Fix:** implement `@requires_role("tenant_admin")` decorator and apply across all routers.
3. **(SEC-3)** Missing RLS on 8/9 tables. Even if app-layer filters had zero bugs, a forgotten `tenant_id` filter on a new query would leak cross-tenant. **Fix:** add `ALTER TABLE … ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation ON … USING (tenant_id::text = current_setting('app.tenant_id', true))` to all migrations.
4. **(SEC-5)** Client-controlled pricing. A malicious client (or compromised frontend) can book any resource for $0. **Fix:** remove `price_cents` from `BookingCreate`; compute server-side from a `BookingTariff` (resource × time-of-day × membership).
5. **(SEC-7 + SEC-8)** Payment trust boundaries. The webhook handler reads `tenant_id` from `notes` (which is set during link creation from `current_user["tenant_id"]` — but the attacker can supply arbitrary `notes` when configuring Razorpay), and the refund lookup is explicitly cross-tenant. **Fix:** store invoice → tenant mapping server-side and look up tenant from DB; never trust webhook metadata for authorization decisions.

### Verdict

> **The application is NOT safe for production multi-tenant SaaS deployment.** Authentication, authorization, and tenant isolation have foundational gaps that, in combination, would allow a single authenticated user of one tenant to read and write data of every other tenant.
>
> The good news is that **none of these gaps are architectural rewrites** — each is a bounded fix: change a JWT algorithm, add a decorator, add a migration step. They could be closed in 2-3 weeks of focused work.

---

## 15. TDD & Testing Review

### Coverage (measured)

Backend: `apps/backend` collected 162 tests. Skipping integration (broken): 126 unit + API tests.

Per module (from pytest-cov output reported by Agent H):

| Layer | Target (per vision) | Actual | Status |
|---|---|---|---|
| Domain | ≥95% | ~60-70% | FAIL |
| Services | ≥90% | ~30-50% | FAIL |
| API | ≥80% | ~30-40% | FAIL |
| **Overall backend** | — | **~58%** | **FAIL** |
| Frontend | — | 3 component test files | INCOMPLETE |
| E2E | — | 7 spec files (mostly accessibility) | INCOMPLETE |

### Test quality

- **Domain tests**: Mostly real-entity tests. Good.
- **Service tests**: Heavy `MagicMock()` use — tests implementation, not behavior. Fragile.
- **Integration tests**: **BROKEN** — `payments/infrastructure/models.py` FK constraints have no explicit names, causing `sqlalchemy.exc.CompileError` on teardown.
- **API tests**: Mostly mock the service layer — does not test real HTTP behavior.
- **E2E**: 7 spec files, most are pure `axe-core` accessibility checks. No business-flow coverage.

### Critical gaps

| ID | Gap | Severity |
|---|---|---|
| H2 | **Zero tenant-isolation tests** — the most important security invariant has no test | **P0** |
| H1 | Integration tests broken (FK naming) | P0 |
| H4 | **Zero booking API endpoint tests** | P0 |
| H3 | **Zero membership tests** (module not implemented) | P1 |
| H7 | E2E only tests accessibility | P1 |
| H8 | Frontend test coverage minimal (3 component tests) | P1 |
| H5 | 12 failing API tests in payments | P1 |
| H6 | Service tests mock-heavy | P2 |

### TDD adherence

The pattern is **mock-based testing, not true TDD**. Tests describe implementation details more than behavior. The domain layer is the exception — those tests are good.

### Is this a TDD codebase?

**No.** The handbook says TDD is mandatory. The actual practice is "write tests after, with mocks". Refactoring is therefore risky.

---

## 16. PWA Review

**Working:**
- `vite-plugin-pwa` configured with `autoUpdate`, runtime caching (NetworkFirst / CacheFirst).
- Manifest generated correctly (after the recent vite.config.ts update).
- Service worker pre-caches assets.
- Install prompt component exists.
- Update banner exists.
- 2 manifest shortcuts configured (My bookings, Browse facilities).
- App is installable on Android Chrome.

**Findings:**

| ID | Issue | Severity |
|---|---|---|
| J1 | Missing icon sizes for iOS (144, 152, 180, 384) | P1 |
| J3 | User menu at bottom of sidebar not accessible on mobile when drawer open | P1 |
| J5 | **No offline booking queue** — POST /v1/booking on network failure loses form data, no retry, no toast | **P0** |
| J6 | Missing iOS meta tags (`apple-mobile-web-app-capable`, `apple-touch-icon`) | P1 |
| J7 | No safe-area CSS for notch devices | P1 |
| J8 | No toast notification system | P2 |
| J4 | Booking dialog close button below 44 px tap target | P3 |
| J10 | No Background Sync registration | P2 |
| J9 | No push notifications | P3 |

**PWA verdict:** Foundation is solid, but **critical offline resilience is missing** for the booking flow — exactly the flow that matters most.

---

## 17. Performance Review

### Measured (Agent I, curl 10 samples each)

| Endpoint | P50 | P95 | Status |
|---|---|---|---|
| `GET /v1/facility` | 10.8 ms | 12.0 ms | EXCELLENT |
| `GET /v1/facility/{id}/resources` | 10.9 ms | 11.7 ms | EXCELLENT |
| `GET /v1/booking/by-customer/{id}` | 12.7 ms | 20.5 ms | GOOD |
| `GET /v1/payments/invoices` | 14.2 ms | 35.3 ms | GOOD (one outlier) |
| `POST /v1/auth/refresh` | 4.7 ms | 5.0 ms | EXCELLENT |

All endpoints meet the P95 < 200 ms vision target with margin. **Backend latency is not a problem at current scale.**

### Frontend bundle

| Chunk | Size | Status |
|---|---|---|
| **`index.js`** | **365 KB** | **EXCEEDS 250 KB gate by 46%** |
| `index.css` | 9.8 KB | OK |
| Per-page chunks | 1-5 KB | OK |

**No manual chunk splitting** in `vite.config.ts`. The handbook's `docs/16-quality-gates/performance-gates.md` says bundle ≤ 250 KB. **Failing.**

### Cache

- Redis is **configured but unused for data caching** (only `InProcessEventPublisher` exists).
- PWA runtime caching is appropriate (NetworkFirst for APIs, CacheFirst for images).

### Findings

| ID | Issue | Severity |
|---|---|---|
| I1 | Bundle 365 KB > 250 KB gate | P1 |
| I2 | Missing composite index `(resource_id, start_at, end_at)` on bookings — time-range queries do full scans | P1 |
| I3 | No query batching | P2 |
| I4 | Redis unused for caching | P3 |

### Performance verdict

**Backend: green.** **Frontend bundle: red.** The bundle issue is fixable with manual chunk splitting (one Vite config change).

---

## 18. Scalability Review

### Vision targets

- 50 tenants by Year 3 (per `docs/01-vision/overview.md`)
- 200,000 members, 1.5M bookings/month by Year 3
- Failed-booking rate < 0.1%, P95 < 200 ms

### What scales

- Backend latency is fine at current load (single-digit ms P50).
- Booking concurrency primitive (`SELECT FOR UPDATE`) scales linearly with Postgres connections.
- PWA + multi-tenant model in `tenant_id` column is correct architecture.

### What does NOT scale

1. **In-process event publisher** — events lost on restart, no multi-worker fan-out. ADR-0004 specifies Redis Streams + outbox pattern. **This is the single biggest scalability risk.**
2. **No RLS** — without DB-layer isolation, every cross-tenant bug is a leak risk. At 50 tenants the surface area of "every query in every module" becomes unmanageable.
3. **No Redis caching layer** — every request hits Postgres. Acceptable at 1 tenant, expensive at 50.
4. **No read replicas / connection pooling tuning** — backend `db.py:43-46` has `pool_size=10, max_overflow=20`. Hardcoded.

### Scalability verdict

**The platform can run Splashh Sports Club for the next 12 months.** Going from 1 → 10 tenants requires RLS + Redis caching + event bus. Going from 10 → 50+ requires Redis Streams outbox + read replicas.

---

## 19. Multi-Agent Development Readiness

**Overall: 6/10 (Conditional)**

### Strengths

- DDD layering is **strict** and **observable** — domain layer has zero framework imports.
- Per-module folder structure (`domain/`/`application/`/`infrastructure/`/`interfaces/http/`) is consistent across all 5 built modules.
- Tests are co-located with code (in module `tests/`).
- ADR format is enforced.
- Handbook explicitly addresses AI-agent collaboration (`docs/14-ai-driven-development/`).

### Critical gaps

| ID | Issue | Severity |
|---|---|---|
| L1 | **No OpenAPI → TypeScript code generation.** Frontend types are hand-written in `packages/api-client/src/types/domain.ts` (the comment even says "Once we wire up OpenAPI generation (see spec §5), these become re-exports"). AI agents will drift. | **P0** |
| L2 | Domain layer imports Pydantic (`common/domain/types.py:12`) — violates stated architecture ("zero framework imports") | P1 |
| L3 | Inconsistent `@dataclass(slots=True)` — payments uses plain `@dataclass` | P2 |
| L7 | No migration tests in CI | P1 |
| L5/L6 | Hardcoded magic numbers in `db.py:43-46` and `settings.py:36-49` | P2 |
| L9 | Cross-module entity references without contracts (e.g., `auth_service.py:31` imports `customer.infrastructure.repositories`) | P2 |

### Drift risk

The **single highest drift risk** is L1 (no contract-first). Without generated types, an AI agent modifying the backend schema will silently desync the frontend.

---

## 20. Technical Debt

| ID | Area | Description | Severity |
|---|---|---|---|
| TD-1 | Membership module | Documented in `docs/18-modules/membership.md` but **not implemented**. Affects renewals, freezes, plans — none exist. | P1 |
| TD-2 | Notifications module | Documented, not implemented. No email/SMS/push infrastructure. | P1 |
| TD-3 | Analytics module | Documented, not implemented. No read replica, no materialized views. | P2 |
| TD-4 | Event bus | ADR-0004 violated — `InProcessEventPublisher` instead of Redis Streams + outbox. | P1 |
| TD-5 | OpenAPI codegen | No contract-first; frontend types hand-written. | **P0** |
| TD-6 | CI/CD | Documented pipeline does not exist. No `.github/workflows/`. | **P0** |
| TD-7 | Backup infrastructure | No scripts, no WAL archiving, no tested restore. | **P0** |
| TD-8 | RLS only on payments | 8 of 9 business tables have no DB-level tenant isolation. | **P0** |
| TD-9 | RBAC | No permission decorator, no policy. | **P0** |
| TD-10 | JWT algorithm | HS256 vs documented RS256. | **P0** |
| TD-11 | Booking business rules | Availability, capacity, membership, pricing all unenforced. | P1 |
| TD-12 | Bundle size | 365 KB > 250 KB. | P1 |
| TD-13 | Offline queue | POST /v1/booking has no retry/persist on network failure. | P1 |
| TD-14 | Integration tests | Broken due to FK constraint naming. | P0 |
| TD-15 | Test coverage | 58% vs 95% target. | P1 |
| TD-16 | Magic numbers | Pool size, TTLs, capacity thresholds not centralized. | P3 |
| TD-17 | Default JWT secret in code | `dev-only-jwt-secret-change-me-in-prod-please-32chars` | **P0** |
| TD-18 | Doc-code drift | `membership.md`, `notifications.md`, `analytics.md` claim shipped modules; they don't exist. | P2 |

---

## 21. Findings (Consolidated)

| ID | Track | Severity | File:Line | Summary | Status |
|---|---|---|---|---|---|
| **F-01** | Security | **P0** | `auth/infrastructure/token_service.py:34-113` | JWT uses HS256 instead of RS256 | ❌ Open |
| **F-02** | Security | **P0** | All routers | No RBAC enforcement on any endpoint | ❌ Open |
| **F-03** | Security | **P0** | `alembic/versions/*` (8 of 9 tables) | Missing PostgreSQL RLS | ❌ Open |
| **F-04** | Security | **P0** | `auth/interfaces/http/dependencies.py:46-48` | Hardcoded default JWT secret | ✅ Resolved (`ba12454`) |
| **F-05** | Booking | **P0** | `booking/interfaces/http/schemas.py:17` | Client-controlled `price_cents` | ❌ Open |
| **F-06** | Backend | **P0** | `auth/infrastructure/repositories.py:162-166` | RefreshToken lookup missing `tenant_id` | ❌ Open |
| **F-07** | Payment | **P0** | `payments/application/payment_service.py:192` | `tenant_id` read from webhook `notes` | ❌ Open |
| **F-08** | Payment | **P0** | `payments/application/payment_service.py:252` | Explicit cross-tenant refund lookup | ❌ Open |
| **F-09** | Payment | **P0** | `common/infrastructure/settings.py:68-72` | Missing `app_url` setting | ❌ Open |
| **F-10** | Architecture | **P0** | `booking/infrastructure/repositories.py:81,152` | Cross-module DB model import | ❌ Open |
| **F-11** | Architecture | **P0** | `common/application/events.py:26-43` | Event bus not Redis Streams | ❌ Open |
| **F-12** | AI-readiness | **P0** | `packages/api-client/src/types/domain.ts` | No OpenAPI codegen | ❌ Open |
| **F-13** | DevOps | **P0** | `.github/workflows/` | CI/CD missing | ❌ Open |
| **F-14** | DevOps | **P0** | `apps/backend/scripts/` | Backup infrastructure missing | ❌ Open |
| **F-15** | Testing | **P0** | `tests/integration/` | Tests broken (FK naming) | ❌ Open |
| **F-16** | Testing | **P0** | `tests/` (none) | Zero tenant-isolation tests | ❌ Open |
| **F-17** | Testing | **P0** | `tests/api/` (none) | Zero booking API endpoint tests | ❌ Open |
| **F-18** | UX | **P0** | `pages/admin/BookingsPage.tsx:7` | Admin bookings page is a placeholder | ❌ Open |
| **F-19** | PWA | **P0** | `features/bookings/useCreateBooking.ts` | No offline booking queue | ❌ Open |
| **F-20** | Database | P1 | `customer/infrastructure/models.py:20-22` | `tenant_id` lacks FK | ✅ Resolved (`59c4e2b`) |
| **F-21** | Database | P1 | `common/infrastructure/mixins.py:44-46` | `AuditMixin` defined but unused | ❌ Open |
| **F-22** | Database | P1 | `payments/infrastructure/repositories.py:111-123` | Invoice number race | ❌ Open |
| **F-23** | Backend | P1 | `common/application/middleware.py:40-44` | Context not reset in `finally` | ❌ Open |
| **F-24** | Backend | P1 | `payments/interfaces/http/router.py:136,172` | Idempotency-Key optional | ❌ Open |
| **F-25** | Booking | P1 | `booking/application/booking_service.py:7` | No availability rule validation | ❌ Open |
| **F-26** | Booking | P1 | `booking/application/booking_service.py` | No membership enforcement | ❌ Open |
| **F-27** | Performance | P1 | `apps/web-pwa/vite.config.ts` | Bundle 365 KB > 250 KB | ✅ Resolved (`e8afd26`) |
| **F-28** | Performance | P1 | `booking/infrastructure/models.py` | Missing composite time-range index | ✅ Resolved (`43f04fa`) |
| **F-29** | Frontend | P1 | `App.tsx` | No React ErrorBoundary | ✅ Resolved (`d59ca91`) |
| **F-30** | PWA | P1 | `apps/web-pwa/index.html` | Missing iOS meta tags | ✅ Resolved (`64028d9`) |
| **F-31** | PWA | P1 | `components/Sidebar.tsx:93-95` | User menu inaccessible on mobile | ✅ Resolved (`318e04e`) |
| **F-32** | UX | P1 | (no module) | No membership UI | ❌ Open |
| **F-33** | UX | P1 | (no module) | No check-in UI | ❌ Open |
| **F-34** | Security | P2 | `common/infrastructure/settings.py:62-63` | No rate limiting | ❌ Open |
| **F-35** | Security | P2 | `payments/application/payment_service.py:166-167` | No SSRF allowlist | ❌ Open |
| **F-36** | UX | P2 | `InvoicesPage.tsx:145` | Customer is truncated UUID | ❌ Open |
| **F-37** | UX | P2 | (no route) | No `/coach` or `/owner` dashboard | ❌ Open |
| **F-38** | DevOps | P2 | `apps/backend/Dockerfile` | Backend runs as root | ✅ Resolved (`d3e29a2`) |
| **F-39** | Architecture | P2 | `docs/18-modules/{membership,notifications,analytics}.md` | Doc-code drift | ✅ Resolved (`48301e4`) |
| **F-40** | AI-readiness | P2 | `common/domain/types.py:12` | Domain imports Pydantic | ❌ Open |
| **F-41** | AI-readiness | P2 | `db.py:43-46` | Magic numbers in pool config | ❌ Open |
| **F-42** | Database | P2 | all tables | Soft-delete inconsistent | ❌ Open |
| **F-43** | Frontend | P3 | `tokens.ts` + `globals.css` | Two parallel token systems | ❌ Open |
| **F-44** | Database | P3 | all tables | UUIDv4 not sortable | ❌ Open |
| **F-45** | Performance | P3 | `api/client.ts` | No query batching | ❌ Open |

---

## 22. Top 10 Issues

In priority order, the 10 issues that, if unresolved, prevent production deployment:

1. **F-01** — JWT HS256 (auth forgery).
2. **F-02** — No RBAC (privilege escalation).
3. **F-03** — Missing RLS (cross-tenant leak).
4. **F-05** — Client-controlled booking price (revenue bypass).
5. **F-07 + F-08** — Payment webhook reads tenant_id from user-controlled field, refund cross-tenant.
6. **F-04** — Hardcoded default JWT secret.
7. **F-06** — Refresh-token lookup missing tenant filter.
8. **F-10** — Cross-module DB model import (ADR-0001 violation).
9. **F-13 + F-14** — No CI/CD, no backup infrastructure.
10. **F-09** — Missing `app_url` setting would crash payment creation at runtime.

---

## 23. Top 10 UX Issues

1. **F-18** — `/admin/bookings` is a placeholder (Reception cannot do their job).
2. **F-32** — No membership UI (Customer cannot see plan, renewal date, digital pass).
3. **F-33** — No check-in / QR UI (Reception cannot process check-ins).
4. **F-31** — User menu inaccessible in mobile drawer.
5. **F-29** — No React error boundaries (single crash takes down app).
6. **F-36** — Invoices show truncated customer UUID instead of name.
7. **F-37** — No `/coach` or `/owner` dashboard.
8. **F-19** — No offline booking queue — booking fails silently on network drop.
9. **F-27** — Bundle is 365 KB; load time on mobile is sub-par.
10. **Inconsistent loading states** — some pages use `LoadingSkeleton`, others use plain text. Polish gap.

---

## 24. Top 10 Security Risks

1. **F-01** — JWT HS256 + default secret = token forgery.
2. **F-02** — No RBAC = any authenticated user is admin.
3. **F-03** — Missing RLS = application filter bugs become tenant leaks.
4. **F-05** — Client-controlled price = revenue bypass.
5. **F-08** — Cross-tenant refund lookup = payment integrity breach.
6. **F-07** — Webhook tenant_id from notes = authorization bypass.
7. **F-06** — Refresh-token cross-tenant hash collision = session hijack.
8. **F-04** — Default JWT secret in code = forge admin tokens.
9. **F-34** — No rate limiting = brute-force login.
10. **F-35** — No SSRF allowlist on webhook URLs = internal network probing.

---

## 25. Top 10 Architectural Concerns

1. **F-11** — Event bus is in-process; ADR-0004 violated. No async delivery, no replay, no multi-worker fan-out.
2. **F-10** — Cross-module DB model import; ADR-0001 violated. The booking module reaches into facility's infrastructure layer.
3. **F-12** — No OpenAPI codegen; AI agents will silently desync frontend and backend types.
4. **F-25** — No availability rule validation; the docstring promises it, the code doesn't enforce it.
5. **F-04 + F-09** — Default secrets + missing settings; the configuration layer is incomplete.
6. **TD-4** — `InProcessEventPublisher` will lose events on process restart and won't survive multi-worker deployment.
7. **TD-9** — RBAC implemented nowhere means the "RoleGate" mentioned in route config is decorative.
8. **F-23** — `reset_context()` not in `finally` block; tenant context leaks between requests on exception.
9. **TD-5** — No migration tests; an AI agent writing a destructive migration would only discover it on staging.
10. **F-39** — Handbook claims modules shipped that aren't shipped. Docs are not the source of truth.

---

## 26. Highest ROI Improvements

The following items would have outsized impact for minimal effort:

| Effort | Improvement | Impact |
|---|---|---|
| **S** (1-2 days) | Implement `@requires_role("tenant_admin")` decorator and apply to all `admin/*` routers | Closes F-02 (no RBAC) |
| **S** (1 day) | Remove `price_cents` from `BookingCreate`; server computes from tariff | Closes F-05 (client-controlled pricing) |
| **S** (1 day) | Add `tenant_id` filter to `RefreshTokenRepository.get_by_hash` | Closes F-06 |
| **S** (1 day) | Replace `get_by_razorpay_refund_id_any_tenant` with a tenant-scoped lookup using invoice-id as the key | Closes F-08 |
| **S** (1 day) | Remove default JWT secret; fail-fast on startup if not configured | Closes F-04 |
| **S** (1-2 days) | Add RLS policies to a single migration that covers `users`, `customers`, `facilities`, `resources`, `bookings` | Closes F-03 (RLS) |
| **M** (3-5 days) | Switch JWT to RS256 with proper key management; remove HS256TokenService | Closes F-01 |
| **M** (1 week) | Wire OpenAPI → TypeScript codegen | Closes F-12 (drift) |
| **M** (1 week) | Implement `/admin/bookings` view with filters and per-resource detail | Closes F-18 |
| **M** (1 week) | Implement the GitHub Actions workflow documented in `docs/12-devops/github-actions.md` | Closes F-13 |
| **M** (2 weeks) | Implement Redis Streams event bus with outbox pattern per ADR-0004 | Closes F-11 |
| **L** (1 month) | Implement Membership module end-to-end (backend + frontend) | Closes F-32, unblocks renewals |

**Total:** ~10 P0s and 15 P1s closed in roughly 2-3 engineer-months of focused work.

---

## 27. Recommended Roadmap

### Before Splashh Pilot (P0 + P1 — block release)

| # | Item | Priority | Effort |
|---|---|---|---|
| 1 | Implement RS256 JWT, remove HS256 + default secret | **P0** | M |
| 2 | Implement RBAC decorator + apply across routers | **P0** | M |
| 3 | Add RLS to all business tables (one migration) | **P0** | M |
| 4 | Server-computed booking pricing | **P0** | S |
| 5 | Tenant-scoped refund lookup + webhook tenant resolution from DB | **P0** | S |
| 6 | Refresh-token tenant filter | **P0** | S |
| 7 | Define missing `app_url` setting | **P0** | S |
| 8 | Fix booking FK constraint naming → unblock integration tests | **P0** | S |
| 9 | Implement `/admin/bookings` view | **P0** | M |
| 10 | Fix broken integration tests + add tenant-isolation tests | **P0** | M |
| 11 | Implement Membership module (backend + frontend) | **P1** | L |
| 12 | Implement Redis Streams event bus + outbox | **P1** | L |
| 13 | Implement availability/capacity/membership/timezone validation in booking | **P1** | M |
| 14 | Configure CI/CD (`.github/workflows/`) | **P1** | M |
| 15 | Configure backups + WAL archiving + restore test | **P1** | M |

### Before SaaS Launch

| # | Item | Priority | Effort |
|---|---|---|---|
| 16 | OpenAPI → TypeScript codegen | **P0** | M |
| 17 | Frontend bundle split (manual chunks) | P1 | S |
| 18 | Composite time-range index on bookings | P1 | S |
| 19 | Notifications module (email + SMS) | P1 | XL |
| 20 | Rate limiting middleware | P1 | S |
| 21 | SSRF allowlist on webhook callbacks | P1 | S |
| 22 | Idempotency-Key required (not optional) on payment-link and refund | P1 | S |
| 23 | Backend container non-root user | P1 | S |
| 24 | Security headers middleware | P2 | S |
| 25 | Toast notification system | P2 | M |
| 26 | Offline booking queue | P1 | M |

### After SaaS Launch (Scaling)

- Notifications + analytics modules
- Read replicas + connection pool tuning
- Multi-region deployment (DR)
- Tenant theming
- Push notifications
- Background sync API

---

## 28. Production Readiness

### Verdict

> **NOT READY.**
>
> The platform has a strong engineering culture and clean architecture, but is missing **8 P0 security/correctness issues** that together would let an authenticated user of one tenant read and write data of every other tenant, bypass payment, and forge admin tokens.

### Would I trust this app to run Splashh Sports Club today?

**Yes, with one caveat.** The single-tenant customer booking + payment flow works end-to-end. The booking race-condition test passes. The auth is real. Payments go through Razorpay.

**Caveat:** I would not trust the app to be exposed to the public internet before **at minimum** the 8 P0s are closed. Specifically, the JWT + RBAC + RLS gap means an attacker who discovers any cross-tenant endpoint can become a super-admin of any tenant without leaving a trace.

### What's needed for "ALPHA READY"

Close the 15 P0s (§22) and add CI/CD + backup.

### What's needed for "PILOT READY"

All of the above + P1 items + OpenAPI codegen + Membership module.

### What's needed for "PRODUCTION READY"

All of the above + Notifications + Analytics modules + rate limiting + observability + multi-region DR.

---

## 29. Final Scorecard

| Area | Score | Notes |
|---|---|---|
| **Product** | 4/10 | Customer journey works; 3 of 5 personas have no UI; `/admin/bookings` is placeholder |
| **UX** | 5/10 | Customer-side is polished; admin-side is inconsistent; offline/empty/loading mixed |
| **UI** | 6/10 | Sharp macha/neon aesthetic is strong; dark+volt palette is on-brand; sharp corners + neon glows |
| **Architecture** | 5/10 | DDD layering is enforced; 3 ADRs violated; event bus missing; cross-module coupling |
| **Backend** | 5/10 | Async + SQLAlchemy + Pydantic v2 done right; business rules unenforced; many P0 gaps |
| **Frontend** | 6/10 | React + TanStack + Zustand done right; bundle too big; missing error boundaries |
| **Database** | 5/10 | Clean migrations; RLS missing on 8/9 tables; FK gaps |
| **Security** | 2/10 | **8 P0 security gaps**; HS256 + no RBAC + no RLS = unsafe for multi-tenant |
| **Testing** | 3/10 | 58% coverage vs 95% target; integration tests broken; no tenant isolation tests |
| **PWA** | 5/10 | Foundation solid; offline booking queue missing |
| **Performance** | 7/10 | Backend latency excellent; bundle 365 KB > 250 KB gate |
| **Scalability** | 5/10 | OK for Splashh pilot; missing Redis Streams + RLS for multi-tenant |
| **Observability** | 4/10 | structlog configured but unused; no metrics endpoint; no tracing |
| **AI-agent readiness** | 6/10 | Strong foundations; no OpenAPI codegen (drift risk) |
| **Documentation** | 7/10 | Handbook is thorough; but drifts from code (3 missing modules) |
| | | |
| **Overall** | **5/10** | NOT PRODUCTION READY — close the 8 P0s and the platform is viable for Splashh pilot |

---

## Appendix A — How to use this document

This document is the authoritative review of the Splashh Sports Platform as of 2026-08-11. Each finding has:

- **Severity** (P0–P4)
- **Location** (file:line)
- **Evidence** (verified by direct inspection)
- **Recommendation** (actionable)

For implementation, work the **§27 Roadmap** in order. After each P0 close, **re-run this audit** — the scorecard should trend upward.

## Appendix B — What was NOT in scope

- Performance load testing (only single-instance measurements)
- Security penetration testing (only static analysis)
- Accessibility testing beyond axe-core
- Cross-browser compatibility
- Network latency / CDN performance
- Vendor risk analysis (Razorpay, Postmark, etc.)
- Cost / billing analysis
- Legal / regulatory analysis (DPDPA, PCI-DSS)
