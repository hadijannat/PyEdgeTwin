"""CSV file sink for PyEdgeTwin."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Any

from pyedgetwin.sinks.base import BaseSink


class CSVSink(BaseSink):
    """
    CSV file sink for local data persistence.

    Writes records to a CSV file with configurable columns.
    Supports append mode for continuous logging.
    """

    DEFAULT_COLUMNS = [
        "timestamp",
        "processed_at",
        "asset_id",
        "twin_id",
        "model_version",
        "raw_value",
        "twin_estimate",
        "anomaly_flag",
        "residual",
    ]

    def __init__(
        self,
        path: str,
        columns: list[str] | None = None,
        append: bool = True,
        delimiter: str = ",",
        include_header: bool = True,
    ) -> None:
        """
        Initialize the CSV sink.

        Args:
            path: Path to the CSV file
            columns: List of columns to include (default: all standard columns)
            append: If True, append to existing file; otherwise overwrite
            delimiter: CSV delimiter character
            include_header: If True, write header row for new files
        """
        self._path = path
        self._columns = columns or self.DEFAULT_COLUMNS
        self._append = append
        self._delimiter = delimiter
        self._include_header = include_header

        self._file: Any = None
        self._writer: csv.DictWriter[str] | None = None
        self._record_count = 0

    def open(self) -> None:
        """
        Open the CSV file and prepare the writer.

        Creates the directory if it doesn't exist.
        Writes header for new files (if include_header is True).
        """
        # Create directory if needed
        dir_path = os.path.dirname(self._path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        # Check if file exists (for header decision)
        file_exists = os.path.exists(self._path) and os.path.getsize(self._path) > 0

        # Open file in appropriate mode
        mode = "a" if self._append else "w"
        self._file = open(self._path, mode, newline="", encoding="utf-8")  # noqa: SIM115

        self._writer = csv.DictWriter(
            self._file,
            fieldnames=self._columns,
            delimiter=self._delimiter,
            extrasaction="ignore",  # Ignore fields not in columns
        )

        # Write header if this is a new file
        if self._include_header and (not file_exists or not self._append):
            self._writer.writeheader()
            self._file.flush()

    def write(self, record: dict[str, Any]) -> None:
        """
        Write a record to the CSV file.

        Args:
            record: The record to write
        """
        if not self._writer:
            raise RuntimeError("CSV sink not initialized")

        # Prepare row with proper formatting
        row = self._prepare_row(record)
        self._writer.writerow(row)
        self._record_count += 1

        # Flush periodically for durability
        if self._record_count % 100 == 0:
            self._file.flush()

    def _prepare_row(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare a record for CSV writing.

        Handles type conversions and missing values.
        """
        row: dict[str, Any] = {}

        for col in self._columns:
            value = record.get(col)

            if value is None:
                row[col] = ""
            elif isinstance(value, datetime):
                row[col] = value.isoformat()
            elif isinstance(value, bool):
                row[col] = str(value).lower()
            elif isinstance(value, float):
                row[col] = f"{value:.6f}"
            else:
                row[col] = str(value)

        return row

    def flush(self) -> None:
        """Flush the file buffer to disk."""
        if self._file:
            self._file.flush()

    def close(self) -> None:
        """Close the CSV file."""
        if self._file:
            self._file.flush()
            self._file.close()
            self._file = None
            self._writer = None

    def health_check(self) -> dict[str, Any]:
        """Return health status information."""
        return {
            "type": "CSVSink",
            "status": "ok" if self._writer else "closed",
            "path": self._path,
            "records_written": self._record_count,
        }
