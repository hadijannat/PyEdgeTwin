"""Time utilities for PyEdgeTwin."""

from datetime import datetime, timezone
from typing import Union


def utc_now() -> datetime:
    """
    Return current UTC time as timezone-aware datetime.

    Returns:
        Current time in UTC with timezone info
    """
    return datetime.now(timezone.utc)


def parse_iso8601(timestamp_str: str) -> datetime:
    """
    Parse an ISO 8601 timestamp string to datetime.

    Handles various formats including:
    - 2024-01-15T12:30:00Z
    - 2024-01-15T12:30:00+00:00
    - 2024-01-15T12:30:00.123456Z

    Args:
        timestamp_str: ISO 8601 formatted timestamp string

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If the string cannot be parsed
    """
    # Replace Z with +00:00 for fromisoformat compatibility
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str[:-1] + "+00:00"

    return datetime.fromisoformat(timestamp_str)


def to_iso8601(dt: datetime) -> str:
    """
    Convert a datetime to ISO 8601 format string.

    Args:
        dt: Datetime object to convert

    Returns:
        ISO 8601 formatted string
    """
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def unix_timestamp(dt: datetime | None = None) -> float:
    """
    Get Unix timestamp (seconds since epoch).

    Args:
        dt: Datetime to convert, or None for current time

    Returns:
        Unix timestamp as float
    """
    if dt is None:
        dt = utc_now()
    return dt.timestamp()


def from_unix_timestamp(ts: Union[int, float]) -> datetime:
    """
    Convert Unix timestamp to datetime.

    Args:
        ts: Unix timestamp (seconds since epoch)

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def duration_ms(start: datetime, end: datetime | None = None) -> float:
    """
    Calculate duration in milliseconds between two datetimes.

    Args:
        start: Start time
        end: End time, or None for current time

    Returns:
        Duration in milliseconds
    """
    if end is None:
        end = utc_now()
    delta = end - start
    return delta.total_seconds() * 1000
