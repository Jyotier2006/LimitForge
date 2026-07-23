# Resume and interview material

## Project heading

**LimitForge | Python, Django, Redis, Lua** — PyPI · GitHub

## Bullets before Redis benchmarking

- Developed a pip-installable rate-limiting library with fixed-window,
  sliding-window-counter, and token-bucket policies over pluggable thread-safe
  in-memory and distributed Redis backends.
- Eliminated distributed check-then-increment races by executing quota checks,
  state mutation, and expiry atomically in bounded Redis Lua scripts.
- Shipped synchronous and asynchronous decorators, configurable Django
  middleware, deterministic boundary tests, and contention tests validating
  exact admission counts.

## Bullets after measuring your final release

Replace brackets only with reproducible results:

- Benchmarked **[X]k operations/second** at **[Y] µs p99** for the in-memory
  backend and **[Z]k operations/second** at **[W] ms p99** through local Redis;
  maintained **[coverage]%** branch-aware test coverage.

Do not combine sequential and concurrent results in one vague number. State the
backend and workload during the interview.

## Questions to practise

1. Why can two Redis clients exceed a limit even though `INCR` is atomic?
2. Why is your backend interface algorithm-level rather than CRUD-level?
3. How does the sliding-window estimate work?
4. What is the maximum boundary burst for fixed window?
5. Why can token bucket accept a burst without violating its long-term rate?
6. What does fail-open protect, and what does it endanger?
7. How do you stop arbitrary user keys from causing unbounded memory growth?
8. Why use lock striping instead of one lock or one lock per key?
9. What does your p99 benchmark actually include?
10. How would you shard global quotas across regions?

## Honest limitations to volunteer

- In-memory limits are process-local.
- Sliding-window counter is approximate.
- Redis is still an infrastructure dependency and potential bottleneck.
- Wall-clock movement can affect timestamp-based policies.
- The first release has Django integration but no native FastAPI or ASGI package.

A candidate who understands limitations is more credible than one claiming the
library is “production perfect.”
