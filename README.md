# LimitForge

[![CI](https://github.com/Jyotier2006/limitforge/actions/workflows/ci.yml/badge.svg)](https://github.com/Jyotier2006/limitforge/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-py.typed-informational)](src/limitforge/py.typed)

**Pluggable, concurrency-safe rate limiting for Python and Django.**

LimitForge implements fixed-window, sliding-window-counter, and token-bucket
policies over two interchangeable storage backends:

- a zero-dependency, thread-safe in-memory backend for one process;
- a Redis backend whose check-and-update operations execute atomically in Lua.

The project is deliberately built around the failure mode that makes a rate
limiter non-trivial: a distributed check followed by a separate increment is
not atomic. Two application workers can observe the same remaining quota and
both accept a request. LimitForge moves the decision and mutation into one
Redis script, preventing that race.

> **Project status:** `0.1.0` is an alpha-quality educational release. The core
> algorithms and concurrency paths are tested, but adopters should validate
> policy behavior and failure strategy for their own production workload.

## Why this project is technically meaningful

A rate limiter is easy to sketch and surprisingly easy to implement
incorrectly. LimitForge demonstrates:

1. **Algorithm trade-offs:** three policies with different accuracy, memory,
   and burst behavior.
2. **Backend abstraction:** the public limiter is independent of whether state
   lives in Python memory or Redis.
3. **Distributed correctness:** Redis Lua scripts combine read, decision,
   mutation, and expiry into one atomic operation.
4. **Framework integration:** drop-in Django middleware and a per-view
   decorator.
5. **Evidence:** deterministic tests, concurrency tests, reproducible latency
   benchmarks, memory-per-key measurements, and a CI Redis integration suite.

## Algorithm comparison

| Algorithm | State per key | Boundary behavior | Burst behavior | Best fit |
|---|---|---|---|---|
| Fixed window | Counter + expiry | Can allow nearly `2 × limit` around a window boundary | High boundary burst | Simple quotas, low memory |
| Sliding-window counter | Current + previous counter + timestamp | Smooths the fixed-window boundary using a weighted estimate | Moderate | General API throttling |
| Token bucket | Token balance + refill timestamp | Continuous refill | Explicit burst up to bucket capacity | APIs that should tolerate short bursts |

All three execute in **O(1)** state operations per decision. See
[`docs/algorithms.md`](docs/algorithms.md) for examples and limitations.

## Installation

### Core, in-memory only

```bash
pip install limitforge
```

### Redis support

```bash
pip install "limitforge[redis]"
```

### Django support

```bash
pip install "limitforge[django]"
```

### From the repository before the first PyPI release

```bash
pip install "git+https://github.com/Jyotier2006/limitforge.git"
```

## Quick start

### Sliding-window rate limiter

```python
from limitforge import RateLimiter, sliding_window

limiter = RateLimiter()
policy = sliding_window(
    limit=100,
    window_seconds=60,
    namespace="public-api",
)

result = limiter.check("user:42", policy)

if result.allowed:
    handle_request()
else:
    print(f"Retry after {result.retry_after:.3f} seconds")
```

Each check returns a structured decision:

```python
RateLimitResult(
    allowed=True,
    limit=100,
    remaining=99,
    retry_after=0.0,
    reset_after=41.732,
    current=1.0,
    algorithm=Algorithm.SLIDING_WINDOW,
    key="user:42",
)
```

### Token bucket with weighted requests

Use `cost` when operations consume unequal capacity:

```python
from limitforge import RateLimiter, token_bucket

limiter = RateLimiter()
policy = token_bucket(
    capacity=1_000,
    refill_seconds=60,
    namespace="llm-token-budget",
)

# One request consumes 120 budget units.
decision = limiter.check("tenant:acme", policy, cost=120)
```

### Function decorator

```python
from limitforge import RateLimiter, fixed_window

limiter = RateLimiter()

@limiter.decorator(
    fixed_window(5, 60, namespace="email-provider"),
    key=lambda recipient: f"recipient:{recipient}",
)
def send_email(recipient: str) -> None:
    ...
```

Rejected calls raise `RateLimitExceeded`. Both synchronous and asynchronous
functions are supported. Client-side throttling may use `wait=True`; server
request paths should normally reject immediately.

## Distributed Redis backend

```python
from limitforge import RateLimiter, RedisBackend, sliding_window

backend = RedisBackend.from_url(
    "redis://localhost:6379/0",
    key_prefix="my-service",
)
limiter = RateLimiter(backend)
policy = sliding_window(100, 60, namespace="search")

result = limiter.check("user:42", policy)
```

### The race that Lua fixes

This implementation is unsafe:

```python
used = int(redis.get(key) or 0)   # worker A reads 4; worker B reads 4
if used < 5:
    redis.incr(key)               # both increment and both allow
    return True
```

LimitForge sends the complete operation to Redis:

```text
read state → calculate allowance → update state → set expiry → return decision
```

Redis executes each Lua script atomically, so another client cannot interleave a
command between those steps. The scripts are intentionally small and bounded;
see [`docs/redis-atomicity.md`](docs/redis-atomicity.md).

## Django middleware

Add the middleware after authentication middleware if limits should use the
logged-in user ID:

```python
MIDDLEWARE = [
    # ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "limitforge.django.RateLimitMiddleware",
]
```

Configure a default policy and endpoint-specific overrides:

```python
LIMITFORGE = {
    "BACKEND": {
        "type": "redis",
        "url": "redis://localhost:6379/0",
        "key_prefix": "shop-api",
    },
    "DEFAULT": {
        "algorithm": "sliding_window",
        "limit": 120,
        "window_seconds": 60,
    },
    "RULES": [
        {
            "name": "login",
            "pattern": r"^/api/login/$",
            "methods": ["POST"],
            "algorithm": "fixed_window",
            "limit": 5,
            "window_seconds": 60,
        },
        {
            "name": "expensive-search",
            "pattern": r"^/api/search/",
            "algorithm": "token_bucket",
            "limit": 20,
            "window_seconds": 60,
        },
    ],
    "EXEMPT_PATHS": ["/health/", "/metrics/"],
    "FAIL_OPEN": False,
    "INCLUDE_PATH_IN_KEY": True,
    "TRUSTED_PROXY_DEPTH": 0,
}
```

A rejected request receives HTTP `429` plus `Retry-After`,
`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and
`X-RateLimit-Policy` headers.

Read [`docs/django.md`](docs/django.md) before trusting forwarded client IPs.

## Benchmarks

The included benchmark records throughput and per-operation p50/p95/p99 latency.
On the repository build environment (Python 3.13.5, Linux x86-64, 1,000-key
workload, 100,000 sequential operations), the in-memory backend measured:

| Algorithm | Ops/sec | p99 overhead |
|---|---:|---:|
| Fixed window | 254,834 | 6.48 µs |
| Sliding-window counter | 234,439 | 6.79 µs |
| Token bucket | 259,673 | 5.20 µs |

These numbers are **not universal performance claims**. They represent one
machine and one working tree. Redis was unavailable in the build environment,
so no Redis number is invented. Run the supplied command against your local
Redis and commit the generated result before using Redis performance in a
resume.

```bash
python scripts/benchmark.py \
  --operations 100000 \
  --workers 1 \
  --output docs/benchmarks.md

python scripts/benchmark.py \
  --operations 50000 \
  --workers 16 \
  --redis-url redis://localhost:6379/0 \
  --output docs/benchmarks-redis.md
```

Full results:

- [`docs/benchmarks.md`](docs/benchmarks.md)
- [`docs/benchmarks-concurrent.md`](docs/benchmarks-concurrent.md)
- [`docs/memory-results.md`](docs/memory-results.md)
- [`docs/benchmarking.md`](docs/benchmarking.md)

## Testing

```bash
python -m pip install -e ".[dev]"
pytest -q --cov=limitforge --cov-report=term-missing
```

Start Redis and run the integration suite:

```bash
docker compose up -d redis
LIMITFORGE_REDIS_URL=redis://localhost:6379/15 pytest -q tests/integration
```

The concurrency test submits 500 attempts for one key from 32 threads and
asserts that exactly 50 are accepted. CI also runs the same atomicity property
through Redis with 1,000 concurrent attempts.

## Architecture

```text
Application / Django middleware / decorator
                    │
                    ▼
               RateLimiter
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
 InMemoryBackend           RedisBackend
 striped locks             atomic Lua scripts
        │                       │
        └──── algorithm-level atomic contract ────┘
```

A crucial design choice is that the backend interface exposes **atomic
algorithm operations**, not generic `get`, `set`, and `increment` methods. A
low-level storage abstraction would force the limiter to perform unsafe
client-side read/modify/write sequences.

See [`docs/architecture.md`](docs/architecture.md) and
[`docs/design-decisions.md`](docs/design-decisions.md).

## Repository layout

```text
limitforge/
├── src/limitforge/
│   ├── backends/
│   │   ├── memory.py
│   │   ├── redis.py
│   │   └── lua/
│   ├── django/
│   ├── limiter.py
│   └── models.py
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/
│   ├── benchmark.py
│   └── memory_benchmark.py
├── docs/
├── examples/django_demo/
├── pyproject.toml
└── docker-compose.yml
```

## Failure behavior

A Redis outage forces a product decision:

- **Fail closed:** reject when the limiter cannot verify quota. Appropriate for
  login, password reset, costly operations, or abuse-sensitive endpoints.
- **Fail open:** allow traffic to preserve availability. Appropriate only when
  the downstream service can tolerate the risk.

`RateLimiter(..., fail_open=False)` is the default. Choose explicitly; do not
hide the trade-off.

## Publishing

The repository contains:

- source-distribution and wheel configuration through `pyproject.toml`;
- `twine check` instructions;
- a TestPyPI verification flow;
- GitHub Actions trusted publishing without a long-lived PyPI API token.

Follow [`docs/publishing.md`](docs/publishing.md). Confirm the distribution name
is still available immediately before first publication; availability is not a
reservation.

## Interview discussion guide

Be ready to defend:

- why the backend abstraction is algorithm-level;
- how fixed-window boundary bursts happen;
- why the sliding-window counter is approximate;
- why Redis Lua fixes check-then-increment races;
- why fail-open and fail-closed are product decisions;
- how key cardinality affects memory;
- how to test atomicity rather than merely test sequential limits;
- how Redis Cluster hash slots affect multi-key scripts;
- what the benchmark includes and does not prove.

A structured answer is available in
[`docs/interview-guide.md`](docs/interview-guide.md).

## Roadmap

- Prometheus metrics callback interface
- Native ASGI middleware
- Redis Cluster operational guide
- Hierarchical per-user and per-tenant quotas
- Optional sliding-window log for exact request timestamps
- Property-based tests for clock boundaries

## License

MIT. See [`LICENSE`](LICENSE).
