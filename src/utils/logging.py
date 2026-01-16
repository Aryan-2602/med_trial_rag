"""Structured logging configuration."""

import contextvars
import time
import uuid
from contextlib import contextmanager
from typing import Any

import structlog

# Request ID context variable
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def configure_logging() -> None:
    """Configure structlog with JSON renderer and UTC timestamps."""
    import logging
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(*args: Any, **kwargs: Any) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    logger = structlog.get_logger(*args, **kwargs)
    request_id = request_id_var.get("")
    if request_id:
        logger = logger.bind(request_id=request_id)
    return logger


def set_request_id(req_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(req_id)


def get_request_id() -> str:
    """Get current request ID, generating one if missing."""
    req_id = request_id_var.get("")
    if not req_id:
        req_id = str(uuid.uuid4())
        request_id_var.set(req_id)
    return req_id


@contextmanager
def log_timing(name: str, **fields: Any):
    """Context manager to log timing information."""
    logger = get_logger()
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"{name}_completed", duration_ms=elapsed_ms, **fields)

