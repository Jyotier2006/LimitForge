"""Thread-safe in-memory backend with per-key locking."""

from __future__ import annotations

import math
import sys
import threading
from dataclasses import dataclass

from .base import BackendDecision


@dataclass(slots=True)
class _FixedState:
    window_start_ms: int
    count: int
    last_seen_ms: int


@dataclass(slots=True)
class _SlidingState:
    window_start_ms: int
    current_count: int
    previous_count: int
    last_seen_ms: int


@dataclass(slots=True)
class _TokenState:
    tokens: float
    last_refill_ms: int
    last_seen_ms: int


class InMemoryBackend:
    """Single-process backend optimized for local applications.

    State mutations are protected by a lock derived from the full storage key.
    Different keys can therefore proceed concurrently. State is lazily pruned
    to avoid unbounded growth for inactive clients.
    """

    def __init__(
        self,
        *,
        lock_stripes: int = 256,
        cleanup_interval: int = 10_000,
        idle_ttl_seconds: float = 3_600,
    ) -> None:
        if lock_stripes <= 0:
            raise ValueError("lock_stripes must be greater than zero")
        if cleanup_interval <= 0:
            raise ValueError("cleanup_interval must be greater than zero")
        if idle_ttl_seconds <= 0:
            raise ValueError("idle_ttl_seconds must be greater than zero")

        self._locks = tuple(threading.Lock() for _ in range(lock_stripes))
        self._fixed: dict[str, _FixedState] = {}
        self._sliding: dict[str, _SlidingState] = {}
        self._tokens: dict[str, _TokenState] = {}
        self._cleanup_interval = cleanup_interval
        self._idle_ttl_ms = round(idle_ttl_seconds * 1000)
        self._operation_count = 0
        self._maintenance_lock = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        return self._locks[hash(key) % len(self._locks)]

    def _after_operation(self, now_ms: int) -> None:
        run_cleanup = False
        with self._maintenance_lock:
            self._operation_count += 1
            if self._operation_count % self._cleanup_interval == 0:
                run_cleanup = True
        if run_cleanup:
            self.prune(now_ms=now_ms)

    def fixed_window(
        self, *, key: str, limit: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision:
        _validate_cost(cost)
        window_start = (now_ms // window_ms) * window_ms
        with self._lock_for(key):
            state = self._fixed.get(key)
            if state is None or state.window_start_ms != window_start:
                state = _FixedState(window_start, 0, now_ms)
                self._fixed[key] = state

            candidate = state.count + cost
            allowed = candidate <= limit
            if allowed:
                state.count = candidate
            state.last_seen_ms = now_ms
            current = state.count

        reset_ms = max(0, window_start + window_ms - now_ms)
        self._after_operation(now_ms)
        return BackendDecision(
            allowed=allowed,
            remaining=max(0, limit - current),
            retry_after_ms=0 if allowed else reset_ms,
            reset_after_ms=reset_ms,
            current=float(current),
        )

    def sliding_window(
        self, *, key: str, limit: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision:
        _validate_cost(cost)
        window_start = (now_ms // window_ms) * window_ms
        with self._lock_for(key):
            state = self._sliding.get(key)
            if state is None:
                state = _SlidingState(window_start, 0, 0, now_ms)
                self._sliding[key] = state
            elif state.window_start_ms != window_start:
                windows_passed = (window_start - state.window_start_ms) // window_ms
                if windows_passed == 1:
                    state.previous_count = state.current_count
                else:
                    state.previous_count = 0
                state.current_count = 0
                state.window_start_ms = window_start

            elapsed = max(0, now_ms - window_start)
            previous_weight = max(0.0, 1.0 - (elapsed / window_ms))
            estimated_before = state.previous_count * previous_weight + state.current_count
            allowed = estimated_before + cost <= limit
            if allowed:
                state.current_count += cost
            state.last_seen_ms = now_ms
            previous_count = state.previous_count
            current_count = state.current_count
            current = previous_count * previous_weight + current_count

        reset_ms = max(0, window_start + window_ms - now_ms)
        retry_ms = 0 if allowed else _sliding_retry_after_ms(
            previous=previous_count,
            current=current_count,
            cost=cost,
            limit=limit,
            elapsed_ms=elapsed,
            window_ms=window_ms,
        )
        self._after_operation(now_ms)
        return BackendDecision(
            allowed=allowed,
            remaining=max(0, math.floor(limit - current)),
            retry_after_ms=retry_ms,
            reset_after_ms=reset_ms,
            current=current,
        )

    def token_bucket(
        self, *, key: str, capacity: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision:
        _validate_cost(cost)
        refill_per_ms = capacity / window_ms
        with self._lock_for(key):
            state = self._tokens.get(key)
            if state is None:
                state = _TokenState(float(capacity), now_ms, now_ms)
                self._tokens[key] = state

            elapsed = max(0, now_ms - state.last_refill_ms)
            state.tokens = min(capacity, state.tokens + elapsed * refill_per_ms)
            state.last_refill_ms = now_ms
            allowed = state.tokens + 1e-12 >= cost
            if allowed:
                state.tokens -= cost
            state.last_seen_ms = now_ms
            tokens = state.tokens

        missing = max(0.0, cost - tokens)
        retry_ms = 0 if allowed else math.ceil(missing / refill_per_ms)
        reset_ms = math.ceil((capacity - tokens) / refill_per_ms)
        self._after_operation(now_ms)
        return BackendDecision(
            allowed=allowed,
            remaining=max(0, math.floor(tokens)),
            retry_after_ms=retry_ms,
            reset_after_ms=reset_ms,
            current=capacity - tokens,
        )

    def reset(self, key: str) -> None:
        with self._lock_for(key):
            self._fixed.pop(key, None)
            self._sliding.pop(key, None)
            self._tokens.pop(key, None)

    def healthcheck(self) -> bool:
        return True

    def tracked_keys(self) -> int:
        return len(set(self._fixed) | set(self._sliding) | set(self._tokens))

    def prune(self, *, now_ms: int) -> int:
        """Remove idle entries and return the number of deleted states."""

        cutoff = now_ms - self._idle_ttl_ms
        removed = 0
        # Acquire every stripe so no mutation can race with dictionary scans.
        for lock in self._locks:
            lock.acquire()
        try:
            for mapping in (self._fixed, self._sliding, self._tokens):
                stale = [key for key, state in mapping.items() if state.last_seen_ms < cutoff]
                for key in stale:
                    del mapping[key]
                removed += len(stale)
        finally:
            for lock in reversed(self._locks):
                lock.release()
        return removed

    def approximate_memory_bytes(self) -> int:
        """Return a transparent, shallow in-process memory estimate."""

        total = (
            sys.getsizeof(self._fixed)
            + sys.getsizeof(self._sliding)
            + sys.getsizeof(self._tokens)
        )
        for mapping in (self._fixed, self._sliding, self._tokens):
            for key, value in mapping.items():
                total += sys.getsizeof(key) + sys.getsizeof(value)
        return total


def _validate_cost(cost: int) -> None:
    if isinstance(cost, bool) or not isinstance(cost, int) or cost <= 0:
        raise ValueError("cost must be a positive integer")


def _sliding_retry_after_ms(
    *, previous: int, current: int, cost: int, limit: int, elapsed_ms: int, window_ms: int
) -> int:
    """Estimate when weighted previous-window usage decays enough."""

    if previous <= 0:
        return max(1, window_ms - elapsed_ms)
    target_weight = (limit - current - cost) / previous
    if target_weight < 0:
        return max(1, window_ms - elapsed_ms)
    target_elapsed = math.ceil(window_ms * (1 - target_weight))
    return max(1, target_elapsed - elapsed_ms)
