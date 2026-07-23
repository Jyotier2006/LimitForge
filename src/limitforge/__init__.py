"""LimitForge: pluggable, concurrency-safe rate limiting for Python."""

from .backends import InMemoryBackend, RedisBackend
from .clock import ManualClock, SystemClock
from .exceptions import BackendUnavailable, LimitForgeError, RateLimitExceeded
from .headers import rate_limit_headers
from .limiter import RateLimiter, fixed_window, sliding_window, token_bucket
from .models import Algorithm, RateLimit, RateLimitResult

__all__ = [
    "Algorithm",
    "BackendUnavailable",
    "InMemoryBackend",
    "LimitForgeError",
    "ManualClock",
    "RateLimit",
    "RateLimitExceeded",
    "RateLimitResult",
    "RateLimiter",
    "RedisBackend",
    "SystemClock",
    "fixed_window",
    "rate_limit_headers",
    "sliding_window",
    "token_bucket",
]

__version__ = "0.1.0"
