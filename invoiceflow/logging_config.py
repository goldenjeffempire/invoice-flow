"""Structured JSON logging configuration for production observability."""

import json
import logging
import re
import threading
import traceback
from datetime import datetime, timezone
from typing import Any

_request_context = threading.local()


def set_request_context(
    request_id: str | None = None, user_id: int | None = None, ip_address: str | None = None
) -> None:
    """Set request context for the current thread."""
    _request_context.request_id = request_id
    _request_context.user_id = user_id
    _request_context.ip_address = ip_address


def clear_request_context() -> None:
    """Clear request context for the current thread."""
    _request_context.request_id = None
    _request_context.user_id = None
    _request_context.ip_address = None


def get_request_context() -> dict[str, Any]:
    """Get current request context for the current thread."""
    return {
        "request_id": getattr(_request_context, "request_id", None),
        "user_id": getattr(_request_context, "user_id", None),
        "ip_address": getattr(_request_context, "ip_address", None),
    }


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        scrubbed = value
        scrubbed = re.sub(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)", "***@***", scrubbed)
        scrubbed = re.sub(r"\bINV-[A-F0-9]{8}\b", "INV-********", scrubbed)
        scrubbed = re.sub(r"\bref_[A-Za-z0-9]+\b", "ref_********", scrubbed)
        return scrubbed
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub_value(val) for key, val in value.items()}
    return value


class PiiScrubberFilter(logging.Filter):
    """Scrub sensitive values from log records."""

    sensitive_keys = {"email", "client_email", "business_email", "reference", "invoice_id", "name"}

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _scrub_value(record.msg)
        if record.args:
            record.args = tuple(_scrub_value(arg) for arg in record.args)
        for key, value in list(record.__dict__.items()):
            if key in self.sensitive_keys:
                record.__dict__[key] = "***"
            elif key == "extra" and isinstance(value, dict):
                record.__dict__[key] = _scrub_value(value)
        return True


class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs logs in a format compatible with log aggregation services.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.process:
            log_data["process_id"] = record.process

        if record.thread:
            log_data["thread_id"] = record.thread

        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id") and record.user_id:
            log_data["user_id"] = record.user_id

        if hasattr(record, "ip_address") and record.ip_address:
            log_data["ip_address"] = record.ip_address

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": (
                    traceback.format_exception(*record.exc_info) if record.exc_info[2] else None
                ),
            }

        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "request_id",
                "user_id",
                "ip_address",
                "message",
            ]:
                if not key.startswith("_"):
                    extra_fields[key] = value

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """
    Logging filter that adds request context from thread-local storage to log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        context = get_request_context()
        for key, value in context.items():
            if value is not None:
                setattr(record, key, value)
        return True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the application's configuration."""
    return logging.getLogger(name)
