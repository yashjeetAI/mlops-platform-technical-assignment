"""HTTP middleware: correlation IDs and request logging."""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import get_logger

CORRELATION_HEADER = "X-Request-ID"

logger = get_logger("http")


def get_correlation_id() -> str | None:
    """Current request's correlation id from the bound log context (or None)."""
    return structlog.contextvars.get_contextvars().get("correlation_id")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Bind a correlation id to the log context for the whole request.

    Reuses an inbound `X-Request-ID` if present, otherwise generates one, echoes
    it back in the response header, and logs one structured line per request.
    """

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid7())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("request_failed", duration_ms=duration_ms)
            structlog.contextvars.clear_contextvars()
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info("request", status_code=response.status_code, duration_ms=duration_ms)
        response.headers[CORRELATION_HEADER] = correlation_id
        structlog.contextvars.clear_contextvars()
        return response
