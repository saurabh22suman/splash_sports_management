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
    state: Annotated[str | None, Query(description="Signed state JWT")] = None,
) -> HTMLResponse:
    """Render the fake Razorpay-style checkout page."""
    if not state:
        raise HTTPException(status_code=400, detail="state is required")
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
