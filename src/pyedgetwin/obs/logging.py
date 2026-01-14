"""Structured logging for PyEdgeTwin."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Outputs log records as single-line JSON objects, suitable for
    log aggregation systems like Elasticsearch, Loki, or CloudWatch.
    """

    def __init__(
        self,
        include_extra: bool = True,
        timestamp_format: str = "iso",
    ) -> None:
        """
        Initialize the JSON formatter.

        Args:
            include_extra: Include extra fields from log records
            timestamp_format: 'iso' for ISO8601, 'unix' for Unix timestamp
        """
        super().__init__()
        self._include_extra = include_extra
        self._timestamp_format = timestamp_format

        # Fields that are part of the standard LogRecord
        self._reserved_attrs = {
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
            "taskName",
            "message",
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Build the base log object
        log_obj: dict[str, Any] = {
            "timestamp": self._format_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add source location for errors
        if record.levelno >= logging.WARNING:
            log_obj["source"] = {
                "file": record.filename,
                "function": record.funcName,
                "line": record.lineno,
            }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_obj["stack_trace"] = record.stack_info

        # Add extra fields from the record
        if self._include_extra:
            for key, value in record.__dict__.items():
                if key not in self._reserved_attrs and not key.startswith("_"):
                    log_obj[key] = self._serialize_value(value)

        return json.dumps(log_obj, default=str)

    def _format_timestamp(self, record: logging.LogRecord) -> str | float:
        """Format the timestamp according to configuration."""
        if self._timestamp_format == "unix":
            return record.created

        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat()

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON output."""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if hasattr(value, "__dict__"):
            return str(value)
        return value


class ContextLogger(logging.LoggerAdapter[logging.Logger]):
    """
    Logger adapter that automatically includes context fields.

    Use this to add consistent context (twin_id, asset_id, etc.) to all
    log messages without repeating them in each call.

    Example:
        logger = ContextLogger(
            logging.getLogger(__name__),
            {"twin_id": "motor-twin-001", "asset_id": "motor-001"}
        )
        logger.info("Processing message")
        # Outputs: {"twin_id": "motor-twin-001", "asset_id": "motor-001", "message": "Processing message", ...}
    """

    def process(  # type: ignore[override]
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Add context fields to the log record."""
        # Merge extra with existing context
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    _twin_id: str | None = None,
    _asset_id: str | None = None,
) -> logging.Logger:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, use JSON formatting
        twin_id: Optional twin ID to include in all logs
        asset_id: Optional asset ID to include in all logs

    Returns:
        Configured root logger
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root.handlers = []

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("paho").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("influxdb_client").setLevel(logging.WARNING)

    return root


def get_context_logger(
    name: str,
    twin_id: str | None = None,
    asset_id: str | None = None,
    **extra: Any,
) -> ContextLogger:
    """
    Get a logger with automatic context fields.

    Args:
        name: Logger name (usually __name__)
        twin_id: Twin ID to include in logs
        asset_id: Asset ID to include in logs
        **extra: Additional context fields

    Returns:
        ContextLogger with the specified context
    """
    context: dict[str, Any] = {}
    if twin_id:
        context["twin_id"] = twin_id
    if asset_id:
        context["asset_id"] = asset_id
    context.update(extra)

    return ContextLogger(logging.getLogger(name), context)
