"""Unit tests for configuration module."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest
import yaml

from pyedgetwin.runtime.config import (
    MQTTConfig,
    ModelConfig,
    RuntimeConfig,
    TwinConfig,
    load_config,
)
from pyedgetwin.runtime.errors import ConfigurationError


class TestMQTTConfig:
    """Tests for MQTTConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = MQTTConfig()
        assert config.host == "localhost"
        assert config.port == 1883
        assert config.qos == 1
        assert config.topics == []

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = MQTTConfig(
            host="broker.example.com",
            port=8883,
            qos=2,
            topics=["test/topic"],
        )
        assert config.host == "broker.example.com"
        assert config.port == 8883
        assert config.qos == 2
        assert config.topics == ["test/topic"]

    def test_topics_string_to_list(self) -> None:
        """Test that a single topic string is converted to a list."""
        config = MQTTConfig(topics="single/topic")
        assert config.topics == ["single/topic"]

    def test_invalid_qos(self) -> None:
        """Test that invalid QoS raises an error."""
        with pytest.raises(ValueError):
            MQTTConfig(qos=3)


class TestModelConfig:
    """Tests for ModelConfig."""

    def test_valid_module_path(self) -> None:
        """Test valid module path."""
        config = ModelConfig(module_path="package.module:ClassName")
        assert config.module_path == "package.module:ClassName"

    def test_invalid_module_path(self) -> None:
        """Test that invalid module path raises an error."""
        with pytest.raises(ValueError, match="must be in format"):
            ModelConfig(module_path="invalid_path_without_colon")


class TestRuntimeConfig:
    """Tests for RuntimeConfig."""

    def test_valid_config(self) -> None:
        """Test valid runtime configuration."""
        config = RuntimeConfig(
            twin_id="test-twin",
            asset_id="test-asset",
        )
        assert config.twin_id == "test-twin"
        assert config.workers == 1
        assert config.queue_overflow_policy == "drop_oldest"

    def test_invalid_overflow_policy(self) -> None:
        """Test that invalid overflow policy raises an error."""
        with pytest.raises(ValueError, match="must be one of"):
            RuntimeConfig(
                twin_id="test",
                asset_id="test",
                queue_overflow_policy="invalid",
            )


class TestTwinConfig:
    """Tests for TwinConfig."""

    def test_valid_config(self, sample_config_dict: dict[str, Any]) -> None:
        """Test valid complete configuration."""
        config = TwinConfig(**sample_config_dict)
        assert config.runtime.twin_id == "test-twin"
        assert config.mqtt.host == "localhost"
        assert config.model.module_path == "tests.fixtures.mock_model:MockModel"

    def test_missing_topics(self, sample_config_dict: dict[str, Any]) -> None:
        """Test that missing topics raises an error."""
        sample_config_dict["mqtt"]["topics"] = []
        with pytest.raises(ValueError, match="(?i)at least one MQTT topic"):
            TwinConfig(**sample_config_dict)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, sample_config_dict: dict[str, Any]) -> None:
        """Test loading a valid configuration file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(sample_config_dict, f)
            f.flush()

            try:
                config = load_config(f.name)
                assert config.runtime.twin_id == "test-twin"
            finally:
                os.unlink(f.name)

    def test_file_not_found(self) -> None:
        """Test that missing file raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="not found"):
            load_config("/nonexistent/path/config.yaml")

    def test_invalid_yaml(self) -> None:
        """Test that invalid YAML raises ConfigurationError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            try:
                with pytest.raises(ConfigurationError, match="Invalid YAML"):
                    load_config(f.name)
            finally:
                os.unlink(f.name)
