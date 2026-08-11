# Findings Roadmap — Splashh Sports Platform

> **Source:** `docs/CODEBASE_REVIEW.md` (2026-08-11 audit)
> **Scope:** Execution plan for all 45 findings (F-01..F-45), grouped by work stream, ordered by dependency.
> **Status:** Plan, not commitments. Items can be parallelized where dependencies allow.

---

## How to read this document

Each finding card has:

- **Title** + cross-reference to the audit doc (`§<section>`)
- **Files** — concrete file:line list to touch
- **Acceptance criteria** — what "done" means
- **Effort** — S/M/L/XL (S ≤ 1 day, M ≤ 1 week, L ≤ 1 month, XL > 1 month)
- **Dependencies** — which other findings must land first
- **Test plan** — what regression coverage to add

Phases are ordered; items within a phase can be parallelized across engineers.

---

## Table of Contents

1. [Phase 0 — Block-Release Security](#phase-0--block-release-security) (1-2 weeks, 1 engineer)
2. [Phase 1 — Pilot Readiness](#phase-1--pilot-readiness) (4-6 weeks, 2 engineers)
3. [Phase 2 — SaaS Launch Readiness](#phase-2--saas-launch-readiness) (4-6 weeks, 2 engineers)
4. [Phase 3 — Post-Launch Scaling](#phase-3--post-launch-scaling) (ongoing)
5. [Work Stream Map](#work-stream-map)
6. [Dependency Graph](#dependency-graph)
7. [Quick Wins](#quick-wins)
8. [Tracking & Verification](#tracking--verification)

---

## Phase 0 — Block-Release Security

> **Why this phase exists:** Without this, the platform cannot be exposed to the public internet. All items here are P0 security/correctness issues that, in combination, let an authenticated user of one tenant become admin of any other tenant.

**Duration:** 1-2 weeks · **Engineers:** 1 backend · **Merge gate:** none of these can ship without security review by 2 reviewers.

### F-01 — Switch JWT to RS256 (P0)

**Audit ref:** §13, §14 (SEC-1)

**Files:**
- `apps/backend/src/auth/infrastructure/token_service.py` (replace `HS256TokenService` with `RS256TokenService`)
- `apps/backend/src/auth/application/auth_service.py:312-314` (remove `NotImplementedError`)
- `apps/backend/src/common/infrastructure/settings.py` (replace `jwt_algorithm: Literal["RS256", "HS256"]` defaults)
- `apps/backend/src/auth/interfaces/http/dependencies.py:46-48` (use asymmetric verifier)
- `apps/backend/scripts/` (add `gen-jwt-keys.sh`)

**Acceptance criteria:**
- [ ] `RS256TokenService` generates access + refresh tokens using RSA key pair
- [ ] `verify_token()` uses the **public** key only; private key never leaves the issuer
- [ ] Production `.env.prod.example` documents `JWT_PRIVATE_KEY_PATH` + `JWT_PUBLIC_KEY_PATH`
- [ ] Dev compose file generates ephemeral keys on startup if missing
- [ ] Existing integration tests updated; all green

**Effort:** M (3-5 days)

**Test plan:**
- Unit: `tests/unit/test_rs256_token_service.py` — roundtrip sign+verify
- Integration: existing `test_auth_endpoints.py` updated for new alg
- Property: cannot sign tokens with the public key (forgery attempt)

---

### F-02 — RBAC decorator + apply to all admin routers (P0)

**Audit ref:** §13, §14 (SEC-2)

**Files:**
- `apps/backend/src/common/interfaces/http/dependencies.py` (new `requires_role(*roles)` factory)
- `apps/backend/src/auth/interfaces/http/router.py` (apply)
- `apps/backend/src/customer/interfaces/http/router.py` (apply)
- `apps/backend/src/facility/interfaces/http/router.py` (apply)
- `apps/backend/src/booking/interfaces/http/router.py` (apply)
- `apps/backend/src/payments/interfaces/http/router.py` (apply — remove the 2 manual checks at lines 135, 171)
- `apps/backend/tests/api/` (new `test_rbac.py`)

**Acceptance criteria:**
- [ ] `requires_role("tenant_admin")` dependency factory exists
- [ ] Every endpoint is classified as `public`, `authenticated`, `staff_only`, or `tenant_admin_only`
- [ ] No router relies solely on `auth_required` without role check
- [ ] Manual role checks removed; replaced with decorator
- [ ] Test: `customer` token receives 403 on every `tenant_admin_only` endpoint

**Effort:** M (1 week)

**Test plan:**
- Matrix test: every role × every endpoint → expected status code

---

### F-03 — Add Postgres RLS to all business tables (P0)

**Audit ref:** §10 (G1), §14 (SEC-3)

**Files:**
- New migration `apps/backend/alembic/versions/20260811_<n>_enable_rls.py`
- `apps/backend/src/common/infrastructure/db.py` (verify `app.tenant_id` is set per-request via `SET LOCAL`)
- `apps/backend/src/common/application/middleware.py:40-44` (also set `tenant_id` outside transactions for the lifespan)
- `apps/backend/tests/integration/` (RLS isolation tests)

**Acceptance criteria:**
- [ ] All 8 unprotected tables have `ALTER TABLE … ENABLE ROW LEVEL SECURITY` + `CREATE POLICY … USING (tenant_id = current_setting('app.tenant_id', true)::uuid)`
- [ ] Integration test: connect as Tenant A, attempt SELECT/UPDATE/DELETE on Tenant B row → expect 0 rows / 0 updates
- [ ] Bypass policy exists for `tenant_admin` service-role contexts (if needed) — and is itself tested

**Effort:** M (1 week)

**Test plan:**
- New `tests/integration/test_tenant_isolation.py` (this is F-15 — combined)
- Cross-tenant read, write, delete, count all blocked

**Dependencies:** none (can run in parallel with F-01, F-02)

---

### F-04 — Remove default JWT secret + fail-fast on startup (P0)

**Audit ref:** §13, §14 (SEC-4)

**Files:**
- `apps/backend/src/auth/interfaces/http/dependencies.py:46-48` (remove `os.environ.get(..., "dev-only-...")` fallback)
- `apps/backend/src/auth/infrastructure/token_service.py:306` (same)
- `apps/backend/src/common/infrastructure/settings.py` (mark `JWT_SECRET` as required, no default)

**Acceptance criteria:**
- [ ] Startup raises `RuntimeError` if `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` is unset (production) or unreadable
- [ ] No fallback to hardcoded secrets anywhere
- [ ] `make -C apps/backend dev` still works for dev (uses ephemeral keys)
- [ ] Test: app refuses to start with missing key path

**Effort:** S (1 day)

**Dependencies:** F-01 (RS256 switch) — should land with it

---

### F-06 — Add `tenant_id` filter to RefreshTokenRepository.get_by_hash (P0)

**Audit ref:** §9 (B3), §14 (SEC-6)

**Files:**
- `apps/backend/src/auth/infrastructure/repositories.py:162-166`

**Acceptance criteria:**
- [ ] `get_by_hash(tenant_id, token_hash)` includes `WHERE tenant_id = ?`
- [ ] Refresh tokens cannot resolve across tenants
- [ ] Unit test: same hash, different tenant → first returns row, second returns None

**Effort:** S (hours)

**Dependencies:** none

---

### F-05 — Server-computed booking price (P0)

**Audit ref:** §11 (E4), §14 (SEC-5)

**Files:**
- `apps/backend/src/booking/interfaces/http/schemas.py:17` (remove `price_cents` from `BookingCreate`)
- `apps/backend/src/booking/application/booking_service.py:38` (server computes price from a `BookingTariff` table)
- New table `booking_tariffs` (resource_id, day_of_week, time_of_day, price_cents, currency)
- New migration
- `apps/web-pwa/src/features/bookings/api.ts` (drop `price_cents` from input)

**Acceptance criteria:**
- [ ] `POST /v1/booking` no longer accepts `price_cents` from client
- [ ] Server looks up tariff by `(resource_id, start_at, day_of_week)` and writes the computed price
- [ ] Reject with 422 if no tariff configured
- [ ] `BookingOut` still returns `price_cents` for display

**Effort:** M (3-5 days, including the tariff seed)

**Dependencies:** none

---

### F-07 — Webhook `tenant_id` resolved from DB, not from `notes` (P0)

**Audit ref:** §12 (B6), §14 (SEC-7)

**Files:**
- `apps/backend/src/payments/application/payment_service.py:192` (replace `notes.tenant_id` with `await invoice_repo.get_by_razorpay_link_id(razorpay_link_id, tenant_id_from_session)`)
- `apps/backend/src/payments/application/payment_service.py` (invoice resolution)

**Acceptance criteria:**
- [ ] Webhook handler never reads `tenant_id` from Razorpay payload metadata
- [ ] Tenant is resolved by looking up the invoice/payment record in DB
- [ ] Webhook with a forged `notes.tenant_id` is treated as if `tenant_id` matched the actual invoice owner

**Effort:** S (1 day)

**Dependencies:** F-08 (refund also reworked)

---

### F-08 — Tenant-scoped refund lookup (P0)

**Audit ref:** §12 (B5), §14 (SEC-8)

**Files:**
- `apps/backend/src/payments/application/payment_service.py:252` (replace `_any_tenant` with `_by_invoice_id_and_refund_id`)
- `apps/backend/src/payments/infrastructure/repositories.py` (add `get_refund_by_invoice_and_razorpay_id(invoice_id, razorpay_refund_id)`)

**Acceptance criteria:**
- [ ] Refund lookup uses invoice_id + razorpay_refund_id, both scoped by tenant
- [ ] Refund for Tenant A's invoice cannot be processed by Tenant B's session
- [ ] `get_by_razorpay_refund_id_any_tenant` removed

**Effort:** S (1 day)

**Dependencies:** can pair with F-07

---

### F-09 — Add `app_url` setting (P0)

**Audit ref:** §9 (B1), §12

**Files:**
- `apps/backend/src/common/infrastructure/settings.py` (add `app_url: str = Field(...)`)
- `.env.prod.example` (document)
- `docker-compose.prod.yml` (wire)

**Acceptance criteria:**
- [ ] `Settings.app_url` is required (no default)
- [ ] Dev compose passes `http://localhost:5173` for `app_url`
- [ ] Payment link generation reads `settings.app_url` (already does — `payment_service.py:163`)
- [ ] Test: payment link URL contains `app_url` host

**Effort:** S (hours)

**Dependencies:** none

---

### F-18 — Implement `/admin/bookings` view (P0)

**Audit ref:** §5 (D2), §6

**Files:**
- `apps/web-pwa/src/pages/admin/BookingsPage.tsx` (full implementation)
- `apps/backend/src/booking/interfaces/http/router.py` (new endpoint `GET /v1/admin/bookings` with tenant + facility + date filters)
- `apps/web-pwa/src/features/bookings/useBookings.ts` (new `useAdminBookings` hook)

**Acceptance criteria:**
- [ ] Admin sees list of today's bookings (default), filterable by facility, resource, status
- [ ] Per-row: customer name + email (via JOIN), resource name, time, status pill
- [ ] Click row → booking detail modal with cancel action (Reception workflow)
- [ ] Pagination (cursor-based)
- [ ] Mobile-responsive (card list like invoices)

**Effort:** M (1 week)

**Dependencies:** new backend endpoint + RBAC (F-02)

---

### F-14 — Fix broken integration tests + add tenant-isolation tests (P0)

**Audit ref:** §10, §15 (H1, H2)

**Files:**
- `apps/backend/src/payments/infrastructure/models.py` (add explicit `name="…"` to every `ForeignKeyConstraint`)
- `apps/backend/tests/integration/test_auth_service.py` (now runs)
- `apps/backend/tests/integration/test_booking_service.py` (now runs)
- New `tests/integration/test_tenant_isolation.py` (covers F-03 too)

**Acceptance criteria:**
- [ ] All 162 tests collect and pass
- [ ] Tenant-isolation tests cover: login as Tenant A, attempt to read/update/delete Tenant B data via every public endpoint
- [ ] Booking concurrency test still passes
- [ ] Coverage report shows ≥70% (was 58%)

**Effort:** M (1 week)

**Dependencies:** F-03 (RLS) to test

---

### F-15 — Tenant-isolation test suite (P0)

**Audit ref:** §15 (H2)

This is a **subset of F-14** — listed separately because it's the single most important test set.

**Files:**
- `apps/backend/tests/integration/test_tenant_isolation.py`

**Acceptance criteria:**
- [ ] Create two tenants, populate with non-overlapping data
- [ ] For every public endpoint that takes an `id`, verify Tenant A's session cannot access Tenant B's resource
- [ ] Bulk operations (list, count) return only Tenant A's data
- [ ] RLS bypass attempts (raw SQL) also fail

**Effort:** included in F-14

---

### F-16 — Booking API endpoint tests (P0)

**Audit ref:** §15 (H4)

**Files:**
- New `apps/backend/tests/api/test_booking_endpoints.py`
- New `apps/backend/tests/api/test_facility_endpoints.py`

**Acceptance criteria:**
- [ ] Every booking endpoint tested with: happy path, validation failure, auth failure, tenant isolation failure, RBAC failure
- [ ] At least 1 concurrency test at the HTTP layer (not just service layer)

**Effort:** S (1 day)

**Dependencies:** F-02 (RBAC), F-05 (server pricing) to be in place

---

### F-19 — Offline booking queue (P0)

**Audit ref:** §16 (J5)

**Files:**
- `apps/web-pwa/src/features/bookings/useCreateBooking.ts` (wrap mutation: IndexedDB queue on failure, retry on reconnect)
- `apps/web-pwa/src/lib/offlineQueue.ts` (new)
- `apps/web-pwa/src/components/OfflineBanner.tsx` (new — shows queue depth)

**Acceptance criteria:**
- [ ] On `POST /v1/booking` failure (network or 5xx), the request is persisted to IndexedDB with idempotency key
- [ ] On reconnect, the queue is drained in order
- [ ] User sees a banner with queue depth + retry button
- [ ] Booking confirmation toast appears once drained

**Effort:** M (3-5 days)

**Dependencies:** F-05 (idempotency on booking POST)

---

### F-10 — Cross-module DB model import (P0)

**Audit ref:** §4 (ADR-0001), §25 (F-10)

**Files:**
- `apps/backend/src/booking/infrastructure/repositories.py:81` (replace direct `FacilityModel` import with call to `FacilityService.get_facility_names(...)`)
- `apps/backend/src/booking/infrastructure/repositories.py:152` (same for `ResourceModel`)
- New methods on `FacilityService`: `get_facility_names(tenant_id, ids: list[UUID]) -> dict[UUID, str]`, `lock_resource_for_update(...)`

**Acceptance criteria:**
- [ ] Booking module no longer imports any model from `facility.infrastructure`
- [ ] Booking still produces the same SQL behavior (verified via integration tests)
- [ ] Dependency rule test (`tests/architecture/`) catches future violations

**Effort:** M (3-5 days)

**Dependencies:** none (mechanical refactor)

---

### F-11 — Replace in-process event publisher with Redis Streams (P0)

**Audit ref:** §4 (ADR-0004), §25 (F-11)

**Files:**
- New `apps/backend/src/common/infrastructure/event_bus/redis_streams.py`
- New `apps/backend/src/common/infrastructure/event_bus/outbox.py`
- New alembic migration `event_outbox` table
- `apps/backend/src/common/application/events.py` (replace `InProcessEventPublisher`)

**Acceptance criteria:**
- [ ] Events written to Postgres outbox table inside the same transaction as the domain change
- [ ] Background worker reads outbox, publishes to Redis Streams, marks rows as `published_at`
- [ ] No events lost on process restart
- [ ] Subscribers can register per event type
- [ ] Tests: simulate process restart between outbox write and publish → no event loss

**Effort:** L (2-3 weeks)

**Dependencies:** none (additive)

---

### F-12 — OpenAPI → TypeScript codegen (P0)

**Audit ref:** §19 (L1), §25 (F-12)

**Files:**
- New `apps/backend/scripts/generate_openapi.py` (or `fastapi openapi-schema`)
- New `packages/api-client/scripts/generate-types.ts` (consume `openapi.json` → TS types)
- `packages/api-client/src/types/domain.ts` (becomes `generated.ts` — re-export)
- `apps/web-pwa/package.json` (script `gen:types`)

**Acceptance criteria:**
- [ ] `pnpm gen:types` regenerates `domain.ts` from backend's `/openapi.json`
- [ ] CI runs `gen:types --check` — fails if generated differs from checked-in
- [ ] All current frontend types match backend Pydantic schemas (verified by build)

**Effort:** M (1 week)

**Dependencies:** none

---

### F-13 — CI/CD pipeline (P0)

**Audit ref:** §16, §17 (K1)

**Files:**
- New `.github/workflows/ci.yml` (lint → type-check → unit → integration → e2e → build)
- New `.github/workflows/release.yml` (build images → push to registry → deploy to Dokploy)
- New `.github/workflows/rollback.yml` (`workflow_dispatch` to roll back)

**Acceptance criteria:**
- [ ] PRs run lint + type-check + unit + integration in <5 min
- [ ] Main branch runs full e2e + builds images + pushes
- [ ] Tag release runs deploy to Dokploy
- [ ] Manual `workflow_dispatch` can roll back

**Effort:** M (1 week)

**Dependencies:** F-14 (tests passing)

---

### F-17 — Membership module (P1)

**Audit ref:** §5 (D4), §20 (TD-1)

**Files:**
- New `apps/backend/src/membership/` (DDD layers)
- New alembic migration
- `apps/web-pwa/src/pages/membership/` (customer-facing)
- `apps/web-pwa/src/pages/admin/membership/` (admin)
- `docs/18-modules/membership.md` (update from "not yet implemented" to "shipped")

**Acceptance criteria:**
- [ ] Member can view plan, status, renewal date, digital pass
- [ ] Member can renew / cancel / freeze
- [ ] Admin can define plans, assign to customers
- [ ] Booking flow checks membership (links to F-26)

**Effort:** XL (1+ month)

**Dependencies:** F-26 (booking membership check) — should land with it

---

## Phase 0 Verification

Before exiting Phase 0:

- [ ] All 8 P0 security items closed
- [ ] `pytest` passes 162/162 tests
- [ ] RLS tests pass for cross-tenant isolation
- [ ] Penetration test (manual): attempt the 5 attack scenarios from §24 — all blocked
- [ ] Smoke test of full booking flow end-to-end
- [ ] Two-reviewer sign-off on security PRs

---

## Phase 1 — Pilot Readiness

> **Goal:** Run Splashh Sports Club live with real customers for 1-2 months. Single tenant. No second tenant yet.

**Duration:** 4-6 weeks · **Engineers:** 2 (1 backend, 1 frontend) · **Merge gate:** Pilot sign-off.

### F-25 — Booking availability rule validation (P1)

**Audit ref:** §11 (E3)

**Files:**
- `apps/backend/src/booking/application/booking_service.py:30` (after locking the resource, call `availability_repo.get_applicable_rules(...)` and verify start_at/end_at falls within a rule)
- `apps/backend/src/facility/infrastructure/repositories.py` (new `get_applicable_rules(resource_id, booking_datetime)`)

**Acceptance criteria:**
- [ ] Booking rejected with 422 if outside any availability rule
- [ ] Booking rejected with 422 during maintenance windows (status != active)
- [ ] Tests: book outside hours → 422; book during maintenance → 422; book during valid window → 201

**Effort:** M (3-5 days)

---

### F-26 — Booking membership enforcement (P1)

**Audit ref:** §11 (E5)

**Files:**
- `apps/backend/src/booking/application/booking_service.py` (after auth, look up customer membership)
- `apps/backend/src/membership/` (new module — see F-17)

**Acceptance criteria:**
- [ ] Booking rejected with 402/403 if customer has no active membership
- [ ] Membership tier determines which resources are bookable
- [ ] Tests: non-member → 403; expired membership → 403; valid → 201

**Effort:** M (depends on F-17)

---

### F-22 — Booking FK constraint naming (P0, blocking integration tests)

**Audit ref:** §15 (H1)

**Files:**
- `apps/backend/src/payments/infrastructure/models.py` (add explicit `name="…"` to every `ForeignKeyConstraint`)
- (verify all other models too)

**Acceptance criteria:**
- [ ] `pytest` collection no longer warns about unnameable constraints
- [ ] All integration tests run to completion

**Effort:** S (hours)

**Dependencies:** none — should land early in Phase 1 so other tests can run

---

### F-23 — Context reset in `finally` block (P1)

**Audit ref:** §9 (B7)

**Files:**
- `apps/backend/src/common/application/middleware.py:40-44` (move `reset_context()` from after commit to `finally:` block)

**Acceptance criteria:**
- [ ] Even when commit fails, `app.tenant_id` is unset on the connection
- [ ] Test: simulated exception → next request has no leaked context

**Effort:** S (hours)

---

### F-24 — Idempotency-Key required (P1)

**Audit ref:** §9 (B8, B9)

**Files:**
- `apps/backend/src/payments/interfaces/http/router.py:136-138, 172-174` (drop `default=None`)

**Acceptance criteria:**
- [ ] `POST /v1/payments/invoices/{id}/payment-link` rejects without `X-Idempotency-Key` → 400
- [ ] `POST /v1/payments/invoices/{id}/refund` rejects without `X-Idempotency-Key` → 400
- [ ] Existing tests updated to send the header

**Effort:** S (hours)

---

### F-20 — `customer.tenant_id` FK (P1)

**Audit ref:** §9 (B2), §10 (G4)

**Files:**
- New alembic migration adding FK on `customers.tenant_id`
- Verify same on `facility`, `booking`, `payments` tables

**Acceptance criteria:**
- [ ] Migration applies without breaking existing data
- [ ] Inserting customer with unknown tenant fails at DB level

**Effort:** S (hours)

---

### F-21 — `AuditMixin` applied to all models (P1)

**Audit ref:** §10 (G2)

**Files:**
- All `apps/backend/src/*/infrastructure/models.py` (add `created_by`, `updated_by` columns + `AuditMixin`)
- New alembic migration
- Update `BaseRepository` to populate audit fields on insert/update

**Acceptance criteria:**
- [ ] Every business table has `created_by` + `updated_by` FK to `users.id`
- [ ] Inserting via repository auto-populates `created_by` from auth context
- [ ] Tests: insert as user X → `created_by = X`

**Effort:** S (1-2 days)

---

### F-29 — React error boundaries (P1)

**Audit ref:** §8 (C7)

**Files:**
- New `apps/web-pwa/src/components/ErrorBoundary.tsx`
- `apps/web-pwa/src/App.tsx` (wrap `<App />`)
- `apps/web-pwa/src/routes/index.tsx` (wrap each lazy page)

**Acceptance criteria:**
- [ ] Unhandled component error → fallback UI, not white screen
- [ ] Error reported via `console.error` + sent to monitoring (when added)

**Effort:** S (1 day)

---

### F-31 — User menu accessibility on mobile (P1)

**Audit ref:** §16 (J3)

**Files:**
- `apps/web-pwa/src/components/Sidebar.tsx:93-95` (move user menu to bottom of drawer + sticky position, or add user menu to TopBar on mobile)
- `apps/web-pwa/src/components/TopBar.tsx` (add user menu on small viewports)

**Acceptance criteria:**
- [ ] Logout / account menu accessible without scrolling on 390 px viewport
- [ ] Tested on iPhone SE (375 px) and iPhone 14 Pro (390 px)

**Effort:** S (1 day)

---

### F-30 — iOS meta tags + touch icon (P1)

**Audit ref:** §16 (J6, J1)

**Files:**
- `apps/web-pwa/index.html` (add `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, `apple-touch-icon`)
- `apps/web-pwa/vite.config.ts` (add 144, 152, 180, 384 icon entries to manifest)

**Acceptance criteria:**
- [ ] iOS Safari install prompt shows correct icon
- [ ] `viewport-fit=cover` present + safe-area CSS applied

**Effort:** S (hours)

---

### F-32 — Membership UI (P1)

**Audit ref:** §5 (D4)

**Files:**
- `apps/web-pwa/src/pages/membership/MyMembershipPage.tsx` (new — view plan, digital pass, renewal date)
- `apps/web-pwa/src/pages/admin/membership/MembershipsPage.tsx` (new — admin plan management)

**Acceptance criteria:**
- [ ] Customer sees plan + status + renewal date
- [ ] Digital pass visible (QR or card design)
- [ ] Renewal CTA visible 7 days before expiry
- [ ] Admin can create/edit/archive plans

**Effort:** L (depends on F-17)

---

### F-33 — Check-in UI (P1)

**Audit ref:** §5 (D5)

**Files:**
- New `apps/web-pwa/src/pages/admin/check-in/` (Reception check-in page)
- `apps/backend/src/booking/interfaces/http/router.py` (existing `POST /v1/booking/{id}/check-in` — already there)

**Acceptance criteria:**
- [ ] Reception can scan QR / enter booking ID → marks checked_in
- [ ] Customer can self check-in via QR shown in `BookingsPage`

**Effort:** M (1 week)

---

### F-27 — Bundle split (P1)

**Audit ref:** §17 (I1)

**Files:**
- `apps/web-pwa/vite.config.ts` (manual chunks: `react-vendor`, `query-vendor`, `ui-kit`, `icons`)

**Acceptance criteria:**
- [ ] `index.js` ≤ 250 KB
- [ ] Vendor code in separate chunks (longer cache TTL)
- [ ] Lighthouse Performance ≥ 90 on mobile

**Effort:** S (1 day)

---

### F-28 — Composite booking time-range index (P1)

**Audit ref:** §17 (I2)

**Files:**
- New alembic migration adding `Index("ix_bookings_resource_window", "tenant_id", "resource_id", "start_at")`

**Acceptance criteria:**
- [ ] EXPLAIN on `list_for_resource` shows index scan, not seq scan
- [ ] P95 latency for booking list ≤ 50 ms at 1M bookings

**Effort:** S (hours)

---

### F-39 — Doc-code drift for membership/notifications/analytics (P2)

**Audit ref:** §20 (TD-18)

**Files:**
- `docs/18-modules/membership.md` — update when shipped
- `docs/18-modules/notifications.md` — mark "not yet implemented" or implement
- `docs/18-modules/analytics.md` — same

**Acceptance criteria:**
- [ ] Each module doc accurately reflects status

**Effort:** S (hours)

---

### F-40 — Remove Pydantic from `common/domain/types.py` (P2)

**Audit ref:** §19 (L2)

**Files:**
- `apps/backend/src/common/domain/types.py:12` (replace Pydantic `StringConstraints` with pure-Python regex helpers)

**Acceptance criteria:**
- [ ] `common/domain/types.py` has zero non-stdlib imports
- [ ] `mypy` still passes
- [ ] Branded types still validate

**Effort:** S (1 day)

---

### F-41 — Centralize magic numbers (P2)

**Audit ref:** §19 (L5, L6)

**Files:**
- `apps/backend/src/common/infrastructure/db.py:43-46` (move pool config to settings)
- `apps/backend/src/common/infrastructure/settings.py` (add `db_pool_size`, `db_max_overflow`, `db_pool_recycle`, `jwt_lockout_*`)

**Acceptance criteria:**
- [ ] No hardcoded magic numbers in `db.py`
- [ ] All magic constants documented in `settings.py` with rationale comment

**Effort:** S (1 day)

---

### F-42 — Soft-delete consistency (P2)

**Audit ref:** §10 (G10)

**Files:**
- All models — pick one pattern (status enum OR `deleted_at`) and apply consistently

**Acceptance criteria:**
- [ ] All soft-deletable tables have one consistent pattern

**Effort:** M (1 week)

---

### F-38 — Backend container non-root user (P1)

**Audit ref:** §17 (K3)

**Files:**
- `apps/backend/Dockerfile` (add `USER appuser` after install)

**Acceptance criteria:**
- [ ] Container runs as non-root (`uid != 0`)
- [ ] All existing functionality still works

**Effort:** S (hours)

---

### F-43 — Single token system (P3)

**Audit ref:** §8 (C4)

**Files:**
- `packages/ui/src/tokens.ts` (delete or keep only for non-color tokens)
- `packages/ui/src/styles/globals.css` (canonical home)

**Acceptance criteria:**
- [ ] Single source of truth for tokens

**Effort:** S (1 day)

---

### F-44 — UUIDv7 / ULID for sortability (P3)

**Audit ref:** §10 (G7)

**Files:**
- New migration to swap UUIDs (large effort — do only if needed)

**Acceptance criteria:**
- [ ] IDs are sortable by creation time

**Effort:** L (migration + data backfill)

**Dependencies:** only if pagination perf becomes a problem

---

### F-45 — Query batching (P3)

**Audit ref:** §17 (I3)

**Files:**
- `packages/api-client/src/api/client.ts` (add batch endpoint or parallelize independent queries)

**Acceptance criteria:**
- [ ] Independent queries on page load run in parallel (already true with TanStack Query)

**Effort:** M (mostly done — verify)

---

### F-37 — Coach / Owner dashboards (P2)

**Audit ref:** §5 (D7)

**Files:**
- New `apps/web-pwa/src/pages/coach/` (schedule, attendance)
- New `apps/web-pwa/src/pages/owner/` (revenue, occupancy)

**Acceptance criteria:**
- [ ] Coach sees today's sessions + attendance
- [ ] Owner sees revenue / occupancy / renewal analytics

**Effort:** L (each)

**Dependencies:** Notifications + Analytics modules

---

### F-34 — Rate limiting middleware (P1)

**Audit ref:** §14 (SEC-10)

**Files:**
- New `apps/backend/src/common/interfaces/http/middleware/rate_limit.py`
- Wire `slowapi` or equivalent
- Apply per-endpoint limits (login: 10/min, others: 120/min)

**Acceptance criteria:**
- [ ] Login brute-force rejected after 10 attempts/min
- [ ] Per-tenant rate limiting

**Effort:** M (3-5 days)

---

### F-35 — SSRF allowlist on webhook URLs (P1)

**Audit ref:** §14 (SEC-11)

**Files:**
- `apps/backend/src/common/domain/ssrf.py` (new — URL validator)
- `apps/backend/src/payments/application/payment_service.py:166-167` (validate before passing to Razorpay)

**Acceptance criteria:**
- [ ] `success_url`/`cancel_url` validated against an allowlist
- [ ] Internal IPs (10/8, 192.168/16, etc.) blocked

**Effort:** M (3-5 days)

---

## Phase 1 Verification

Before exiting Phase 1:

- [ ] Customer pilot can book + pay + check-in + cancel end-to-end
- [ ] Admin can manage facilities, resources, users, invoices, bookings
- [ ] Coverage ≥ 80% on services, ≥ 85% on domain
- [ ] E2E suite covers: register → book → pay → cancel
- [ ] Single-tenant smoke test passes for 1 week with no P0/P1 incidents

---

## Phase 2 — SaaS Launch Readiness

> **Goal:** Onboard a second tenant. Multi-tenant safety proven.

**Duration:** 4-6 weeks · **Engineers:** 2 (1 backend, 1 frontend)

### F-17 — Membership module (continued)

If not done in Phase 1: complete membership (backend + frontend) — see §5 (D4), §20 (TD-1).

### TD-2 — Notifications module (P1)

**Files:**
- New `apps/backend/src/notifications/` (DDD)
- SES / Postmark provider
- `apps/web-pwa/src/features/notifications/`

**Acceptance criteria:**
- [ ] Email on booking confirmation, cancellation, invoice issued
- [ ] SMS via Twilio for same-day reminders

**Effort:** XL

### TD-3 — Analytics module (P2)

**Files:**
- New `apps/backend/src/analytics/` (read-only replicas or materialized views)

**Acceptance criteria:**
- [ ] Owner dashboard renders real revenue / occupancy / churn metrics

**Effort:** L

---

## Phase 3 — Post-Launch Scaling

### Backend

- Read replicas (modify `BaseRepository` to route by query)
- Connection pool tuning per-tenant
- Multi-region deployment (`docs/02-architecture/disaster-recovery.md`)

### Observability

- Metrics endpoint (`/metrics`) using `prometheus_client`
- Distributed tracing via OpenTelemetry (`opentelemetry-instrumentation-fastapi`)
- Log aggregation (Datadog / Grafana)

### Frontend

- Background Sync API for offline mutations
- Push notifications (VAPID)
- Service worker updates with user prompt (not `autoUpdate`)

### Security

- Pen test by external firm
- SOC 2 compliance
- DPDPA audit
- PCI-DSS scope review

---

## Work Stream Map

| Work Stream | Findings | Phase |
|---|---|---|
| **Security hardening** | F-01, F-02, F-03, F-04, F-06, F-34, F-35 | 0, 1 |
| **Payment trust** | F-05, F-07, F-08, F-09, F-24 | 0, 1 |
| **Booking business rules** | F-25, F-26 | 1 |
| **Architecture cleanup** | F-10, F-11, F-12, F-40 | 0, 1, 2 |
| **Testing recovery** | F-14, F-15, F-16, F-22 | 0, 1 |
| **DevOps / Production** | F-13, F-38 | 0, 1 |
| **Membership + missing modules** | F-17, F-32, F-33, TD-2, TD-3 | 1, 2 |
| **Frontend polish** | F-18, F-29, F-31, F-36, F-43 | 0, 1 |
| **PWA resilience** | F-19, F-30 | 0, 1 |
| **Performance** | F-27, F-28, F-45 | 1 |
| **AI-readiness** | F-12, F-40, F-41 | 0, 1 |
| **Database hygiene** | F-20, F-21, F-22, F-42, F-44 | 0, 1 |
| **Backend cleanup** | F-23, F-39 | 1 |

---

## Dependency Graph

```
F-01 ─┐
F-04 ─┤
       ├─► F-03 ─► F-14 ─► F-15 ─► F-12
F-02 ─┘        │
                ├─► F-13 (CI)
F-06 (independent)
                │
F-07 ─┐
F-08 ─┤
       ├─► F-24 (idempotency)
F-09 ─┘

F-05 ─► F-19 (offline booking)         F-10 (independent)
                                       F-11 (independent, large)
                                       F-22 ─► F-14 (unblocks tests)

F-25 ─► F-17 ─► F-26 ─► F-32 (membership UX)
        └─► F-33 (check-in UX)
```

Critical path: **F-01 → F-02 → F-03 → F-14 → F-15 → F-12**.

---

## Quick Wins (≤ 1 day each)

These can be tackled in parallel by any engineer with no coordination:

| Item | Effort | Why quick |
|---|---|---|
| F-09 | S | Define missing `app_url` setting |
| F-06 | S | Add tenant filter to one query |
| F-04 | S | Remove default JWT secret |
| F-22 | S | Add explicit FK constraint names |
| F-23 | S | Move `reset_context()` to `finally` |
| F-24 | S | Make idempotency key required |
| F-20 | S | Add FK on `customer.tenant_id` |
| F-29 | S | Add React `ErrorBoundary` |
| F-31 | S | Move user menu in mobile sidebar |
| F-30 | S | Add iOS meta tags |
| F-27 | S | Vite manual chunks |
| F-28 | S | Add composite index |
| F-38 | S | Non-root container user |
| F-39 | S | Doc-code drift sync |

That's **14 quick wins** that collectively close ~6 P0s and ~6 P1s in roughly **2 engineer-days total** if parallelized.

---

## Tracking & Verification

### Per-finding DoD

Every finding must satisfy:

1. **Code change** lands on `main` via PR
2. **Tests** added (unit + integration as appropriate)
3. **Docs** updated (handbook, README, inline)
4. **Verification** by a second reviewer (mandatory for P0/P1)
5. **Re-run audit** — finding marked resolved in `CODEBASE_REVIEW.md`

### Per-phase exit criteria

- **Phase 0 exit:** 0 P0 findings open; penetration-test scenarios blocked
- **Phase 1 exit:** Splashh pilot runs 4 weeks without P0/P1 incident
- **Phase 2 exit:** 2nd tenant onboarded with RLS-confirmed isolation

### Reporting

Weekly status update:
- Findings opened (newly discovered during implementation)
- Findings closed (with PR link)
- Coverage %
- CI status

### When to re-audit

After every Phase exit, re-run this audit. The scorecard in `CODEBASE_REVIEW.md` should trend upward. If it doesn't, investigate why.

---

## Appendix A — Findings-to-Card Index

| Finding | Phase | Stream | Card section |
|---|---|---|---|
| F-01 | 0 | Security hardening | F-01 |
| F-02 | 0 | Security hardening | F-02 |
| F-03 | 0 | Security hardening | F-03 |
| F-04 | 0 | Security hardening | F-04 |
| F-05 | 0 | Payment trust | F-05 |
| F-06 | 0 | Security hardening | F-06 |
| F-07 | 0 | Payment trust | F-07 |
| F-08 | 0 | Payment trust | F-08 |
| F-09 | 0 | Payment trust | F-09 |
| F-10 | 0 | Architecture cleanup | F-10 |
| F-11 | 0 | Architecture cleanup | F-11 |
| F-12 | 0 | AI-readiness | F-12 |
| F-13 | 0 | DevOps | F-13 |
| F-14 | 0 | Testing recovery | F-14 |
| F-15 | 0 | Testing recovery | F-15 |
| F-16 | 0 | Testing recovery | F-16 |
| F-17 | 1 | Membership | F-17 |
| F-18 | 0 | Frontend polish | F-18 |
| F-19 | 0 | PWA resilience | F-19 |
| F-20 | 1 | DB hygiene | F-20 |
| F-21 | 1 | DB hygiene | F-21 |
| F-22 | 1 | DB hygiene | F-22 |
| F-23 | 1 | Backend cleanup | F-23 |
| F-24 | 1 | Backend cleanup | F-24 |
| F-25 | 1 | Booking rules | F-25 |
| F-26 | 1 | Booking rules | F-26 |
| F-27 | 1 | Performance | F-27 |
| F-28 | 1 | Performance | F-28 |
| F-29 | 1 | Frontend polish | F-29 |
| F-30 | 1 | PWA resilience | F-30 |
| F-31 | 1 | Frontend polish | F-31 |
| F-32 | 1 | Membership | F-32 |
| F-33 | 1 | Membership | F-33 |
| F-34 | 1 | Security | F-34 |
| F-35 | 1 | Security | F-35 |
| F-36 | 1 | Frontend polish | F-36 |
| F-37 | 2 | Frontend polish | F-37 |
| F-38 | 1 | DevOps | F-38 |
| F-39 | 1 | Backend cleanup | F-39 |
| F-40 | 1 | Architecture cleanup | F-40 |
| F-41 | 1 | Architecture cleanup | F-41 |
| F-42 | 1 | DB hygiene | F-42 |
| F-43 | 2 | Architecture cleanup | F-43 |
| F-44 | 3 | DB hygiene | F-44 |
| F-45 | 2 | Performance | F-45 |
