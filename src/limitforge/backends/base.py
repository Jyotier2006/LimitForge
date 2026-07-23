"""Atomic backend contract.

The abstraction intentionally exposes algorithm-level atomic operations rather
than low-level ``get``/``set`` primitives. A generic check-then-increment API
would make distributed implementations vulnerable to races.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BackendDecision:
    allowed: bool
    remaining: int
    retry_after_ms: int
    reset_after_ms: int
    current: float


class RateLimitBackend(Protocol):
    def fixed_window(
        self, *, key: str, limit: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision: ...

    def sliding_window(
        self, *, key: str, limit: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision: ...

    def token_bucket(
        self, *, key: str, capacity: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision: ...

    def reset(self, key: str) -> None: ...

    def healthcheck(self) -> bool: ...
