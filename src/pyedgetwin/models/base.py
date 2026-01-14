"""Base model block interface for PyEdgeTwin."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelBlockContext:
    """
    Context provided to model blocks during initialization.

    Contains all the information a model block needs to initialize itself,
    including twin identity, configuration parameters, and runtime settings.
    """

    asset_id: str
    """Identifier of the physical asset being modeled."""

    twin_id: str
    """Identifier of this digital twin instance."""

    model_version: str
    """Version string of the model block."""

    config: dict[str, Any] = field(default_factory=dict)
    """Model-specific configuration parameters from the config file."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with a default."""
        return self.config.get(key, default)


class ModelBlock(ABC):
    """
    Abstract base class for all model blocks.

    A model block encapsulates the hybrid model logic that transforms
    incoming sensor data into twin estimates. It can implement any
    combination of physics-based models and data-driven techniques.

    Lifecycle:
        1. `init()` is called once when the runtime starts
        2. `process()` is called for each incoming message
        3. `shutdown()` is called when the runtime stops

    Example:
        class KalmanFilter(ModelBlock):
            def init(self, context: ModelBlockContext) -> None:
                self.Q = context.get("process_noise", 0.01)
                self.R = context.get("measurement_noise", 0.1)
                self.x = 0.0
                self.P = 1.0

            def process(self, msg: dict) -> dict:
                z = msg.get("value", 0.0)
                # ... Kalman filter logic ...
                return {
                    "raw_value": z,
                    "twin_estimate": self.x,
                    "anomaly_flag": False,
                }

            def shutdown(self) -> None:
                pass
    """

    @abstractmethod
    def init(self, context: ModelBlockContext) -> None:
        """
        Initialize the model block with the provided context.

        This is called once when the twin runtime starts. Use this method
        to initialize internal state, load model weights, or set up any
        resources needed for processing.

        Args:
            context: Contains asset/twin IDs and configuration parameters

        Raises:
            ModelBlockError: If initialization fails
        """
        ...

    @abstractmethod
    def process(self, msg: dict[str, Any]) -> dict[str, Any]:
        """
        Process an incoming message and return the result.

        This is called for each message received from the connector.
        The method should be thread-safe if workers > 1.

        Args:
            msg: The incoming message as a dictionary. Typically contains
                 at least 'value' and 'timestamp' fields.

        Returns:
            A dictionary with at least these required keys:
            - raw_value (float): The original input value
            - twin_estimate (float): The model's estimate/prediction
            - anomaly_flag (bool): Whether an anomaly was detected

            Optional keys:
            - residual (float): Difference between raw and estimate
            - confidence (float): Confidence score (0-1)
            - state_vector (list[float]): Internal state for debugging

        Raises:
            ModelBlockError: If processing fails
        """
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """
        Clean up any resources used by the model block.

        This is called when the twin runtime is shutting down. Use this
        method to release resources, save state, or perform any cleanup.

        This method should not raise exceptions; log errors instead.
        """
        ...

    def validate_output(self, output: dict[str, Any]) -> bool:
        """
        Validate that the output contains required keys.

        Args:
            output: The output dictionary from process()

        Returns:
            True if valid, False otherwise
        """
        required_keys = {"raw_value", "twin_estimate", "anomaly_flag"}
        return required_keys.issubset(output.keys())

    def get_state(self) -> dict[str, Any]:
        """
        Get the current internal state for debugging/inspection.

        Override this method to expose internal state for monitoring.

        Returns:
            Dictionary containing internal state information
        """
        return {}
