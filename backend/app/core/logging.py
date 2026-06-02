"""
Personal AI OS - Structured Logging & Request Tracing

Provides JSON-formatted structured logging with per-request correlation IDs
propagated via `contextvars`. Includes a FastAPI middleware that generates
or extracts `X-Request-ID` headers.
"""
import logging
import json
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

# pyrefly: ignore [missing-import]
from fastapi import Request, Response
# pyrefly: ignore [missing-import]
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


# --- Context Variables ---
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")


# --- JSON Log Formatter ---

class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.

    Automatically attaches request_id and user_id from contextvars
    to every log line for distributed tracing.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get("-"),
            "user_id": user_id_var.get("-"),
        }

        # Add extra fields if present
        if hasattr(record, "extra_data") and record.extra_data:
            log_entry["data"] = record.extra_data

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add source location for errors
        if record.levelno >= logging.WARNING:
            log_entry["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_entry, default=str)


# --- Logger Factory ---

_configured = False


def setup_logging(level: str = "INFO"):
    """
    Configure the root logger with JSON formatting.

    Call once during application startup.
    """
    global _configured
    if _configured:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with structured JSON output.

    Usage:
        logger = get_logger(__name__)
        logger.info("Rule created", extra={"extra_data": {"rule_id": "..."}})
    """
    if not _configured:
        setup_logging()
    return logging.getLogger(name)


# --- Request Tracing Middleware ---

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that assigns a unique `X-Request-ID` to every request.

    If the client sends an `X-Request-ID` header, it is reused.
    The ID is stored in a contextvar and automatically attached
    to all structured log output.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract or generate request ID
        req_id = request.headers.get("X-Request-ID", uuid4().hex[:16])
        request_id_var.set(req_id)

        # Extract user identifier
        user = request.headers.get("X-User-ID", "-")
        user_id_var.set(user)

        logger = get_logger("http")
        start_time = time.time()

        logger.info(
            f"{request.method} {request.url.path}",
            extra={"extra_data": {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "client": request.client.host if request.client else "unknown",
            }},
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"Request failed: {exc}",
                exc_info=True,
                extra={"extra_data": {"duration_ms": duration_ms}},
            )
            raise

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Attach headers
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Duration-Ms"] = str(duration_ms)

        logger.info(
            f"{request.method} {request.url.path} → {response.status_code}",
            extra={"extra_data": {
                "status": response.status_code,
                "duration_ms": duration_ms,
            }},
        )

        return response
