"""Tests for the /webhooks/razorpay endpoint."""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from common.domain.exceptions import Validation
from payments.interfaces.http.deps import get_payment_service
from payments.interfaces.http.router import router as payments_router

WEBHOOK_SECRET = "whsec_test_secret"


def _sign(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@pytest.fixture
async def client():
    app = FastAPI()
    app.include_router(payments_router, prefix="/v1")

    # Create a mock provider that simulates signature verification
    mock_provider = MagicMock()
    mock_provider.verify_webhook = MagicMock(
        side_effect=lambda payload, sig: (
            json.loads(payload) if sig != "badsig"
            else (_ for _ in ()).throw(Validation("Invalid signature"))
        ),
    )

    app.state.payment_provider = mock_provider
    app.state.event_bus = MagicMock()

    # Override service dep with a mock that calls through to verify_webhook
    async def _service():
        svc = MagicMock()

        # Make handle_webhook actually verify signature via provider
        async def mock_handle_webhook(*, raw_payload: bytes, signature: str):
            # This simulates what the real service does
            try:
                mock_provider.verify_webhook(raw_payload, signature)
            except Exception as e:
                raise Validation(
                    "Invalid webhook signature", details={"error": str(e)}
                ) from e

        svc.handle_webhook = AsyncMock(side_effect=mock_handle_webhook)
        return svc

    app.dependency_overrides[get_payment_service] = _service
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_webhook_returns_200(client):
    """Test that a valid signed webhook returns 200."""
    payload_dict = {
        "id": "evt_1",
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_1"}}},
    }
    payload = json.dumps(payload_dict).encode()
    response = await client.post(
        "/v1/webhooks/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": _sign(payload)},
    )
    assert response.status_code == 200


async def test_webhook_400_on_invalid_signature(client):
    """Test that an invalid signature returns 400."""
    payload = b"{}"
    response = await client.post(
        "/v1/webhooks/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": "badsig"},
    )
    assert response.status_code == 400


async def test_webhook_400_on_missing_signature_header(client):
    """Test that missing signature header returns 400."""
    response = await client.post("/v1/webhooks/razorpay", content=b"{}")
    assert response.status_code == 400


async def test_webhook_end_to_end_with_real_signature():
    """End-to-end: verifies webhook with real RazorpayAdapter verifies signature correctly.

    Note: Full E2E with database state changes requires production-like session management.
    This test verifies the signature verification path works correctly.
    """
    from payments.application.provider import RazorpayAdapter

    # Test that the real RazorpayAdapter correctly verifies HMAC-SHA256 signatures
    adapter = RazorpayAdapter(
        key_id="rzp_test_xxx",
        key_secret="test_secret",
        webhook_secret=WEBHOOK_SECRET
    )

    # Build a valid payload
    payload_dict = {
        "id": "evt_test_1",
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_test_1"}}},
    }
    payload = json.dumps(payload_dict).encode()
    valid_sig = _sign(payload)

    # Verify valid signature passes
    result = adapter.verify_webhook(payload, valid_sig)
    assert result["id"] == "evt_test_1"

    # Verify invalid signature raises
    from razorpay.errors import SignatureVerificationError
    with pytest.raises(SignatureVerificationError):
        adapter.verify_webhook(payload, "invalid_signature")
