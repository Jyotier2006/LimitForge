import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from limitforge import RateLimiter, fixed_window, sliding_window, token_bucket
from limitforge.backends import RedisBackend

redis = pytest.importorskip("redis")


@pytest.fixture
def redis_backend():
    url = os.getenv("LIMITFORGE_REDIS_URL", "redis://localhost:6379/15")
    client = redis.Redis.from_url(url)
    try:
        client.ping()
    except redis.RedisError:
        pytest.skip("Redis is not available")
    client.flushdb()
    yield RedisBackend(client, key_prefix="limitforge-test")
    client.flushdb()


def test_redis_fixed_window_is_atomic_under_concurrency(redis_backend) -> None:
    limiter = RateLimiter(redis_backend)
    policy = fixed_window(100, 60, namespace="atomic")
    with ThreadPoolExecutor(max_workers=40) as pool:
        results = list(pool.map(lambda _: limiter.check("same", policy).allowed, range(1000)))
    assert sum(results) == 100


@pytest.mark.parametrize(
    "policy",
    [sliding_window(5, 10, namespace="s"), token_bucket(5, 10, namespace="t")],
)
def test_redis_algorithms_enforce_limit(redis_backend, policy) -> None:
    limiter = RateLimiter(redis_backend)
    assert sum(limiter.check("u", policy).allowed for _ in range(20)) == 5
