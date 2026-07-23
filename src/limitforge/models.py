"""Public data models used by LimitForge."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Algorithm(str, Enum):
    """Supported rate-limiting algorithms."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass(frozen=True, slots=True)
class RateLimit:
    """Configuration for one rate limit.

    ``limit`` is the maximum number of units accepted during ``window_seconds``
    for window-based algorithms. For token bucket, it is the bucket capacity and
    ``window_seconds`` is the time required to refill that capacity.
    """

    limit: int
    window_seconds: float
    algorithm: Algorithm = Algorithm.SLIDING_WINDOW
    namespace: str = "default"

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be greater than zero")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero")
        if not self.namespace or ":" in self.namespace:
            raise ValueError("namespace must be non-empty and cannot contain ':'")

    @property
    def window_ms(self) -> int:
        """Window length in integer milliseconds."""

        return max(1, round(self.window_seconds * 1000))


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    """Decision returned by every rate-limit check."""

    allowed: bool
    limit: int
    remaining: int
    retry_after: float
    reset_after: float
    current: float
    algorithm: Algorithm
    key: str

    @property
    def retry_after_ms(self) -> int:
        return max(0, round(self.retry_after * 1000))

    @property
    def reset_after_ms(self) -> int:
        return max(0, round(self.reset_after * 1000))
