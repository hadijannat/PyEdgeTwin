"""Main runtime engine for PyEdgeTwin."""

from __future__ import annotations

import logging
import signal
import sys
import threading
from typing import Any

from pyedgetwin.io.mqtt import MQTTConnector
from pyedgetwin.io.schemas import parse_ingress_message
from pyedgetwin.models.base import ModelBlock, ModelBlockContext
from pyedgetwin.models.loader import load_model_block, validate_model_output
from pyedgetwin.runtime.config import TwinConfig
from pyedgetwin.runtime.errors import ModelBlockError, SinkError
from pyedgetwin.runtime.queueing import BoundedQueue
from pyedgetwin.sinks import create_sink
from pyedgetwin.sinks.base import BaseSink
from pyedgetwin.sinks.stdout import StdoutSink
from pyedgetwin.utils.time import utc_now

logger = logging.getLogger(__name__)


class TwinRuntime:
    """
    Main runtime engine orchestrating the PyEdgeTwin data pipeline.

    The runtime manages:
    - MQTT connection and message ingestion
    - Message queuing with backpressure handling
    - Model block execution
    - Output to configured sinks

    Pipeline flow:
        MQTT → Queue → Worker(s) → Model Block → Sinks
    """

    def __init__(self, config: TwinConfig) -> None:
        """
        Initialize the twin runtime.

        Args:
            config: Complete twin configuration
        """
        self._config = config
        self._running = threading.Event()
        self._shutdown_event = threading.Event()

        # Components (initialized in start())
        self._queue: BoundedQueue | None = None
        self._connector: MQTTConnector | None = None
        self._model: ModelBlock | None = None
        self._sinks: list[BaseSink] = []
        self._worker_threads: list[threading.Thread] = []
        self._health_server: Any = None

        # Metrics
        self._messages_received = 0
        self._messages_processed = 0
        self._processing_errors = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        """
        Initialize all components and start processing.

        Raises:
            Various exceptions if initialization fails
        """
        twin_id = self._config.runtime.twin_id
        logger.info(f"Starting twin runtime: {twin_id}")

        # Initialize message queue
        self._queue = BoundedQueue(
            maxsize=self._config.runtime.queue_size,
            overflow_policy=self._config.runtime.queue_overflow_policy,
        )
        logger.debug(
            f"Queue initialized: size={self._config.runtime.queue_size}, "
            f"policy={self._config.runtime.queue_overflow_policy}"
        )

        # Initialize model block
        context = ModelBlockContext(
            asset_id=self._config.runtime.asset_id,
            twin_id=twin_id,
            model_version=self._config.model.version,
            config=self._config.model.params,
        )
        self._model = load_model_block(self._config.model, context)
        logger.info(f"Model block loaded: {self._config.model.module_path}")

        # Initialize sinks
        self._init_sinks()

        # Initialize and connect MQTT
        self._connector = MQTTConnector(self._config.mqtt)
        self._connector.connect()

        # Subscribe to configured topics
        for topic in self._config.mqtt.topics:
            self._connector.subscribe(topic, self._on_message)
            logger.info(f"Subscribed to topic: {topic}")

        # Start health server if enabled
        if self._config.health.enabled:
            self._start_health_server()

        # Start worker threads
        self._running.set()
        for i in range(self._config.runtime.workers):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"worker-{i}",
                daemon=True,
            )
            thread.start()
            self._worker_threads.append(thread)
            logger.debug(f"Started worker thread: worker-{i}")

        logger.info(
            f"Twin runtime started successfully "
            f"(workers={self._config.runtime.workers}, "
            f"sinks={len(self._sinks)})"
        )

    def _init_sinks(self) -> None:
        """Initialize all configured sinks."""
        if not self._config.sinks:
            # Default to stdout sink
            logger.info("No sinks configured, using stdout")
            sink = StdoutSink()
            sink.open()
            self._sinks.append(sink)
            return

        for sink_type, sink_config in self._config.sinks.items():
            try:
                sink = create_sink(sink_type, sink_config)
                sink.open()
                self._sinks.append(sink)
                logger.info(f"Initialized sink: {sink_type}")
            except Exception as e:
                logger.error(f"Failed to initialize sink {sink_type}: {e}")
                raise SinkError(f"Failed to initialize sink: {e}") from e

    def _start_health_server(self) -> None:
        """Start the health endpoint server."""
        try:
            from pyedgetwin.runtime.health import HealthServer

            self._health_server = HealthServer(
                host=self._config.health.host,
                port=self._config.health.port,
                readiness_check=self._readiness_check,
                liveness_check=self._liveness_check,
            )
            self._health_server.start()
            logger.info(
                f"Health server started at "
                f"http://{self._config.health.host}:{self._config.health.port}"
            )
        except Exception as e:
            logger.warning(f"Failed to start health server: {e}")

    def _readiness_check(self) -> bool:
        """Check if the runtime is ready to process messages."""
        return (
            self._running.is_set()
            and self._connector is not None
            and self._connector.is_connected()
            and self._model is not None
            and len(self._sinks) > 0
        )

    def _liveness_check(self) -> bool:
        """Check if the runtime is alive."""
        return self._running.is_set()

    def _on_message(self, payload: dict[str, Any]) -> None:
        """
        Callback for incoming MQTT messages.

        Adds messages to the processing queue.
        """
        with self._lock:
            self._messages_received += 1

        # Add ingestion timestamp
        payload["_ingested_at"] = utc_now().isoformat()

        if not self._queue.put(payload, timeout=1.0):
            logger.warning("Failed to enqueue message (queue overflow)")

    def _worker_loop(self) -> None:
        """
        Worker thread processing messages from the queue.

        Runs until the runtime is stopped.
        """
        thread_name = threading.current_thread().name
        logger.debug(f"{thread_name}: Starting worker loop")

        while self._running.is_set():
            try:
                # Get message with timeout so we can check running flag
                try:
                    msg = self._queue.get(timeout=1.0)
                except Exception:
                    continue

                # Process the message
                self._process_message(msg)
                self._queue.task_done()

            except Exception as e:
                logger.error(f"{thread_name}: Unexpected error: {e}")

        logger.debug(f"{thread_name}: Worker loop stopped")

    def _process_message(self, msg: dict[str, Any]) -> None:
        """
        Process a single message through the model and sinks.

        Args:
            msg: Raw message from the queue
        """
        try:
            # Parse ingress message
            ingress = parse_ingress_message(msg, strict=False)

            # Process through model block
            if self._model is None:
                raise ModelBlockError("Model block not initialized")

            model_output = self._model.process(msg)

            # Validate model output
            is_valid, missing = validate_model_output(model_output)
            if not is_valid:
                logger.warning(f"Model output missing required keys: {missing}")
                # Add defaults for missing keys
                model_output.setdefault("raw_value", msg.get("value", 0.0))
                model_output.setdefault("twin_estimate", msg.get("value", 0.0))
                model_output.setdefault("anomaly_flag", False)

            # Create egress record
            record = self._create_record(ingress, model_output)

            # Write to all sinks
            for sink in self._sinks:
                try:
                    sink.write(record)
                except Exception as e:
                    logger.error(f"Sink write error: {e}")

            with self._lock:
                self._messages_processed += 1

        except Exception as e:
            with self._lock:
                self._processing_errors += 1
            logger.error(f"Error processing message: {e}")

    def _create_record(
        self,
        ingress: Any,
        model_output: dict[str, Any],
    ) -> dict[str, Any]:
        """Create the output record for sinks."""
        return {
            "asset_id": self._config.runtime.asset_id,
            "twin_id": self._config.runtime.twin_id,
            "model_version": self._config.model.version,
            "timestamp": ingress.timestamp.isoformat(),
            "processed_at": utc_now().isoformat(),
            "raw_value": model_output.get("raw_value"),
            "twin_estimate": model_output.get("twin_estimate"),
            "anomaly_flag": model_output.get("anomaly_flag", False),
            "residual": model_output.get("residual"),
            "confidence": model_output.get("confidence"),
            **{
                k: v
                for k, v in model_output.items()
                if k not in {"raw_value", "twin_estimate", "anomaly_flag", "residual", "confidence"}
            },
        }

    def stop(self) -> None:
        """Gracefully shutdown the runtime."""
        if not self._running.is_set():
            return

        logger.info("Stopping twin runtime...")
        self._running.clear()

        # Wait for workers to finish
        for thread in self._worker_threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(f"Worker {thread.name} did not stop cleanly")

        # Shutdown model
        if self._model:
            try:
                self._model.shutdown()
                logger.debug("Model block shutdown complete")
            except Exception as e:
                logger.error(f"Error during model shutdown: {e}")

        # Flush and close sinks
        for sink in self._sinks:
            try:
                sink.flush()
                sink.close()
            except Exception as e:
                logger.error(f"Error closing sink: {e}")

        # Disconnect MQTT
        if self._connector:
            self._connector.disconnect()

        # Stop health server
        if self._health_server:
            try:
                self._health_server.stop()
            except Exception as e:
                logger.warning(f"Error stopping health server: {e}")

        logger.info("Twin runtime stopped")

    def run_forever(self) -> None:
        """
        Run until interrupted by signal.

        Sets up signal handlers for graceful shutdown.
        """

        # Set up signal handlers
        def signal_handler(signum: int, _frame: Any) -> None:
            logger.info(f"Received signal {signum}")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Start the runtime
        self.start()

        # Wait for shutdown
        try:
            while self._running.is_set():
                self._shutdown_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.stop()

    def get_stats(self) -> dict[str, Any]:
        """Get runtime statistics."""
        with self._lock:
            stats = {
                "twin_id": self._config.runtime.twin_id,
                "asset_id": self._config.runtime.asset_id,
                "running": self._running.is_set(),
                "messages_received": self._messages_received,
                "messages_processed": self._messages_processed,
                "processing_errors": self._processing_errors,
                "workers": len(self._worker_threads),
                "sinks": len(self._sinks),
            }

        if self._queue:
            stats["queue"] = self._queue.stats()

        if self._connector:
            stats["connector"] = self._connector.health_check()

        return stats
