"""Bounded message queue for PyEdgeTwin."""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any

from pyedgetwin.runtime.errors import QueueOverflowError

logger = logging.getLogger(__name__)


class BoundedQueue:
    """
    Thread-safe bounded queue with configurable overflow policies.

    Overflow Policies:
        - drop_oldest: Remove oldest message to make room (default)
        - drop_newest: Discard the new message if queue is full
        - block: Block until space is available (with timeout)

    This queue is designed for the ingestion pipeline where we need
    to handle backpressure gracefully.
    """

    def __init__(
        self,
        maxsize: int = 1000,
        overflow_policy: str = "drop_oldest",
    ) -> None:
        """
        Initialize the bounded queue.

        Args:
            maxsize: Maximum number of items in the queue
            overflow_policy: How to handle overflow ('drop_oldest', 'drop_newest', 'block')

        Raises:
            ValueError: If overflow_policy is invalid
        """
        valid_policies = {"drop_oldest", "drop_newest", "block"}
        if overflow_policy not in valid_policies:
            raise ValueError(
                f"Invalid overflow_policy: {overflow_policy}. "
                f"Must be one of {valid_policies}"
            )

        self._queue: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._maxsize = maxsize
        self._policy = overflow_policy
        self._dropped_count = 0
        self._total_put = 0
        self._lock = threading.Lock()

    def put(
        self,
        item: Any,
        timeout: float | None = None,
    ) -> bool:
        """
        Put an item in the queue, handling overflow per policy.

        Args:
            item: Item to add to the queue
            timeout: Timeout for 'block' policy (ignored for other policies)

        Returns:
            True if item was added, False if dropped

        Raises:
            QueueOverflowError: If policy is 'block' and timeout exceeded
        """
        with self._lock:
            self._total_put += 1

        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            return self._handle_overflow(item, timeout)

    def _handle_overflow(
        self,
        item: Any,
        timeout: float | None,
    ) -> bool:
        """Handle queue overflow based on policy."""
        if self._policy == "drop_oldest":
            # Remove oldest item and add new one
            try:
                dropped = self._queue.get_nowait()
                with self._lock:
                    self._dropped_count += 1
                logger.debug(f"Queue full, dropped oldest item")
                self._queue.put_nowait(item)
                return True
            except queue.Empty:
                # Queue was emptied between checks, try again
                try:
                    self._queue.put_nowait(item)
                    return True
                except queue.Full:
                    with self._lock:
                        self._dropped_count += 1
                    return False

        elif self._policy == "drop_newest":
            # Discard the new item
            with self._lock:
                self._dropped_count += 1
            logger.debug("Queue full, dropping newest message")
            return False

        elif self._policy == "block":
            # Block until space is available
            try:
                self._queue.put(item, block=True, timeout=timeout)
                return True
            except queue.Full:
                raise QueueOverflowError(
                    "Queue is full and timeout exceeded",
                    details={"timeout": timeout, "size": self._queue.qsize()},
                )

        return False

    def get(self, timeout: float | None = None) -> Any:
        """
        Get an item from the queue.

        Args:
            timeout: How long to wait for an item

        Returns:
            The next item from the queue

        Raises:
            queue.Empty: If no item is available within timeout
        """
        return self._queue.get(timeout=timeout)

    def get_nowait(self) -> Any:
        """
        Get an item without waiting.

        Returns:
            The next item from the queue

        Raises:
            queue.Empty: If no item is available
        """
        return self._queue.get_nowait()

    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete."""
        self._queue.task_done()

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()

    def full(self) -> bool:
        """Check if the queue is full."""
        return self._queue.full()

    @property
    def size(self) -> int:
        """Current number of items in the queue."""
        return self._queue.qsize()

    @property
    def maxsize(self) -> int:
        """Maximum size of the queue."""
        return self._maxsize

    @property
    def dropped_count(self) -> int:
        """Number of messages dropped due to overflow."""
        with self._lock:
            return self._dropped_count

    @property
    def total_put(self) -> int:
        """Total number of put() calls."""
        with self._lock:
            return self._total_put

    def stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            return {
                "size": self._queue.qsize(),
                "maxsize": self._maxsize,
                "dropped": self._dropped_count,
                "total_put": self._total_put,
                "overflow_policy": self._policy,
            }
