"""Structured logging via structlog.

JSON output in deployed environments; coloured console output for local dev.
Per-request context (e.g. correlation_id) is merged in through contextvars, so
every log line emitted during a request carries it — similar to pino child loggers.
"""
import logging

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    is_local = settings.environment == "local"
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    renderer = (
        structlog.dev.ConsoleRenderer()
        if is_local
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
