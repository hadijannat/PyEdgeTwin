"""Base connector interface for PyEdgeTwin."""

from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseConnector(ABC):
    """
    Abstract base class for all I/O connectors.

    Connectors are responsible for ingesting data from external sources
    (e.g., MQTT brokers, HTTP endpoints) and optionally publishing
    processed results.
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the data source.

        Raises:
            ConnectionError: If connection cannot be established
        """
        ...

    @abstractmethod
    def subscribe(
        self,
        topic: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """
        Subscribe to a topic/channel with a message callback.

        Args:
            topic: The topic or channel to subscribe to
            callback: Function to call when a message is received.
                     Receives the parsed message payload as a dict.
        """
        ...

    @abstractmethod
    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """
        Publish a message to a topic/channel.

        Args:
            topic: The topic or channel to publish to
            payload: The message payload as a dictionary
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """
        Gracefully close the connection.

        Should ensure all pending messages are handled before disconnecting.
        """
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the connector is currently connected.

        Returns:
            True if connected, False otherwise
        """
        ...

    def health_check(self) -> dict[str, Any]:
        """
        Perform a health check and return status information.

        Returns:
            Dictionary with health status information
        """
        return {
            "connected": self.is_connected(),
            "type": self.__class__.__name__,
        }
