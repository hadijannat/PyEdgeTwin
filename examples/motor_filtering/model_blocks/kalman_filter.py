"""Kalman Filter model block for motor temperature filtering.

This implements a simple 1D Kalman filter for filtering noisy temperature
sensor readings and detecting anomalies based on the innovation (prediction error).

The Kalman filter is a classic example of a hybrid model:
- Physics: State transition model (temperature changes slowly)
- Data: Noise estimation from sensor characteristics

References:
- Welch & Bishop, "An Introduction to the Kalman Filter"
- https://www.kalmanfilter.net/
"""

from __future__ import annotations

import logging
import math
from typing import Any

from pyedgetwin.models.base import ModelBlock, ModelBlockContext

logger = logging.getLogger(__name__)


class KalmanFilterModel(ModelBlock):
    """
    1D Kalman filter for sensor noise reduction and anomaly detection.

    State model: x[k] = x[k-1] + w[k]  (random walk)
    Measurement model: z[k] = x[k] + v[k]

    Where:
    - x: True temperature state
    - z: Noisy measurement
    - w ~ N(0, Q): Process noise
    - v ~ N(0, R): Measurement noise

    Anomaly detection is based on the normalized innovation:
    - innovation = z - x_predicted
    - normalized = |innovation| / sqrt(P_predicted + R)
    - anomaly if normalized > threshold
    """

    def __init__(self) -> None:
        """Initialize (actual setup happens in init())."""
        self._Q: float = 0.01  # Process noise variance
        self._R: float = 0.1   # Measurement noise variance
        self._x: float = 0.0   # State estimate
        self._P: float = 1.0   # Error covariance
        self._anomaly_threshold: float = 3.0
        self._context: ModelBlockContext | None = None
        self._message_count: int = 0

    def init(self, context: ModelBlockContext) -> None:
        """
        Initialize the Kalman filter with configuration parameters.

        Args:
            context: Runtime context with configuration
        """
        self._context = context
        params = context.config

        # Load filter parameters
        self._Q = params.get("process_noise", 0.01)
        self._R = params.get("measurement_noise", 0.1)
        self._x = params.get("initial_estimate", 0.0)
        self._P = 1.0  # Initial uncertainty

        # Anomaly detection
        self._anomaly_threshold = params.get("anomaly_threshold", 3.0)

        logger.info(
            f"KalmanFilterModel initialized: Q={self._Q}, R={self._R}, "
            f"x0={self._x}, threshold={self._anomaly_threshold}"
        )

    def process(self, msg: dict[str, Any]) -> dict[str, Any]:
        """
        Process a measurement through the Kalman filter.

        Args:
            msg: Incoming message with 'value' field

        Returns:
            Dict with raw_value, twin_estimate, anomaly_flag, and filter state
        """
        # Extract measurement
        z = float(msg.get("value", 0.0))
        self._message_count += 1

        # === Prediction Step ===
        # State prediction (random walk model)
        x_pred = self._x

        # Covariance prediction
        P_pred = self._P + self._Q

        # === Update Step ===
        # Innovation (measurement residual)
        innovation = z - x_pred

        # Innovation covariance
        S = P_pred + self._R

        # Kalman gain
        K = P_pred / S

        # State update
        self._x = x_pred + K * innovation

        # Covariance update
        self._P = (1 - K) * P_pred

        # === Anomaly Detection ===
        # Normalized innovation (Mahalanobis-like distance)
        normalized_innovation = abs(innovation) / math.sqrt(S)
        anomaly = normalized_innovation > self._anomaly_threshold

        if anomaly:
            logger.warning(
                f"Anomaly detected: z={z:.2f}, x={self._x:.2f}, "
                f"innovation={innovation:.2f}, normalized={normalized_innovation:.2f}"
            )

        return {
            "raw_value": z,
            "twin_estimate": self._x,
            "anomaly_flag": anomaly,
            "residual": innovation,
            "kalman_gain": K,
            "error_covariance": self._P,
            "normalized_innovation": normalized_innovation,
        }

    def shutdown(self) -> None:
        """Clean up (nothing to do for this model)."""
        logger.info(
            f"KalmanFilterModel shutdown: processed {self._message_count} messages"
        )

    def get_state(self) -> dict[str, Any]:
        """Get current filter state for debugging."""
        return {
            "x": self._x,
            "P": self._P,
            "Q": self._Q,
            "R": self._R,
            "message_count": self._message_count,
        }
