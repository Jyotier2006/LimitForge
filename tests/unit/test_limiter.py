import asyncio

import pytest

from limitforge import (
    BackendUnavailable,
    ManualClock,
    RateLimiter,
    RateLimitExceeded,
    fixed_window,
)
from limitforge.backends import InMemoryBackend


class BrokenBackend:
    def fixed_window(self, **kwargs):  # type: ignore[no-untyped-def]
        raise BackendUnavailable("offline")

    sliding_window = fixed_window
    token_bucket = fixed_window

    def reset(self, key: str) -> None:
        raise BackendUnavailable("offline")

    def healthcheck(self) -> bool:
        return False


def test_namespaces_isolate_policies() -> None:
    limiter = RateLimiter(InMemoryBackend(), clock=ManualClock())
    a = fixed_window(1, 60, namespace="login")
    b = fixed_window(1, 60, namespace="search")
    assert limiter.check("same-user", a).allowed
    assert limiter.check("same-user", b).allowed


def test_fail_open_is_explicit() -> None:
    strict = RateLimiter(BrokenBackend())
    with pytest.raises(BackendUnavailable):
        strict.check("u", fixed_window(1, 1))

    tolerant = RateLimiter(BrokenBackend(), fail_open=True)
    result = tolerant.check("u", fixed_window(1, 1))
    assert result.allowed
    assert result.remaining == 1


def test_sync_decorator_rejects() -> None:
    limiter = RateLimiter(InMemoryBackend(), clock=ManualClock())

    @limiter.decorator(fixed_window(1, 60), key=lambda user: user)
    def greet(user: str) -> str:
        return f"hello {user}"

    assert greet("alice") == "hello alice"
    with pytest.raises(RateLimitExceeded):
        greet("alice")


def test_async_decorator_rejects() -> None:
    limiter = RateLimiter(InMemoryBackend(), clock=ManualClock())

    @limiter.decorator(fixed_window(1, 60), key="global")
    async def operation() -> int:
        return 42

    assert asyncio.run(operation()) == 42
    with pytest.raises(RateLimitExceeded):
        asyncio.run(operation())


def test_input_validation() -> None:
    limiter = RateLimiter()
    policy = fixed_window(1, 1)
    with pytest.raises(ValueError):
        limiter.check("", policy)
    with pytest.raises(ValueError):
        limiter.check("u", policy, cost=0)
    with pytest.raises(ValueError):
        limiter.check("u", policy, cost=2)
    with pytest.raises(ValueError):
        RateLimiter(max_key_length=0)
    with pytest.raises(ValueError):
        RateLimiter(max_key_length=2).check("long", policy)


def test_reset_and_decorator_validation(monkeypatch) -> None:
    clock = ManualClock()
    backend = InMemoryBackend()
    limiter = RateLimiter(backend, clock=clock)
    policy = fixed_window(1, 1)
    assert limiter.check("u", policy).allowed
    limiter.reset("u", policy)
    assert limiter.check("u", policy).allowed

    with pytest.raises(ValueError):
        limiter.decorator(policy, key="x", max_wait_seconds=-1)

    @limiter.decorator(policy, key=lambda: "")
    def bad_key() -> None:
        return None

    with pytest.raises(ValueError):
        bad_key()


def test_waiting_decorator_retries(monkeypatch) -> None:
    import time

    clock = ManualClock()
    limiter = RateLimiter(InMemoryBackend(), clock=clock)
    policy = fixed_window(1, 1)
    limiter.check("global", policy)

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds=seconds)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    @limiter.decorator(policy, key="global", wait=True, max_wait_seconds=1)
    def operation() -> str:
        return "done"

    assert operation() == "done"


def test_waiting_decorator_respects_max_wait() -> None:
    clock = ManualClock()
    limiter = RateLimiter(InMemoryBackend(), clock=clock)
    policy = fixed_window(1, 10)
    limiter.check("global", policy)

    @limiter.decorator(policy, key="global", wait=True, max_wait_seconds=1)
    def operation() -> None:
        return None

    with pytest.raises(RateLimitExceeded):
        operation()
