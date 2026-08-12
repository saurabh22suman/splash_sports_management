"""RFC 7807 problem+json error responses.

Maps domain exceptions to HTTP responses. The HTTP layer is the only place
that knows about HTTP; modules raise domain exceptions and this layer
translates.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.application.context import get_context
from common.domain.exceptions import DomainError
from common.infrastructure.logging import get_logger

_logger = get_logger(__name__)


def _problem(
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = get_context().request_id if get_context() else None
    body: dict[str, Any] = {
        "type": f"https://errors.splashh.dev/{code}",
        "title": title,
        "status": status_code,
        "code": code,
    }
    if detail is not None:
        body["detail"] = detail
    if errors is not None:
        body["errors"] = errors
    if request_id:
        body["request_id"] = request_id

    return JSONResponse(status_code=status_code, content=body)


async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    _logger.info("domain_error", code=exc.code, message=exc.message, details=exc.details)
    return _problem(
        status_code=exc.http_status,
        code=exc.code,
        title=exc.__class__.__name__,
        detail=exc.message,
    )


async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(p) for p in err.get("loc", [])),
            "message": err.get("msg", ""),
            "type": err.get("type"),
        }
        for err in exc.errors()
    ]
    return _problem(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        title="Validation Error",
        detail="One or more fields failed validation",
        errors=errors,
    )


async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _problem(
        status_code=exc.status_code,
        code=f"http_{exc.status_code}",
        title=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        detail=exc.detail if isinstance(exc.detail, str) else None,
    )


async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    _logger.exception("unhandled_exception", error=str(exc))
    return _problem(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        title="Internal Server Error",
        detail="An unexpected error occurred.",
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
