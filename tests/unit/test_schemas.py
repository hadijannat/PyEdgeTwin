"""Unit tests for message schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from pyedgetwin.io.schemas import (
    IngressMessage,
    EgressMessage,
    parse_ingress_message,
    create_egress_message,
)


class TestIngressMessage:
    """Tests for IngressMessage schema."""

    def test_valid_message(self) -> None:
        """Test creating a valid ingress message."""
        msg = IngressMessage(
            asset_id="motor-001",
            timestamp=datetime.now(timezone.utc),
            value=42.5,
            unit="celsius",
        )
        assert msg.asset_id == "motor-001"
        assert msg.value == 42.5
        assert msg.unit == "celsius"

    def test_timestamp_from_iso_string(self) -> None:
        """Test parsing timestamp from ISO string."""
        msg = IngressMessage(
            asset_id="test",
            timestamp="2024-01-15T12:30:00Z",
            value=1.0,
        )
        assert msg.timestamp.year == 2024
        assert msg.timestamp.month == 1
        assert msg.timestamp.day == 15

    def test_timestamp_from_unix(self) -> None:
        """Test parsing timestamp from Unix timestamp."""
        unix_ts = 1705322400.0  # 2024-01-15 12:00:00 UTC
        msg = IngressMessage(
            asset_id="test",
            timestamp=unix_ts,
            value=1.0,
        )
        assert msg.timestamp.year == 2024

    def test_extra_fields_allowed(self) -> None:
        """Test that extra fields are preserved."""
        msg = IngressMessage(
            asset_id="test",
            timestamp=datetime.now(timezone.utc),
            value=1.0,
            custom_field="extra",
        )
        assert hasattr(msg, "custom_field")


class TestEgressMessage:
    """Tests for EgressMessage schema."""

    def test_valid_message(self) -> None:
        """Test creating a valid egress message."""
        now = datetime.now(timezone.utc)
        msg = EgressMessage(
            asset_id="motor-001",
            twin_id="twin-001",
            model_version="1.0.0",
            timestamp=now,
            processed_at=now,
            raw_value=42.5,
            twin_estimate=42.0,
            anomaly_flag=False,
        )
        assert msg.asset_id == "motor-001"
        assert msg.twin_id == "twin-001"
        assert msg.raw_value == 42.5
        assert msg.twin_estimate == 42.0
        assert msg.anomaly_flag is False

    def test_optional_fields(self) -> None:
        """Test optional fields."""
        now = datetime.now(timezone.utc)
        msg = EgressMessage(
            asset_id="test",
            twin_id="twin",
            model_version="1.0",
            timestamp=now,
            processed_at=now,
            raw_value=1.0,
            twin_estimate=1.0,
            anomaly_flag=False,
            residual=0.0,
            confidence=0.95,
        )
        assert msg.residual == 0.0
        assert msg.confidence == 0.95


class TestParseIngressMessage:
    """Tests for parse_ingress_message function."""

    def test_parse_valid_message(self, sample_ingress_message: dict[str, Any]) -> None:
        """Test parsing a valid message."""
        msg = parse_ingress_message(sample_ingress_message, strict=True)
        assert msg.asset_id == "motor-001"
        assert msg.value == 42.5

    def test_parse_minimal_message(self) -> None:
        """Test parsing with minimal fields in non-strict mode."""
        raw = {"value": 123.0}
        msg = parse_ingress_message(raw, strict=False)
        assert msg.value == 123.0
        assert msg.asset_id == "unknown"

    def test_strict_mode_raises_on_invalid(self) -> None:
        """Test that strict mode raises on invalid messages."""
        raw = {"invalid": "data"}
        with pytest.raises(Exception):
            parse_ingress_message(raw, strict=True)


class TestCreateEgressMessage:
    """Tests for create_egress_message function."""

    def test_create_egress(self) -> None:
        """Test creating an egress message from ingress + model output."""
        ingress = IngressMessage(
            asset_id="motor-001",
            timestamp=datetime.now(timezone.utc),
            value=42.5,
        )

        model_output = {
            "raw_value": 42.5,
            "twin_estimate": 42.0,
            "anomaly_flag": False,
            "residual": 0.5,
        }

        egress = create_egress_message(
            ingress=ingress,
            model_output=model_output,
            twin_id="twin-001",
            model_version="1.0.0",
        )

        assert egress.asset_id == "motor-001"
        assert egress.twin_id == "twin-001"
        assert egress.raw_value == 42.5
        assert egress.twin_estimate == 42.0
        assert egress.residual == 0.5
