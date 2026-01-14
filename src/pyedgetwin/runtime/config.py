"""Configuration schemas for PyEdgeTwin using Pydantic."""

from __future__ import annotations

import os
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class MQTTConfig(BaseModel):
    """MQTT broker connection configuration."""

    host: str = "localhost"
    port: int = Field(default=1883, ge=1, le=65535)
    username: str | None = None
    password: str | None = None
    client_id: str | None = None
    qos: int = Field(default=1, ge=0, le=2)
    topics: list[str] = Field(default_factory=list)
    reconnect_delay_min: float = Field(default=1.0, gt=0)
    reconnect_delay_max: float = Field(default=60.0, gt=0)
    keepalive: int = Field(default=60, ge=1)

    @field_validator("topics", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> list[str]:
        """Ensure topics is always a list."""
        if isinstance(v, str):
            return [v]
        return list(v) if v else []


class InfluxDBConfig(BaseModel):
    """InfluxDB 2.x sink configuration."""

    url: str = "http://localhost:8086"
    token: str
    org: str
    bucket: str
    batch_size: int = Field(default=500, ge=1, le=10000)
    flush_interval_ms: int = Field(default=10000, ge=100, le=60000)
    measurement: str = "twin_output"

    @field_validator("token", "org", "bucket", mode="before")
    @classmethod
    def resolve_env_vars(cls, v: Any) -> str:
        """Resolve environment variable references like ${VAR_NAME}."""
        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
            env_var = v[2:-1]
            return os.environ.get(env_var, v)
        return str(v) if v else ""


class CSVConfig(BaseModel):
    """CSV sink configuration."""

    path: str
    append: bool = True
    columns: list[str] | None = None


class ModelConfig(BaseModel):
    """Model block configuration."""

    module_path: str  # e.g., "mypackage.models:KalmanFilter"
    version: str = "1.0.0"
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("module_path")
    @classmethod
    def validate_module_path(cls, v: str) -> str:
        """Validate module path format."""
        if ":" not in v:
            raise ValueError("module_path must be in format 'package.module:ClassName'")
        return v


class RuntimeConfig(BaseModel):
    """Runtime engine configuration."""

    twin_id: str
    asset_id: str
    workers: int = Field(default=1, ge=1, le=32)
    queue_size: int = Field(default=1000, ge=1, le=100000)
    queue_overflow_policy: str = Field(default="drop_oldest")

    @field_validator("queue_overflow_policy")
    @classmethod
    def validate_policy(cls, v: str) -> str:
        """Validate queue overflow policy."""
        valid_policies = {"drop_oldest", "drop_newest", "block"}
        if v not in valid_policies:
            raise ValueError(f"queue_overflow_policy must be one of {valid_policies}")
        return v


class HealthConfig(BaseModel):
    """Health endpoint configuration."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)


class TwinConfig(BaseModel):
    """Root configuration schema for PyEdgeTwin."""

    runtime: RuntimeConfig
    mqtt: MQTTConfig = Field(default_factory=MQTTConfig)
    model: ModelConfig
    sinks: dict[str, dict[str, Any]] = Field(default_factory=dict)
    health: HealthConfig = Field(default_factory=HealthConfig)

    @model_validator(mode="after")
    def validate_config(self) -> TwinConfig:
        """Perform cross-field validation."""
        # Ensure at least one topic is configured
        if not self.mqtt.topics:
            raise ValueError("At least one MQTT topic must be configured")
        return self


def load_config(config_path: str) -> TwinConfig:
    """
    Load and validate configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Validated TwinConfig instance

    Raises:
        ConfigurationError: If the configuration is invalid
    """
    import yaml

    from pyedgetwin.runtime.errors import ConfigurationError

    try:
        with open(config_path) as f:
            raw_config = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigurationError(f"Configuration file not found: {config_path}") from e
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}") from e

    # Recursively expand environment variables in all string values
    raw_config = _expand_env_vars_recursive(raw_config)

    # Apply environment variable overrides
    raw_config = _apply_env_overrides(raw_config)

    try:
        return TwinConfig(**raw_config)
    except Exception as e:
        raise ConfigurationError(f"Configuration validation failed: {e}") from e


def _expand_env_vars_recursive(obj: Any) -> Any:
    """
    Recursively expand environment variable references in all string values.

    Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.
    """
    if isinstance(obj, str):
        return resolve_env_vars_in_string(obj)
    elif isinstance(obj, dict):
        return {k: _expand_env_vars_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_env_vars_recursive(item) for item in obj]
    return obj


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """
    Apply environment variable overrides to configuration.

    Supports nested key paths via PYEDGETWIN_* environment variables.
    """
    env_map = {
        "PYEDGETWIN_MQTT_HOST": ("mqtt", "host"),
        "PYEDGETWIN_MQTT_PORT": ("mqtt", "port"),
        "PYEDGETWIN_MQTT_USERNAME": ("mqtt", "username"),
        "PYEDGETWIN_MQTT_PASSWORD": ("mqtt", "password"),
        "PYEDGETWIN_TWIN_ID": ("runtime", "twin_id"),
        "PYEDGETWIN_ASSET_ID": ("runtime", "asset_id"),
    }

    for env_var, path in env_map.items():
        value = os.environ.get(env_var)
        if value:
            _set_nested(config, path, value)

    return config


def _set_nested(d: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    """Set a nested dictionary value."""
    import contextlib

    for key in path[:-1]:
        d = d.setdefault(key, {})
    # Try to convert to int for port-like values
    if path[-1] == "port":
        with contextlib.suppress(ValueError, TypeError):
            value = int(value)
    d[path[-1]] = value


def resolve_env_vars_in_string(value: str) -> str:
    """
    Resolve environment variable references in a string.

    Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.
    """
    pattern = r"\$\{([^}]+)\}"

    def replace(match: re.Match[str]) -> str:
        var_expr = match.group(1)
        if ":-" in var_expr:
            var_name, default = var_expr.split(":-", 1)
            return os.environ.get(var_name, default)
        return os.environ.get(var_expr, match.group(0))

    return re.sub(pattern, replace, value)
