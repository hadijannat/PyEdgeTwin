"""Message schemas for PyEdgeTwin using Pydantic."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class IngressMessage(BaseModel):
    """
    Schema for incoming sensor/telemetry data.

    This is the expected format for messages received from data sources.
    Additional fields are allowed and preserved in metadata.
    """

    asset_id: str = Field(description="Identifier of the physical asset")
    timestamp: datetime = Field(description="Measurement timestamp")
    value: float = Field(description="Primary measurement value")
    unit: str | None = Field(default=None, description="Unit of measurement")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata fields"
    )

    model_config = {"extra": "allow"}

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Handle ISO format with Z suffix
            if v.endswith("Z"):
                v = v[:-1] + "+00:00"
            return datetime.fromisoformat(v)
        if isinstance(v, (int, float)):
            # Assume Unix timestamp
            return datetime.fromtimestamp(v)
        raise ValueError(f"Cannot parse timestamp from {type(v)}: {v}")


class EgressMessage(BaseModel):
    """
    Schema for model block output / processed data.

    This is the format that model blocks must produce and sinks expect.
    """

    # Identity fields
    asset_id: str = Field(description="Identifier of the physical asset")
    twin_id: str = Field(description="Identifier of this digital twin instance")
    model_version: str = Field(description="Version of the model block")

    # Timestamp
    timestamp: datetime = Field(description="Original measurement timestamp")
    processed_at: datetime = Field(description="Processing timestamp")

    # Required model outputs
    raw_value: float = Field(description="Original input value")
    twin_estimate: float = Field(description="Model estimate/prediction")
    anomaly_flag: bool = Field(description="Whether an anomaly was detected")

    # Optional model outputs
    residual: float | None = Field(
        default=None, description="Difference between raw and estimate"
    )
    confidence: float | None = Field(
        default=None, description="Confidence score (0-1)"
    )
    state_vector: list[float] | None = Field(
        default=None, description="Internal state vector"
    )

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional output fields"
    )

    model_config = {"extra": "allow"}


def parse_ingress_message(
    raw: dict[str, Any],
    strict: bool = False,
) -> IngressMessage:
    """
    Parse a raw message dictionary into an IngressMessage.

    Args:
        raw: Raw message dictionary
        strict: If True, raise on validation errors. If False, use defaults.

    Returns:
        Parsed IngressMessage

    Raises:
        ValidationError: If strict=True and validation fails
    """
    from pyedgetwin.runtime.errors import ValidationError

    try:
        return IngressMessage(**raw)
    except Exception as e:
        if strict:
            raise ValidationError(f"Message validation failed: {e}")
        # Create a minimal valid message with defaults
        return IngressMessage(
            asset_id=raw.get("asset_id", "unknown"),
            timestamp=datetime.now(),
            value=float(raw.get("value", 0.0)),
            metadata=raw,
        )


def create_egress_message(
    ingress: IngressMessage,
    model_output: dict[str, Any],
    twin_id: str,
    model_version: str,
) -> EgressMessage:
    """
    Create an EgressMessage from an IngressMessage and model output.

    Args:
        ingress: The original ingress message
        model_output: Output from the model block's process() method
        twin_id: ID of the twin instance
        model_version: Version of the model block

    Returns:
        Complete EgressMessage ready for sinks
    """
    from pyedgetwin.utils.time import utc_now

    return EgressMessage(
        asset_id=ingress.asset_id,
        twin_id=twin_id,
        model_version=model_version,
        timestamp=ingress.timestamp,
        processed_at=utc_now(),
        raw_value=model_output.get("raw_value", ingress.value),
        twin_estimate=model_output.get("twin_estimate", ingress.value),
        anomaly_flag=model_output.get("anomaly_flag", False),
        residual=model_output.get("residual"),
        confidence=model_output.get("confidence"),
        state_vector=model_output.get("state_vector"),
        metadata={
            k: v
            for k, v in model_output.items()
            if k
            not in {
                "raw_value",
                "twin_estimate",
                "anomaly_flag",
                "residual",
                "confidence",
                "state_vector",
            }
        },
    )
