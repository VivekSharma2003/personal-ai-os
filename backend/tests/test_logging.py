"""
Tests for Structured Logging & Request Tracing (Feature 2).
"""
import json
import logging
import pytest

from app.core.logging import (
    JSONFormatter,
    get_logger,
    setup_logging,
    request_id_var,
    user_id_var,
)


def test_json_formatter_produces_valid_json():
    """JSONFormatter should output parseable JSON."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Hello structured logging",
        args=None,
        exc_info=None,
    )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Hello structured logging"
    assert "timestamp" in parsed
    assert "request_id" in parsed
    assert "logger" in parsed


def test_json_formatter_includes_request_id():
    """Request ID from contextvars should appear in log output."""
    token = request_id_var.set("test-req-123")
    try:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="With correlation ID",
            args=None,
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["request_id"] == "test-req-123"
    finally:
        request_id_var.reset(token)


def test_json_formatter_includes_user_id():
    """User ID from contextvars should appear in log output."""
    token = user_id_var.set("user-456")
    try:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="With user ID",
            args=None,
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["user_id"] == "user-456"
    finally:
        user_id_var.reset(token)


def test_json_formatter_includes_source_for_errors():
    """Error logs should include source file/line information."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="/app/core/test.py",
        lineno=42,
        msg="Something went wrong",
        args=None,
        exc_info=None,
    )

    output = formatter.format(record)
    parsed = json.loads(output)
    assert "source" in parsed
    assert parsed["source"]["line"] == 42


def test_get_logger_returns_named_logger():
    """get_logger should return a logger with the given name."""
    logger = get_logger("app.test_module")
    assert logger.name == "app.test_module"
    assert isinstance(logger, logging.Logger)


def test_json_formatter_handles_extra_data():
    """Extra data should be included when provided."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="With extras",
        args=None,
        exc_info=None,
    )
    record.extra_data = {"key": "value", "count": 42}

    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["data"]["key"] == "value"
    assert parsed["data"]["count"] == 42
