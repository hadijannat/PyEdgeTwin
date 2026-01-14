"""Health endpoint server for PyEdgeTwin."""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

from pyedgetwin.obs.metrics import get_metrics

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for health check endpoints.

    Endpoints:
        GET /healthz - Liveness probe (is the process alive?)
        GET /readyz  - Readiness probe (is the service ready to accept traffic?)
        GET /metrics - Runtime metrics in JSON format
    """

    # Class-level callbacks set by HealthServer
    readiness_check: Callable[[], bool] = staticmethod(lambda: True)
    liveness_check: Callable[[], bool] = staticmethod(lambda: True)

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/healthz":
            self._handle_health(self.liveness_check, "liveness")
        elif self.path == "/readyz":
            self._handle_health(self.readiness_check, "readiness")
        elif self.path == "/metrics":
            self._handle_metrics()
        else:
            self.send_error(404, "Not Found")

    def _handle_health(
        self,
        check: Callable[[], bool],
        check_type: str,
    ) -> None:
        """Handle health check endpoint."""
        try:
            is_healthy = check()
            status_code = 200 if is_healthy else 503

            body = {
                "status": "ok" if is_healthy else "unhealthy",
                "check": check_type,
            }

        except Exception as e:
            status_code = 503
            body = {
                "status": "error",
                "check": check_type,
                "error": str(e),
            }

        self._send_json_response(status_code, body)

    def _handle_metrics(self) -> None:
        """Handle metrics endpoint."""
        try:
            metrics = get_metrics().to_dict()
            self._send_json_response(200, metrics)
        except Exception as e:
            self._send_json_response(500, {"error": str(e)})

    def _send_json_response(self, status_code: int, body: dict[str, Any]) -> None:
        """Send a JSON response."""
        response = json.dumps(body).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP logging."""
        # Only log errors or if debug is enabled
        if args and "error" in str(args[0]).lower():
            logger.warning(f"Health endpoint: {format % args}")


class HealthServer:
    """
    HTTP server for health and metrics endpoints.

    Runs in a background thread, separate from the main processing loop.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        readiness_check: Callable[[], bool] | None = None,
        liveness_check: Callable[[], bool] | None = None,
    ) -> None:
        """
        Initialize the health server.

        Args:
            host: Host address to bind to
            port: Port to listen on
            readiness_check: Function to check readiness (returns True if ready)
            liveness_check: Function to check liveness (returns True if alive)
        """
        self._host = host
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

        # Set up callbacks
        if readiness_check:
            HealthHandler.readiness_check = staticmethod(readiness_check)
        if liveness_check:
            HealthHandler.liveness_check = staticmethod(liveness_check)

    def start(self) -> None:
        """Start the health server in a background thread."""
        try:
            self._server = HTTPServer((self._host, self._port), HealthHandler)
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                name="health-server",
                daemon=True,
            )
            self._thread.start()
            logger.info(f"Health server listening on http://{self._host}:{self._port}")
        except OSError as e:
            logger.error(f"Failed to start health server on port {self._port}: {e}")
            raise

    def stop(self) -> None:
        """Stop the health server."""
        if self._server:
            self._server.shutdown()
            logger.debug("Health server stopped")

    def is_running(self) -> bool:
        """Check if the health server is running."""
        return self._thread is not None and self._thread.is_alive()
