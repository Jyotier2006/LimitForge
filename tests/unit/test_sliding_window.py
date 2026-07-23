import pytest

from limitforge import ManualClock, RateLimiter, sliding_window
from limitforge.backends import InMemoryBackend


def test_sliding_window_smooths_boundary_burst() -> None:
    clock = ManualClock(0)
    limiter = RateLimiter(InMemoryBackend(), clock=clock)
    policy = sliding_window(10, 10)

    for _ in range(10):
        assert limiter.check("user", policy).allowed

    clock.advance(seconds=10)
    # At the boundary the previous window still has full weight, unlike fixed window.
    first_new_window = limiter.check("user", policy)
    assert not first_new_window.allowed

    clock.advance(seconds=5)
    for _ in range(5):
        assert limiter.check("user", policy).allowed
    assert not limiter.check("user", policy).allowed


def test_sliding_retry_after_is_estimated() -> None:
    clock = ManualClock(0)
    limiter = RateLimiter(InMemoryBackend(), clock=clock)
    policy = sliding_window(4, 4)
    for _ in range(4):
        limiter.check("u", policy)
    clock.advance(seconds=4)
    blocked = limiter.check("u", policy)
    assert blocked.retry_after == pytest.approx(1.0)


def test_sliding_window_same_window_retry_uses_boundary() -> None:
    clock = ManualClock(0)
    limiter = RateLimiter(InMemoryBackend(), clock=clock)
    policy = sliding_window(2, 10)
    assert limiter.check("u", policy, cost=2).allowed
    blocked = limiter.check("u", policy)
    assert blocked.retry_after == 10
