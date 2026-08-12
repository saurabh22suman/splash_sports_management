"""Tests for the /webhooks/razorpay endpoint."""

import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401
from auth.infrastructure.models import TenantModel
from auth.interfaces.http.dependencies import auth_required, CurrentPrincipal
from common.domain.exceptions import Validation
from common.infrastructure import db as db_module
from payments.infrastructure.models import (
    InvoiceLineItemModel,
    InvoiceModel,
    PaymentModel,
    ProcessedRazorpayEventModel,
    RefundModel,
    TenantPaymentConfigModel,
)
from payments.interfaces.http.deps import get_payment_service
from payments.interfaces.http.router import router as payments_router

WEBHOOK_SECRET = "whsec_test_secret"


def _sign(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Build FastAPI app with payments router and dependency overrides for testing."""
    from common.interfaces.http.errors import register_error_handlers

    app = FastAPI()
    # Register error handlers to convert domain exceptions to HTTP responses
    register_error_handlers(app)
    # Include router at /v1/payments to match main app behavior
    app.include_router(payments_router, prefix="/v1/payments")

    # Create in-memory SQLite for testing - needed for F-07 tenant resolution
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(TenantModel.__table__.create)
        await conn.run_sync(TenantPaymentConfigModel.__table__.create)
        await conn.run_sync(InvoiceModel.__table__.create)
        await conn.run_sync(InvoiceLineItemModel.__table__.create)
        await conn.run_sync(PaymentModel.__table__.create)
        await conn.run_sync(RefundModel.__table__.create)
        await conn.run_sync(ProcessedRazorpayEventModel.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Seed test data with a tenant for F-07 webhook tenant resolution
    tenant_id = uuid4()
    async with factory() as session:
        # Create tenant
        tenant = TenantModel(
            id=tenant_id,
            name="Test Tenant",
            slug="test-tenant",
            primary_contact_email="test@example.com",
            status="onboarding",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(tenant)

        # Create tenant payment config
        cfg = TenantPaymentConfigModel(
            tenant_id=tenant_id,
            razorpay_account_id="acc_test_123",
            default_currency="INR",
        )
        session.add(cfg)

        await session.commit()

    _factory = factory

    async def override_get_session():
        async with _factory() as s:
            yield s

    # Override get_session for the webhook endpoint
    app.dependency_overrides[db_module.get_session] = override_get_session

    # Override auth_required so the webhook doesn't require auth
    # The webhook uses signature verification instead
    test_principal = CurrentPrincipal(
        user_id=uuid4(),
        tenant_id=tenant_id,
        roles=("tenant_admin",),
        jti="webhook-test-jti",
    )
    app.dependency_overrides[auth_required] = lambda: test_principal

    # Create a mock provider that simulates signature verification
    mock_provider = MagicMock()
    mock_provider.verify_webhook = MagicMock(
        side_effect=lambda payload, sig: (
            json.loads(payload)
            if sig != "badsig"
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
                raise Validation("Invalid webhook signature", details={"error": str(e)}) from e

        svc.handle_webhook = AsyncMock(side_effect=mock_handle_webhook)
        return svc

    app.dependency_overrides[get_payment_service] = _service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_webhook_returns_200(client: AsyncClient) -> None:
    """Test that a valid signed webhook returns 200."""
    payload_dict = {
        "id": "evt_1",
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_1"}}},
    }
    payload = json.dumps(payload_dict).encode()
    response = await client.post(
        "/v1/payments/webhooks/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": _sign(payload)},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webhook_400_on_invalid_signature(client: AsyncClient) -> None:
    """Test that an invalid signature returns 400."""
    payload = b"{}"
    response = await client.post(
        "/v1/payments/webhooks/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": "badsig"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_400_on_missing_signature_header(client: AsyncClient) -> None:
    """Test that missing signature header returns 400."""
    response = await client.post("/v1/payments/webhooks/razorpay", content=b"{}")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_end_to_end_with_real_signature() -> None:
    """End-to-end: verifies webhook with real RazorpayAdapter verifies signature correctly.

    Note: Full E2E with database state changes requires production-like session management.
    This test verifies the signature verification path works correctly.
    """
    from datetime import datetime
    from payments.application.provider import RazorpayAdapter

    # Test that the real RazorpayAdapter correctly verifies HMAC-SHA256 signatures
    adapter = RazorpayAdapter(
        key_id="rzp_test_xxx", key_secret="test_secret", webhook_secret=WEBHOOK_SECRET
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
