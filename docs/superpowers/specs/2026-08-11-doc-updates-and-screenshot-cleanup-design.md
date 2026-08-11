# Doc Updates + Screenshot Cleanup — Design

**Date:** 2026-08-11
**Status:** Approved
**Scope:** Targeted doc-drift fixes + remove leftover Playwright MCP session output

---

## Context

A long Playwright MCP session captured 7 PNG screenshots and a `.playwright-mcp/`
directory into the repo root. These are session artifacts, not reference images, and
they were left as untracked files. Separately, the documentation in `docs/` has drifted
from the shipped codebase: the most visible gap is `docs/18-modules/payments.md`, which
describes a Stripe-based design that was never implemented. We shipped Razorpay
payment links (INR-only) with HMAC-verified webhooks in commit `5f17ad5`.

This spec captures the targeted doc fixes and the cleanup of leftover session output.
It does **not** perform a full doc-vs-code audit (deferred) and does **not** implement
the membership module (next plan after this one).

---

## Goals

1. Remove the 7 PNGs and `.playwright-mcp/` from the repo root.
2. Prevent future Playwright MCP output from polluting the repo.
3. Update the docs that most directly mislead a new contributor:
   - `payments.md` (Stripe → Razorpay, accurate endpoint + event list)
   - `README.md` (status table reflects payments as shipped)
   - `18-modules/README.md` (Module Structure section reflects actual DDD layout)
   - `membership.md` (clearly marked as not yet implemented)

## Non-Goals

- Full doc-vs-code audit across `docs/`
- Drift fixes in `auth.md`, `flow-*.md`, `00-handbook/`, `04-backend/`, `09-security/`
- Membership module implementation
- OpenAPI codegen or any tooling change

---

## Work Items

### 1. Cleanup commit — `chore: remove untracked screenshots, ignore future Playwright MCP output`

**Files to delete:**
- `admin-facilities.png`
- `customer-bookings.png`
- `customer-facilities.png`
- `login-page-customer.png`
- `mobile-drawer-open.png`
- `mobile-facilities-closed.png`
- `user-menu-open.png`
- `.playwright-mcp/` (directory)

**`.gitignore` addition** (append to end of file):

```gitignore
# Playwright MCP session output (scratch artifacts)
.playwright-mcp/
```

Existing `.gitignore` already covers `playwright-report/` and `test-results/`, so
only the MCP-specific directory is missing.

### 2. Payments doc — `docs(payments): align module doc with shipped Razorpay implementation`

`docs/18-modules/payments.md` currently describes Stripe. Rewrite to match reality
as of commit `5f17ad5`.

**Aggregates — replace Stripe-specific field names with Razorpay ones:**

- `Payment.razorpay_payment_link_id` (not `stripe_payment_intent_id`)
- `Payment.razorpay_payment_id` (set when webhook fires)
- `Refund.razorpay_refund_id` (not `stripe_refund_id`)
- `Invoice` — add `description: str | None` (already in code)

**Endpoints — replace the 13 invented endpoints with the 6 actually shipped** (from
`apps/backend/src/payments/interfaces/http/router.py`):

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/payments/invoices` | tenant_admin | Optional `Idempotency-Key` |
| `GET`  | `/payments/invoices` | any authed | Filter by `status`, `customer_id`; customers see only their own |
| `GET`  | `/payments/invoices/{invoice_id}` | any authed | 404 on missing/unauthorized |
| `POST` | `/payments/invoices/{invoice_id}/payment-link` | customer only | **Requires `Idempotency-Key`** |
| `POST` | `/payments/invoices/{invoice_id}/refund` | tenant_admin only | **Requires `Idempotency-Key`**, body `{ reason }` |
| `POST` | `/webhooks/razorpay` | public | HMAC-SHA256 via `X-Razorpay-Signature` header |

Remove the `/payments/methods` section entirely — not implemented, out of scope.

**Events — replace invented events with the four actually emitted** (from
`apps/backend/src/payments/application/payment_service.py` + `application/events.py`):

| Event | When | Consumed by |
|---|---|---|
| `InvoiceCreated` | After invoice persisted | notifications, analytics |
| `InvoicePaid` | After Razorpay `payment.captured` webhook | booking (confirm), membership (activate), notifications |
| `PaymentFailed` | After Razorpay `payment.failed` webhook | booking (cancel), notifications |
| `RefundIssued` | After `refund_invoice` completes | notifications, analytics |

Drop the duplicated `InvoiceGenerated`/`InvoiceSent`/`PaymentAuthorized`/`PaymentCaptured`
rows — those don't exist in code.

**Invariants — update:**

1. Idempotency — same request must not double-charge
2. No double-capture — handled by Razorpay payment-link lifecycle
3. Refund limit — Full-refund only at this stage (`RefundRequest` accepts `reason` only; partial refunds are an open question)
4. **INR only** — `INR` is the only accepted currency (paise-denominated value object)
5. **No stored card data** — Razorpay-hosted page is the only payment surface; we never see PAN/CVV

**Open Questions** — keep the partial-refunds question (NOT yet implemented;
`RefundRequest` only accepts `reason`). Drop the payment-plans question
(out of scope).

**Related Documents** — point to `flow-payment.md` and the secrets-management doc.

### 3. Top-level README — `docs(README): mark payments as shipped; reference membership worktree`

`README.md`:

- In "What's in this prototype" table, add a row:
  - `payments` | **Working** | Razorpay payment links + webhooks (INR); admin invoice list, customer pay page
- Remove "Stripe/Razorpay integration" from the "Next phase" list.
- Add a single sentence in "Next phase" noting that `feature/membership-v1`
  is in progress (keeps the README honest about active work without listing
  every in-flight branch).

### 4. Modules README — `docs(modules): update Module Structure to actual DDD layout`

`docs/18-modules/README.md`:

The current "Module Structure" section shows a flat layout
(`router.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`,
`events.py`, `exceptions.py`). Actual code uses DDD layering. Replace
the section with the real layout and a short rationale.

**New layout** (matches `apps/backend/src/{auth,payment,booking,customer,facility,common}/`):

```
module_name/
├── application/          # Use cases / orchestration
│   ├── service.py        # Public service class
│   ├── events.py         # Domain event publishers
│   └── providers.py      # External integrations (e.g. Razorpay)
├── domain/               # Pure business logic, no I/O
│   ├── entities.py       # Aggregates, entities
│   └── value_objects.py  # Money, IDs, status enums
├── infrastructure/       # Persistence and side-effecting adapters
│   ├── models.py         # SQLAlchemy ORM models
│   ├── repositories.py   # Data access
│   └── idempotency.py    # Module-specific persistence (if needed)
└── interfaces/           # Transport adapters
    └── http/             # FastAPI router, schemas, deps
        ├── router.py
        ├── schemas.py
        └── deps.py
```

Add a 2–3 sentence note on why: boundary discipline (domain has no
SQLAlchemy/Redis imports), testability (domain layer is pure),
multi-tenant RLS stays in infrastructure.

**Do not** touch the Module Map, Dependency Rules, or "How to Add a New
Module" sections — those are still accurate.

### 5. Membership doc — `docs(membership): mark module as not yet implemented`

`docs/18-modules/membership.md`:

Add a prominent status block at the top:

> **Status — Not yet implemented.** The backend module, alembic migration,
> router, and PWA pages do not exist in `apps/backend/src/` or
> `apps/web-pwa/src/`. Implementation is in progress on
> `feature/membership-v1`. See `docs/02-architecture/flow-membership.md`
> and the membership design doc for the current intent.

Leave the rest of the doc (Aggregates, Public APIs, Events, Dependencies,
Invariants) as-is — it represents the intended design, just not the
shipped reality.

---

## Commit Plan

Five commits, in this order:

1. `chore: remove untracked screenshots, ignore future Playwright MCP output`
2. `docs(payments): align module doc with shipped Razorpay implementation`
3. `docs(README): mark payments as shipped; reference membership worktree`
4. `docs(modules): update Module Structure to actual DDD layout`
5. `docs(membership): mark module as not yet implemented`

(Originally proposed as "two commits" — refined to five to make doc fixes
individually reviewable and trivially revertable.)

---

## Verification

- After each commit: `git status` clean, `git diff --stat HEAD~1` shows only intended files.
- After all commits: `git grep -l "stripe" apps/ docs/` returns no false positives in `payments.md`.
- After all commits: `git grep -l "Stripe" docs/18-modules/payments.md` is empty.
- After `.gitignore` change: `git status` should not list `.playwright-mcp/` even after recreating the dir.

---

## Risks

- **Low.** All changes are additive (new `.gitignore` rule) or replace doc text
  that already contradicted shipped code. No code changes; no behavior changes.
- Cross-reference links in `payments.md` may need to be re-checked after the rewrite.
- If `flow-payment.md` references Stripe specifically, that's out of scope for this spec.

---

## Related

- Commit `5f17ad5` — `Merge feature/payments-v1: Razorpay payments module`
- Commit `d543b0b` — `docs(membership): implementation plan (14 tasks)`
