"""LimitForge exceptions."""

from __future__ import annotations

from .models import RateLimitResult


class LimitForgeError(Exception):
    """Base exception for the package."""


class BackendUnavailable(LimitForgeError):
    """Raised when a configured backend cannot be reached."""


class RateLimitExceeded(LimitForgeError):
    """Raised by decorators when a call is rejected."""

    def __init__(self, result: RateLimitResult) -> None:
        self.result = result
        super().__init__(
            f"rate limit exceeded for {result.key!r}; "
            f"retry after {result.retry_after:.3f}s"
        )
