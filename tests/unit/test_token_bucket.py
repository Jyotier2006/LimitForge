import pytest

from limitforge import ManualClock, RateLimiter, token_bucket
from limitforge.backends import InMemoryBackend


def test_token_bucket_allows_burst_then_refills() -> None:
    clock = ManualClock()
    limiter = RateLimiter(InMemoryBackend(), clock=clock)
    policy = token_bucket(5, 10)  # 0.5 tokens per second

    for _ in range(5):
        assert limiter.check("user", policy).allowed

    blocked = limiter.check("user", policy)
    assert not blocked.allowed
    assert blocked.retry_after == pytest.approx(2.0)

    clock.advance(seconds=2)
    allowed = limiter.check("user", policy)
    assert allowed.allowed
    assert allowed.remaining == 0


def test_token_bucket_cost() -> None:
    limiter = RateLimiter(InMemoryBackend(), clock=ManualClock())
    policy = token_bucket(10, 10)
    assert limiter.check("job", policy, cost=7).allowed
    assert not limiter.check("job", policy, cost=4).allowed
