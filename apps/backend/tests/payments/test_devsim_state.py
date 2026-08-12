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
