# Architecture

## Goals

LimitForge separates four concerns:

1. policy configuration;
2. key identity;
3. atomic state transition;
4. framework-specific request handling.

The core package contains no mandatory third-party runtime dependency.

## Core flow

```text
caller
  │ key + policy + cost
  ▼
RateLimiter.check
  │ validates input and creates a namespaced storage key
  ▼
RateLimitBackend atomic operation
  │
  ├── InMemoryBackend: striped lock + Python state
  └── RedisBackend: one Lua script invocation
  ▼
BackendDecision
  ▼
RateLimitResult
```

## Why the backend API is not CRUD

A tempting interface is:

```python
class Backend:
    def get(key): ...
    def increment(key): ...
    def expire(key): ...
```

That interface cannot guarantee the rate-limit decision is atomic. The
application would read, decide, and update in separate operations. A transaction
might fix one algorithm but leaks Redis-specific behavior into the core.

LimitForge instead defines:

```python
fixed_window(...)
sliding_window(...)
token_bucket(...)
```

Each backend promises that the complete state transition is atomic. The
abstraction is slightly less generic and much more honest.

## In-memory locking

A single global lock would be correct but serialize unrelated users. The
in-memory backend uses lock striping:

```text
hash(storage_key) mod stripe_count → lock
```

Requests for different stripes can proceed simultaneously. Two keys can collide
on one stripe, which reduces throughput but not correctness. A lock per key
would provide finer granularity but requires its own lifecycle management and
can become a memory leak under high key cardinality.

## Cleanup

The in-memory backend records `last_seen_ms` and periodically removes idle state.
Cleanup acquires all stripes before scanning dictionaries. This is intentionally
infrequent: cleanup is maintenance work, not part of every request.

Redis state expires through key TTLs:

- fixed window: one window;
- sliding counter: two windows;
- token bucket: approximately twice the full refill interval.

## Namespacing

Storage keys contain:

```text
policy namespace : algorithm : caller key
```

The Redis backend adds an application prefix. Independent policies therefore do
not accidentally consume one another's quotas.

## Extension points

A new backend must preserve the atomic contract. A new algorithm requires:

1. a policy identity;
2. a backend operation;
3. in-memory state and locking;
4. a Redis script or equivalent atomic primitive;
5. deterministic and concurrent tests;
6. documentation of accuracy, burst, memory, and retry semantics.
