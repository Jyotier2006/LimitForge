from concurrent.futures import ThreadPoolExecutor

from limitforge import ManualClock, RateLimiter, fixed_window
from limitforge.backends import InMemoryBackend


def test_in_memory_check_and_increment_is_atomic() -> None:
    limiter = RateLimiter(InMemoryBackend(lock_stripes=64), clock=ManualClock())
    policy = fixed_window(50, 60)

    with ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(lambda _: limiter.check("shared", policy).allowed, range(500)))

    assert sum(results) == 50
