"""Pytest configuration and shared fixtures for PyEdgeTwin tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_config_dict() -> dict[str, Any]:
    """Return a sample configuration dictionary."""
    return {
        "runtime": {
            "twin_id": "test-twin",
            "asset_id": "test-asset",
            "workers": 1,
            "queue_size": 100,
            "queue_overflow_policy": "drop_oldest",
        },
        "mqtt": {
            "host": "localhost",
            "port": 1883,
            "qos": 1,
            "topics": ["test/topic"],
        },
        "model": {
            "module_path": "tests.fixtures.mock_model:MockModel",
            "version": "1.0.0",
            "params": {"alpha": 0.5},
        },
        "sinks": {},
        "health": {
            "enabled": False,
            "port": 8080,
        },
    }


@pytest.fixture
def sample_ingress_message() -> dict[str, Any]:
    """Return a sample ingress message."""
    return {
        "asset_id": "motor-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "value": 42.5,
        "unit": "celsius",
    }


@pytest.fixture
def sample_egress_record() -> dict[str, Any]:
    """Return a sample egress record."""
    return {
        "asset_id": "motor-001",
        "twin_id": "test-twin",
        "model_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "raw_value": 42.5,
        "twin_estimate": 42.0,
        "anomaly_flag": False,
        "residual": 0.5,
    }


@pytest.fixture
def mock_mqtt_client() -> MagicMock:
    """Return a mock MQTT client."""
    client = MagicMock()
    client.is_connected.return_value = True
    client.subscribe.return_value = (0, 1)
    client.publish.return_value = MagicMock(mid=1)
    return client


@pytest.fixture
def mock_influx_client() -> MagicMock:
    """Return a mock InfluxDB client."""
    client = MagicMock()
    health = MagicMock()
    health.status = "pass"
    client.health.return_value = health
    client.write_api.return_value = MagicMock()
    return client
