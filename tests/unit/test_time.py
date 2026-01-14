"""Unit tests for time utilities."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pyedgetwin.utils.time import (
    utc_now,
    parse_iso8601,
    to_iso8601,
    unix_timestamp,
    from_unix_timestamp,
    duration_ms,
)


class TestUtcNow:
    """Tests for utc_now function."""

    def test_returns_utc(self) -> None:
        """Test that utc_now returns UTC time."""
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_is_current_time(self) -> None:
        """Test that the time is approximately current."""
        before = datetime.now(timezone.utc)
        now = utc_now()
        after = datetime.now(timezone.utc)

        assert before <= now <= after


class TestParseIso8601:
    """Tests for parse_iso8601 function."""

    def test_parse_with_z_suffix(self) -> None:
        """Test parsing timestamp with Z suffix."""
        dt = parse_iso8601("2024-01-15T12:30:00Z")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 12
        assert dt.minute == 30

    def test_parse_with_offset(self) -> None:
        """Test parsing timestamp with timezone offset."""
        dt = parse_iso8601("2024-01-15T12:30:00+00:00")
        assert dt.year == 2024
        assert dt.tzinfo is not None

    def test_parse_with_microseconds(self) -> None:
        """Test parsing timestamp with microseconds."""
        dt = parse_iso8601("2024-01-15T12:30:00.123456Z")
        assert dt.microsecond == 123456

    def test_invalid_format_raises(self) -> None:
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            parse_iso8601("not a timestamp")


class TestToIso8601:
    """Tests for to_iso8601 function."""

    def test_with_timezone(self) -> None:
        """Test conversion with timezone."""
        dt = datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        result = to_iso8601(dt)
        assert "2024-01-15" in result
        assert "12:30:00" in result

    def test_without_timezone(self) -> None:
        """Test conversion without timezone assumes UTC."""
        dt = datetime(2024, 1, 15, 12, 30, 0)
        result = to_iso8601(dt)
        assert "+00:00" in result


class TestUnixTimestamp:
    """Tests for unix_timestamp function."""

    def test_from_datetime(self) -> None:
        """Test converting datetime to Unix timestamp."""
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        ts = unix_timestamp(dt)
        assert isinstance(ts, float)
        assert ts > 0

    def test_current_time(self) -> None:
        """Test getting current Unix timestamp."""
        ts = unix_timestamp()
        assert isinstance(ts, float)
        assert ts > 1700000000  # After 2023


class TestFromUnixTimestamp:
    """Tests for from_unix_timestamp function."""

    def test_convert_to_datetime(self) -> None:
        """Test converting Unix timestamp to datetime."""
        ts = 1705320000.0  # 2024-01-15 12:00:00 UTC
        dt = from_unix_timestamp(ts)
        assert dt.year == 2024
        assert dt.tzinfo == timezone.utc


class TestDurationMs:
    """Tests for duration_ms function."""

    def test_duration_calculation(self) -> None:
        """Test duration calculation."""
        start = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 12, 0, 1, tzinfo=timezone.utc)

        duration = duration_ms(start, end)
        assert duration == 1000.0

    def test_duration_to_now(self) -> None:
        """Test duration to current time."""
        start = utc_now()
        # Should be a very small duration
        duration = duration_ms(start)
        assert 0 <= duration < 100  # Less than 100ms
