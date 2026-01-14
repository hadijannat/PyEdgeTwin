"""Exception hierarchy for PyEdgeTwin."""

from typing import Any


class PyEdgeTwinError(Exception):
    """Base exception for all PyEdgeTwin errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(PyEdgeTwinError):
    """Raised when configuration is invalid or missing."""

    pass


class ConnectionError(PyEdgeTwinError):
    """Raised when connection to an external service fails."""

    pass


class ModelBlockError(PyEdgeTwinError):
    """Raised when model block initialization or execution fails."""

    pass


class SinkError(PyEdgeTwinError):
    """Raised when sink operation fails."""

    pass


class QueueOverflowError(PyEdgeTwinError):
    """Raised when message queue exceeds capacity and cannot accept more messages."""

    pass


class ValidationError(PyEdgeTwinError):
    """Raised when message or data validation fails."""

    pass


class ShutdownError(PyEdgeTwinError):
    """Raised when shutdown procedure encounters an error."""

    pass
