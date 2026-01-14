"""Output sinks for PyEdgeTwin."""

from importlib.metadata import entry_points
from typing import Any

from pyedgetwin.sinks.base import BaseSink

__all__ = ["BaseSink", "create_sink"]


def create_sink(sink_type: str, config: dict[str, Any]) -> BaseSink:
    """
    Factory function to create sinks by type or entrypoint.

    Args:
        sink_type: The type of sink to create (e.g., 'stdout', 'csv', 'influxdb2')
        config: Configuration dictionary for the sink

    Returns:
        An initialized sink instance

    Raises:
        ValueError: If the sink type is unknown
    """
    # Lazy imports to avoid circular dependencies
    from pyedgetwin.sinks.csv_sink import CSVSink
    from pyedgetwin.sinks.influxdb2 import InfluxDB2Sink
    from pyedgetwin.sinks.stdout import StdoutSink

    builtin: dict[str, type[BaseSink]] = {
        "stdout": StdoutSink,
        "csv": CSVSink,
        "influxdb2": InfluxDB2Sink,
    }

    if sink_type in builtin:
        return builtin[sink_type](**config)

    # Check entrypoints for plugins
    eps = entry_points(group="pyedgetwin.sinks")
    for ep in eps:
        if ep.name == sink_type:
            cls = ep.load()
            return cls(**config)

    raise ValueError(f"Unknown sink type: {sink_type}")
