"""Global exception handlers – prevent internal details from leaking."""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """Pass through HTTPException with structured detail if already dict."""
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content={"error": detail})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(detail)}},
    )


async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all: log the real error, return a safe 500 with trace_id."""
    trace_id = uuid.uuid4().hex
    logger.exception(
        "Unhandled exception on %s %s [trace_id=%s]",
        request.method, request.url.path, trace_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "trace_id": trace_id,
            }
        },
    )
