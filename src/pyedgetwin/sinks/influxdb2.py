"""InfluxDB 2.x sink for PyEdgeTwin with batch writes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from influxdb_client import InfluxDBClient, WriteOptions  # type: ignore[attr-defined]
from influxdb_client.client.write_api import WriteApi

from pyedgetwin.runtime.errors import SinkError
from pyedgetwin.sinks.base import BaseSink

logger = logging.getLogger(__name__)


class InfluxDB2Sink(BaseSink):
    """
    InfluxDB 2.x sink with batch writes.

    Uses WriteApi with configurable batch_size and flush_interval for
    optimal write performance. Proper flush/close handling ensures
    no data is lost during shutdown.

    See: https://influxdb-client.readthedocs.io/en/stable/usage.html
    """

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str,
        batch_size: int = 500,
        flush_interval_ms: int = 10000,
        measurement: str = "twin_output",
    ) -> None:
        """
        Initialize the InfluxDB2 sink.

        Args:
            url: InfluxDB server URL (e.g., http://localhost:8086)
            token: Authentication token
            org: Organization name
            bucket: Target bucket name
            batch_size: Number of points to batch before writing
            flush_interval_ms: Maximum time between flushes in milliseconds
            measurement: InfluxDB measurement name
        """
        self._url = url
        self._token = token
        self._org = org
        self._bucket = bucket
        self._batch_size = batch_size
        self._flush_interval_ms = flush_interval_ms
        self._measurement = measurement

        self._client: InfluxDBClient | None = None
        self._write_api: WriteApi | None = None
        self._record_count = 0
        self._error_count = 0

    def open(self) -> None:
        """
        Initialize InfluxDB client with batching configuration.

        Raises:
            SinkError: If connection or health check fails
        """
        logger.info(f"Connecting to InfluxDB at {self._url}")

        try:
            self._client = InfluxDBClient(
                url=self._url,
                token=self._token,
                org=self._org,
            )

            # Verify connection with health check
            health = self._client.health()
            if health.status != "pass":
                raise SinkError(
                    f"InfluxDB health check failed: {health.message}",
                    details={"status": health.status},
                )

            # Configure batch writing with proper options
            # See: https://docs.influxdata.com/influxdb/v2/write-data/best-practices/optimize-writes/
            write_options = WriteOptions(
                batch_size=self._batch_size,
                flush_interval=self._flush_interval_ms,
                jitter_interval=2_000,  # Random jitter to spread writes
                retry_interval=5_000,  # Initial retry delay
                max_retries=5,
                max_retry_delay=30_000,
                exponential_base=2,
            )

            self._write_api = self._client.write_api(
                write_options=write_options,
                success_callback=self._on_success,
                error_callback=self._on_error,
                retry_callback=self._on_retry,
            )

            logger.info(
                f"Connected to InfluxDB (org={self._org}, bucket={self._bucket}, "
                f"batch_size={self._batch_size}, flush_interval={self._flush_interval_ms}ms)"
            )

        except SinkError:
            raise
        except Exception as e:
            raise SinkError(
                f"Failed to connect to InfluxDB: {e}",
                details={"url": self._url, "org": self._org},
            ) from e

    def write(self, record: dict[str, Any]) -> None:
        """
        Write a record as an InfluxDB point.

        The record is converted to line protocol format with:
        - Measurement: configured measurement name
        - Tags: asset_id, twin_id, model_version
        - Fields: raw_value, twin_estimate, anomaly_flag, residual, etc.
        - Timestamp: processed_at or current time

        Args:
            record: The processed data record
        """
        if not self._write_api:
            raise SinkError("InfluxDB sink not initialized")

        try:
            point = self._record_to_point(record)
            self._write_api.write(bucket=self._bucket, record=point)
            self._record_count += 1
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error writing to InfluxDB: {e}")

    def _record_to_point(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Convert a record dictionary to an InfluxDB point dictionary.

        Returns:
            Point dictionary suitable for write_api.write()
        """
        # Extract timestamp
        timestamp = record.get("processed_at") or record.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif timestamp is None:
            timestamp = datetime.utcnow()

        # Build tags
        tags = {
            "asset_id": str(record.get("asset_id", "unknown")),
            "twin_id": str(record.get("twin_id", "unknown")),
            "model_version": str(record.get("model_version", "unknown")),
        }

        # Build fields (only include non-None values)
        fields: dict[str, Any] = {}

        if "raw_value" in record and record["raw_value"] is not None:
            fields["raw_value"] = float(record["raw_value"])

        if "twin_estimate" in record and record["twin_estimate"] is not None:
            fields["twin_estimate"] = float(record["twin_estimate"])

        if "anomaly_flag" in record:
            fields["anomaly_flag"] = bool(record["anomaly_flag"])

        if "residual" in record and record["residual"] is not None:
            fields["residual"] = float(record["residual"])

        if "confidence" in record and record["confidence"] is not None:
            fields["confidence"] = float(record["confidence"])

        # Add any additional numeric fields from metadata
        excluded_keys = {"timestamp", "processed_at", "asset_id", "twin_id", "model_version"}
        for key, value in record.items():
            if (
                key not in fields
                and key not in tags
                and key not in excluded_keys
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                fields[key] = float(value)

        return {
            "measurement": self._measurement,
            "tags": tags,
            "fields": fields,
            "time": timestamp,
        }

    def flush(self) -> None:
        """
        Flush any buffered data to InfluxDB.

        Note: The WriteApi handles flushing automatically, but this
        can be called to force an immediate flush.
        """
        # The batching WriteApi flushes automatically
        # Calling close() will flush remaining data
        pass

    def close(self) -> None:
        """
        Close the InfluxDB connection, flushing all buffered data.

        IMPORTANT: write_api.close() must be called to flush remaining
        batched data before closing the client.
        """
        logger.info("Closing InfluxDB sink...")

        if self._write_api:
            try:
                # close() flushes remaining batched data
                self._write_api.close()  # type: ignore[no-untyped-call]
                logger.debug("WriteApi closed and flushed")
            except Exception as e:
                logger.error(f"Error closing WriteApi: {e}")

        if self._client:
            try:
                self._client.close()  # type: ignore[no-untyped-call]
                logger.debug("InfluxDB client closed")
            except Exception as e:
                logger.error(f"Error closing client: {e}")

        logger.info(
            f"InfluxDB sink closed (records={self._record_count}, errors={self._error_count})"
        )

    def _on_success(self, _conf: tuple[str, str, str], _data: str) -> None:
        """Callback for successful batch writes."""
        logger.debug("Successfully wrote batch to InfluxDB")

    def _on_error(self, _conf: tuple[str, str, str], _data: str, exception: Exception) -> None:
        """Callback for failed batch writes."""
        self._error_count += 1
        logger.error(f"Failed to write batch to InfluxDB: {exception}")

    def _on_retry(self, _conf: tuple[str, str, str], _data: str, exception: Exception) -> None:
        """Callback for retried batch writes."""
        logger.warning(f"Retrying batch write to InfluxDB: {exception}")

    def health_check(self) -> dict[str, Any]:
        """Return health status information."""
        status = "ok"
        connected = False

        if self._client:
            try:
                health = self._client.health()
                connected = health.status == "pass"
                if not connected:
                    status = "unhealthy"
            except Exception:
                status = "error"

        return {
            "type": "InfluxDB2Sink",
            "status": status,
            "connected": connected,
            "url": self._url,
            "bucket": self._bucket,
            "records_written": self._record_count,
            "errors": self._error_count,
        }
