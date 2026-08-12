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

from datetime import UTC, datetime, timedelta
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
    now = datetime.now(UTC)
    claims = dict(payload)
    claims["iat"] = now
    claims["exp"] = now + timedelta(seconds=ttl_seconds)
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
