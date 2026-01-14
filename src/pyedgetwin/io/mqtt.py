"""MQTT connector for PyEdgeTwin using Paho MQTT v2."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.reasoncodes import ReasonCode

from pyedgetwin.io.base import BaseConnector
from pyedgetwin.runtime.config import MQTTConfig
from pyedgetwin.runtime.errors import ConnectionError

logger = logging.getLogger(__name__)


class MQTTConnector(BaseConnector):
    """
    MQTT connector using Paho MQTT v2 callback API.

    Features:
    - Automatic reconnection with exponential backoff
    - Thread-safe message handling
    - QoS configuration per subscription
    - Optional message publishing for processed outputs

    Note:
        This uses CallbackAPIVersion.VERSION2 as required by paho-mqtt >= 2.0.
        See: https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
    """

    def __init__(self, config: MQTTConfig) -> None:
        """
        Initialize the MQTT connector.

        Args:
            config: MQTT configuration including host, port, credentials
        """
        self._config = config
        self._client: mqtt.Client | None = None
        self._connected = threading.Event()
        self._callbacks: dict[str, Callable[[dict[str, Any]], None]] = {}
        self._reconnect_delay = config.reconnect_delay_min
        self._lock = threading.Lock()
        self._running = False

    def connect(self) -> None:
        """
        Establish connection to the MQTT broker.

        Raises:
            ConnectionError: If connection cannot be established
        """
        logger.info(f"Connecting to MQTT broker at {self._config.host}:{self._config.port}")

        # Create client with Paho v2 callback API
        self._client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=self._config.client_id,
            clean_session=True,
        )

        # Set up callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Configure authentication if provided
        if self._config.username:
            self._client.username_pw_set(
                self._config.username,
                self._config.password,
            )

        # Set keepalive
        self._running = True

        try:
            self._client.connect(
                self._config.host,
                self._config.port,
                keepalive=self._config.keepalive,
            )
            # Start the network loop in a background thread
            self._client.loop_start()

            # Wait for connection with timeout
            if not self._connected.wait(timeout=10.0):
                raise ConnectionError(
                    "Timeout waiting for MQTT connection",
                    details={"host": self._config.host, "port": self._config.port},
                )

        except Exception as e:
            self._running = False
            if isinstance(e, ConnectionError):
                raise
            raise ConnectionError(
                f"Failed to connect to MQTT broker: {e}",
                details={"host": self._config.host, "port": self._config.port},
            ) from e

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        """
        Paho v2 on_connect callback.

        Called when the client connects to the broker.
        """
        if reason_code.is_failure:
            logger.error(f"MQTT connection failed: {reason_code}")
            return

        logger.info(f"Connected to MQTT broker: {reason_code.getName()}")
        self._connected.set()
        self._reconnect_delay = self._config.reconnect_delay_min

        # Resubscribe to all topics on reconnect
        with self._lock:
            for topic in self._callbacks:
                result = client.subscribe(topic, qos=self._config.qos)
                logger.debug(f"Subscribed to {topic}: {result}")

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        """
        Paho v2 on_disconnect callback with exponential backoff.

        Called when the client disconnects from the broker.
        """
        self._connected.clear()

        if not self._running:
            logger.info("MQTT disconnected (shutdown)")
            return

        logger.warning(f"MQTT disconnected: {reason_code.getName()}")

        # Exponential backoff for reconnection is handled by Paho's reconnect_delay_set
        # but we log our intention here
        if reason_code.is_failure:
            logger.info(f"Will retry connection in {self._reconnect_delay:.1f}s")
            self._reconnect_delay = min(
                self._reconnect_delay * 2,
                self._config.reconnect_delay_max,
            )

    def _on_message(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """
        Handle incoming MQTT messages.

        Parses JSON payload and routes to registered callback.
        """
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.debug(f"Received message on {msg.topic}: {payload}")

            # Find matching callback (exact match or wildcard)
            callback = self._find_callback(msg.topic)
            if callback:
                callback(payload)
            else:
                logger.warning(f"No callback registered for topic: {msg.topic}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {msg.topic}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from {msg.topic}: {e}")

    def _find_callback(self, topic: str) -> Callable[[dict[str, Any]], None] | None:
        """Find the callback for a topic, supporting wildcards."""
        with self._lock:
            # Exact match first
            if topic in self._callbacks:
                return self._callbacks[topic]

            # Check wildcard matches
            for pattern, callback in self._callbacks.items():
                if self._matches_topic(pattern, topic):
                    return callback

            return None

    @staticmethod
    def _matches_topic(pattern: str, topic: str) -> bool:
        """Check if a topic matches an MQTT wildcard pattern."""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")

        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == "#":
                return True
            if i >= len(topic_parts):
                return False
            if pattern_part != "+" and pattern_part != topic_parts[i]:
                return False

        return len(pattern_parts) == len(topic_parts)

    def subscribe(
        self,
        topic: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """
        Subscribe to a topic with a message callback.

        Args:
            topic: MQTT topic pattern (supports + and # wildcards)
            callback: Function to call when a message is received
        """
        with self._lock:
            self._callbacks[topic] = callback

        if self._client and self._connected.is_set():
            result = self._client.subscribe(topic, qos=self._config.qos)
            logger.info(f"Subscribed to {topic}, result: {result}")

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """
        Publish a message to a topic.

        Args:
            topic: MQTT topic to publish to
            payload: Message payload as dictionary (will be JSON encoded)
        """
        if not self._client or not self._connected.is_set():
            logger.warning(f"Cannot publish to {topic}: not connected")
            return

        try:
            message = json.dumps(payload, default=str).encode("utf-8")
            info = self._client.publish(topic, message, qos=self._config.qos)
            logger.debug(f"Published to {topic}: mid={info.mid}")
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")

    def disconnect(self) -> None:
        """Gracefully disconnect from the broker."""
        self._running = False

        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error during MQTT disconnect: {e}")
            finally:
                self._connected.clear()

        logger.info("MQTT connector disconnected")

    def is_connected(self) -> bool:
        """Check if currently connected to the broker."""
        return self._connected.is_set()

    def health_check(self) -> dict[str, Any]:
        """Return health status information."""
        return {
            "type": "MQTTConnector",
            "connected": self.is_connected(),
            "host": self._config.host,
            "port": self._config.port,
            "subscriptions": list(self._callbacks.keys()),
        }
