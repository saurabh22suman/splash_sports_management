# Phase 0 Payment Trust — Audit-Update Design

> **For agentic workers:** This is a design spec. After approval, use superpowers:writing-plans to produce an implementation plan.

**Date:** 2026-08-12
**Status:** Design (pending user approval)
**Scope:** Sub-project B of Phase 0 — close audit-doc drift for F-05, F-07, F-08.

---

## Context

The Phase 0 audit (`docs/CODEBASE_REVIEW.md`, 2026-08-11) identified 45 findings. F-05, F-07, and F-08 — the three P0 payment-trust findings — were implemented in code before the audit was written and shipped in the initial commit (`7af5802`). They have full test coverage that passes locally (88/88), but the audit doc still lists them as `❌ Open`.

Like Sub-project A (Phase 0 Security) where F-02, F-03, F-15 had the same drift, the right move is a 1-day audit-doc refresh — not a re-implementation.

**Sub-project A precedent (already shipped):** F-02/F-03/F-15 audit rows updated in commit `f2bdf39` ("docs(review): mark F-02, F-03, F-15 resolved…"). Same pattern applies here.

---

## Goal

Mark F-05, F-07, F-08 as `✅ Resolved` in `docs/CODEBASE_REVIEW.md`, with each row's status cell pointing at the implementing commit. No code changes.

---

## Why code is already shipped (verification evidence)

### F-05 — Server-computed booking price

**Audit's acceptance criteria:**
- [ ] `POST /v1/booking` no longer accepts `price_cents` from client
- [ ] Server looks up tariff by `(resource_id, start_at, day_of_week)` and writes the computed price
- [ ] Reject with 422 if no tariff configured
- [ ] `BookingOut` still returns `price_cents` for display

**Code verification:**
- `apps/backend/src/booking/interfaces/http/schemas.py:18-22` — `BookingCreate` has no `price_cents` field; comment at line 14-16: "price_cents is NOT accepted from client (F-05 security fix). Price is computed server-side from BookingTariff table."
- `apps/backend/src/booking/application/booking_service.py:30-69` — `compute_price()` function; comment: "This is the F-05 security fix: server computes price from BookingTariff instead of accepting client-controlled price_cents."
- `apps/backend/src/booking/application/booking_service.py:99-108` — `create_booking()` calls `compute_price()` when `price_cents is None`.
- `apps/backend/src/booking/infrastructure/models.py:52-79` — `BookingTariffModel` with all required columns and constraints.
- `apps/backend/alembic/versions/20260811_0006_booking_tariffs.py` — Migration that creates `booking_tariffs` table with RLS policy enabled.
- `apps/backend/src/booking/interfaces/http/schemas.py:42` — `BookingOut.price_cents` still returned for display.

**Test verification:** `tests/unit/test_booking_tariff.py` (8/8 pass) + `tests/api/test_booking_endpoints.py::TestBookingCreateSchema::test_booking_out_includes_price_for_display` (1/1 pass).

### F-07 — Webhook tenant_id from DB, not notes

**Audit's acceptance criteria:**
- [ ] Webhook handler never reads `tenant_id` from Razorpay payload metadata
- [ ] Tenant is resolved by looking up the invoice/payment record in DB
- [ ] Webhook with a forged `notes.tenant_id` is treated as if `tenant_id` matched the actual invoice owner

**Code verification:**
- `apps/backend/src/payments/application/payment_service.py:188-258` — `payment.captured` and `payment.failed` handlers; comments at lines 190 and 229: "F-07 Fix: Resolve tenant from DB, not from user-controlled notes."
- The handlers call `get_by_razorpay_payment_id_for_any_tenant(razorpay_payment_id)` first, then use `payment.tenant_id` (line 203, 241) for all subsequent operations. The `notes` dict is read only for non-tenant fields; `notes.tenant_id` is never used.

**Test verification:** `tests/payments/test_webhook_endpoint.py` (3 tests pass) + `tests/payments/test_webhook_service.py` (4 tests pass, including `test_webhook_payment_captured_marks_paid`, `test_webhook_dedup_by_event_id`, `test_webhook_payment_failed`, `test_webhook_refund_processed_marks_refund`).

### F-08 — Tenant-scoped refund lookup

**Audit's acceptance criteria:**
- [ ] Refund lookup uses invoice_id + razorpay_refund_id, both scoped by tenant
- [ ] Refund for Tenant A's invoice cannot be processed by Tenant B's session
- [ ] `get_by_razorpay_refund_id_any_tenant` removed

**Code verification:**
- `apps/backend/src/payments/application/payment_service.py:260-301` — `refund.processed` handler; comment at line 263: "F-08 Fix".
- The handler resolves tenant via `payment.tenant_id` (line 277), then calls `get_by_razorpay_id_with_payment(tenant_id, razorpay_payment_id, razorpay_refund_id)` (line 278-280) — the WHERE clause at `apps/backend/src/payments/infrastructure/repositories.py:240-250` includes `RefundModel.tenant_id == tenant_id` AND `PaymentModel.razorpay_payment_id == razorpay_payment_id` AND `RefundModel.razorpay_refund_id == razorpay_refund_id`.
- The unsafe `get_by_razorpay_refund_id_any_tenant` does not exist in the codebase (grep confirms).

**Test verification:** `tests/payments/test_refund_endpoint.py` (2 tests pass) + `tests/payments/test_refund_service.py` (3 tests pass, including `test_refund_invoice_creates_razorpay_refund` and `test_refund_invoice_409_on_pending`).

---

## Out-of-scope hardening (deferred)

This design does **not** touch:

1. **Renaming `get_by_razorpay_payment_id_for_any_tenant()`** — the function name suggests cross-tenant access, which could mislead future callers. The current usage is correct (only from webhook entrypoint), but a rename to `get_by_razorpay_payment_id_for_webhook()` would harden against misuse. Deferred to a follow-up "Payment trust hardening" spec.

2. **F-09 (`app_url` setting)** — separate P0 already shipped but not in scope of this sub-project. Audit doc row will be updated as part of the existing F-09 work tracked elsewhere.

3. **F-24 (`X-Idempotency-Key` required)** — already shipped in code (router.py rejects without header, line 136-138/172-174 per audit), audit-doc update deferred.

---

## Architecture

**Files modified (1 file, 3 rows):**

| File | Lines | Change |
|---|---|---|
| `docs/CODEBASE_REVIEW.md` | 681 | F-05 status cell: `❌ Open` → `✅ Resolved (`7af5802`) — BookingTariffModel + migration 0006; BookingCreate no longer accepts price_cents; server computes via compute_price()` |
| `docs/CODEBASE_REVIEW.md` | 683 | F-07 status cell: `❌ Open` → `✅ Resolved (`7af5802`) — webhook resolves tenant_id from payment.tenant_id (DB), never from notes` |
| `docs/CODEBASE_REVIEW.md` | 684 | F-08 status cell: `❌ Open` → `✅ Resolved (`7af5802`) — refund lookup uses get_by_razorpay_id_with_payment (tenant-scoped)` |

**Files NOT modified:**
- `apps/backend/src/**` — no production code change
- `apps/backend/tests/**` — no test change
- `apps/web-pwa/**` — no frontend change

---

## Components

There is no new component; this is purely a documentation refresh. The status-cell format mirrors the existing `✅ Resolved (`ba12454`)` style used at lines 677, 678, 680 for F-01/F-02/F-04.

---

## Data flow

Not applicable — this is a doc-only change with no runtime behavior.

---

## Error handling

Not applicable — the change is human-readable markdown; if a line is malformed, `git diff` will show it before commit.

---

## Testing

**Verification commands:**

```bash
# 1. Confirm the three rows updated cleanly
grep -n "F-05 | \|F-07 | \|F-08 | " docs/CODEBASE_REVIEW.md
# Expected: 3 lines, each ending with "✅ Resolved"

# 2. Confirm no production code changed
git diff --stat HEAD~1 HEAD
# Expected: only docs/CODEBASE_REVIEW.md appears

# 3. Confirm payment tests still green
cd apps/backend && PYTHONPATH=src pytest tests/unit/test_booking_tariff.py tests/payments/ --tb=no -q
# Expected: ~88 passed, 0 failed
```

---

## Verification (definition of done)

- [ ] F-05, F-07, F-08 rows in `docs/CODEBASE_REVIEW.md` show `✅ Resolved` with a one-line note referencing the implementing commit
- [ ] `git log --oneline -1` shows the audit-update commit
- [ ] `git diff HEAD~1 HEAD --stat` shows only `docs/CODEBASE_REVIEW.md` modified
- [ ] Full payment test suite (`tests/payments/` + `tests/unit/test_booking_tariff.py`) remains 88/88 green
- [ ] No `apps/backend/src/` files modified

---

## Risk

**Low.** Markdown-only change. If something is wrong with the wording, the next audit refresh can correct it; there is no runtime impact.

The only concern is the F-07 `_any_tenant` naming discussed in "Out-of-scope hardening" above — but that risk exists today and is not introduced by this change.
