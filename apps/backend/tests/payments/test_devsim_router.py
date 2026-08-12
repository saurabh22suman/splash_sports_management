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
    from common.infrastructure.logging import configure_logging
    from common.infrastructure.settings import reset_settings_cache, get_settings

    reset_settings_cache()
    settings = get_settings()
    assert settings.dev_state_secret == DEV_STATE_SECRET

    # Configure structlog to route through stdlib logging so pytest's caplog can capture.
    # json_logs=True keeps messages parseable (no ANSI color codes breaking assertions).
    configure_logging(level="INFO", json_logs=True)
    _ = settings  # silence unused warning

    app = FastAPI()
    app.include_router(devsim_router)
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
    response = await client.get(f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}?state=not-a-jwt")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_checkout_with_expired_state_returns_400(client):
    payload = _payload()
    payload["exp"] = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
    expired = jwt.encode(payload, DEV_STATE_SECRET, algorithm="HS256")
    response = await client.get(f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}?state={expired}")
    assert response.status_code == 400


# ---- POST endpoint tests (Task 6) ----


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


# ---- Logging tests (Final fix) ----
# Note: structlog outputs to stdout via ConsoleRenderer, so we use capfd to capture


@pytest.mark.asyncio
async def test_post_capture_logs_devsim_action(client, monkeypatch, caplog):
    """Verify devsim.action is logged on successful capture."""
    from payments.interfaces.http import devsim_router as router_module

    async def fake_post(url, payload, *, signature):
        return 200

    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    token = _valid_state_token()
    with caplog.at_level("INFO", logger="payments.interfaces.http.devsim_router"):
        response = await client.post(
            f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture",
            data={"state": token},
        )
    assert response.status_code == 200

    # Check that devsim.action was logged (caplog is independent of stream config).
    text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "devsim.action" in text
    assert DEV_PAYMENT_LINK_ID in text
    assert ('"action": "capture"' in text) or ("action=capture" in text)
    assert ('"result": "success"' in text) or ("result=success" in text)


@pytest.mark.asyncio
async def test_post_decline_logs_devsim_action(client, monkeypatch, caplog):
    """Verify devsim.action is logged on decline."""
    from payments.interfaces.http import devsim_router as router_module

    async def fake_post(url, payload, *, signature):
        return 200

    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    token = _valid_state_token()
    with caplog.at_level("INFO", logger="payments.interfaces.http.devsim_router"):
        response = await client.post(
            f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/decline",
            data={"state": token},
        )
    assert response.status_code == 200

    text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "devsim.action" in text
    assert ('"action": "decline"' in text) or ("action=decline" in text)


@pytest.mark.asyncio
async def test_post_abandon_logs_devsim_action(client, caplog):
    """Verify devsim.action is logged on abandon (no webhook fired)."""
    token = _valid_state_token()
    with caplog.at_level("INFO", logger="payments.interfaces.http.devsim_router"):
        response = await client.post(
            f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/abandon",
            data={"state": token},
        )
    assert response.status_code == 200

    text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "devsim.action" in text
    assert ('"action": "abandon"' in text) or ("action=abandon" in text)
    assert ('"result": "abandoned"' in text) or ("result=abandoned" in text)


@pytest.mark.asyncio
async def test_invalid_state_logs_devsim_state_tamper(client, caplog):
    """Verify devsim.state_tamper is logged on invalid JWT."""
    with caplog.at_level("WARNING", logger="payments.interfaces.http.devsim_router"):
        response = await client.post(
            f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture",
            data={"state": "not-a-valid-jwt"},
        )
    assert response.status_code == 400

    text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "devsim.state_tamper" in text
    has_malformed = '"reason": "malformed_jwt"' in text or "reason=malformed_jwt" in text
    has_invalid = '"reason": "invalid_jwt"' in text or "reason=invalid_jwt" in text
    assert has_malformed or has_invalid


@pytest.mark.asyncio
async def test_link_id_mismatch_logs_devsim_state_tamper(client, monkeypatch, caplog):
    """Verify devsim.state_tamper is logged on link_id mismatch."""
    from payments.interfaces.http import devsim_router as router_module

    async def fake_post(url, payload, *, signature):
        return 200

    monkeypatch.setattr(router_module, "post_webhook", fake_post)

    # Create token with different link_id
    payload = _payload()
    payload["payment_link_id"] = "plink_dev_different"
    from payments.application.devsim_state import encode_state

    wrong_link_token = encode_state(payload, secret=DEV_STATE_SECRET, ttl_seconds=3600)

    with caplog.at_level("WARNING", logger="payments.interfaces.http.devsim_router"):
        response = await client.post(
            f"/dev/mock-checkout/{DEV_PAYMENT_LINK_ID}/capture",
            data={"state": wrong_link_token},
        )
    assert response.status_code == 400

    text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "devsim.state_tamper" in text
    assert ('"reason": "link_id_mismatch"' in text) or ("reason=link_id_mismatch" in text)
