# Interview guide

## 30-second explanation

> LimitForge is a pip-installable rate-limiting library with fixed-window,
> sliding-window-counter, and token-bucket policies. I separated policy logic
> from storage through an atomic backend contract. The in-memory backend uses
> striped locks, while the Redis backend executes read-check-update-expire in a
> Lua script so multiple workers cannot over-admit through a check-then-increment
> race. I added Django middleware, concurrency tests, latency benchmarks, and
> memory-per-key measurements.

## Why not a generic storage interface?

A generic `get` plus `increment` interface is too weak: the limiter could not
promise an atomic decision. The backend owns algorithm-level state transitions,
which makes correctness explicit and testable.

## Why three algorithms?

- Fixed window is simple but has boundary bursts.
- Sliding-window counter smooths boundaries with O(1) state, but is approximate.
- Token bucket permits a configurable burst and enforces an average refill rate.

The point is not quantity; it is being able to select a policy according to
product behavior.

## What race did you fix?

Two application processes can both read “4 of 5 used” and both permit a request
before incrementing. Redis commands are individually atomic, but the decision
spans multiple commands. A Lua script turns the whole transition into one atomic
server-side operation.

## Why Lua instead of a distributed lock?

The operation is short, bounded, and entirely about Redis state. Lua avoids a
separate acquire/lease/release lifecycle and one extra round trip. A distributed
lock would be justified for work that cannot be expressed as a small atomic
state transition.

## What would fail at very high scale?

- hot identities can concentrate load on one Redis shard;
- key cardinality can drive memory;
- a single Redis deployment can become a bottleneck or failure domain;
- clock skew can distort timestamp-based policies;
- cross-region global quotas add latency and consistency trade-offs.

Potential responses include regional quotas, tenant sharding, local token
allocation, hierarchical limits, and bounded-cardinality identity design.

## How did you test correctness?

Deterministic clocks test exact boundaries without sleeping. Thread-pool tests
verify the number accepted under contention. Redis CI performs 1,000 concurrent
checks against one key and asserts the configured limit is never exceeded.

## What do benchmarks prove?

They quantify one implementation on one environment. They help detect
regressions and support transparent resume numbers. They do not prove production
HTTP throughput or universal superiority.

## Strong follow-up improvements

1. Prometheus counters and latency hooks.
2. Native ASGI middleware.
3. Hierarchical tenant plus user quotas.
4. Redis Cluster and multi-region design document.
5. Property-based tests for timing and cost invariants.
