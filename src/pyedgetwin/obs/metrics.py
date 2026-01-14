"""Runtime metrics for PyEdgeTwin."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RuntimeMetrics:
    """
    Thread-safe runtime metrics container.

    Tracks message processing statistics for observability.
    These metrics can be exposed via the /metrics endpoint.
    """

    # Message counters
    messages_received: int = 0
    messages_processed: int = 0
    messages_dropped: int = 0

    # Error counters
    processing_errors: int = 0
    sink_write_errors: int = 0
    connection_errors: int = 0

    # Timing
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_message_time: datetime | None = None
    last_error_time: datetime | None = None

    # Internal
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def increment(self, metric: str, value: int = 1) -> None:
        """
        Thread-safe increment of a counter metric.

        Args:
            metric: Name of the metric to increment
            value: Amount to increment by (default: 1)
        """
        with self._lock:
            current = getattr(self, metric, 0)
            setattr(self, metric, current + value)

    def set(self, metric: str, value: Any) -> None:
        """
        Thread-safe set of a metric value.

        Args:
            metric: Name of the metric to set
            value: Value to set
        """
        with self._lock:
            setattr(self, metric, value)

    def record_message_received(self) -> None:
        """Record that a message was received."""
        with self._lock:
            self.messages_received += 1
            self.last_message_time = datetime.now(timezone.utc)

    def record_message_processed(self) -> None:
        """Record that a message was successfully processed."""
        with self._lock:
            self.messages_processed += 1

    def record_message_dropped(self) -> None:
        """Record that a message was dropped (queue overflow)."""
        with self._lock:
            self.messages_dropped += 1

    def record_error(self, error_type: str = "processing") -> None:
        """
        Record an error occurrence.

        Args:
            error_type: Type of error ('processing', 'sink', 'connection')
        """
        with self._lock:
            if error_type == "processing":
                self.processing_errors += 1
            elif error_type == "sink":
                self.sink_write_errors += 1
            elif error_type == "connection":
                self.connection_errors += 1
            self.last_error_time = datetime.now(timezone.utc)

    def get_uptime_seconds(self) -> float:
        """Get the runtime uptime in seconds."""
        with self._lock:
            return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def get_processing_rate(self) -> float:
        """Get the average processing rate (messages/second)."""
        uptime = self.get_uptime_seconds()
        if uptime <= 0:
            return 0.0
        with self._lock:
            return self.messages_processed / uptime

    def to_dict(self) -> dict[str, Any]:
        """
        Convert metrics to a dictionary for JSON serialization.

        Returns:
            Dictionary with all metric values
        """
        with self._lock:
            return {
                "messages_received": self.messages_received,
                "messages_processed": self.messages_processed,
                "messages_dropped": self.messages_dropped,
                "processing_errors": self.processing_errors,
                "sink_write_errors": self.sink_write_errors,
                "connection_errors": self.connection_errors,
                "uptime_seconds": self.get_uptime_seconds(),
                "processing_rate": round(self.get_processing_rate(), 2),
                "start_time": self.start_time.isoformat(),
                "last_message_time": (
                    self.last_message_time.isoformat() if self.last_message_time else None
                ),
                "last_error_time": (
                    self.last_error_time.isoformat() if self.last_error_time else None
                ),
            }

    def reset(self) -> None:
        """Reset all counters (useful for testing)."""
        with self._lock:
            self.messages_received = 0
            self.messages_processed = 0
            self.messages_dropped = 0
            self.processing_errors = 0
            self.sink_write_errors = 0
            self.connection_errors = 0
            self.start_time = datetime.now(timezone.utc)
            self.last_message_time = None
            self.last_error_time = None


# Global metrics instance
_global_metrics: RuntimeMetrics | None = None
_metrics_lock = threading.Lock()


def get_metrics() -> RuntimeMetrics:
    """
    Get the global metrics instance.

    Returns:
        The global RuntimeMetrics instance (creates one if needed)
    """
    global _global_metrics
    with _metrics_lock:
        if _global_metrics is None:
            _global_metrics = RuntimeMetrics()
        return _global_metrics


def reset_metrics() -> None:
    """Reset the global metrics instance."""
    global _global_metrics
    with _metrics_lock:
        if _global_metrics:
            _global_metrics.reset()
        else:
            _global_metrics = RuntimeMetrics()
