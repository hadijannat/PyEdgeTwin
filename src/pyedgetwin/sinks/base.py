"""Base sink interface for PyEdgeTwin."""

from abc import ABC, abstractmethod
from typing import Any


class BaseSink(ABC):
    """
    Abstract base class for all output sinks.

    Sinks are responsible for persisting or forwarding processed data
    from the model blocks. Examples include databases, files, and
    message queues.

    Lifecycle:
        1. `open()` is called once when the runtime starts
        2. `write()` is called for each processed message
        3. `flush()` may be called periodically or on shutdown
        4. `close()` is called when the runtime stops

    Sinks should handle batching internally if needed for performance.
    """

    @abstractmethod
    def open(self) -> None:
        """
        Initialize the sink connection/resource.

        This is called once when the twin runtime starts. Use this method
        to establish connections, open files, or initialize resources.

        Raises:
            SinkError: If initialization fails
        """
        ...

    @abstractmethod
    def write(self, record: dict[str, Any]) -> None:
        """
        Write a single record to the sink.

        This is called for each processed message. The implementation
        may buffer records internally and write them in batches.

        Args:
            record: The processed data as a dictionary. This is typically
                   an EgressMessage converted to a dict.

        Raises:
            SinkError: If write fails
        """
        ...

    @abstractmethod
    def flush(self) -> None:
        """
        Flush any buffered data to the sink.

        This is called periodically and during shutdown to ensure
        all data is persisted.

        Raises:
            SinkError: If flush fails
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """
        Gracefully close the sink.

        This is called when the twin runtime is shutting down.
        Implementations MUST flush any remaining data before closing.

        This method should not raise exceptions; log errors instead.
        """
        ...

    def health_check(self) -> dict[str, Any]:
        """
        Perform a health check and return status information.

        Returns:
            Dictionary with health status information
        """
        return {
            "type": self.__class__.__name__,
            "status": "ok",
        }

    def __enter__(self) -> "BaseSink":
        """Context manager entry."""
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit with cleanup."""
        self.flush()
        self.close()
