"""Command-line interface for PyEdgeTwin."""

from __future__ import annotations

import logging
import sys

import click

from pyedgetwin import __version__


@click.group()
@click.version_option(version=__version__, prog_name="pyedgetwin")
def main() -> None:
    """
    PyEdgeTwin - Python runtime for hybrid model deployment on edge devices.

    Use 'pyedgetwin run' to start the twin runtime with a configuration file.
    """
    pass


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to YAML configuration file",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Logging level (default: INFO)",
)
@click.option(
    "--log-format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Log output format (default: text)",
)
def run(config: str, log_level: str, log_format: str) -> None:
    """
    Start the twin runtime.

    Loads the configuration from the specified YAML file and starts
    processing messages from the configured MQTT topics through the
    model block and into the configured sinks.

    Example:
        pyedgetwin run -c config.yaml
        pyedgetwin run -c config.yaml --log-level DEBUG
        pyedgetwin run -c config.yaml --log-format json
    """
    # Set up logging
    _setup_logging(log_level, log_format)

    logger = logging.getLogger(__name__)
    logger.info(f"PyEdgeTwin v{__version__}")
    logger.info(f"Loading configuration from: {config}")

    try:
        # Load configuration
        from pyedgetwin.runtime.config import load_config

        twin_config = load_config(config)
        logger.info(f"Configuration loaded for twin: {twin_config.runtime.twin_id}")

        # Create and run the runtime
        from pyedgetwin.runtime.runner import TwinRuntime

        runtime = TwinRuntime(twin_config)
        runtime.run_forever()

    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if log_level.upper() == "DEBUG":
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to YAML configuration file",
)
def validate(config: str) -> None:
    """
    Validate a configuration file.

    Checks that the configuration file is valid YAML and contains
    all required fields with correct types.

    Example:
        pyedgetwin validate -c config.yaml
    """
    _setup_logging("INFO", "text")

    try:
        from pyedgetwin.runtime.config import load_config

        twin_config = load_config(config)

        click.echo(click.style("Configuration is valid!", fg="green"))
        click.echo(f"  Twin ID: {twin_config.runtime.twin_id}")
        click.echo(f"  Asset ID: {twin_config.runtime.asset_id}")
        click.echo(f"  Model: {twin_config.model.module_path}")
        click.echo(f"  Topics: {twin_config.mqtt.topics}")
        click.echo(f"  Sinks: {list(twin_config.sinks.keys()) or ['stdout']}")

    except Exception as e:
        click.echo(click.style(f"Configuration error: {e}", fg="red"))
        sys.exit(1)


@main.command()
def info() -> None:
    """
    Show information about PyEdgeTwin installation.

    Displays version information, installed dependencies, and
    available plugins.
    """
    click.echo(f"PyEdgeTwin v{__version__}")
    click.echo()

    # Python version
    import platform
    click.echo(f"Python: {platform.python_version()}")
    click.echo(f"Platform: {platform.platform()}")
    click.echo()

    # Dependencies
    click.echo("Dependencies:")
    deps = [
        ("paho-mqtt", "paho.mqtt"),
        ("influxdb-client", "influxdb_client"),
        ("pyyaml", "yaml"),
        ("click", "click"),
        ("pydantic", "pydantic"),
    ]
    for name, module in deps:
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "installed")
            click.echo(f"  {name}: {version}")
        except ImportError:
            click.echo(click.style(f"  {name}: not installed", fg="red"))

    click.echo()

    # Registered plugins
    click.echo("Registered sinks:")
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="pyedgetwin.sinks")
        for ep in eps:
            click.echo(f"  {ep.name}: {ep.value}")
    except Exception:
        click.echo("  (unable to list)")

    click.echo()
    click.echo("Registered connectors:")
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="pyedgetwin.connectors")
        for ep in eps:
            click.echo(f"  {ep.name}: {ep.value}")
    except Exception:
        click.echo("  (unable to list)")


def _setup_logging(level: str, format_type: str) -> None:
    """Configure logging for the CLI."""
    handlers = []

    if format_type == "json":
        from pyedgetwin.obs.logging import JSONFormatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        handlers.append(handler)
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(handler)

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("paho").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


if __name__ == "__main__":
    main()
