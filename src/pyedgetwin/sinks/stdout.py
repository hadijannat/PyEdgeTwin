"""Stdout sink for PyEdgeTwin - prints records as JSON."""

from __future__ import annotations

import json
import sys
from typing import Any

from pyedgetwin.sinks.base import BaseSink


class StdoutSink(BaseSink):
    """
    Simple sink that prints records to stdout as JSON.

    Useful for debugging, development, and piping output to other tools.
    """

    def __init__(
        self,
        pretty: bool = False,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
    ) -> None:
        """
        Initialize the stdout sink.

        Args:
            pretty: If True, format JSON with indentation
            include_fields: If specified, only include these fields
            exclude_fields: Fields to exclude from output
        """
        self._pretty = pretty
        self._include_fields = set(include_fields) if include_fields else None
        self._exclude_fields = set(exclude_fields) if exclude_fields else set()
        self._record_count = 0

    def open(self) -> None:
        """No initialization needed for stdout."""
        pass

    def write(self, record: dict[str, Any]) -> None:
        """
        Write a record to stdout as JSON.

        Args:
            record: The record to write
        """
        # Filter fields if configured
        output = self._filter_fields(record)

        # Format and print
        if self._pretty:
            json_str = json.dumps(output, indent=2, default=str)
        else:
            json_str = json.dumps(output, default=str)

        print(json_str)
        sys.stdout.flush()
        self._record_count += 1

    def _filter_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Filter fields based on include/exclude configuration."""
        if self._include_fields:
            return {k: v for k, v in record.items() if k in self._include_fields}

        if self._exclude_fields:
            return {k: v for k, v in record.items() if k not in self._exclude_fields}

        return record

    def flush(self) -> None:
        """Flush stdout."""
        sys.stdout.flush()

    def close(self) -> None:
        """No cleanup needed for stdout."""
        pass

    def health_check(self) -> dict[str, Any]:
        """Return health status information."""
        return {
            "type": "StdoutSink",
            "status": "ok",
            "records_written": self._record_count,
        }
