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
