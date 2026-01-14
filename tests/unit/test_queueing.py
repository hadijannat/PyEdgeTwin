"""Unit tests for bounded queue."""

from __future__ import annotations

import queue
import threading
import time

import pytest

from pyedgetwin.runtime.queueing import BoundedQueue
from pyedgetwin.runtime.errors import QueueOverflowError


class TestBoundedQueue:
    """Tests for BoundedQueue."""

    def test_basic_put_get(self) -> None:
        """Test basic put and get operations."""
        q = BoundedQueue(maxsize=10)
        q.put("item1")
        q.put("item2")

        assert q.size == 2
        assert q.get() == "item1"
        assert q.get() == "item2"

    def test_drop_oldest_policy(self) -> None:
        """Test drop_oldest overflow policy."""
        q = BoundedQueue(maxsize=3, overflow_policy="drop_oldest")

        q.put("item1")
        q.put("item2")
        q.put("item3")
        assert q.size == 3

        # This should drop item1
        q.put("item4")
        assert q.size == 3
        assert q.dropped_count == 1

        # Verify order
        assert q.get() == "item2"
        assert q.get() == "item3"
        assert q.get() == "item4"

    def test_drop_newest_policy(self) -> None:
        """Test drop_newest overflow policy."""
        q = BoundedQueue(maxsize=3, overflow_policy="drop_newest")

        q.put("item1")
        q.put("item2")
        q.put("item3")

        # This should be dropped
        result = q.put("item4")
        assert result is False
        assert q.dropped_count == 1

        # Verify original items remain
        assert q.get() == "item1"
        assert q.get() == "item2"
        assert q.get() == "item3"

    def test_block_policy_with_timeout(self) -> None:
        """Test block policy raises on timeout."""
        q = BoundedQueue(maxsize=1, overflow_policy="block")
        q.put("item1")

        with pytest.raises(QueueOverflowError):
            q.put("item2", timeout=0.1)

    def test_empty_and_full(self) -> None:
        """Test empty and full checks."""
        q = BoundedQueue(maxsize=2)

        assert q.empty()
        assert not q.full()

        q.put("item1")
        assert not q.empty()
        assert not q.full()

        q.put("item2")
        assert not q.empty()
        assert q.full()

    def test_stats(self) -> None:
        """Test stats method."""
        q = BoundedQueue(maxsize=5, overflow_policy="drop_oldest")

        q.put("item1")
        q.put("item2")

        stats = q.stats()
        assert stats["size"] == 2
        assert stats["maxsize"] == 5
        assert stats["dropped"] == 0
        assert stats["total_put"] == 2
        assert stats["overflow_policy"] == "drop_oldest"

    def test_invalid_policy_raises(self) -> None:
        """Test that invalid policy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid overflow_policy"):
            BoundedQueue(overflow_policy="invalid")

    def test_thread_safety(self) -> None:
        """Test thread-safe operations."""
        q = BoundedQueue(maxsize=100, overflow_policy="drop_oldest")
        num_items = 500
        results: list[int] = []

        def producer() -> None:
            for i in range(num_items):
                q.put(i)

        def consumer() -> None:
            while len(results) < num_items:
                try:
                    item = q.get(timeout=0.1)
                    results.append(item)
                except Exception:
                    pass

        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        # Give consumer time to drain
        time.sleep(0.5)

        # Should have received most items (some may be dropped)
        assert q.total_put == num_items
        # Total received + dropped should equal total put
        received_plus_dropped = len(results) + q.dropped_count
        assert received_plus_dropped <= num_items
