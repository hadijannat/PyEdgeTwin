# PyEdgeTwin: A Python Framework for Hybrid Model Deployment on Edge Devices

**SoftwareX Manuscript Outline**

> [!NOTE]
> This document follows the [SoftwareX manuscript template](https://www.sciencedirect.com/journal/softwarex/publish/guide-for-authors). The final submission must use the official LaTeX/Word template.

---

## Metadata

| Field | Value |
|-------|-------|
| **Software Name** | PyEdgeTwin |
| **Current Version** | 0.1.0 |
| **Permanent Link** | https://github.com/aeroshariati/PyEdgeTwin |
| **Legal Code License** | Apache-2.0 |
| **Code Versioning** | Git |
| **Software Language** | Python 3.10+ |
| **Compilation Requirements** | Docker, pip |
| **Support Email** | h.jannatabadi@iat.rwth-aachen.de |

---

## 1. Motivation and Significance

### 1.1 Problem Statement

Deploying hybrid models (physics-based + data-driven) on streaming industrial telemetry at the edge presents a **hybrid deployment gap**:

- **Complex Runtime Plumbing**: Connecting MQTT brokers, time-series databases, and model execution requires significant boilerplate code
- **Lack of Standardization**: No Python-first framework specifically targets this hybrid model execution pattern
- **Reproducibility Challenges**: Industrial edge deployments are difficult to replicate in academic settings

### 1.2 Existing Solutions and Gaps

| Platform | Scope | Gap for Hybrid Models |
|----------|-------|----------------------|
| Eclipse Ditto | Digital twin state management | Not a Python-native execution runtime |
| EdgeX Foundry | Device interoperability | Broader than hybrid model deployment |
| AWS IoT Greengrass | Edge ML inference | Cloud-vendor lock-in, not reproducible sandbox |
| OpenTwins | IoT + ML visualization | Broader scope, less focused on config-driven execution |

### 1.3 PyEdgeTwin's Contribution

PyEdgeTwin fills this gap as a **Python-first, container-native runtime** that:

1. Standardizes the lifecycle of hybrid models on streaming data
2. Provides a reproducible one-command sandbox for research
3. Offers clean extension points for integration with broader platforms via MQTT/HTTP

---

## 2. Software Description

### 2.1 Software Architecture

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
                        ┌────────────────────────────────┼──────────┐
                        ▼                                ▼          ▼
               ┌─────────────────┐              ┌───────────┐  ┌─────────┐
               │    InfluxDB     │              │    CSV    │  │  stdout │
               │     (Sink)      │              │   (Sink)  │  │  (Sink) │
               └─────────────────┘              └───────────┘  └─────────┘
```

### 2.2 Software Functionalities

#### Core Components

| Component | Purpose |
|-----------|---------|
| `pyedgetwin.runtime` | Orchestrates ingestion → validation → model execution → persistence |
| `pyedgetwin.io` | MQTT connector with Paho v2 callback API, automatic reconnection |
| `pyedgetwin.models` | Model Block interface with `init/process/shutdown` lifecycle |
| `pyedgetwin.sinks` | Pluggable outputs: InfluxDB2 (batched), CSV, stdout |
| `pyedgetwin.obs` | Structured logging, health endpoints (`/healthz`, `/readyz`) |

#### Key Features

1. **YAML Configuration with Environment Overrides**: Single config file controls model, sinks, and runtime behavior
2. **Plugin System**: Models and sinks loadable via module path or Python entry-points
3. **Deterministic Defaults**: Single worker, bounded queue for research reproducibility
4. **Production Reliability**: Batch writes, graceful shutdown, exponential backoff reconnection

### 2.3 Sample Code

```python
from pyedgetwin.models.base import ModelBlock, ModelBlockContext

class KalmanFilter(ModelBlock):
    def init(self, context: ModelBlockContext) -> None:
        self.Q = context.get("process_noise", 0.01)
        self.R = context.get("measurement_noise", 0.1)
        self.x, self.P = 0.0, 1.0

    def process(self, msg: dict) -> dict:
        z = msg.get("value", 0.0)
        # Kalman filter prediction + update
        K = self.P / (self.P + self.R)
        self.x = self.x + K * (z - self.x)
        self.P = (1 - K) * self.P + self.Q
        return {
            "raw_value": z,
            "twin_estimate": self.x,
            "anomaly_flag": abs(z - self.x) > 3 * (self.P + self.R) ** 0.5,
        }

    def shutdown(self) -> None:
        pass
```

---

## 3. Illustrative Examples

### 3.1 Motor Temperature Filtering

**Use Case**: Industrial motor with noisy temperature sensor

**Physics Component**: Random walk state model (temperature changes slowly)

**Data Component**: Kalman filter noise estimation from sensor characteristics

**Demonstration**:
```bash
cd examples/motor_filtering
docker compose up -d
# Dashboard: http://localhost:8501
```

### 3.2 Reproducibility

All paper figures are generated deterministically:
```bash
make reproduce
# Outputs:
#   - examples/motor_filtering/output/twin_data.csv
#   - examples/motor_filtering/output/figure_raw_vs_twin.png
```

---

## 4. Impact

### 4.1 Academic Impact

- **Reduced Time-to-Experiment**: Researchers can deploy hybrid models without infrastructure expertise
- **Reproducible Results**: Deterministic seeds, bounded queues, one-command setup
- **Extensible Architecture**: Plugin system enables comparative studies

### 4.2 Industrial Impact

- **Brownfield Compatibility**: MQTT-native, integrates with existing OT infrastructure
- **Edge Deployment**: Documented ARM support, minimal resource footprint
- **Standards Alignment**: Clear integration path with Eclipse Ditto, EdgeX Foundry

### 4.3 Quantitative Metrics

| Metric | Value |
|--------|-------|
| Lines of boilerplate saved | ~500 per deployment |
| Time to first streaming demo | < 10 minutes |
| Test coverage | > 80% |
| CI pipeline stages | 5 (lint, typecheck, unit, integration, docker) |

---

## 5. Conclusions

PyEdgeTwin provides a **methodological enabler** for hybrid model deployment research. By standardizing the edge deployment substrate, it allows researchers and practitioners to focus on model development rather than infrastructure plumbing.

---

## 6. Conflict of Interest

None declared.

---

## 7. Acknowledgments

*To be added upon submission*

---

## Data Availability Statement

> Data is generated deterministically by the included virtual asset simulator with seed=42. All figures are reproducible via `make reproduce`. No external datasets are required.

---

## References

1. SoftwareX Guide for Authors: https://www.sciencedirect.com/journal/softwarex/publish/guide-for-authors
2. Eclipse Ditto: https://eclipse.dev/ditto/
3. EdgeX Foundry: https://docs.edgexfoundry.org/
4. Paho MQTT v2 Migration: https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
5. InfluxDB Write Best Practices: https://docs.influxdata.com/influxdb/v2/write-data/best-practices/optimize-writes/
