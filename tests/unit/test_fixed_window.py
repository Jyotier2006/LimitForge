from limitforge import ManualClock, RateLimiter, fixed_window
from limitforge.backends import InMemoryBackend


def test_fixed_window_blocks_until_boundary() -> None:
    clock = ManualClock(10_000)
    limiter = RateLimiter(InMemoryBackend(), clock=clock)
    policy = fixed_window(3, 10)

    assert [limiter.check("user", policy).allowed for _ in range(3)] == [True] * 3
    blocked = limiter.check("user", policy)
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after == 10

    clock.advance(seconds=10)
    renewed = limiter.check("user", policy)
    assert renewed.allowed is True
    assert renewed.remaining == 2


def test_fixed_window_supports_weighted_cost() -> None:
    limiter = RateLimiter(InMemoryBackend(), clock=ManualClock())
    policy = fixed_window(5, 60)
    assert limiter.check("tenant", policy, cost=3).allowed
    rejected = limiter.check("tenant", policy, cost=3)
    assert not rejected.allowed
    assert rejected.current == 3
