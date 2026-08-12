# Dev Payment Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-hosted dev payment simulator so the customer checkout flow can be exercised end-to-end locally without a real Razorpay account.

**Architecture:** Two new pieces (a `DevSimAdapter` that satisfies the existing `PaymentProvider` Protocol, and a dev-only FastAPI router serving a fake Razorpay checkout page). The simulator fires real, HMAC-signed Razorpay-shaped webhooks over HTTP to the existing `/v1/payments/webhook` endpoint, exercising the full production code path. State is encoded in a signed JWT in the URL — fully stateless. Gated by `DEV_PAYMENT_SIMULATOR_ENABLED=true`; refuses to start in production.

**Tech Stack:** Python 3.12, FastAPI, pydantic-settings, pyjwt[crypto] (already a dep), httpx (already a dep), structlog, pytest + pytest-asyncio + httpx (TestClient via ASGITransport).

---

## Global Constraints

- `pyjwt[crypto]>=2.10.0` is already in `apps/backend/pyproject.toml`. No new top-level deps required.
- `httpx>=0.28.0` is already in `apps/backend/pyproject.toml`.
- No changes to `payment_service.py`, `payments/interfaces/http/router.py`, webhook handler, webhook service, repositories, DB models, or idempotency store. Everything routes through existing code paths.
- `NullAdapter` (`apps/backend/src/payments/application/provider.py:51-93`) is retained unchanged for unit tests that need a deterministic stub.
- Settings keys are loaded via pydantic-settings from env vars; tests override via env vars + `reset_settings_cache()` (autouse fixture in `apps/backend/conftest.py`).
- All FK constraints, naming, and module boundaries per existing conventions (ADR-0001, ADR list in `docs/17-adrs/`).
- Async tests use `@pytest.mark.asyncio` (not `asyncio_mode = auto`).
- Endpoint tests build a minimal FastAPI app with `httpx.ASGITransport` (pattern in `tests/payments/test_webhook_endpoint.py:39-65`).
- Webhook signing uses `hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()` — identical to the format Razorpay uses and the same code path the production webhook handler verifies (verified at `tests/payments/test_webhook_endpoint.py:35-36`).
- The devsim POSTs to its own origin (`request.url.scheme + "://" + request.url.netloc`), never to `APP_URL` (which points at the frontend).
- Single commit per task with a conventional-commit message (`feat:`, `test:`, `chore:`, `docs:`).
- All commands run from repo root unless otherwise noted.

---

## File Structure

This plan creates 7 new files and modifies 3 existing files across 8 tasks.

| File | Responsibility | Task |
|---|---|---|
| `apps/backend/src/common/infrastructure/settings.py` (modify) | Add `dev_payment_simulator_enabled` + `dev_state_secret` | Task 1 |
| `.env.prod.example` (modify) | Add `DEV_PAYMENT_SIMULATOR_ENABLED=false` (must stay false in prod) | Task 1 |
| `apps/backend/src/payments/application/devsim_state.py` (create) | `encode_state(payload)`, `decode_state(token)` — HS256 JWT roundtrip | Task 2 |
| `apps/backend/src/payments/application/devsim_webhook.py` (create) | `sign_and_post_webhook(...)` — HMAC-sign + POST event over HTTP | Task 3 |
| `apps/backend/src/payments/application/devsim_adapter.py` (create) | `DevSimAdapter` — `PaymentProvider` Protocol impl | Task 4 |
| `apps/backend/src/payments/interfaces/http/devsim_router.py` (create) | FastAPI router: GET `/dev/mock-checkout/{id}` + 4 POST action endpoints | Tasks 5-6 |
| `apps/backend/src/common/interfaces/http/app.py` (modify) | Provider swap (Razorpay→DevSim) + router mount + startup validation | Task 7 |
| `apps/backend/tests/payments/test_devsim_state.py` (create) | 4 tests for state JWT | Task 2 |
| `apps/backend/tests/payments/test_devsim_webhook.py` (create) | 3 tests for webhook signing + POST | Task 3 |
| `apps/backend/tests/payments/test_devsim_adapter.py` (create) | 4 tests for `DevSimAdapter` | Task 4 |
| `apps/backend/tests/payments/test_devsim_router.py` (create) | 12 tests for GET page + 4 POST actions + error paths | Tasks 5-6 |
| `apps/backend/tests/payments/test_settings_prod_guard.py` (create) | 2 tests for startup-time validation | Task 8 |

---

## Tasks

### Task 1: Add settings fields + update prod env example

**Files:**
- Modify: `apps/backend/src/common/infrastructure/settings.py:74-78` (add 2 new fields after the Razorpay block)
- Modify: `.env.prod.example:41` (add `DEV_PAYMENT_SIMULATOR_ENABLED=false` after the Razorpay block)
- Create: `apps/backend/tests/payments/test_devsim_settings.py`

**Interfaces:**
- Consumes: nothing (no prior task in this plan)
- Produces: `Settings.dev_payment_simulator_enabled: bool` (default `False`) and `Settings.dev_state_secret: str` (default `"dev-state-secret-change-me"`)

---

- [ ] **Step 1: Verify pyjwt is already a dependency**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
grep -n "pyjwt" pyproject.toml
```

Expected: one line containing `pyjwt[crypto]>=2.10.0`. If missing, stop and ask the user — but the dependency is already present (verified 2026-08-12).

- [ ] **Step 2: Write the failing test for new settings fields**

Create `apps/backend/tests/payments/test_devsim_settings.py`:

```python
"""Tests for the dev payment simulator settings fields."""
from common.infrastructure.settings import Settings


def test_dev_payment_simulator_enabled_defaults_to_false():
    s = Settings()
    assert s.dev_payment_simulator_enabled is False


def test_dev_state_secret_has_documented_default():
    s = Settings()
    assert s.dev_state_secret == "dev-state-secret-change-me"


def test_dev_payment_simulator_enabled_can_be_overridden():
    s = Settings(dev_payment_simulator_enabled=True)
    assert s.dev_payment_simulator_enabled is True


def test_dev_state_secret_can_be_overridden():
    s = Settings(dev_state_secret="my-custom-secret")
    assert s.dev_state_secret == "my-custom-secret"
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_settings.py -v 2>&1 | tail -10
```

Expected: 4 errors like `AttributeError: 'Settings' object has no attribute 'dev_payment_simulator_enabled'` — confirming the fields do not exist yet.

- [ ] **Step 4: Add the fields to `Settings`**

Edit `apps/backend/src/common/infrastructure/settings.py`. Find the Razorpay block at line 74:

```python
    # ---- Payments (Razorpay) ----
    razorpay_key_id: str = Field(default="rzp_test_placeholder", description="Razorpay public key id")
    razorpay_key_secret: str = Field(default="rzp_test_placeholder_secret", description="Razorpay secret API key")
    razorpay_webhook_secret: str = Field(default="whsec_placeholder", description="Razorpay webhook signing secret (HMAC SHA256)")
    payments_provider: Literal["razorpay", "null"] = Field(default="razorpay", description="Which PaymentProvider adapter to use")
```

Add the following block immediately AFTER `payments_provider`:

```python

    # ---- Dev Payment Simulator (NEVER enable in production) ----
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

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_settings.py -v 2>&1 | tail -10
```

Expected: `4 passed`.

- [ ] **Step 6: Update `.env.prod.example`**

Edit `/home/soloengine/Github/splash_sports_management/.env.prod.example`. Find line 41 (`PAYMENTS_PROVIDER=razorpay`) and add after it:

```bash
# --- Dev Payment Simulator (NEVER set to true in production) ---
DEV_PAYMENT_SIMULATOR_ENABLED=false
# DEV_STATE_SECRET must be set when DEV_PAYMENT_SIMULATOR_ENABLED=true.
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

- [ ] **Step 7: Verify only intended files changed**

```bash
cd /home/soloengine/Github/splash_sports_management
git status --short
git diff --stat
```

Expected: 3 files — `settings.py` modified, `test_devsim_settings.py` new, `.env.prod.example` modified. No other files.

- [ ] **Step 8: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/common/infrastructure/settings.py \
        apps/backend/tests/payments/test_devsim_settings.py \
        .env.prod.example
git commit -m "$(cat <<'EOF'
feat(payments): add dev simulator settings fields

Adds dev_payment_simulator_enabled (bool, default false) and
dev_state_secret (str, default 'dev-state-secret-change-me') to
Settings. Both are wired through pydantic-settings and override-able
via env vars. Defaults are safe: simulator is off, and the default
secret only matters when the simulator is on (which itself is
refused in production by Task 7's startup guard).

Tests cover field presence, defaults, and override behavior.
EOF
)"
```

---

### Task 2: Implement state JWT encode/decode

**Files:**
- Create: `apps/backend/src/payments/application/devsim_state.py`
- Create: `apps/backend/tests/payments/test_devsim_state.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `encode_state(payload: dict, *, secret: str, ttl_seconds: int = 86400) -> str`
  - `decode_state(token: str, *, secret: str) -> dict` (raises `jwt.PyJWTError` on invalid/expired/tampered)

The state JWT payload schema (enforced by callers, not by `encode_state`):
```python
{
  "tenant_id": str (UUID),
  "invoice_id": str (UUID),
  "payment_id": str (UUID),
  "payment_link_id": str,
  "amount_paise": int,
  "currency": str,
  "line_items": list[dict],
  "iat": int,
  "exp": int,
}
```

---

- [ ] **Step 1: Write the failing tests**

Create `apps/backend/tests/payments/test_devsim_state.py`:

```python
"""Tests for devsim_state: HS256-signed JWT roundtrip with tamper/expiry rejection."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from payments.application.devsim_state import decode_state, encode_state


SECRET = "test-secret-32chars-or-more-1234567890"
PAYLOAD = {
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "invoice_id": "22222222-2222-2222-2222-222222222222",
    "payment_id": "33333333-3333-3333-3333-333333333333",
    "payment_link_id": "plink_dev_abc123",
    "amount_paise": 150000,
    "currency": "INR",
    "line_items": [{"description": "Lane 4", "total_paise": 150000}],
}


def test_encode_decode_roundtrip():
    token = encode_state(PAYLOAD, secret=SECRET)
    decoded = decode_state(token, secret=SECRET)
    # iat + exp are added by encode_state
    for key, value in PAYLOAD.items():
        assert decoded[key] == value
    assert "iat" in decoded
    assert "exp" in decoded
    assert decoded["exp"] > decoded["iat"]


def test_decode_rejects_tampered_signature():
    token = encode_state(PAYLOAD, secret=SECRET)
    # Replace last char of signature to break HMAC
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(jwt.PyJWTError):
        decode_state(tampered, secret=SECRET)


def test_decode_rejects_wrong_secret():
    token = encode_state(PAYLOAD, secret=SECRET)
    with pytest.raises(jwt.PyJWTError):
        decode_state(token, secret="different-secret")


def test_decode_rejects_expired_token(monkeypatch):
    # Encode with a 1-second TTL, then freeze time past expiry
    token = encode_state(PAYLOAD, secret=SECRET, ttl_seconds=1)
    # pyjwt validates exp using datetime.utcnow() by default; we backdate exp manually
    # by re-encoding with a clearly-past exp.
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    payload["exp"] = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
    expired = jwt.encode(payload, SECRET, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_state(expired, secret=SECRET)


def test_encode_respects_custom_ttl():
    token = encode_state(PAYLOAD, secret=SECRET, ttl_seconds=60)
    decoded = decode_state(token, secret=SECRET)
    assert decoded["exp"] - decoded["iat"] == 60
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_state.py -v 2>&1 | tail -10
```

Expected: 5 errors with `ModuleNotFoundError: No module named 'payments.application.devsim_state'` (or `ImportError`).

- [ ] **Step 3: Implement `devsim_state.py`**

Create `apps/backend/src/payments/application/devsim_state.py`:

```python
"""HMAC-signed state JWT for the dev payment simulator.

The state JWT is carried in the `?state=<token>` query param of the
fake checkout URL. It carries the invoice/payment context needed to
construct a webhook event when the user clicks an action button.

Stateless: no DB lookup is performed to decode. The token's signature
is verified with `dev_state_secret` (an HS256 secret) and the `exp`
claim is enforced by pyjwt.

Why HS256 (not RS256): this is a state-encoding token, not an
authentication token. The dev simulator is the only issuer and the
only verifier, so a symmetric secret is appropriate.
"""
from __future__ import annotations

from typing import Any

import jwt


def encode_state(
    payload: dict[str, Any],
    *,
    secret: str,
    ttl_seconds: int = 86_400,
) -> str:
    """Encode `payload` as a signed HS256 JWT with iat+exp set.

    Args:
        payload: arbitrary key/value pairs to embed. Caller is responsible
            for the schema (see module docstring).
        secret: HMAC secret used to sign the token.
        ttl_seconds: lifetime of the token. Default 24 hours to match
            `PaymentLinkResult.expires_at`.

    Returns:
        Encoded JWT string.
    """
    now = jwt.api_jws.datetime_now()
    claims = dict(payload)
    claims["iat"] = now
    claims["exp"] = now + jwt.api_jws.timedelta(seconds=ttl_seconds)
    return jwt.encode(claims, secret, algorithm="HS256")


def decode_state(token: str, *, secret: str) -> dict[str, Any]:
    """Decode and verify a state JWT.

    Args:
        token: encoded JWT string.
        secret: HMAC secret used to verify the signature. Must match
            the secret used at encode time.

    Returns:
        Decoded payload as a dict.

    Raises:
        jwt.PyJWTError: on invalid signature, expired token, malformed
            token, or wrong algorithm.
    """
    return jwt.decode(token, secret, algorithms=["HS256"])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_state.py -v 2>&1 | tail -10
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/payments/application/devsim_state.py \
        apps/backend/tests/payments/test_devsim_state.py
git commit -m "$(cat <<'EOF'
feat(payments): add devsim_state encode/decode (HS256 JWT roundtrip)

Stateless state encoding for the dev payment simulator. The JWT
carries invoice/payment context in the ?state= URL query param;
no DB lookup needed to reconstruct it. HS256 chosen because this
is a state-encoding token, not an auth token — only the simulator
issues and verifies it.

Tests cover roundtrip, tampered signature, wrong secret, expired
token, and custom TTL.
EOF
)"
```

---

### Task 3: Implement webhook signing + HTTP poster

**Files:**
- Create: `apps/backend/src/payments/application/devsim_webhook.py`
- Create: `apps/backend/tests/payments/test_devsim_webhook.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `build_event(event_type: Literal["payment.captured", "payment.failed"], *, payment_id: str, amount_paise: int, currency: str, description: str, tenant_id: str, invoice_id: str, payment_link_id: str) -> dict` — returns the Razorpay-shaped event dict
  - `sign_payload(payload: bytes, *, secret: str) -> str` — returns the hex HMAC-SHA256 signature
  - `post_webhook(url: str, payload: bytes, *, signature: str) -> int` — async, returns HTTP status code from the webhook endpoint

---

- [ ] **Step 1: Write the failing tests**

Create `apps/backend/tests/payments/test_devsim_webhook.py`:

```python
"""Tests for devsim_webhook: Razorpay event shape + HMAC signing + HTTP POST."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest

from payments.application.devsim_webhook import (
    build_event,
    post_webhook,
    sign_payload,
)

WEBHOOK_SECRET = "whsec_test_secret"


def test_build_event_payment_captured_shape():
    event = build_event(
        "payment.captured",
        payment_id="pay_dev_abc123",
        amount_paise=150000,
        currency="INR",
        description="Lane 4 booking",
        tenant_id="11111111-1111-1111-1111-111111111111",
        invoice_id="22222222-2222-2222-2222-222222222222",
        payment_link_id="plink_dev_abc",
    )
    assert event["entity"] == "event"
    assert event["event"] == "payment.captured"
    assert event["contains"] == ["payment"]
    assert event["payload"]["payment"]["entity"]["id"] == "pay_dev_abc123"
    assert event["payload"]["payment"]["entity"]["amount"] == 150000
    assert event["payload"]["payment"]["entity"]["currency"] == "INR"
    assert event["payload"]["payment"]["entity"]["status"] == "captured"
    assert event["payload"]["payment"]["entity"]["notes"]["tenant_id"] == (
        "11111111-1111-1111-1111-111111111111"
    )
    assert event["payload"]["payment"]["entity"]["notes"]["invoice_id"] == (
        "22222222-2222-2222-2222-222222222222"
    )
    assert event["payload"]["payment"]["entity"]["notes"]["payment_link_id"] == "plink_dev_abc"
    assert "created_at" in event
    assert isinstance(event["created_at"], int)


def test_build_event_payment_failed_shape():
    event = build_event(
        "payment.failed",
        payment_id="pay_dev_xyz",
        amount_paise=150000,
        currency="INR",
        description="Lane 4 booking",
        tenant_id="11111111-1111-1111-1111-111111111111",
        invoice_id="22222222-2222-2222-2222-222222222222",
        payment_link_id="plink_dev_xyz",
    )
    assert event["event"] == "payment.failed"
    assert event["payload"]["payment"]["entity"]["status"] == "failed"
    assert "error_description" in event["payload"]["payment"]["entity"]


def test_sign_payload_matches_production_format():
    payload = b'{"event":"payment.captured"}'
    sig = sign_payload(payload, secret=WEBHOOK_SECRET)
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    assert sig == expected


@pytest.mark.asyncio
async def test_post_webhook_calls_httpx_with_correct_url_and_headers():
    payload = b'{"event":"payment.captured"}'
    sig = sign_payload(payload, secret=WEBHOOK_SECRET)
    with patch(
        "payments.application.devsim_webhook.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        status = await post_webhook(
            "http://localhost:8000/v1/payments/webhook", payload, signature=sig
        )

    assert status == 200
    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.call_args.kwargs
    assert call_kwargs["content"] == payload
    assert call_kwargs["headers"]["X-Razorpay-Signature"] == sig
    assert call_kwargs["headers"]["Content-Type"] == "application/json"
    assert mock_client.post.call_args.args[0] == "http://localhost:8000/v1/payments/webhook"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_webhook.py -v 2>&1 | tail -10
```

Expected: 4 errors with `ModuleNotFoundError: No module named 'payments.application.devsim_webhook'`.

- [ ] **Step 3: Implement `devsim_webhook.py`**

Create `apps/backend/src/payments/application/devsim_webhook.py`:

```python
"""Build Razorpay-shaped webhook events, HMAC-sign them, POST to the real endpoint.

This module is what makes the dev simulator exercise the production webhook
code path: every event is signed with the same secret the production handler
verifies against, and POSTed over HTTP to /v1/payments/webhook.

Webhook signing format matches the production Razorpay format:
    signature = hex(HMAC_SHA256(webhook_secret, raw_body))
The production webhook handler verifies with the same algorithm — see
`apps/backend/src/payments/application/provider.py` (RazorpayAdapter.verify_webhook).
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Literal

import httpx


def build_event(
    event_type: Literal["payment.captured", "payment.failed"],
    *,
    payment_id: str,
    amount_paise: int,
    currency: str,
    description: str,
    tenant_id: str,
    invoice_id: str,
    payment_link_id: str,
) -> dict:
    """Build a Razorpay-shaped event payload.

    The shape mirrors what the production webhook handler parses
    (`payments.application.webhook_service` — verify against current
    implementation before relying on any field).
    """
    if event_type == "payment.captured":
        status = "captured"
        entity: dict = {
            "id": payment_id,
            "amount": amount_paise,
            "currency": currency,
            "status": status,
            "description": description[:255],
            "notes": {
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "payment_id": payment_id,
                "payment_link_id": payment_link_id,
            },
        }
    elif event_type == "payment.failed":
        status = "failed"
        entity = {
            "id": payment_id,
            "amount": amount_paise,
            "currency": currency,
            "status": status,
            "error_description": "Payment declined by user",
            "error_code": "PAYMENT_DECLINED",
            "description": description[:255],
            "notes": {
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "payment_id": payment_id,
                "payment_link_id": payment_link_id,
            },
        }
    else:
        raise ValueError(f"unsupported event_type: {event_type!r}")

    return {
        "entity": "event",
        "account_id": "acc_dev",
        "event": event_type,
        "contains": ["payment"],
        "payload": {"payment": {"entity": entity}},
        "created_at": int(time.time()),
    }


def sign_payload(payload: bytes, *, secret: str) -> str:
    """Return hex(HMAC_SHA256(secret, payload)).

    This matches the format Razorpay uses and the format the production
    webhook handler verifies against (see `RazorpayAdapter.verify_webhook`).
    """
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def post_webhook(url: str, payload: bytes, *, signature: str) -> int:
    """POST `payload` to `url` with the X-Razorpay-Signature header.

    Returns the HTTP status code from the webhook endpoint.

    Raises:
        httpx.HTTPError: on transport-level failure (connection refused,
            timeout, etc.). The caller (router action handler) is
            responsible for converting this to a 502 user-facing response.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
        )
        return response.status_code
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_webhook.py -v 2>&1 | tail -10
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/payments/application/devsim_webhook.py \
        apps/backend/tests/payments/test_devsim_webhook.py
git commit -m "$(cat <<'EOF'
feat(payments): add devsim_webhook (event build + HMAC sign + HTTP POST)

Three helpers used by the devsim router:
- build_event: produces Razorpay-shaped payment.captured / payment.failed
  events with notes.tenant_id (so F-07 tenant resolution still works).
- sign_payload: hex(HMAC_SHA256(secret, raw_body)) — same format the
  production webhook handler verifies.
- post_webhook: async POST to /v1/payments/webhook via httpx.

Tests cover event shape for both event types, signature format
matches production, and POST is called with correct URL/headers/body.
EOF
)"
```

---

### Task 4: Implement `DevSimAdapter`

**Files:**
- Create: `apps/backend/src/payments/application/devsim_adapter.py`
- Create: `apps/backend/tests/payments/test_devsim_adapter.py`

**Interfaces:**
- Consumes:
  - `encode_state(payload, *, secret, ttl_seconds)` from `payments.application.devsim_state` (Task 2)
  - `Settings.app_url` and `Settings.dev_state_secret` from `common.infrastructure.settings` (Task 1)
- Produces:
  - `DevSimAdapter` class with `__init__(self, *, app_url: str, dev_state_secret: str, webhook_secret: str)` satisfying the `PaymentProvider` Protocol (same shape as `NullAdapter`/`RazorpayAdapter` in `apps/backend/src/payments/application/provider.py`)

---

- [ ] **Step 1: Write the failing tests**

Create `apps/backend/tests/payments/test_devsim_adapter.py`:

```python
"""Tests for DevSimAdapter — drop-in PaymentProvider that returns dev URLs."""
from __future__ import annotations

import hashlib
import hmac
from uuid import uuid4

import pytest

from payments.application.devsim_adapter import DevSimAdapter
from payments.application.devsim_state import decode_state
from payments.application.provider import PaymentLinkResult


@pytest.fixture
def adapter() -> DevSimAdapter:
    return DevSimAdapter(
        app_url="http://localhost:5173",
        dev_state_secret="dev-state-secret-32chars-or-more-12345",
        webhook_secret="whsec_test_secret",
    )


def _invoice(amount_paise: int = 150000):
    return {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "customer_id": uuid4(),
        "invoice_number": "INV-000001",
        "description": "Lane 4 booking",
        "line_items": [
            {
                "description": "Lane 4",
                "quantity": 1,
                "unit_price_paise": amount_paise,
                "total_paise": amount_paise,
            }
        ],
        "currency": "INR",
        "total": {"amount_paise": amount_paise, "currency": "INR"},
    }


@pytest.mark.asyncio
async def test_create_payment_link_returns_dev_url_with_signed_state(adapter):
    inv = _invoice()
    result = await adapter.create_payment_link(
        invoice=inv,
        payment_id=uuid4(),
        idempotency_key="key-1",
        success_url="https://app.example/book/pay/abc/return",
        cancel_url="https://app.example/book/pay/abc",
        customer={"name": "Alex", "email": "alex@example.com", "contact": "+919999999999"},
    )
    assert isinstance(result, PaymentLinkResult)
    assert result.short_url.startswith("http://localhost:5173/dev/mock-checkout/")
    assert "?state=" in result.short_url
    assert result.razorpay_payment_link_id.startswith("plink_dev_")
    assert result.razorpay_order_id is None


@pytest.mark.asyncio
async def test_state_payload_includes_invoice_amount_and_currency(adapter):
    inv = _invoice(amount_paise=200000)
    payment_id = uuid4()
    result = await adapter.create_payment_link(
        invoice=inv,
        payment_id=payment_id,
        idempotency_key="key-2",
        success_url="https://app.example/x",
        cancel_url="https://app.example/y",
        customer={"name": "B", "email": "b@x.com", "contact": "+910000000000"},
    )
    # Parse the state JWT
    state_token = result.short_url.split("?state=")[1]
    payload = decode_state(state_token, secret=adapter.dev_state_secret)
    assert payload["amount_paise"] == 200000
    assert payload["currency"] == "INR"
    assert payload["payment_id"] == str(payment_id)
    assert payload["tenant_id"] == str(inv["tenant_id"])
    assert payload["invoice_id"] == str(inv["id"])
    assert payload["payment_link_id"] == result.razorpay_payment_link_id


@pytest.mark.asyncio
async def test_short_url_uses_configured_app_url():
    adapter = DevSimAdapter(
        app_url="https://my-dev.example.com",
        dev_state_secret="dev-state-secret-32chars-or-more-12345",
        webhook_secret="whsec_test_secret",
    )
    result = await adapter.create_payment_link(
        invoice=_invoice(),
        payment_id=uuid4(),
        idempotency_key="k",
        success_url="https://x/y",
        cancel_url="https://x/z",
        customer={"name": "B", "email": "b@x.com", "contact": "+910000000000"},
    )
    assert result.short_url.startswith("https://my-dev.example.com/dev/mock-checkout/")


@pytest.mark.asyncio
async def test_refund_returns_deterministic_id(adapter):
    refund = await adapter.create_refund(
        razorpay_payment_id="pay_dev_abc",
        amount_paise=50000,
        idempotency_key="rk",
    )
    assert refund["id"].startswith("rfnd_dev_")
    assert refund["amount"] == 50000
    assert refund["status"] == "processed"


def test_verify_webhook_uses_real_hmac_signature(adapter):
    payload = b'{"event":"payment.captured"}'
    expected_sig = hmac.new(
        adapter.webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    # Should NOT raise — same code path as RazorpayAdapter
    event = adapter.verify_webhook(payload, expected_sig)
    assert event["event"] == "payment.captured"


def test_verify_webhook_rejects_bad_signature(adapter):
    payload = b'{"event":"payment.captured"}'
    with pytest.raises(Exception):
        adapter.verify_webhook(payload, "bad-signature")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_adapter.py -v 2>&1 | tail -10
```

Expected: 6 errors with `ModuleNotFoundError: No module named 'payments.application.devsim_adapter'`.

- [ ] **Step 3: Implement `DevSimAdapter`**

Create `apps/backend/src/payments/application/devsim_adapter.py`:

```python
"""DevSimAdapter — PaymentProvider implementation that returns dev checkout URLs.

Satisfies the same Protocol as NullAdapter and RazorpayAdapter (see
`apps/backend/src/payments/application/provider.py`). Drop-in replacement.

Differences from NullAdapter:
- short_url points at the backend's own /dev/mock-checkout/ route (real URL)
- state is encoded as a signed JWT in the URL (real state, not a fake stub)
- verify_webhook uses real HMAC verification (same as RazorpayAdapter)

Differences from RazorpayAdapter:
- No SDK calls. No external network. No idempotency-key header (we mint
  the link id locally).
- short_url is a backend path; redirect happens server-side via the
  simulator router (Task 5).
"""
from __future__ import annotations

import json
from typing import Protocol
from uuid import UUID, uuid4

from payments.application.devsim_state import encode_state

# Importing from the same module as NullAdapter/RazorpayAdapter to share
# the dataclass and Protocol definitions.
from payments.application.provider import (  # noqa: F401  (re-exported via type)
    PaymentLinkResult,
    PaymentProvider,
)


class DevSimAdapter:
    """Dev-only PaymentProvider. Routes checkout through the backend's own
    /dev/mock-checkout router (mounted only when DEV_PAYMENT_SIMULATOR_ENABLED).
    """

    def __init__(
        self,
        *,
        app_url: str,
        dev_state_secret: str,
        webhook_secret: str,
    ) -> None:
        self.app_url = app_url.rstrip("/")
        self.dev_state_secret = dev_state_secret
        self.webhook_secret = webhook_secret

    async def create_payment_link(
        self,
        *,
        invoice: dict,
        payment_id: UUID,
        idempotency_key: str,
        success_url: str,
        cancel_url: str,
        customer: dict,
    ) -> PaymentLinkResult:
        link_id = f"plink_dev_{uuid4().hex[:16]}"
        from datetime import UTC, datetime, timedelta

        amount_paise = invoice["total"]["amount_paise"]
        currency = invoice["total"]["currency"]
        line_items = invoice.get("line_items", [])

        state_token = encode_state(
            {
                "tenant_id": str(invoice["tenant_id"]),
                "invoice_id": str(invoice["id"]),
                "payment_id": str(payment_id),
                "payment_link_id": link_id,
                "amount_paise": amount_paise,
                "currency": currency,
                "line_items": line_items,
            },
            secret=self.dev_state_secret,
            ttl_seconds=86_400,
        )

        short_url = f"{self.app_url}/dev/mock-checkout/{link_id}?state={state_token}"
        return PaymentLinkResult(
            short_url=short_url,
            razorpay_payment_link_id=link_id,
            razorpay_order_id=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

    async def fetch_payment(self, razorpay_payment_id: str) -> dict:
        # The dev simulator never stores payment state — callers should
        # use the webhook path to learn payment status.
        return {
            "id": razorpay_payment_id,
            "status": "captured",
            "amount": 0,
            "currency": "INR",
        }

    async def create_refund(
        self,
        *,
        razorpay_payment_id: str,
        amount_paise: int,
        idempotency_key: str,
    ) -> dict:
        return {
            "id": f"rfnd_dev_{uuid4().hex[:16]}",
            "amount": amount_paise,
            "status": "processed",
        }

    def verify_webhook(self, payload: bytes, signature: str) -> dict:
        # Same HMAC-SHA256 verification format as RazorpayAdapter —
        # exercise the real signature path so the simulator is a faithful
        # substitute for the real provider.
        import hashlib
        import hmac

        expected = hmac.new(
            self.webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("invalid webhook signature")
        return json.loads(payload.decode())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_adapter.py -v 2>&1 | tail -10
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/payments/application/devsim_adapter.py \
        apps/backend/tests/payments/test_devsim_adapter.py
git commit -m "$(cat <<'EOF'
feat(payments): add DevSimAdapter (PaymentProvider Protocol impl)

Drop-in replacement for RazorpayAdapter that returns a backend-hosted
dev checkout URL instead of a Razorpay URL. State is encoded as a
signed JWT in the URL; verify_webhook uses real HMAC-SHA256
verification so the simulator exercises the production signature
path. Refund returns deterministic ids.

Tests cover short_url shape, state JWT contents (amount/currency/
tenant_id/invoice_id), configurable app_url, refund id shape, and
HMAC verify_webhook behavior including tamper rejection.
EOF
)"
```

---

### Task 5: Devsim router — GET checkout page + HTML

**Files:**
- Create: `apps/backend/src/payments/interfaces/http/devsim_router.py` (partial — GET only; POST actions in Task 6)
- Create: `apps/backend/tests/payments/test_devsim_router.py` (partial — GET tests only; POST tests in Task 6)

**Interfaces:**
- Consumes:
  - `decode_state(token, *, secret)` from `payments.application.devsim_state` (Task 2)
  - `Settings.dev_state_secret` from `common.infrastructure.settings` (Task 1)
- Produces:
  - FastAPI `APIRouter` instance named `router` with prefix `/dev/mock-checkout` containing:
    - `GET /{link_id}` — renders fake checkout HTML, validates state JWT
  - `_render_checkout_html(state: dict) -> str` (module-private; returns HTML string)

---

- [ ] **Step 1: Write the failing tests (GET only)**

Create `apps/backend/tests/payments/test_devsim_router.py` (initial GET-only version):

```python
"""Tests for the devsim router: GET checkout page + POST action endpoints.

POST action tests are added in Task 6.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from payments.application.devsim_state import encode_state
from payments.interfaces.http.devsim_router import router as devsim_router


DEV_STATE_SECRET = "test-dev-state-secret-32chars-or-more-1234567890"
DEV_PAYMENT_LINK_ID = "plink_dev_abc12345"


def _payload() -> dict:
    return {
        "tenant_id": str(uuid4()),
        "invoice_id": str(uuid4()),
        "payment_id": str(uuid4()),
        "payment_link_id": DEV_PAYMENT_LINK_ID,
        "amount_paise": 150000,
        "currency": "INR",
        "line_items": [{"description": "Lane 4 booking", "total_paise": 150000}],
    }


def _valid_state_token() -> str:
    return encode_state(_payload(), secret=DEV_STATE_SECRET, ttl_seconds=3600)


@pytest_asyncio.fixture
async def client(monkeypatch) -> AsyncIterator[AsyncClient]:
    """Build a minimal FastAPI app with the devsim router mounted."""
    monkeypatch.setenv("DEV_STATE_SECRET", DEV_STATE_SECRET)
    from common.infrastructure.settings import reset_settings_cache, get_settings

    reset_settings_cache()
    settings = get_settings()
    assert settings.dev_state_secret == DEV_STATE_SECRET

    app = FastAPI()
    app.include_router(devsim_router, prefix="/dev")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_checkout_renders_html_with_action_buttons(client):
    token = _valid_state_token()
    response = await client.get(f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}?state={token}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    # Page must contain the 4 action buttons
    assert 'action="/dev/mock-checkout/' in html
    assert "capture" in html
    assert "decline" in html
    assert "capture-partial" in html
    # Abandon is just a button that doesn't POST anywhere (it's a "leave" UX).
    # The page should still mention it.
    assert "abandon" in html.lower() or "leave" in html.lower()
    # Invoice summary should be visible
    assert "Lane 4 booking" in html
    assert "1500" in html  # INR formatted (150000 paise = ₹1500)


@pytest.mark.asyncio
async def test_get_checkout_without_state_returns_400(client):
    response = await client.get(f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_checkout_with_invalid_state_returns_400(client):
    response = await client.get(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}?state=not-a-jwt"
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_checkout_with_expired_state_returns_400(client):
    payload = _payload()
    payload["exp"] = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
    expired = jwt.encode(payload, DEV_STATE_SECRET, algorithm="HS256")
    response = await client.get(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}?state={expired}"
    )
    assert response.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_router.py -v 2>&1 | tail -10
```

Expected: 4 errors with `ModuleNotFoundError: No module named 'payments.interfaces.http.devsim_router'`.

- [ ] **Step 3: Implement the router (GET only — POST endpoints stubbed for Task 6)**

Create `apps/backend/src/payments/interfaces/http/devsim_router.py`:

```python
"""Dev-only FastAPI router for the mock payment checkout page.

Mounted under `/dev/mock-checkout` by `common.interfaces.http.app`
when DEV_PAYMENT_SIMULATOR_ENABLED=true.

Endpoints (Task 5):
- GET  /dev/mock-checkout/{link_id}   — render fake checkout HTML

Endpoints (Task 6, stubbed for now with NotImplementedError so the
router still imports cleanly):
- POST /dev/mock-checkout/{link_id}/capture           — happy path
- POST /dev/mock-checkout/{link_id}/decline           — failure
- POST /dev/mock-checkout/{link_id}/capture-partial   — partial payment
- POST /dev/mock-checkout/{link_id}/abandon           — abandoned (no-op)
"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from common.infrastructure.settings import get_settings
from payments.application.devsim_state import decode_state


router = APIRouter(prefix="/dev/mock-checkout", tags=["dev-payment-simulator"])


def _render_checkout_html(state: dict) -> str:
    """Return the fake Razorpay-style checkout page as an HTML string.

    The 4 action buttons post to sibling endpoints (capture, decline,
    capture-partial, abandon). The abandon button is informational only —
    it doesn't POST (closing the page is enough).
    """
    link_id = state["payment_link_id"]
    amount_paise = state["amount_paise"]
    amount_inr = amount_paise / 100
    currency = state["currency"]
    description = "; ".join(
        li.get("description", "") for li in state.get("line_items", [])
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Dev Payment Simulator — {link_id}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 40px auto; padding: 20px; }}
    h1 {{ font-size: 18px; color: #333; }}
    .summary {{ background: #f5f5f5; padding: 16px; border-radius: 4px; margin-bottom: 24px; }}
    .summary dt {{ font-weight: bold; display: inline-block; width: 100px; }}
    .summary dd {{ display: inline; margin: 0; }}
    .row {{ margin: 8px 0; }}
    form {{ display: inline-block; margin-right: 8px; }}
    button {{ padding: 10px 20px; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; font-size: 14px; }}
    .primary {{ background: #3399cc; color: white; border-color: #3399cc; }}
    .danger {{ background: #cc3333; color: white; border-color: #cc3333; }}
    input[type="number"] {{ padding: 8px; border: 1px solid #ccc; border-radius: 4px; width: 100px; }}
  </style>
</head>
<body>
  <h1>Dev Payment Simulator</h1>
  <p style="color:#888; font-size: 12px;">Payment link: {link_id}</p>
  <dl class="summary">
    <div class="row"><dt>Amount</dt><dd>₹{amount_inr:.2f} {currency}</dd></div>
    <div class="row"><dt>Description</dt><dd>{description}</dd></div>
  </dl>

  <form method="post" action="/dev/mock-checkout/{link_id}/capture">
    <button type="submit" class="primary">Pay ₹{amount_inr:.2f}</button>
  </form>

  <form method="post" action="/dev/mock-checkout/{link_id}/decline">
    <button type="submit" class="danger">Decline</button>
  </form>

  <form method="post" action="/dev/mock-checkout/{link_id}/capture-partial">
    <input type="number" name="amount_paise" min="1" max="{amount_paise}" placeholder="paise" required />
    <button type="submit">Pay partial</button>
  </form>

  <p style="margin-top: 24px; font-size: 12px; color: #888;">
    To abandon: close this page. (Reopening will still work until the link expires.)
  </p>
</body>
</html>"""


def _decode_state_or_400(token: str) -> dict:
    """Decode the state JWT or raise 400."""
    settings = get_settings()
    try:
        return decode_state(token, secret=settings.dev_state_secret)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail=f"invalid state: {exc}") from exc


@router.get("/{link_id}", response_class=HTMLResponse)
async def get_checkout(
    link_id: str,
    state: Annotated[str, Query(description="Signed state JWT")],
) -> HTMLResponse:
    """Render the fake Razorpay-style checkout page."""
    payload = _decode_state_or_400(state)
    if payload["payment_link_id"] != link_id:
        raise HTTPException(status_code=400, detail="link_id mismatch")
    return HTMLResponse(content=_render_checkout_html(payload))


# ---- POST endpoints (stubs — Task 6 will replace these) ----


@router.post("/{link_id}/capture")
async def post_capture(link_id: str, request: Request) -> dict:  # pragma: no cover
    raise NotImplementedError("filled in by Task 6")


@router.post("/{link_id}/decline")
async def post_decline(link_id: str, request: Request) -> dict:  # pragma: no cover
    raise NotImplementedError("filled in by Task 6")


@router.post("/{link_id}/capture-partial")
async def post_capture_partial(
    link_id: str,
    request: Request,
    amount_paise: Annotated[int, Form()] = 0,
) -> dict:  # pragma: no cover
    raise NotImplementedError("filled in by Task 6")


@router.post("/{link_id}/abandon")
async def post_abandon(link_id: str, request: Request) -> dict:  # pragma: no cover
    raise NotImplementedError("filled in by Task 6")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_router.py -v 2>&1 | tail -10
```

Expected: `4 passed` (only the GET tests run; POST tests not yet added).

- [ ] **Step 5: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/payments/interfaces/http/devsim_router.py \
        apps/backend/tests/payments/test_devsim_router.py
git commit -m "$(cat <<'EOF'
feat(payments): add devsim router GET checkout page

GET /dev/mock-checkout/{link_id} renders a Razorpay-style HTML
page with 4 action buttons (Pay, Decline, Pay partial, Abandon)
plus an inline form for partial-amount input. State is verified
via HMAC-signed JWT; invalid/expired tokens return 400.

POST action endpoints are stubbed (NotImplementedError) and will
be filled in by Task 6.
EOF
)"
```

---

### Task 6: Devsim router — POST action endpoints

**Files:**
- Modify: `apps/backend/src/payments/interfaces/http/devsim_router.py` (replace 4 stubs)
- Modify: `apps/backend/tests/payments/test_devsim_router.py` (append 7 new tests)

**Interfaces:**
- Consumes:
  - `decode_state(token, *, secret)` from `payments.application.devsim_state` (Task 2)
  - `build_event(...)`, `sign_payload(...)`, `post_webhook(...)` from `payments.application.devsim_webhook` (Task 3)
  - `Settings.dev_state_secret`, `Settings.razorpay_webhook_secret` from `common.infrastructure.settings`
- Produces: 4 working POST endpoints:
  - `POST /{link_id}/capture` — fires `payment.captured` webhook, returns HTML success page
  - `POST /{link_id}/decline` — fires `payment.failed` webhook, returns HTML failure page
  - `POST /{link_id}/capture-partial` — fires `payment.captured` with requested amount; rejects amount > invoice or <= 0
  - `POST /{link_id}/abandon` — no-op (returns HTML "abandoned" page; no webhook)

---

- [ ] **Step 1: Append failing tests for POST endpoints**

Append the following to `apps/backend/tests/payments/test_devsim_router.py` (after the existing GET tests):

```python
@pytest.mark.asyncio
async def test_post_capture_fires_webhook_and_returns_success(client, monkeypatch):
    """POST /capture fires payment.captured webhook and returns success HTML."""
    from payments.interfaces.http import devsim_router as router_module

    posted_to = []
    async def fake_post(url, payload, *, signature):
        posted_to.append((url, payload, signature))
        return 200
    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    token = _valid_state_token()
    response = await client.post(f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture")
    # POST without state in body → 400 first
    assert response.status_code == 400

    # Now POST with state in the form body
    response = await client.post(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture",
        data={"state": token},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Payment successful" in response.text

    # Webhook was fired with the right shape
    assert len(posted_to) == 1
    url, payload_bytes, signature = posted_to[0]
    assert url.endswith("/v1/payments/webhook")
    import json
    event = json.loads(payload_bytes)
    assert event["event"] == "payment.captured"
    assert event["payload"]["payment"]["entity"]["amount"] == 150000


@pytest.mark.asyncio
async def test_post_decline_fires_payment_failed_webhook(client, monkeypatch):
    from payments.interfaces.http import devsim_router as router_module

    posted_to = []
    async def fake_post(url, payload, *, signature):
        posted_to.append(payload)
        return 200
    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    token = _valid_state_token()
    response = await client.post(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/decline",
        data={"state": token},
    )
    assert response.status_code == 200
    assert "declined" in response.text.lower() or "failed" in response.text.lower()

    import json
    event = json.loads(posted_to[0])
    assert event["event"] == "payment.failed"
    assert event["payload"]["payment"]["entity"]["status"] == "failed"


@pytest.mark.asyncio
async def test_post_capture_partial_uses_requested_amount(client, monkeypatch):
    from payments.interfaces.http import devsim_router as router_module

    posted_to = []
    async def fake_post(url, payload, *, signature):
        posted_to.append(payload)
        return 200
    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    token = _valid_state_token()
    response = await client.post(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture-partial",
        data={"state": token, "amount_paise": "50000"},
    )
    assert response.status_code == 200

    import json
    event = json.loads(posted_to[0])
    assert event["event"] == "payment.captured"
    assert event["payload"]["payment"]["entity"]["amount"] == 50000


@pytest.mark.asyncio
async def test_post_capture_partial_rejects_amount_exceeding_invoice(client, monkeypatch):
    from payments.interfaces.http import devsim_router as router_module

    posted_to = []
    async def fake_post(url, payload, *, signature):
        posted_to.append(payload)
        return 200
    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    token = _valid_state_token()  # invoice is 150000 paise
    response = await client.post(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture-partial",
        data={"state": token, "amount_paise": "200000"},
    )
    assert response.status_code == 400
    assert "exceeds" in response.text.lower() or "400" in response.text
    # Webhook was NOT fired
    assert posted_to == []


@pytest.mark.asyncio
async def test_post_capture_partial_rejects_non_positive_amount(client):
    token = _valid_state_token()
    response = await client.post(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture-partial",
        data={"state": token, "amount_paise": "0"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_with_invalid_state_returns_400(client):
    response = await client.post(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture",
        data={"state": "not-a-jwt"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_abandon_is_a_no_op(client, monkeypatch):
    """Abandon fires no webhook — same behavior as closing the page."""
    from payments.interfaces.http import devsim_router as router_module

    posted_to = []
    async def fake_post(url, payload, *, signature):
        posted_to.append(payload)
        return 200
    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    token = _valid_state_token()
    response = await client.post(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/abandon",
        data={"state": token},
    )
    assert response.status_code == 200
    assert "abandoned" in response.text.lower() or "no payment" in response.text.lower()
    assert posted_to == []


@pytest.mark.asyncio
async def test_post_webhook_failure_returns_502(client, monkeypatch):
    """If the webhook POST fails (5xx), the action endpoint returns 502."""
    from payments.interfaces.http import devsim_router as router_module

    async def fake_post(url, payload, *, signature):
        return 500
    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    token = _valid_state_token()
    response = await client.post(
        f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture",
        data={"state": token},
    )
    assert response.status_code == 502
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_router.py -v 2>&1 | tail -15
```

Expected: 8 new failures, all `NotImplementedError`. The 4 GET tests still pass.

- [ ] **Step 3: Replace the 4 POST stubs with real implementations**

Edit `apps/backend/src/payments/interfaces/http/devsim_router.py`. Replace the 4 stub functions at the bottom (after the `get_checkout` handler) with:

```python
def _build_backend_webhook_url(request: Request) -> str:
    """Compute the URL of /v1/payments/webhook on this same server.

    We POST to the request's own origin (scheme + netloc), NOT to
    settings.app_url — `app_url` points at the frontend, not the backend.
    This is the only place in the devsim that needs to know the backend's
    own host:port.
    """
    return f"{request.url.scheme}://{request.url.netloc}/v1/payments/webhook"


def _fire_webhook(
    request: Request,
    *,
    event_type: str,
    state: dict,
    amount_paise: int,
) -> None:
    """Build event, sign with webhook secret, POST to real webhook endpoint."""
    import json

    from payments.application.devsim_webhook import build_event, sign_payload, post_webhook

    settings = get_settings()
    event = build_event(
        event_type,
        payment_id=f"pay_dev_{state['payment_link_id'].removeprefix('plink_dev_')}",
        amount_paise=amount_paise,
        currency=state["currency"],
        description="; ".join(li.get("description", "") for li in state.get("line_items", [])),
        tenant_id=state["tenant_id"],
        invoice_id=state["invoice_id"],
        payment_link_id=state["payment_link_id"],
    )
    payload_bytes = json.dumps(event).encode()
    signature = sign_payload(payload_bytes, secret=settings.razorpay_webhook_secret)
    url = _build_backend_webhook_url(request)
    return payload_bytes, signature, url


async def _fire_or_502(request: Request, *, event_type: str, state: dict, amount_paise: int):
    """Helper: fire the webhook; raise 502 on transport failure or 5xx response."""
    import httpx
    from payments.application.devsim_webhook import post_webhook

    payload_bytes, signature, url = _fire_webhook(
        request, event_type=event_type, state=state, amount_paise=amount_paise
    )
    try:
        status = await post_webhook(url, payload_bytes, signature=signature)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"webhook transport error: {exc}") from exc
    if status >= 500:
        raise HTTPException(status_code=502, detail=f"webhook returned {status}")
    return status


def _success_html(link_id: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><title>Payment successful</title></head>
<body style="font-family: system-ui; max-width: 480px; margin: 40px auto;">
  <h1>Payment successful</h1>
  <p>Your booking is confirmed. (Dev link <code>{link_id}</code>.)</p>
  <p><a href="/">Return to app</a></p>
</body></html>"""


def _failure_html(link_id: str, reason: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><title>Payment failed</title></head>
<body style="font-family: system-ui; max-width: 480px; margin: 40px auto;">
  <h1>Payment failed</h1>
  <p>Reason: {reason}. (Dev link <code>{link_id}</code>.)</p>
  <p><a href="/">Return to app</a></p>
</body></html>"""


def _abandoned_html(link_id: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><title>Payment abandoned</title></head>
<body style="font-family: system-ui; max-width: 480px; margin: 40px auto;">
  <h1>Payment abandoned</h1>
  <p>No payment was made. (Dev link <code>{link_id}</code>.)</p>
  <p><a href="/">Return to app</a></p>
</body></html>"""


@router.post("/{link_id}/capture", response_class=HTMLResponse)
async def post_capture(
    link_id: str,
    request: Request,
    state: Annotated[str, Form()] = "",
) -> HTMLResponse:
    payload = _decode_state_or_400(state)
    if payload["payment_link_id"] != link_id:
        raise HTTPException(status_code=400, detail="link_id mismatch")
    await _fire_or_502(
        request, event_type="payment.captured", state=payload, amount_paise=payload["amount_paise"]
    )
    return HTMLResponse(content=_success_html(link_id))


@router.post("/{link_id}/decline", response_class=HTMLResponse)
async def post_decline(
    link_id: str,
    request: Request,
    state: Annotated[str, Form()] = "",
) -> HTMLResponse:
    payload = _decode_state_or_400(state)
    if payload["payment_link_id"] != link_id:
        raise HTTPException(status_code=400, detail="link_id mismatch")
    await _fire_or_502(
        request, event_type="payment.failed", state=payload, amount_paise=payload["amount_paise"]
    )
    return HTMLResponse(content=_failure_html(link_id, "declined by user"))


@router.post("/{link_id}/capture-partial", response_class=HTMLResponse)
async def post_capture_partial(
    link_id: str,
    request: Request,
    state: Annotated[str, Form()] = "",
    amount_paise: Annotated[int, Form()] = 0,
) -> HTMLResponse:
    payload = _decode_state_or_400(state)
    if payload["payment_link_id"] != link_id:
        raise HTTPException(status_code=400, detail="link_id mismatch")
    if amount_paise <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    if amount_paise > payload["amount_paise"]:
        raise HTTPException(
            status_code=400,
            detail=f"amount {amount_paise} exceeds invoice total {payload['amount_paise']}",
        )
    await _fire_or_502(
        request, event_type="payment.captured", state=payload, amount_paise=amount_paise
    )
    return HTMLResponse(content=_success_html(link_id))


@router.post("/{link_id}/abandon", response_class=HTMLResponse)
async def post_abandon(
    link_id: str,
    request: Request,
    state: Annotated[str, Form()] = "",
) -> HTMLResponse:
    # Abandon is a no-op: no webhook fires, just return a confirmation page.
    # (Real Razorpay does not fire a webhook when the user abandons either.)
    # We still verify state so a stale/abandoned session can't be probed.
    _decode_state_or_400(state)
    return HTMLResponse(content=_abandoned_html(link_id))
```

- [ ] **Step 4: Run all 12 router tests to verify they pass**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_devsim_router.py -v 2>&1 | tail -15
```

Expected: `12 passed`.

- [ ] **Step 5: Verify no regression on existing tests**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/ --tb=no -q 2>&1 | tail -3
```

Expected: all existing payment tests still pass (no regression from devsim code).

- [ ] **Step 6: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/payments/interfaces/http/devsim_router.py \
        apps/backend/tests/payments/test_devsim_router.py
git commit -m "$(cat <<'EOF'
feat(payments): implement devsim POST action endpoints

Replaces the 4 POST stubs with real implementations:

- POST /capture: fires payment.captured webhook with full invoice
  amount, returns success HTML page
- POST /decline: fires payment.failed webhook, returns failure page
- POST /capture-partial: validates 0 < amount_paise <= invoice total,
  fires payment.captured with the requested amount
- POST /abandon: no-op (no webhook — matches real Razorpay behavior
  on checkout abandonment)

All endpoints:
- Verify state JWT signature + expiry
- Verify path link_id matches state.payment_link_id
- POST to request.url.scheme://request.url.netloc (the backend's
  own origin, never APP_URL which is the frontend)
- Sign payload with settings.razorpay_webhook_secret so the real
  /v1/payments/webhook endpoint accepts it
- Return 502 if the webhook POST fails (5xx or transport error)

Tests: 8 new (capture/decline/partial valid+reject/partial non-pos/
invalid state/abandon/webhook-failure) + 4 GET from Task 5 = 12 total.
EOF
)"
```

---

### Task 7: Wire up in `app.py` (provider swap + router mount + startup guards)

**Files:**
- Modify: `apps/backend/src/common/interfaces/http/app.py:55-68` (lifespan provider init) and `_register_module_routers` (add /dev router mount when enabled)

**Interfaces:**
- Consumes: `Settings.dev_payment_simulator_enabled`, `Settings.dev_state_secret`, `Settings.razorpay_webhook_secret`, `Settings.environment` (Task 1); `DevSimAdapter` (Task 4); `devsim_router` (Task 6)
- Produces: at app startup:
  - Raises `RuntimeError` if `environment == "production"` and `dev_payment_simulator_enabled`
  - Raises `RuntimeError` if `dev_payment_simulator_enabled` and `environment != "development"` and `dev_state_secret == "dev-state-secret-change-me"`
  - Logs a WARNING if `dev_payment_simulator_enabled` and using default secret in dev
  - Instantiates `DevSimAdapter(...)` when `dev_payment_simulator_enabled` (regardless of `payments_provider`)
  - Mounts the devsim router under `/dev` when `dev_payment_simulator_enabled`

---

- [ ] **Step 1: Read the current lifespan block**

```bash
sed -n '49,76p' /home/soloengine/Github/splash_sports_management/apps/backend/src/common/interfaces/http/app.py
```

Expected: the lifespan function starting with `@asynccontextmanager async def lifespan(_: FastAPI)`.

- [ ] **Step 2: Add the validation helpers and modify the provider init**

Edit `apps/backend/src/common/interfaces/http/app.py`. Replace the existing lifespan body lines 55-68 (the comment `# Initialize payment provider and event bus` through `app.state.payment_provider = RazorpayAdapter(...)`) with:

```python
        # --- Startup-time validation for dev payment simulator ---
        if settings.dev_payment_simulator_enabled:
            if settings.environment == "production":
                raise RuntimeError(
                    "DEV_PAYMENT_SIMULATOR_ENABLED must be False when ENVIRONMENT=production"
                )
            if (
                settings.environment != "development"
                and settings.dev_state_secret == "dev-state-secret-change-me"
            ):
                raise RuntimeError(
                    "DEV_STATE_SECRET must be set (not the default) when "
                    "DEV_PAYMENT_SIMULATOR_ENABLED=true and ENVIRONMENT != development"
                )
            if (
                settings.environment == "development"
                and settings.dev_state_secret == "dev-state-secret-change-me"
            ):
                _logger.warning("dev_state_secret_using_default")

        # Initialize payment provider and event bus
        from common.application.events import InProcessEventPublisher
        from payments.application.devsim_adapter import DevSimAdapter
        from payments.application.provider import RazorpayAdapter

        app.state.event_bus = InProcessEventPublisher()
        if settings.dev_payment_simulator_enabled:
            app.state.payment_provider = DevSimAdapter(
                app_url=settings.app_url,
                dev_state_secret=settings.dev_state_secret,
                webhook_secret=settings.razorpay_webhook_secret,
            )
            _logger.warning(
                "payment_simulator_active",
                provider="devsim",
                environment=settings.environment,
            )
        else:
            app.state.payment_provider = RazorpayAdapter(
                key_id=settings.razorpay_key_id,
                key_secret=settings.razorpay_key_secret,
                webhook_secret=settings.razorpay_webhook_secret,
            )
        _logger.info("payment_provider_initialised", provider=type(app.state.payment_provider).__name__)
```

- [ ] **Step 3: Mount the devsim router when enabled**

Edit `_register_module_routers` (lines 105-122). Replace it with:

```python
def _register_module_routers(app: FastAPI) -> None:
    """Mount each module's HTTP router under `/v1/<module>`.

    Each module's router owns its own resource-relative paths (`""`, `/{id}`,
    `/{id}/cancel`, etc.) — the shared prefix adds the module namespace.
    This keeps URLs like `/v1/bookings/{id}/cancel` while letting each module
    router stay self-contained. We import lazily so a broken module doesn't
    prevent the app from booting.
    """
    settings = get_settings()
    for module_name in ("auth", "customer", "facility", "booking", "payments"):
        try:
            module = __import__(module_name, fromlist=["interfaces"])
            router = getattr(module.interfaces, "router", None)  # type: ignore[attr-defined]
        except (ImportError, AttributeError):
            continue
        if router is None:
            continue
        app.include_router(router, prefix=f"/v1/{module_name}", tags=[module_name])

    # Dev payment simulator (gated by env flag, never mounted in prod).
    if settings.dev_payment_simulator_enabled:
        try:
            from payments.interfaces.http.devsim_router import router as devsim_router

            app.include_router(devsim_router, prefix="/dev", tags=["dev-payment-simulator"])
        except ImportError:
            _logger.warning("devsim_router_unavailable")
```

- [ ] **Step 4: Verify the app still boots**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src python -c "from common.interfaces.http.app import create_app; app = create_app(); print('OK', [r.path for r in app.routes if 'dev' in r.path])"
```

Expected: `OK []` (no dev routes mounted by default; the `DEV_PAYMENT_SIMULATOR_ENABLED` env var is not set in the default environment).

- [ ] **Step 5: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/common/interfaces/http/app.py
git commit -m "$(cat <<'EOF'
feat(payments): wire devsim into app startup (provider swap + router mount)

When DEV_PAYMENT_SIMULATOR_ENABLED=true:
- DevSimAdapter replaces RazorpayAdapter (regardless of PAYMENTS_PROVIDER)
- /dev/mock-checkout router is mounted under /dev

Startup-time validation (raises RuntimeError on app construction):
- environment=production + simulator enabled → refuse to start
- environment!=development + simulator enabled + default secret → refuse
- environment=development + simulator enabled + default secret → warn only

Mounted only when the flag is set, so production has zero devsim code
in its URL surface.
EOF
)"
```

---

### Task 8: Production-guard tests

**Files:**
- Create: `apps/backend/tests/payments/test_settings_prod_guard.py`

**Interfaces:**
- Consumes: `create_app()` from `common.interfaces.http.app` (Task 7)
- Produces: 2 test functions that exercise the startup validation in Task 7

---

- [ ] **Step 1: Write the failing tests**

Create `apps/backend/tests/payments/test_settings_prod_guard.py`:

```python
"""Startup-time validation: dev simulator must never run in production, and
must never use the default secret outside development.
"""
from __future__ import annotations

import pytest


def test_prod_env_with_simulator_enabled_raises_on_app_creation(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_PAYMENT_SIMULATOR_ENABLED", "true")
    monkeypatch.setenv("DEV_STATE_SECRET", "any-real-secret-32chars-or-more-xxx")

    from common.infrastructure.settings import reset_settings_cache, get_settings
    reset_settings_cache()
    settings = get_settings()
    assert settings.environment == "production"
    assert settings.dev_payment_simulator_enabled is True

    from common.interfaces.http.app import create_app
    with pytest.raises(RuntimeError, match="DEV_PAYMENT_SIMULATOR_ENABLED must be False"):
        create_app()


def test_non_dev_env_with_simulator_enabled_and_default_secret_raises(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DEV_PAYMENT_SIMULATOR_ENABLED", "true")
    monkeypatch.setenv("DEV_STATE_SECRET", "dev-state-secret-change-me")

    from common.infrastructure.settings import reset_settings_cache
    reset_settings_cache()

    from common.interfaces.http.app import create_app
    with pytest.raises(RuntimeError, match="DEV_STATE_SECRET must be set"):
        create_app()


def test_dev_env_with_simulator_and_default_secret_does_not_raise(monkeypatch):
    """Sanity check: dev + simulator + default secret is allowed (with warning)."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_PAYMENT_SIMULATOR_ENABLED", "true")
    monkeypatch.setenv("DEV_STATE_SECRET", "dev-state-secret-change-me")

    from common.infrastructure.settings import reset_settings_cache
    reset_settings_cache()

    from common.interfaces.http.app import create_app
    # Should not raise
    app = create_app()
    # /dev route is mounted
    paths = [r.path for r in app.routes]
    assert any("/dev/mock-checkout" in p for p in paths)


def test_devsim_routes_not_mounted_when_flag_false(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_PAYMENT_SIMULATOR_ENABLED", "false")

    from common.infrastructure.settings import reset_settings_cache
    reset_settings_cache()

    from common.interfaces.http.app import create_app
    app = create_app()
    paths = [r.path for r in app.routes]
    assert not any("/dev/mock-checkout" in p for p in paths)
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/test_settings_prod_guard.py -v 2>&1 | tail -15
```

Expected: `4 passed`. (The validation logic was added in Task 7, so the tests should already pass; this is verification, not red→green.)

- [ ] **Step 3: Verify no regression on existing payment tests**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/payments/ --tb=no -q 2>&1 | tail -3
```

Expected: all existing payment tests still pass.

- [ ] **Step 4: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/tests/payments/test_settings_prod_guard.py
git commit -m "$(cat <<'EOF'
test(payments): cover devsim startup guards

Verifies Task 7's validation:
- env=production + simulator → raises RuntimeError
- env=staging + simulator + default secret → raises RuntimeError
- env=development + simulator + default secret → app boots, /dev route mounted
- env=development + simulator disabled → app boots, no /dev route
EOF
)"
```

---

## Verification (after all tasks land)

- [ ] `pytest tests/payments/test_devsim_*.py tests/payments/test_settings_prod_guard.py tests/payments/test_devsim_settings.py` → all green
- [ ] `pytest tests/payments/` (full payment suite) → all 88+ existing tests still pass, no regression
- [ ] With `DEV_PAYMENT_SIMULATOR_ENABLED=true` and `ENVIRONMENT=development`:
  - `curl http://localhost:8000/v1/payments/<payment_id>/link -X POST ...` → returns `short_url` starting with `http://localhost:5173/dev/mock-checkout/`
  - Open `short_url` in browser → renders fake Razorpay page
  - Click "Pay" → success page appears, booking is confirmed in DB
  - Click "Decline" → failure page, booking stays `awaiting_payment`
- [ ] With `ENVIRONMENT=production` and `DEV_PAYMENT_SIMULATOR_ENABLED=true` → app fails to start with the documented RuntimeError
- [ ] With `ENVIRONMENT=staging` and `DEV_PAYMENT_SIMULATOR_ENABLED=true` and default `DEV_STATE_SECRET` → app fails to start

## Out of scope

- An end-to-end integration test (full booking → mock checkout → webhook → booking confirmed). The unit tests in Tasks 2-8 cover the devsim contract at the component level. A full integration test requires DB seeding (tenant/customer/resource/booking/invoice/payment) using the pattern from `tests/integration/test_booking_service.py` and the HTTP client pattern from `tests/payments/test_invoice_endpoints.py`. Recommended as a follow-up PR that adds `tests/integration/test_devsim_end_to_end.py`.
- Replacing `NullAdapter` (kept for unit tests that just need a deterministic stub).
- Reconciling abandoned checkouts (no timeout fires; relies on existing reconciliation logic if any).
- Styling the fake checkout page to look like real Razorpay.
- Multi-currency partial payments (only INR supported, matches RazorpayAdapter).
