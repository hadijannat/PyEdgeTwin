# PyEdgeTwin

[![CI](https://github.com/aeroshariati/PyEdgeTwin/actions/workflows/ci.yml/badge.svg)](https://github.com/aeroshariati/PyEdgeTwin/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**PyEdgeTwin** is a Python-first, container-native runtime framework for deploying hybrid (physics + data-driven) models on streaming industrial telemetry at the edge.

## Features

- **Hybrid Model Deployment**: Deploy physics-based models enhanced with ML corrections on edge devices
- **MQTT-Native**: First-class MQTT support with automatic reconnection and QoS handling
- **Pluggable Architecture**: Extensible sinks (InfluxDB, CSV, custom) and model blocks
- **Production-Ready**: Health endpoints, structured logging, metrics, and graceful shutdown
- **Container-Native**: Docker-first design with proper healthchecks and compose orchestration
- **Reproducible**: Deterministic runtime defaults for research reproducibility

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Virtual Asset  │────▶│   MQTT Broker   │────▶│  Twin Runtime   │
│   (Simulator)   │     │   (Mosquitto)   │     │  (PyEdgeTwin)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │   Model Block   │
                                                │ (Kalman/Hybrid) │
                                                └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        ▼                                ▼                                ▼
               ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
               │    InfluxDB     │              │       CSV       │              │     stdout      │
               │     (Sink)      │              │     (Sink)      │              │     (Sink)      │
               └─────────────────┘              └─────────────────┘              └─────────────────┘
```

## Quick Start

### Installation

```bash
pip install pyedgetwin
```

Or install from source:

```bash
git clone https://github.com/aeroshariati/PyEdgeTwin.git
cd PyEdgeTwin
pip install -e ".[dev]"
```

### Run the Demo

The fastest way to see PyEdgeTwin in action:

```bash
cd examples/motor_filtering
docker compose up -d
```

This starts:
- **Mosquitto**: MQTT broker
- **InfluxDB**: Time-series database
- **Virtual Asset**: Simulates motor temperature sensor
- **Twin Runtime**: Runs a Kalman filter on the data
- **Dashboard**: Streamlit visualization at http://localhost:8501

### Basic Usage

1. Create a configuration file (`config.yaml`):

```yaml
runtime:
  twin_id: "motor-twin-001"
  asset_id: "motor-001"
  workers: 1

mqtt:
  host: localhost
  port: 1883
  topics:
    - "sensors/motor-001/temperature"

model:
  module_path: "mymodels.kalman:KalmanFilter"
  version: "1.0.0"
  params:
    process_noise: 0.01
    measurement_noise: 0.1

sinks:
  influxdb2:
    url: "http://localhost:8086"
    token: "${INFLUXDB_TOKEN}"
    org: "myorg"
    bucket: "twins"
```

2. Create a model block:

```python
from pyedgetwin.models.base import ModelBlock, ModelBlockContext

class KalmanFilter(ModelBlock):
    def init(self, context: ModelBlockContext) -> None:
        self.Q = context.config.get("process_noise", 0.01)
        self.R = context.config.get("measurement_noise", 0.1)
        self.x = 0.0  # State estimate
        self.P = 1.0  # Error covariance

    def process(self, msg: dict) -> dict:
        z = msg.get("value", 0.0)

        # Prediction
        x_pred, P_pred = self.x, self.P + self.Q

        # Update
        K = P_pred / (P_pred + self.R)
        self.x = x_pred + K * (z - x_pred)
        self.P = (1 - K) * P_pred

        return {
            "raw_value": z,
            "twin_estimate": self.x,
            "anomaly_flag": abs(z - self.x) > 3 * (P_pred + self.R) ** 0.5,
            "residual": z - self.x,
        }

    def shutdown(self) -> None:
        pass
```

3. Run the twin:

```bash
pyedgetwin run -c config.yaml
```

## Configuration

PyEdgeTwin uses YAML configuration with environment variable substitution:

| Section | Key | Description |
|---------|-----|-------------|
| `runtime` | `twin_id` | Unique identifier for this twin instance |
| `runtime` | `asset_id` | ID of the physical asset being modeled |
| `runtime` | `workers` | Number of worker threads (default: 1) |
| `mqtt` | `host`, `port` | MQTT broker connection |
| `mqtt` | `topics` | Topics to subscribe to |
| `model` | `module_path` | Python path to model class (`package.module:ClassName`) |
| `model` | `params` | Parameters passed to model initialization |
| `sinks` | `influxdb2` | InfluxDB 2.x sink configuration |
| `sinks` | `csv` | CSV file sink configuration |

## Model Block Interface

All model blocks must implement:

```python
class ModelBlock(ABC):
    def init(self, context: ModelBlockContext) -> None:
        """Initialize with twin context and parameters."""
        ...

    def process(self, msg: dict) -> dict:
        """Process a message. Must return raw_value, twin_estimate, anomaly_flag."""
        ...

    def shutdown(self) -> None:
        """Cleanup resources."""
        ...
```

## Health Endpoints

When enabled, PyEdgeTwin exposes:

- `GET /healthz` - Liveness probe
- `GET /readyz` - Readiness probe (checks connector and sinks)
- `GET /metrics` - Runtime metrics (JSON)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/

# Run type checker
mypy src/pyedgetwin/
```

## Citation

If you use PyEdgeTwin in your research, please cite:

```bibtex
@software{pyedgetwin,
  author = {Shariati, Aero},
  title = {PyEdgeTwin: Python Runtime for Hybrid Model Deployment on Edge Devices},
  year = {2024},
  url = {https://github.com/aeroshariati/PyEdgeTwin}
}
```

## License

Apache License 2.0 - see [LICENSE.txt](LICENSE.txt) for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
