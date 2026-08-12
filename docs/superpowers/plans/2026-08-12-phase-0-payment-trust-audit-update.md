# Phase 0 Payment Trust — Audit Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mark F-05, F-07, F-08 as `✅ Resolved` in `docs/CODEBASE_REVIEW.md` since all three payment-trust P0 findings are already implemented in code (commit `7af5802`) with 88/88 tests passing.

**Architecture:** Three 1-line status-cell updates in the audit doc. No code changes. Single commit. Mirrors the Sub-project A pattern used for F-02/F-03/F-15 in commit `f2bdf39`.

**Tech Stack:** Markdown, git. No runtime dependencies.

## Global Constraints

- Only `docs/CODEBASE_REVIEW.md` is modified.
- No production code (`apps/backend/src/`) or test code (`apps/backend/tests/`) is touched.
- Status-cell format mirrors the existing resolved style: `✅ Resolved (`<commit-sha>`) — <one-line note>`.
- All three rows point at the same commit SHA (`7af5802`), the initial commit where F-05/F-07/F-08 were first implemented.
- Single commit message: `docs(review): mark F-05, F-07, F-08 resolved — payment trust fixes shipped in initial commit`.
- Verification commands run from the repo root unless otherwise stated.

---

## File Structure

This plan modifies 1 file across 1 task.

| File | Responsibility | Task |
|---|---|---|
| `docs/CODEBASE_REVIEW.md` (3 status cells: F-05 at line 681, F-07 at line 683, F-08 at line 684) | Mark F-05, F-07, F-08 as resolved | Task 1 |
| (no new files; no production code changes) | — | — |

---

## Tasks

### Task 1: Mark F-05, F-07, F-08 as resolved in audit doc

**Files:**
- Modify: `docs/CODEBASE_REVIEW.md:681` (F-05 status cell)
- Modify: `docs/CODEBASE_REVIEW.md:683` (F-07 status cell)
- Modify: `docs/CODEBASE_REVIEW.md:684` (F-08 status cell)

**Interfaces:**
- Consumes: nothing (no prior task in this plan)
- Produces: 3 lines in `docs/CODEBASE_REVIEW.md` that each end with `✅ Resolved` instead of `❌ Open`

**Reference (current state of each row):** all three rows currently end with `| ❌ Open |`. The pattern for `✅ Resolved` already exists in the same table at lines 677, 678, 680 (F-01, F-02, F-04).

**Audit doc row formats (verifying the existing pattern at lines 677-680):**

```
| **F-01** | Security | **P0** | `auth/infrastructure/token_service.py:34-113` | JWT uses HS256 instead of RS256 | ✅ Resolved (`ba12454`) — RS256 is production path; HS256 retained for dev/test only |
```

The status cell is the **last column** (after the pipe-separated columns: ID, Category, Priority, File, Description, Status). Each row is one line.

---

- [ ] **Step 1: Establish the baseline state**

Confirm the three target rows are currently `❌ Open`:

```bash
cd /home/soloengine/Github/splash_sports_management
grep -n "F-05 | \|F-07 | \|F-08 | " docs/CODEBASE_REVIEW.md
```

Expected: 3 lines, each ending with `| ❌ Open |`.

- [ ] **Step 2: Mark F-05 resolved**

Edit `docs/CODEBASE_REVIEW.md`. Find the F-05 row (line 681) and replace its trailing `| ❌ Open |` with:

```
| ✅ Resolved (`7af5802`) — BookingTariffModel + migration 0006; BookingCreate no longer accepts price_cents; server computes via compute_price() |
```

Use the Edit tool. `old_string` must be the exact existing row including leading columns — copy from the grep output above. The unique part is the F-05 ID plus the file path plus the description plus the trailing `| ❌ Open |`.

- [ ] **Step 3: Mark F-07 resolved**

Edit `docs/CODEBASE_REVIEW.md`. Find the F-07 row (line 683) and replace its trailing `| ❌ Open |` with:

```
| ✅ Resolved (`7af5802`) — webhook resolves tenant_id from payment.tenant_id (DB), never from notes |
```

- [ ] **Step 4: Mark F-08 resolved**

Edit `docs/CODEBASE_REVIEW.md`. Find the F-08 row (line 684) and replace its trailing `| ❌ Open |` with:

```
| ✅ Resolved (`7af5802`) — refund lookup uses get_by_razorpay_id_with_payment (tenant-scoped) |
```

- [ ] **Step 5: Verify all three rows updated cleanly**

```bash
cd /home/soloengine/Github/splash_sports_management
grep -n "F-05 | \|F-07 | \|F-08 | " docs/CODEBASE_REVIEW.md
```

Expected: 3 lines, each ending with `| ✅ Resolved (`7af5802`)` (the trailing `)` is followed by either end-of-line or `|`).

- [ ] **Step 6: Verify only the audit doc changed**

```bash
cd /home/soloengine/Github/splash_sports_management
git status --short
git diff --stat
```

Expected: `docs/CODEBASE_REVIEW.md` is the only modified file. No other files modified, no untracked files.

- [ ] **Step 7: Run payment tests to confirm no regression**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/unit/test_booking_tariff.py tests/payments/test_webhook_endpoint.py tests/payments/test_webhook_service.py tests/payments/test_refund_endpoint.py tests/payments/test_refund_service.py tests/payments/test_payment_link_endpoint.py tests/payments/test_payment_link_service.py tests/payments/test_repositories.py tests/payments/test_invoice_endpoints.py tests/payments/test_invoice_service.py tests/payments/test_value_objects.py tests/payments/test_idempotency_store.py tests/payments/test_entities.py tests/payments/test_payments_events.py tests/payments/test_provider.py --tb=no -q 2>&1 | tail -3
```

Expected: `88 passed` (or close to it — if a single test was renamed or merged, allow ±3). **0 failed.**

Note: `tests/payments/test_models_round_trip.py` may show as ERROR due to missing `aiosqlite`/`responses` packages in some environments; that is an environmental issue, not a regression from this plan. The audit-doc update touches no code, so cannot cause test failures.

- [ ] **Step 8: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add docs/CODEBASE_REVIEW.md
git commit -m "docs(review): mark F-05, F-07, F-08 resolved — payment trust fixes shipped in initial commit

F-05: BookingTariffModel + migration 0006_booking_tariffs; BookingCreate
  no longer accepts price_cents; server computes via compute_price().

F-07: webhook resolves tenant_id from payment.tenant_id (DB), never from
  user-controlled notes.

F-08: refund lookup uses get_by_razorpay_id_with_payment (tenant-scoped);
  get_by_razorpay_refund_id_any_tenant never existed.

Code shipped in 7af5802 (initial commit); 88/88 payment tests pass."
```

---

## Verification (after Task 1 lands)

- [ ] `grep -n "F-05 | \|F-07 | \|F-08 | " docs/CODEBASE_REVIEW.md` shows 3 lines ending with `✅ Resolved`
- [ ] `git log -1 --stat` shows only `docs/CODEBASE_REVIEW.md` modified
- [ ] Full payment + booking-tariff test suite: `88 passed, 0 failed` (or similar; allow minor count drift if test file renames)
- [ ] No `apps/backend/src/**` or `apps/backend/tests/**` files modified

## Out of scope for this plan

- Renaming `get_by_razorpay_payment_id_for_any_tenant()` → `get_by_razorpay_payment_id_for_webhook()` (hardening suggestion from spec; deferred to a future "Payment trust hardening" plan)
- F-09 audit-doc row update (`app_url` setting, shipped but not yet in audit doc refresh scope) — separate small plan
- F-24 audit-doc row update (`X-Idempotency-Key` required, shipped but not yet in audit doc refresh scope) — separate small plan
