"""Demonstrate that an in-memory check-and-increment is atomic per process."""

from concurrent.futures import ThreadPoolExecutor

from limitforge import RateLimiter, fixed_window

limiter = RateLimiter()
policy = fixed_window(100, 60, namespace="demo")

with ThreadPoolExecutor(max_workers=40) as pool:
    results = list(pool.map(lambda _: limiter.check("same-key", policy), range(1_000)))

accepted = sum(result.allowed for result in results)
rejected = len(results) - accepted
print(f"accepted={accepted}, rejected={rejected}")
assert accepted == 100
