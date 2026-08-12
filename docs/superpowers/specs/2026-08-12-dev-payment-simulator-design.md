# Dev Payment Simulator Design

> **For agentic workers:** This is a design spec. After approval, use superpowers:writing-plans to produce an implementation plan.

**Date:** 2026-08-12
**Status:** Design (pending user approval)
**Scope:** Add a self-hosted dev payment simulator so the customer payment flow can be exercised end-to-end locally without a real Razorpay account.

---

## Context

The codebase already has a `NullAdapter` (stub provider) at `apps/backend/src/payments/application/provider.py:51-93` that returns deterministic fake values for `create_payment_link`, `fetch_payment`, `create_refund`, and `verify_webhook`. Selection between providers is settings-driven (`payments_provider: Literal["razorpay", "null"]` in `settings.py:78`) and wired in `app.py:60-68`.

What `NullAdapter` does **not** do:

- It returns `https://stub.test/rzp/<id>` URLs that don't actually exist — the customer-facing redirect has nowhere to land.
- It accepts any webhook signature, so even if a developer manually POSTed a webhook, the production code path (HMAC verification, signature-dedup, event processing) is not exercised.
- There is no way to simulate failure paths (declines, abandoned checkouts, partial payments) for testing downstream behavior.

End result: backend devs can build features against the API contract, but **no one** — frontend dev, QA, demo prep, manual end-to-end testing — can walk through the customer payment flow locally without a real Razorpay test account.

This design adds a richer dev-only simulator that hosts a fake Razorpay checkout page on the backend itself, fires properly-signed webhooks to the real webhook handler, and supports the four scenarios a developer needs to test.

---

## Goal

When `DEV_PAYMENT_SIMULATOR_ENABLED=true`, the backend behaves like Razorpay for purposes of local development:

1. `create_payment_link` returns a backend-hosted URL (`/dev/mock-checkout/<id>?state=<jwt>`) instead of a Razorpay URL.
2. That URL serves a fake Razorpay-style checkout page with four buttons: **Pay**, **Decline**, **Pay partial**, **Abandon**.
3. Each non-Abandon button fires a properly-signed Razorpay-shaped webhook event to `/v1/payments/webhook` over HTTP, exercising the full production webhook code path.
4. Nothing below the provider boundary changes — `payment_service.py`, webhook handler, repositories, DB models, and idempotency all run unchanged.

When `DEV_PAYMENT_SIMULATOR_ENABLED=false`, the simulator code is not loaded and not reachable. Production behavior is unchanged.

---

## Non-goals

- Not a test fixture. `NullAdapter` stays as the minimal "for tests" stub. The simulator is for **dev environments and manual end-to-end testing**, not pytest.
- Not a UI for customers. The fake checkout page is plain HTML served from the backend, not styled like Razorpay's real checkout, not localized, not accessible beyond basic keyboard nav.
- Not a reconciliation simulator. Abandoned-checkout reconciliation is out of scope; existing behavior is preserved.
- Not a staging/production tool. The simulator refuses to start when `environment == "production"`.

---

## Decisions locked during brainstorming

1. **Full end-to-end checkout flow** as the primary use case (not just API mocking).
2. **Backend hosts the fake checkout page** at `/dev/mock-checkout/<link_id>` — not a frontend-only simulator route, not an admin-only trigger.
3. **Stateless state encoding** — the invoice/payment/customer context is carried in a signed JWT in the URL query string. No fake-payment persistence.
4. **All four failure scenarios supported**: capture (happy), decline, abandoned checkout, partial payment.
5. **Always-on simulator, gated by env flag** — the simulator code lives outside the `PaymentProvider` Protocol selection; `DEV_PAYMENT_SIMULATOR_ENABLED=true` causes `DevSimAdapter` to be used in place of `RazorpayAdapter`, regardless of `PAYMENTS_PROVIDER` value.
6. **Webhook fired via signed HTTP POST to `/v1/payments/webhook`** — uses `settings.razorpay_webhook_secret`, exercises the real signature-verification code path.

---

## Architecture

```
                       ┌─────────────────────────────────────────┐
                       │  web-pwa (customer browser)             │
                       └─────────────────────────────────────────┘
                              │  1. clicks 'Pay' on booking
                              ▼
   POST /v1/payments/{payment_id}/link  ──►  payment_service.create_payment_link
                              │              │
                              │              ▼
                              │      app.state.payment_provider
                              │              │
                              │              ▼  if DEV_PAYMENT_SIMULATOR_ENABLED:
                              │        DevSimAdapter.create_payment_link()
                              │              │  returns short_url = APP_URL +
                              │              │              "/dev/mock-checkout/<id>?state=<jwt>"
                              │
                              ▼
                       redirect to dev URL
                              │
                              ▼
   GET /dev/mock-checkout/<id>?state=<jwt>
                              │  ◄─── backend serves fake Razorpay-like HTML
                              ▼
   customer clicks [Pay] [Decline] [Pay partial ₹X] [Abandon]
                              │
                              ▼
   POST /dev/mock-checkout/<id>/{action}
                              │  ◄─── backend signs payload with razorpay_webhook_secret
                              │       and POSTs to /v1/payments/webhook
                              ▼
   /v1/payments/webhook  ──►  verify_webhook() (real path)
                              │       process webhook event
                              │       update payment + invoice state
                              ▼
                       payment.captured/failed  ──►  booking confirmed / held
```

**Three principles:**

1. **Zero changes to `payment_service.py`, webhook handler, webhook service, repositories, or DB layer.** Everything routes through existing code paths.
2. **`DevSimAdapter` satisfies the same `PaymentProvider` Protocol** as `RazorpayAdapter` — drop-in replacement.
3. **The dev router is mounted only when `DEV_PAYMENT_SIMULATOR_ENABLED=true`** — never reachable in prod.

---

## Components

### New files

| File | Responsibility |
|---|---|
| `apps/backend/src/payments/application/devsim_adapter.py` | `DevSimAdapter` class — implements `PaymentProvider` Protocol. Returns dev URLs instead of Razorpay URLs. |
| `apps/backend/src/payments/application/devsim_state.py` | `encode_state(payload) -> str` / `decode_state(token) -> payload` — HMAC-SHA256 signed JWT using `DEV_STATE_SECRET`. Stateless; no DB. |
| `apps/backend/src/payments/application/devsim_webhook.py` | `sign_and_post_webhook(event, payment_link_id)` — builds a Razorpay-shaped JSON event, signs it with `settings.razorpay_webhook_secret`, POSTs to `/v1/payments/webhook`. Uses `httpx.AsyncClient`. |
| `apps/backend/src/payments/interfaces/http/devsim_router.py` | FastAPI router for `/dev/mock-checkout/*` (HTML page + action endpoints). Mounted only when enabled. |
| `apps/backend/src/payments/interfaces/http/templates/devsim/checkout.html` | Jinja2 template for the fake checkout page. Shows invoice summary + 4 buttons. |

### Modified files

| File | Change |
|---|---|
| `apps/backend/src/common/infrastructure/settings.py` | Add `dev_payment_simulator_enabled: bool = False` and `dev_state_secret: str` with a documented non-prod-only default. |
| `apps/backend/src/common/interfaces/http/app.py` | (a) When `dev_payment_simulator_enabled=True`, instantiate `DevSimAdapter` instead of `RazorpayAdapter`. (b) Mount the devsim router under `/dev`. Log a startup warning that dev simulator is active. |
| `apps/backend/.env.example` (or equivalent) | Document the new env vars + a "DEV ONLY" comment. |
| `apps/backend/tests/payments/test_devsim_adapter.py` | New tests: state encode/decode round-trip, tamper rejection, expiry, all 4 action buttons produce correctly signed webhooks. |
| `apps/backend/tests/payments/test_devsim_router.py` | New tests: router only mounted when flag is true; HTML page renders; each action endpoint fires the right webhook shape. |

### Untouched

`payment_service.py`, webhook endpoint, webhook service, repositories, DB models, idempotency store, value objects, `null_adapter.py`. Everything below the provider boundary runs unchanged.

### File-layout reasoning

Group devsim code under `payments/` (not a separate `devsim/` module) because:

- It satisfies the existing `PaymentProvider` Protocol.
- It generates real `payment.captured` / `payment.failed` events that the existing webhook handler consumes.
- It is logically a payments concern that just happens to have a UI surface.

The devsim router goes under `interfaces/http/` to match the existing module pattern (webhook router, payment_link router, refund router all live there).

---

## Data flow

### Common prefix: create_payment_link

1. Customer on web-pwa clicks **Pay** on a booking.
2. `POST /v1/payments/{payment_id}/link` (existing endpoint, unchanged).
3. `payment_service.create_payment_link(...)` calls `provider.create_payment_link(...)`.
4. With devsim enabled, `DevSimAdapter.create_payment_link`:
   - Generates `link_id = f"plink_dev_{uuid4().hex[:16]}"`.
   - Builds state payload: `{tenant_id, invoice_id, payment_id, amount_paise, currency, line_items, exp, iat}`.
   - Signs with `settings.dev_state_secret` → `state_token`.
   - Returns `PaymentLinkResult(short_url=f"{APP_URL}/dev/mock-checkout/{link_id}?state={state_token}", razorpay_payment_link_id=link_id, razorpay_order_id=None, expires_at=now+24h)`.
5. web-pwa redirects browser to `short_url`.
6. Backend serves `GET /dev/mock-checkout/{link_id}?state=...` → renders `checkout.html` (shows invoice summary + 4 buttons).

### Happy path: Pay (full capture)

1. Customer clicks **Pay ₹X.XX**.
2. `POST /dev/mock-checkout/{link_id}/capture` (form submit, no JS required).
3. Router validates `state` JWT (signature + expiry), reconstructs payload.
4. Router builds Razorpay-shaped event:
   ```json
   {
     "entity": "event",
     "account_id": "acc_dev",
     "event": "payment.captured",
     "contains": ["payment"],
     "payload": {
       "payment": {
         "entity": {
           "id": "pay_dev_<16hex>",
           "amount": <amount_paise>,
           "currency": "INR",
           "status": "captured",
           "description": "<invoice line items joined>",
           "notes": {
             "tenant_id": "<tenant_id>",
             "invoice_id": "<invoice_id>",
             "payment_id": "<payment_id>",
             "payment_link_id": "<link_id>"
           }
         }
       }
     },
     "created_at": <unix_ts>
   }
   ```
5. Router signs payload: `signature = HMAC_SHA256(razorpay_webhook_secret, payload)`.
6. Router POSTs `httpx.AsyncClient.post(f"{request_base_url}/v1/payments/webhook", content=payload_bytes, headers={"X-Razorpay-Signature": signature})`, where `request_base_url = request.url.scheme + "://" + request.url.netloc`. (We POST to the request's own origin, not `APP_URL`, because `APP_URL` points at the frontend, not the backend.)
7. Existing webhook handler validates signature → resolves tenant from `notes.tenant_id` (DB lookup per F-07) → marks payment captured → emits `PaymentCaptured` event → booking gets confirmed (existing logic).
8. Router returns HTML success page: "Payment successful — your booking is confirmed" + redirect link back to web-pwa booking page.

### Decline

1. Customer clicks **Decline**.
2. `POST /dev/mock-checkout/{link_id}/decline`.
3. Same flow as capture but builds `event: payment.failed` with `payload.payment.entity.status = "failed"`, `error_description: "Payment declined by user"`.
4. Existing webhook marks payment failed → emits `PaymentFailed` event → booking stays in `awaiting_payment`.
5. HTML returns "Payment failed" + link back to retry.

### Abandon (timeout)

1. Customer clicks **Abandon** or closes the page.
2. Nothing happens. NO webhook is fired. (Real Razorpay does this — abandoned payments eventually expire; reconciliation job picks them up.)
3. Reconciliation behavior is unchanged.
4. If user re-opens the URL, the page still renders (state JWT still valid until `exp`). They can still pay or decline.

### Partial payment

1. Customer enters partial amount (e.g., ₹50 of ₹100 invoice) in a small input field on the page.
2. Clicks **Pay partial**.
3. `POST /dev/mock-checkout/{link_id}/capture-partial` with form field `amount_paise`.
4. Router validates `0 < amount_paise <= invoice.amount_paise` (rejects otherwise with 400).
5. Same webhook flow as capture but with `payment.entity.amount = amount_paise` (less than invoice total).
6. Existing webhook handler processes — assumes downstream code handles partial state. If current code does not handle partial, that is an existing bug exposed by the simulator; it is flagged in the implementation plan but not fixed by it.

### What state we do NOT store

- No "pending link" table.
- No "fake payment" row.
- No Redis cache.
- Everything needed to construct the webhook event is in the state JWT or the invoice DB row.

### State JWT details

- Algorithm: HS256 (matches existing JWT infra).
- TTL: 24 hours from issue (matches `expires_at` on `PaymentLinkResult`).
- Payload: `{tenant_id, invoice_id, payment_id, payment_link_id, amount_paise, currency, line_items, exp, iat}`.
- Secret: `settings.dev_state_secret` — required, default allowed only in `environment=development`.
- Library: `pyjwt` (already a transitive dep of FastAPI ecosystem — verify in `pyproject.toml` before implementation).

---

## Settings + env

**New env vars (additions to `settings.py`):**

```python
dev_payment_simulator_enabled: bool = Field(
    default=False,
    description="DEV ONLY: replaces the real payment provider with a fake checkout "
                "page. Must be False in production.",
)
dev_state_secret: str = Field(
    default="dev-state-secret-change-me",
    description="HMAC secret used to sign the state JWT carried in the dev mock-checkout URL. "
                "MUST be overridden in any non-development environment.",
)
```

**Validation rules (enforced in `app.py` startup):**

- `if settings.environment == "production" and settings.dev_payment_simulator_enabled: raise RuntimeError(...)` — fails fast at app startup.
- `if settings.dev_payment_simulator_enabled and settings.environment != "development" and settings.dev_state_secret == "dev-state-secret-change-me": raise RuntimeError(...)` — refuses the default secret outside dev.
- `if settings.environment == "development" and settings.dev_state_secret == "dev-state-secret-change-me": _logger.warning("dev_state_secret_using_default")` — soft warn in dev.

**`.env.example` additions:**

```bash
# --- Dev Payment Simulator (NEVER enable in production) ---
DEV_PAYMENT_SIMULATOR_ENABLED=false
# DEV_STATE_SECRET must be set when DEV_PAYMENT_SIMULATOR_ENABLED=true
# DEV_STATE_SECRET=<generate a random 32+ char string>
```

**Startup log line** in `app.py` when enabled: `WARNING payment_simulator_active provider=devsim env=<env>`.

---

## Error handling

| Scenario | Response | User sees |
|---|---|---|
| State JWT signature invalid | 400 | HTML error page: "Invalid payment link — please return to the booking page." |
| State JWT expired (>24h) | 400 | "This payment link has expired — please request a new one." |
| State JWT tampered (e.g., amount changed in DB query) | 400 | Same as invalid signature. |
| `/dev/mock-checkout/{unknown_link_id}` | 404 | "Payment link not found." |
| Partial amount > invoice total | 400 (form re-render with error message) | "Amount exceeds invoice total of ₹X" |
| Partial amount <= 0 | 400 | "Amount must be positive." |
| Webhook POST to `/v1/payments/webhook` fails (5xx, network error) | 502 | "Could not reach payment processor — please retry." Form re-renders; no double-charge because webhook handler has its own idempotency dedup via F-24. |
| Click action twice (browser double-submit) | First POST succeeds; second POST hits webhook idempotency dedup (already shipped in F-24) and is a no-op | Same HTML success page. |

**Logging:** every devsim action logs `{event: devsim.action, link_id, tenant_id, payment_id, action, result}` at INFO. Tamper attempts log at WARNING with `event: devsim.state_tamper`.

**Idempotency:** the state JWT carries `payment_link_id` (deterministic), so duplicate POSTs produce webhook events with the same `entity.id`. The existing webhook idempotency dedup (F-24, `X-Idempotency-Key` + `ProcessedRazorpayEvent` table) catches and skips them.

---

## Testing

### Unit tests (new files)

`tests/payments/test_devsim_state.py`:

- `test_encode_decode_roundtrip`
- `test_decode_rejects_tampered_signature`
- `test_decode_rejects_expired_token` (use freezegun or backdate `exp`)
- `test_decode_rejects_wrong_secret`

`tests/payments/test_devsim_adapter.py`:

- `test_create_payment_link_returns_dev_url_with_signed_state`
- `test_state_payload_includes_invoice_amount_and_currency`
- `test_short_url_uses_app_url_from_settings`
- `test_refund_returns_deterministic_id` (so this still satisfies any refund tests)
- `test_verify_webhook_uses_real_signature_verification` — same path as RazorpayAdapter

`tests/payments/test_devsim_webhook.py`:

- `test_sign_and_post_produces_valid_signature` — verify the signature using `hmac.compare_digest`
- `test_event_shape_matches_razorpay_payment_captured` — JSON keys match what the webhook handler expects
- `test_httpx_post_called_with_correct_url` (mock httpx)

`tests/payments/test_devsim_router.py`:

- `test_router_not_mounted_when_flag_false`
- `test_get_checkout_renders_html_with_action_buttons`
- `test_post_capture_fires_webhook_and_returns_success_page`
- `test_post_decline_fires_payment_failed_webhook`
- `test_post_capture_partial_rejects_amount_exceeding_invoice`
- `test_post_capture_partial_uses_requested_amount`
- `test_post_with_invalid_state_returns_400`
- `test_post_with_expired_state_returns_400`

### Integration test

`tests/integration/test_devsim_end_to_end.py`:

- Full flow: create booking → create payment link → POST capture → assert webhook processed → assert booking status = confirmed.
- Uses `httpx.AsyncClient` + `ASGITransport` to call the devsim router from inside the same app.

### Negative test

`tests/payments/test_settings_prod_guard.py`:

- `test_prod_env_with_simulator_enabled_raises_on_app_creation`
- `test_non_dev_env_with_default_secret_raises`

### No-regression

All 88 existing payment tests (per F-05/F-07/F-08 plan) must still pass. Devsim code does not touch `payment_service.py`, webhook handler, or repositories.

---

## Risks

1. **Frontend URL misconfiguration.** The devsim's `short_url` (returned by `create_payment_link`) uses `settings.app_url`. If `app_url` is unset or points at a non-reachable host, the customer's browser redirect fails. Mitigation: this is the same risk Razorpay has in dev (customer browser can't reach real Razorpay), and the existing dev workflow already requires a reachable `app_url`; no new validation added beyond what already exists.

2. **Default secret in non-dev environments.** If someone copies a dev `.env` to staging, the default secret would silently work but be insecure. Mitigation: hard raise in non-dev environments when default secret is in use.

3. **Devsim HTTP POST loop.** The devsim POSTs to its own webhook endpoint. If the app is configured to route external traffic back through itself (e.g., behind a reverse proxy), this could in theory loop. Mitigation: devsim POSTs to the `BaseURL` of the request itself (`request.url.scheme://request.url.netloc/v1/payments/webhook`), never to a configured public URL.

4. **pyjwt not in deps.** HS256 signing for state JWT requires pyjwt. If it is not in `pyproject.toml`, the build will fail at import time. Mitigation: implementation plan Step 0 verifies pyjwt is present and adds it if not.

5. **Existing partial-payment handling.** Simulator exposes the partial-payment flow; if downstream webhook handler does not handle `amount < invoice.amount` correctly, the test for capture-partial will fail. This is acceptable — surfacing existing bugs is one of the simulator's values — but should be flagged in the plan as out-of-scope-to-fix.

---

## Out of scope

- Styling the fake checkout page to look like real Razorpay.
- Reconciling abandoned checkouts (no timeout fires; relies on existing reconciliation logic if any).
- A "list of recent dev payments" admin view.
- Multi-currency partial payments (only INR supported, matches RazorpayAdapter).
- Recurring/subscription payments (not in scope for v1).
- Replacing the `NullAdapter` (kept for unit tests that just need a deterministic stub).
