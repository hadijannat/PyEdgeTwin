"""Unit tests for sink implementations."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest

from pyedgetwin.sinks.stdout import StdoutSink
from pyedgetwin.sinks.csv_sink import CSVSink


class TestStdoutSink:
    """Tests for StdoutSink."""

    def test_write_record(self, capsys: Any, sample_egress_record: dict[str, Any]) -> None:
        """Test writing a record to stdout."""
        sink = StdoutSink()
        sink.open()
        sink.write(sample_egress_record)
        sink.close()

        captured = capsys.readouterr()
        assert "motor-001" in captured.out
        assert "42.5" in captured.out

    def test_pretty_format(self, capsys: Any) -> None:
        """Test pretty JSON formatting."""
        sink = StdoutSink(pretty=True)
        sink.open()
        sink.write({"key": "value"})
        sink.close()

        captured = capsys.readouterr()
        assert "\n" in captured.out  # Pretty format has newlines

    def test_field_filtering(self, capsys: Any) -> None:
        """Test field filtering."""
        sink = StdoutSink(include_fields=["asset_id", "value"])
        sink.open()
        sink.write({"asset_id": "test", "value": 1.0, "other": "excluded"})
        sink.close()

        captured = capsys.readouterr()
        assert "asset_id" in captured.out
        assert "other" not in captured.out

    def test_health_check(self) -> None:
        """Test health check."""
        sink = StdoutSink()
        sink.open()
        health = sink.health_check()
        assert health["type"] == "StdoutSink"
        assert health["status"] == "ok"
        sink.close()


class TestCSVSink:
    """Tests for CSVSink."""

    def test_write_records(self) -> None:
        """Test writing records to CSV."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            path = f.name

        try:
            sink = CSVSink(path=path, append=False)
            sink.open()

            sink.write({
                "timestamp": "2024-01-15T12:00:00Z",
                "asset_id": "motor-001",
                "raw_value": 42.5,
                "twin_estimate": 42.0,
            })
            sink.write({
                "timestamp": "2024-01-15T12:01:00Z",
                "asset_id": "motor-001",
                "raw_value": 43.0,
                "twin_estimate": 42.5,
            })

            sink.close()

            # Verify file contents
            with open(path) as f:
                contents = f.read()
                assert "timestamp" in contents  # Header
                assert "motor-001" in contents
                assert "42.5" in contents
                # Count lines (header + 2 data rows)
                lines = contents.strip().split("\n")
                assert len(lines) == 3

        finally:
            os.unlink(path)

    def test_append_mode(self) -> None:
        """Test append mode doesn't duplicate header."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            path = f.name

        try:
            # First write
            sink1 = CSVSink(path=path, append=True)
            sink1.open()
            sink1.write({"timestamp": "2024-01-15T12:00:00Z", "raw_value": 1.0})
            sink1.close()

            # Second write (append)
            sink2 = CSVSink(path=path, append=True)
            sink2.open()
            sink2.write({"timestamp": "2024-01-15T12:01:00Z", "raw_value": 2.0})
            sink2.close()

            # Verify only one header
            with open(path) as f:
                contents = f.read()
                # Count occurrences of "timestamp" - should be 1 (header only)
                assert contents.count("timestamp") == 1

        finally:
            os.unlink(path)

    def test_custom_columns(self) -> None:
        """Test custom column configuration."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            path = f.name

        try:
            sink = CSVSink(
                path=path,
                columns=["timestamp", "value"],
                append=False,
            )
            sink.open()
            sink.write({"timestamp": "2024-01-15", "value": 1.0, "extra": "ignored"})
            sink.close()

            with open(path) as f:
                header = f.readline().strip()
                assert header == "timestamp,value"

        finally:
            os.unlink(path)

    def test_creates_directory(self) -> None:
        """Test that sink creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "data.csv")

            sink = CSVSink(path=path)
            sink.open()
            sink.write({"value": 1.0})
            sink.close()

            assert os.path.exists(path)
