"""HTTP middleware.

* `RequestContextMiddleware` — binds [`RequestContext`] to the current task,
  reads `X-Request-ID` (or generates one), and adds it to the response.
* `CORSMiddleware` — handled by Starlette (configured via settings).
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from common.application.context import RequestContext, bind_context, reset_context
from common.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a [`RequestContext`] for the duration of the request."""

    def __init__(self, app: Callable, *, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming_id = request.headers.get(self.header_name)
        request_id = incoming_id if incoming_id else RequestContext.new().request_id

        ctx = RequestContext(request_id=request_id)
        bind_context(ctx)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            _logger.exception("request_failed", method=request.method, path=request.url.path)
            raise
        finally:
            reset_context()

        elapsed_ms = (time.perf_counter() - start) * 1000
        _logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(elapsed_ms, 2),
        )
        response.headers[self.header_name] = request_id
        return response
