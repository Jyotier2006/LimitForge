"""High-level rate limiter."""

from __future__ import annotations

import asyncio
import functools
import inspect
import math
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, cast

from .backends.base import RateLimitBackend
from .backends.memory import InMemoryBackend
from .clock import Clock, SystemClock
from .exceptions import BackendUnavailable, RateLimitExceeded
from .models import Algorithm, RateLimit, RateLimitResult

P = ParamSpec("P")
R = TypeVar("R")
KeyFunction = Callable[P, str]


class RateLimiter:
    """Apply rate-limit policies through a pluggable atomic backend."""

    def __init__(
        self,
        backend: RateLimitBackend | None = None,
        *,
        clock: Clock | None = None,
        fail_open: bool = False,
        max_key_length: int = 512,
    ) -> None:
        if max_key_length <= 0:
            raise ValueError("max_key_length must be greater than zero")
        self.backend = backend or InMemoryBackend()
        self.clock = clock or SystemClock()
        self.fail_open = fail_open
        self.max_key_length = max_key_length

    def check(self, key: str, policy: RateLimit, *, cost: int = 1) -> RateLimitResult:
        """Consume ``cost`` units and return the decision.

        A key is namespaced by algorithm and policy namespace so unrelated
        policies never share backend state accidentally.
        """

        if not key:
            raise ValueError("key must be non-empty")
        if len(key) > self.max_key_length:
            raise ValueError(f"key cannot exceed {self.max_key_length} characters")
        if isinstance(cost, bool) or not isinstance(cost, int) or cost <= 0:
            raise ValueError("cost must be a positive integer")
        if cost > policy.limit:
            raise ValueError("cost cannot exceed the policy limit or bucket capacity")

        now_ms = self.clock.now_ms()
        storage_key = self.storage_key(key, policy)
        try:
            if policy.algorithm is Algorithm.FIXED_WINDOW:
                decision = self.backend.fixed_window(
                    key=storage_key,
                    limit=policy.limit,
                    window_ms=policy.window_ms,
                    now_ms=now_ms,
                    cost=cost,
                )
            elif policy.algorithm is Algorithm.SLIDING_WINDOW:
                decision = self.backend.sliding_window(
                    key=storage_key,
                    limit=policy.limit,
                    window_ms=policy.window_ms,
                    now_ms=now_ms,
                    cost=cost,
                )
            elif policy.algorithm is Algorithm.TOKEN_BUCKET:
                decision = self.backend.token_bucket(
                    key=storage_key,
                    capacity=policy.limit,
                    window_ms=policy.window_ms,
                    now_ms=now_ms,
                    cost=cost,
                )
            else:  # pragma: no cover - StrEnum exhaustiveness guard
                raise ValueError(f"unsupported algorithm: {policy.algorithm}")
        except BackendUnavailable:
            if not self.fail_open:
                raise
            return RateLimitResult(
                allowed=True,
                limit=policy.limit,
                remaining=policy.limit,
                retry_after=0,
                reset_after=0,
                current=0,
                algorithm=policy.algorithm,
                key=key,
            )

        return RateLimitResult(
            allowed=decision.allowed,
            limit=policy.limit,
            remaining=decision.remaining,
            retry_after=decision.retry_after_ms / 1000,
            reset_after=decision.reset_after_ms / 1000,
            current=decision.current,
            algorithm=policy.algorithm,
            key=key,
        )

    def reset(self, key: str, policy: RateLimit) -> None:
        self.backend.reset(self.storage_key(key, policy))

    @staticmethod
    def storage_key(key: str, policy: RateLimit) -> str:
        return f"{policy.namespace}:{policy.algorithm.value}:{key}"

    def decorator(
        self,
        policy: RateLimit,
        *,
        key: str | KeyFunction[P],
        cost: int = 1,
        wait: bool = False,
        max_wait_seconds: float | None = None,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """Decorate sync or async callables.

        By default rejected calls raise :class:`RateLimitExceeded`. With
        ``wait=True``, the wrapper sleeps and retries until allowed. ``wait`` is
        mainly useful for client-side API throttling; request middleware should
        reject immediately instead.
        """

        if max_wait_seconds is not None and max_wait_seconds < 0:
            raise ValueError("max_wait_seconds cannot be negative")

        def decorate(function: Callable[P, R]) -> Callable[P, R]:
            if inspect.iscoroutinefunction(function):

                @functools.wraps(function)
                async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                    resolved_key = _resolve_key(key, args, kwargs)
                    waited = 0.0
                    while True:
                        result = self.check(resolved_key, policy, cost=cost)
                        if result.allowed:
                            return await function(*args, **kwargs)
                        if not wait or not _can_wait(result, waited, max_wait_seconds):
                            raise RateLimitExceeded(result)
                        await asyncio.sleep(result.retry_after)
                        waited += result.retry_after

                return cast(Callable[P, R], async_wrapper)

            @functools.wraps(function)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                import time

                resolved_key = _resolve_key(key, args, kwargs)
                waited = 0.0
                while True:
                    result = self.check(resolved_key, policy, cost=cost)
                    if result.allowed:
                        return function(*args, **kwargs)
                    if not wait or not _can_wait(result, waited, max_wait_seconds):
                        raise RateLimitExceeded(result)
                    time.sleep(result.retry_after)
                    waited += result.retry_after

            return sync_wrapper

        return decorate


def fixed_window(limit: int, window_seconds: float, *, namespace: str = "default") -> RateLimit:
    return RateLimit(limit, window_seconds, Algorithm.FIXED_WINDOW, namespace)


def sliding_window(limit: int, window_seconds: float, *, namespace: str = "default") -> RateLimit:
    return RateLimit(limit, window_seconds, Algorithm.SLIDING_WINDOW, namespace)


def token_bucket(capacity: int, refill_seconds: float, *, namespace: str = "default") -> RateLimit:
    return RateLimit(capacity, refill_seconds, Algorithm.TOKEN_BUCKET, namespace)


def _resolve_key(key: str | KeyFunction[P], args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    value = key(*args, **kwargs) if callable(key) else key
    if not isinstance(value, str) or not value:
        raise ValueError("resolved rate-limit key must be a non-empty string")
    return value


def _can_wait(
    result: RateLimitResult, waited: float, max_wait_seconds: float | None
) -> bool:
    if result.retry_after <= 0 or not math.isfinite(result.retry_after):
        return False
    return max_wait_seconds is None or waited + result.retry_after <= max_wait_seconds
