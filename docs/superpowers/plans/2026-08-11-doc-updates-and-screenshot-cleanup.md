# Doc Updates + Screenshot Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove leftover Playwright MCP session output from the repo root, ignore future MCP session output, and fix four known doc-drift spots so a new contributor gets an accurate picture of the shipped codebase.

**Architecture:** Five small, independent commits. No code changes. Each commit is a self-contained, reviewable diff. Verification commands are given for every commit.

**Tech Stack:** Git, `git grep`, `find`, markdown.

## Global Constraints

- **Branch:** All work happens on `main` (this is doc/maintenance work; no code is being added).
- **Commit messages:** Conventional Commits (`chore:`, `docs(...)`). Sign-off line `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` on every commit.
- **No code changes** — this plan touches only `.png` files, one directory, `.gitignore`, and `.md` files in `docs/`.
- **Spec:** `docs/superpowers/specs/2026-08-11-doc-updates-and-screenshot-cleanup-design.md` is the source of truth. If any step conflicts with the spec, the spec wins.
- **Verification:** Every task ends with a verification block. Do not mark a task complete until verification passes.

---

## File Map

**Deleted:**
- `admin-facilities.png`
- `customer-bookings.png`
- `customer-facilities.png`
- `login-page-customer.png`
- `mobile-drawer-open.png`
- `mobile-facilities-closed.png`
- `user-menu-open.png`
- `.playwright-mcp/` (directory)

**Modified:**
- `.gitignore` — append `.playwright-mcp/` ignore rule
- `docs/18-modules/payments.md` — full rewrite to match shipped Razorpay implementation
- `README.md` — add `payments` to shipped table, add `feature/membership-v1` note, drop "Stripe/Razorpay" from Next phase
- `docs/18-modules/README.md` — replace Module Structure section with actual DDD layout
- `docs/18-modules/membership.md` — prepend "Not yet implemented" status block

**Created:** None.

---

## Task 1: Delete untracked screenshots and the Playwright MCP directory

**Files:**
- Delete: 7 PNGs and `.playwright-mcp/` (listed in File Map)

- [ ] **Step 1: Verify the files exist with the expected names**

Run:
```bash
ls -1 *.png 2>/dev/null; echo "---"; ls -1d .playwright-mcp 2>/dev/null; echo "done"
```

Expected output: exactly 7 lines of `.png` filenames matching the File Map, then `---`, then `.playwright-mcp`, then `done`. If any name differs, stop and reconcile before proceeding.

- [ ] **Step 2: Delete the 7 PNGs and the `.playwright-mcp/` directory**

Run:
```bash
rm -f admin-facilities.png customer-bookings.png customer-facilities.png \
      login-page-customer.png mobile-drawer-open.png mobile-facilities-closed.png \
      user-menu-open.png
rm -rf .playwright-mcp/
```

- [ ] **Step 3: Verify deletion**

Run:
```bash
ls -1 *.png 2>/dev/null; echo "---"; ls -1d .playwright-mcp 2>/dev/null; echo "done"
```

Expected output: both sections empty before `done`. (Only the 7 PNGs and the dir should be gone; everything else in the repo root stays.)

- [ ] **Step 4: Verify `git status` shows no new changes yet**

Run:
```bash
git status --short
```

Expected output: only the untracked files remaining from before the change (none related to PNGs or `.playwright-mcp/`). Specifically, the line `.playwright-mcp/` must not appear, and no `*.png` line must appear in repo-root untracked files.

**Do not commit yet — Task 2 adds the `.gitignore` rule first, and both go in the same commit.**

---

## Task 2: Append `.playwright-mcp/` to `.gitignore`

**Files:**
- Modify: `.gitignore` (append one comment + one pattern)

- [ ] **Step 1: Read the current `.gitignore` to confirm it ends without `.playwright-mcp/`**

Run:
```bash
tail -5 .gitignore
```

Expected output: ends with one of the existing rules (e.g. `.superpowers/`) — no `.playwright-mcp/` entry.

- [ ] **Step 2: Append the new rule**

Append this exact block to the end of `.gitignore` (keep a single trailing newline):

```gitignore

# Playwright MCP session output (scratch artifacts)
.playwright-mcp/
```

The full `.gitignore` should end with:
```
# Superpowers scratch (brainstorm mockups, SDD progress)
.superpowers/

# Playwright MCP session output (scratch artifacts)
.playwright-mcp/
```

Use the Edit tool to add the block, or `cat >> .gitignore` if editing in shell.

- [ ] **Step 3: Verify the rule is in place**

Run:
```bash
tail -4 .gitignore
```

Expected output: includes the comment and `.playwright-mcp/` line as the last non-empty line.

- [ ] **Step 4: Recreate the dir and confirm `git status` ignores it**

Run:
```bash
mkdir -p .playwright-mcp && touch .playwright-mcp/probe.png && git status --short
```

Expected output: `.playwright-mcp/probe.png` does **not** appear in the untracked list. Then clean up:

```bash
rm -rf .playwright-mcp/
```

- [ ] **Step 5: Commit the cleanup and `.gitignore` change together**

Run:
```bash
git add .gitignore
git commit -m "$(cat <<'EOF'
chore: remove untracked screenshots, ignore future Playwright MCP output

Clean up seven PNG screenshots and a .playwright-mcp/ directory left
behind by a long Playwright MCP session. Add .playwright-mcp/ to
.gitignore so future session output is filtered out automatically.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected output: one commit on `main`, message matches, files in the commit are exactly `admin-facilities.png` (deleted), `customer-bookings.png` (deleted), `customer-facilities.png` (deleted), `login-page-customer.png` (deleted), `mobile-drawer-open.png` (deleted), `mobile-facilities-closed.png` (deleted), `user-menu-open.png` (deleted), `.playwright-mcp/` (if tracked — likely not), and `.gitignore` (modified).

- [ ] **Step 6: Verify the commit**

Run:
```bash
git log -1 --stat
```

Expected: shows the commit with the expected file changes. Confirm the working tree is otherwise clean (no leftover untracked PNGs).

---

## Task 3: Rewrite `docs/18-modules/payments.md` to match shipped Razorpay code

**Files:**
- Modify: `docs/18-modules/payments.md` (full content replacement)

**Reference facts (verbatim from `apps/backend/src/payments/`):**
- `Invoice` (in `domain/entities.py`): has `description: str` (not optional in the entity, default empty string), `line_items: list[LineItem]`, status transitions: `DRAFT/PENDING → PAID/FAILED/REFUNDED`.
- `Payment`: has `razorpay_payment_id: str | None`, `razorpay_payment_link_id: str | None`, `idempotency_key: str | None`, `captured_at: datetime | None`.
- `Refund`: has `razorpay_refund_id: str | None`, `amount: Money`, `reason: str`, `status: RefundStatus` (`PENDING/COMPLETED/FAILED`).
- Events (in `application/events.py`): `InvoiceCreated`, `InvoicePaid`, `PaymentFailed`, `RefundIssued`. All carry `invoice_id` (optional) and `currency: str = "INR"`.
- Endpoints (in `interfaces/http/router.py`): the six listed in the spec.

- [ ] **Step 1: Confirm the file's current line count as a sanity baseline**

Run:
```bash
wc -l docs/18-modules/payments.md
```

Expected: `145 docs/18-modules/payments.md` (matches the read on 2026-08-11).

- [ ] **Step 2: Replace the entire file content with the rewritten version**

Overwrite `docs/18-modules/payments.md` with this exact content:

````markdown
# Payments Module

> Invoices, payment links, refunds, and Razorpay webhook handling.

The payments module manages **financial transactions** — creating invoices,
issuing Razorpay-hosted payment links, processing webhook events, and
issuing refunds. All amounts are denominated in INR (paise) and use a
`Money` value object. Card data is never stored; Razorpay is the only
payment surface.

---

## Purpose

The payments module:
- Creates invoices for one or more line items
- Issues Razorpay-hosted payment links for invoices
- Verifies and processes Razorpay webhook events (`payment.captured`, `payment.failed`, `refund.processed`)
- Issues refunds (full only at this stage) and emits refund events
- Enforces idempotency on all mutating endpoints via `Idempotency-Key`

---

## Aggregates

### Invoice

```python
class Invoice(AggregateRoot):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str
    status: InvoiceStatus           # DRAFT, PENDING, PAID, FAILED, REFUNDED
    subtotal: Money
    tax: Money
    total: Money
    due_date: date
    paid_at: datetime | None
    description: str
    line_items: list[LineItem]
    created_at: datetime
    updated_at: datetime

    def can_pay(self) -> bool: ...
    def can_refund(self) -> bool: ...
    def mark_paid(self, when: datetime) -> None: ...
    def mark_failed(self) -> None: ...
    def mark_refunded(self, when: datetime) -> None: ...
```

### Payment

```python
class Payment(AggregateRoot):
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    amount: Money
    status: PaymentStatus           # PENDING, CAPTURED, FAILED
    razorpay_payment_id: str | None       # set on payment.captured
    razorpay_payment_link_id: str | None  # set on link creation
    idempotency_key: str | None
    captured_at: datetime | None
    created_at: datetime

    def mark_captured(self, when: datetime) -> None: ...
```

### Refund

```python
class Refund(AggregateRoot):
    id: UUID
    tenant_id: UUID
    payment_id: UUID
    amount: Money
    status: RefundStatus            # PENDING, COMPLETED, FAILED
    razorpay_refund_id: str | None
    reason: str
    created_at: datetime
```

### TenantPaymentConfig

```python
class TenantPaymentConfig(AggregateRoot):
    tenant_id: UUID
    razorpay_account_id: str | None
    default_currency: str           # always "INR" at this stage
    created_at: datetime
    updated_at: datetime
```

---

## Public APIs

All endpoints are mounted under the FastAPI app. The `Idempotency-Key`
header is required on every mutating endpoint that touches Razorpay
(`/payment-link`, `/refund`) and optional (but recommended) on
`POST /payments/invoices`.

### Invoices

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/payments/invoices` | tenant_admin | Optional `Idempotency-Key`; body = `{ customer_id, description, due_date, line_items[] }` |
| `GET`  | `/payments/invoices` | any authenticated | Filterable by `status` and `customer_id`; customers see only their own invoices |
| `GET`  | `/payments/invoices/{invoice_id}` | any authenticated | Returns 404 to avoid leaking existence of unauthorized invoices |

### Payment Links

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/payments/invoices/{invoice_id}/payment-link` | customer only | **Requires `Idempotency-Key`**. Returns `{ short_url, razorpay_payment_link_id, expires_at }` |

### Refunds

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/payments/invoices/{invoice_id}/refund` | tenant_admin only | **Requires `Idempotency-Key`**; body = `{ reason }` (full refund only) |

### Webhooks

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/webhooks/razorpay` | public (signature-verified) | HMAC-SHA256 via `X-Razorpay-Signature` header; handles `payment.captured`, `payment.failed`, `refund.processed` |

---

## Events

All events are frozen dataclasses extending `DomainEvent`. `invoice_id` and
`customer_id` are present on every event for downstream correlation. `currency`
defaults to `"INR"`.

| Event | When | Consumed by |
|---|---|---|
| `InvoiceCreated` | After invoice is persisted | notifications, analytics |
| `InvoicePaid` | After Razorpay `payment.captured` webhook | booking (confirm), membership (activate), notifications |
| `PaymentFailed` | After Razorpay `payment.failed` webhook | booking (cancel), notifications |
| `RefundIssued` | After `refund_invoice` completes | notifications, analytics |

---

## Idempotency

Mutating endpoints accept an `Idempotency-Key` header. The
`IdempotencyStore` (in `payments/infrastructure/idempotency.py`) deduplicates
requests across retries:

- Backed by Redis with a PostgreSQL fallback
- Keys are scoped to `(tenant_id, idempotency_key)` and TTL-bounded
- Same key + same body → returns the original response
- Same key + different body → `Conflict` (409)

---

## Dependencies

**Upstream:**
- `auth` (tenant context, role check)
- `customer` (customer lookup for invoice creation)

**Downstream:**
- `booking` (consumes `InvoicePaid` to confirm a booking; `PaymentFailed` to cancel)
- `membership` (consumes `InvoicePaid` to activate a subscription — future work)
- `notifications` (consumes all four events)
- `analytics` (consumes all four events)

---

## Invariants

1. **Idempotency** — Same request must not double-charge
2. **No double-capture** — Handled by Razorpay payment-link lifecycle
3. **Refund limit** — Full refund only at this stage (`RefundRequest` accepts `reason` only); partial refunds are an open question
4. **INR only** — `default_currency` is `"INR"`; the `Money` value object is paise-denominated
5. **No stored card data** — Razorpay-hosted page is the only payment surface; we never see PAN/CVV
6. **Tenant isolation** — Every query is scoped by `tenant_id`; customers can only read their own invoices

---

## Webhook Security

- The `/webhooks/razorpay` endpoint is the only public (unauthenticated) payment endpoint
- Requests are verified using `razorpay.Client.utility.verify_webhook_signature`
- Missing or invalid `X-Razorpay-Signature` header → `400`
- Successful processing is **idempotent on Razorpay event id** — duplicate webhook deliveries are silently dropped

---

## Open Questions

- Partial refunds (`RefundRequest.amount` optional) — Deferred; today, refunds are always full
- Multi-currency support — Deferred; INR is the only accepted currency
- Payment plans / installments — Out of scope

---

## Related Documents

- [Payment Flow](../../02-architecture/flow-payment.md)
- [Secrets Management](../../09-security/secrets-management.md)
- [Idempotency Pattern](../../02-architecture/caching-strategy.md#idempotency)
- [Booking Module](./booking.md)
````

- [ ] **Step 3: Verify no `Stripe` references remain**

Run:
```bash
grep -n -i "stripe" docs/18-modules/payments.md
```

Expected: no output (zero matches, case-insensitive).

- [ ] **Step 4: Verify the four event names appear in the file**

Run:
```bash
grep -n -E "InvoiceCreated|InvoicePaid|PaymentFailed|RefundIssued" docs/18-modules/payments.md
```

Expected: at least one match per event name.

- [ ] **Step 5: Verify the six endpoints appear in the file**

Run:
```bash
grep -n -E "^\| \`(POST|GET)\`" docs/18-modules/payments.md
```

Expected: exactly 6 matches (3 invoices, 1 payment-link, 1 refund, 1 webhook).

- [ ] **Step 6: Commit the rewrite**

Run:
```bash
git add docs/18-modules/payments.md
git commit -m "$(cat <<'EOF'
docs(payments): align module doc with shipped Razorpay implementation

The previous text described a Stripe-based design that was never
implemented. As of commit 5f17ad5, the payments module uses Razorpay
payment links (INR-only) with HMAC-verified webhooks. Rewrite the
aggregates, endpoints, events, dependencies, and invariants sections
to match the actual code in apps/backend/src/payments/. Keep the
"partial refunds" open question — RefundRequest only accepts reason
at this stage.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected output: one commit on `main` modifying only `docs/18-modules/payments.md`.

- [ ] **Step 7: Verify the diff scope**

Run:
```bash
git show --stat HEAD
```

Expected: exactly one file changed (`docs/18-modules/payments.md`).

---

## Task 4: Update `README.md` — payments shipped, membership worktree in progress

**Files:**
- Modify: `README.md` (status table + Next phase section)

- [ ] **Step 1: Locate the "What's in this prototype" table in `README.md`**

Read `README.md` lines 96–115 (the table is there per the 2026-08-11 snapshot).

- [ ] **Step 2: Add a `payments` row to the shipped-modules table**

In the table that starts `| Module | Status | Notes |`, add a new row immediately after the `booking` row (and before any closing `|---|---|---|---|`):

```markdown
| `payments` | Working | Razorpay payment links + webhooks (INR); admin invoice list, customer pay page; HMAC-verified webhooks |
```

After the edit, the table should have 6 rows: `common`, `auth`, `customer`, `facility`, `booking`, `payments`, `web-pwa` (verify `web-pwa` is still the last row — do not reorder it).

- [ ] **Step 3: Update the "Next phase" section**

The current "Next phase" list contains (in order):
- Push notifications
- OpenAPI client codegen
- Stripe/Razorpay integration
- SMS / email notifications
- Background workers
- Production deploy / CI-CD

Make these changes:
- Delete the line `Stripe/Razorpay integration` entirely
- Add a single new bullet at the end of the list:
  ```markdown
  - `membership` module — in progress on `feature/membership-v1` worktree
  ```

After the edit, the "Next phase" section should have 6 bullets, in order, none of which mention Stripe.

- [ ] **Step 4: Verify no `Stripe` references remain in `README.md`**

Run:
```bash
grep -n -i "stripe" README.md
```

Expected: no output.

- [ ] **Step 5: Verify the new bullets are present**

Run:
```bash
grep -n -E "^\| \`payments\`|feature/membership-v1" README.md
```

Expected: at least one match per pattern (one for the table row, one for the new bullet).

- [ ] **Step 6: Commit the README change**

Run:
```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs(README): mark payments as shipped; reference membership worktree

The payments module was merged in 5f17ad5 but README still listed
"Stripe/Razorpay integration" under Next phase. Move it into the
shipped-modules table, drop the Next-phase line, and add a single
bullet noting that the membership module is in progress on
feature/membership-v1.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected output: one commit on `main` modifying only `README.md`.

---

## Task 5: Update `docs/18-modules/README.md` Module Structure to DDD layout

**Files:**
- Modify: `docs/18-modules/README.md` (replace only the "Module Structure" section)

- [ ] **Step 1: Read the current "Module Structure" section to confirm boundaries**

The section starts with `## Module Structure` (around line 108) and ends just before `## How to Add a New Module` (around line 130). Confirm this by reading lines 108–132 of `docs/18-modules/README.md`.

- [ ] **Step 2: Replace the "Module Structure" section**

Replace the entire section (from the `## Module Structure` heading through the last line of the `module_name/` tree block, i.e. through the `└── tests/` block) with this new content:

````markdown
## Module Structure

Each backend module is organized by **DDD layer**, not by file role. The
layering enforces boundary discipline: the `domain/` layer has no
SQLAlchemy, Redis, or FastAPI imports, which keeps the core business
logic testable in isolation and keeps multi-tenant RLS concerns in
`infrastructure/`.

```
module_name/
├── application/             # Use cases / orchestration (depends on domain + infrastructure)
│   ├── service.py           # Public service class (e.g. PaymentService, BookingService)
│   ├── events.py            # Domain event publishers
│   └── providers.py         # External integrations (e.g. Razorpay, email)
├── domain/                  # Pure business logic, no I/O
│   ├── entities.py          # Aggregates and entities (dataclasses)
│   └── value_objects.py     # Money, IDs, status enums
├── infrastructure/          # Persistence and side-effecting adapters
│   ├── models.py            # SQLAlchemy ORM models
│   ├── repositories.py      # Data access
│   └── idempotency.py       # Module-specific persistence (only when needed)
└── interfaces/              # Transport adapters
    ├── __init__.py          # Public API exports (router, deps)
    └── http/                # FastAPI adapter
        ├── router.py        # Route handlers
        ├── schemas.py       # Pydantic request/response models
        └── deps.py          # FastAPI dependency-injection wiring
```

`common/` follows the same shape but contributes shared base classes
(`AggregateRoot`, `BaseRepository`) used by 3+ modules.

**Do not:**
- Add SQLAlchemy or Redis imports to `domain/`
- Put business logic in `interfaces/` — handlers should be thin
- Create a top-level `service.py` or `router.py` in the module root

**Test files** live inside the module at `tests/test_<layer>.py`
(e.g. `tests/test_service.py`, `tests/test_integration.py`).
````

- [ ] **Step 3: Verify the old flat layout is gone**

Run:
```bash
grep -n -E "router\.py|service\.py|repository\.py|schemas\.py" docs/18-modules/README.md
```

Expected: the matches should appear only inside the **new** Module Structure section's tree, and only as paths inside the new `application/`, `interfaces/http/` sub-trees. The old flat listing (`router.py  # FastAPI routes` etc.) must not appear.

- [ ] **Step 4: Verify the new layer names appear**

Run:
```bash
grep -n -E "^(├──|│   ) (application|domain|infrastructure|interfaces)/?$|## Module Structure" docs/18-modules/README.md
```

Expected: the new layer directories appear in the tree block.

- [ ] **Step 5: Verify the Module Map, Dependency Rules, and "How to Add a New Module" sections are untouched**

Run:
```bash
grep -n -E "^## (Module Map|Dependency Rules|How to Add a New Module|Common Module|Related Documents)" docs/18-modules/README.md
```

Expected: those headings are still present (we only edited `## Module Structure`).

- [ ] **Step 6: Commit the change**

Run:
```bash
git add docs/18-modules/README.md
git commit -m "$(cat <<'EOF'
docs(modules): update Module Structure to actual DDD layout

The old doc described a flat layout (router.py / service.py /
repository.py at module root). Actual code uses DDD layering with
application/, domain/, infrastructure/, and interfaces/http/ subdirs.
Replace the section to match reality and add a short rationale on
why the layering matters (boundary discipline, testable domain,
RLS in infrastructure).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected output: one commit on `main` modifying only `docs/18-modules/README.md`.

---

## Task 6: Mark `docs/18-modules/membership.md` as not yet implemented

**Files:**
- Modify: `docs/18-modules/membership.md` (prepend status block)

- [ ] **Step 1: Read the current file header**

Read `docs/18-modules/membership.md` lines 1–10. Expected: starts with `# Membership Module` then a blockquote intro.

- [ ] **Step 2: Insert a status block immediately after the existing intro blockquote**

After the existing line 4 (`The membership module manages **subscription lifecycle** — plans, subscriptions, renewals, cancellations, and freezes.`) and before the `---` separator on line 6, insert this block:

```markdown

> **Status — Not yet implemented.** The backend module folder,
> alembic migration, FastAPI router, and PWA pages do not exist in
> `apps/backend/src/` or `apps/web-pwa/src/`. Implementation is in
> progress on `feature/membership-v1`. For the current intent, see
> [Membership Flow](../../02-architecture/flow-membership.md) and the
> membership design doc.
```

The full updated header should look like (with the existing blockquote preserved):

```markdown
# Membership Module

> Plans, subscriptions, renewals, and freezes.

The membership module manages **subscription lifecycle** — plans, subscriptions, renewals, cancellations, and freezes.

> **Status — Not yet implemented.** The backend module folder,
> alembic migration, FastAPI router, and PWA pages do not exist in
> `apps/backend/src/` or `apps/web-pwa/src/`. Implementation is in
> progress on `feature/membership-v1`. For the current intent, see
> [Membership Flow](../../02-architecture/flow-membership.md) and the
> membership design doc.

---

## Purpose
...
```

Use the Edit tool to insert the block, leaving the rest of the file (Aggregates, Public APIs, Events, Dependencies, Invariants) untouched.

- [ ] **Step 3: Verify the status block is present**

Run:
```bash
grep -n -E "Status — Not yet implemented|feature/membership-v1" docs/18-modules/membership.md
```

Expected: at least one match for the status phrase and one for the worktree name.

- [ ] **Step 4: Verify the rest of the doc is preserved (spot check)**

Run:
```bash
grep -n -E "^## (Purpose|Aggregates|Public APIs|Events|Dependencies|Invariants)" docs/18-modules/membership.md
```

Expected: all six `## ` section headings still present.

- [ ] **Step 5: Commit the change**

Run:
```bash
git add docs/18-modules/membership.md
git commit -m "$(cat <<'EOF'
docs(membership): mark module as not yet implemented

membership.md describes an intended design but the backend module,
migration, router, and PWA pages do not exist. Prepend a prominent
status block calling this out, link to flow-membership.md and the
design doc, and leave the rest of the file (Aggregates, Public APIs,
Events, Dependencies, Invariants) untouched since they represent
the intended design.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected output: one commit on `main` modifying only `docs/18-modules/membership.md`.

---

## Final Verification

After all six tasks are complete:

- [ ] **F1: `git log -6 --oneline` shows the expected commits in order**

Run:
```bash
git log -6 --oneline
```

Expected: the most recent 6 commits (oldest first) are:
1. The pre-existing commit before any of this work
2. `chore: remove untracked screenshots, ignore future Playwright MCP output`
3. `docs(payments): align module doc with shipped Razorpay implementation`
4. `docs(README): mark payments as shipped; reference membership worktree`
5. `docs(modules): update Module Structure to actual DDD layout`
6. `docs(membership): mark module as not yet implemented`

- [ ] **F2: `git grep -i stripe` returns no false positives in the changed docs**

Run:
```bash
git grep -i "stripe" -- README.md docs/18-modules/
```

Expected: no output.

- [ ] **F3: Working tree is clean**

Run:
```bash
git status
```

Expected: `nothing to commit, working tree clean`. No untracked PNGs, no `.playwright-mcp/`.

- [ ] **F4: `.gitignore` ignores `.playwright-mcp/`**

Run:
```bash
mkdir -p .playwright-mcp && touch .playwright-mcp/probe.png && git check-ignore -v .playwright-mcp/probe.png; rm -rf .playwright-mcp/
```

Expected output: a line beginning with `.gitignore:` confirming the ignore rule matched. (Then we remove the probe so the final tree is clean.)
