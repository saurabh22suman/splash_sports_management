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

from common.infrastructure.logging import get_logger
from common.infrastructure.settings import get_settings
from payments.application.devsim_state import decode_state
from payments.application.devsim_webhook import build_event, sign_payload, post_webhook

_logger = get_logger(__name__)


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
    except jwt.ExpiredSignatureError as exc:
        _logger.warning("devsim.state_tamper", reason="expired_jwt", token_prefix=token[:20] if token else "")
        raise HTTPException(status_code=400, detail=f"invalid state: {exc}") from exc
    except jwt.InvalidSignatureError as exc:
        _logger.warning("devsim.state_tamper", reason="invalid_jwt", token_prefix=token[:20] if token else "")
        raise HTTPException(status_code=400, detail=f"invalid state: {exc}") from exc
    except jwt.PyJWTError as exc:
        _logger.warning("devsim.state_tamper", reason="malformed_jwt", token_prefix=token[:20] if token else "")
        raise HTTPException(status_code=400, detail=f"invalid state: {exc}") from exc


@router.get("/{link_id}", response_class=HTMLResponse)
async def get_checkout(
    link_id: str,
    state: Annotated[str | None, Query(description="Signed state JWT")] = None,
) -> HTMLResponse:
    """Render the fake Razorpay-style checkout page."""
    if not state:
        raise HTTPException(status_code=400, detail="state is required")
    payload = _decode_state_or_400(state)
    if payload["payment_link_id"] != link_id:
        _logger.warning("devsim.state_tamper", link_id=link_id, reason="link_id_mismatch")
        raise HTTPException(status_code=400, detail="link_id mismatch")
    return HTMLResponse(content=_render_checkout_html(payload))


# ---- POST endpoints (Task 6 implementations) ----


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
) -> tuple[bytes, str, str]:
    """Build event, sign with webhook secret, POST to real webhook endpoint."""
    import json

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
        _logger.warning("devsim.state_tamper", link_id=link_id, reason="link_id_mismatch")
        raise HTTPException(status_code=400, detail="link_id mismatch")
    await _fire_or_502(
        request, event_type="payment.captured", state=payload, amount_paise=payload["amount_paise"]
    )
    _logger.info(
        "devsim.action",
        link_id=link_id,
        tenant_id=payload["tenant_id"],
        payment_id=payload["payment_id"],
        action="capture",
        result="success",
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
        _logger.warning("devsim.state_tamper", link_id=link_id, reason="link_id_mismatch")
        raise HTTPException(status_code=400, detail="link_id mismatch")
    await _fire_or_502(
        request, event_type="payment.failed", state=payload, amount_paise=payload["amount_paise"]
    )
    _logger.info(
        "devsim.action",
        link_id=link_id,
        tenant_id=payload["tenant_id"],
        payment_id=payload["payment_id"],
        action="decline",
        result="success",
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
        _logger.warning("devsim.state_tamper", link_id=link_id, reason="link_id_mismatch")
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
    _logger.info(
        "devsim.action",
        link_id=link_id,
        tenant_id=payload["tenant_id"],
        payment_id=payload["payment_id"],
        action="capture-partial",
        result="success",
        amount_paise=amount_paise,
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
    payload = _decode_state_or_400(state)
    if payload["payment_link_id"] != link_id:
        _logger.warning("devsim.state_tamper", link_id=link_id, reason="link_id_mismatch")
        raise HTTPException(status_code=400, detail="link_id mismatch")
    _logger.info(
        "devsim.action",
        link_id=link_id,
        tenant_id=payload["tenant_id"],
        payment_id=payload["payment_id"],
        action="abandon",
        result="abandoned",
    )
    return HTMLResponse(content=_abandoned_html(link_id))
