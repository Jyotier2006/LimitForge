"""Clock abstractions make algorithms deterministic and testable."""

from __future__ import annotations

import threading
import time
from typing import Protocol


class Clock(Protocol):
    def now_ms(self) -> int:
        """Return monotonic-ish time in milliseconds."""
        ...


class SystemClock:
    """Production clock based on wall time for cross-process consistency."""

    def now_ms(self) -> int:
        return time.time_ns() // 1_000_000


class ManualClock:
    """Thread-safe deterministic clock intended for tests and examples."""

    def __init__(self, start_ms: int = 0) -> None:
        self._now_ms = start_ms
        self._lock = threading.Lock()

    def now_ms(self) -> int:
        with self._lock:
            return self._now_ms

    def advance(self, *, milliseconds: int = 0, seconds: float = 0) -> None:
        delta = milliseconds + round(seconds * 1000)
        if delta < 0:
            raise ValueError("clock cannot move backwards")
        with self._lock:
            self._now_ms += delta
