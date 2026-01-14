"""Mock model block for testing."""

from __future__ import annotations

from typing import Any

from pyedgetwin.models.base import ModelBlock, ModelBlockContext


class MockModel(ModelBlock):
    """Simple mock model for testing purposes."""

    def __init__(self) -> None:
        self._context: ModelBlockContext | None = None
        self._alpha: float = 1.0
        self._process_count: int = 0

    def init(self, context: ModelBlockContext) -> None:
        """Initialize with context."""
        self._context = context
        self._alpha = context.config.get("alpha", 1.0)

    def process(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Process a message by applying a simple scaling."""
        self._process_count += 1
        value = msg.get("value", 0.0)
        estimate = value * self._alpha

        return {
            "raw_value": value,
            "twin_estimate": estimate,
            "anomaly_flag": False,
            "residual": value - estimate,
        }

    def shutdown(self) -> None:
        """Cleanup."""
        pass

    @property
    def process_count(self) -> int:
        """Return the number of messages processed."""
        return self._process_count


class FailingModel(ModelBlock):
    """Model that raises an exception for testing error handling."""

    def init(self, context: ModelBlockContext) -> None:
        pass

    def process(self, msg: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("Intentional test failure")

    def shutdown(self) -> None:
        pass


class AnomalyModel(ModelBlock):
    """Model that always flags anomalies for testing."""

    def init(self, context: ModelBlockContext) -> None:
        pass

    def process(self, msg: dict[str, Any]) -> dict[str, Any]:
        value = msg.get("value", 0.0)
        return {
            "raw_value": value,
            "twin_estimate": value,
            "anomaly_flag": True,
            "residual": 0.0,
        }

    def shutdown(self) -> None:
        pass
