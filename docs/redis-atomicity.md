# Redis atomicity and the check-then-increment race

## Unsafe sequence

Assume a limit of five and a stored count of four:

```text
Worker A: GET count → 4
Worker B: GET count → 4
Worker A: 4 < 5, INCR → 5, allow
Worker B: 4 < 5, INCR → 6, allow
```

The individual Redis commands are atomic. The multi-command business decision
is not.

## LimitForge sequence

Each algorithm runs as one Lua script:

```text
EVALSHA script key limit window timestamp cost
```

The script reads state, calculates the decision, mutates accepted state, applies
TTL, and returns all headers in one server-side operation. Redis does not
interleave another client's command during script execution.

## Why not use a Python lock?

A `threading.Lock` protects one Python process only. It does not coordinate:

- multiple Gunicorn workers;
- multiple containers;
- multiple hosts;
- separate services sharing one quota.

A distributed lock could coordinate them, but it adds lock acquisition and
release complexity. The short Lua operation directly makes the state transition
atomic without a separate lock lifecycle.

## Script constraints

Redis scripts block other Redis work while running. LimitForge scripts therefore:

- perform a bounded number of O(1) commands;
- avoid loops over user-controlled collections;
- avoid network access;
- set expiry in the same atomic operation;
- use one state key per decision.

## Redis Cluster

Current scripts use one key per invocation and are naturally located in one hash
slot. Future algorithms that touch multiple keys must use a shared hash tag or a
different design. Do not assume a script can atomically access arbitrary keys
across Redis Cluster slots.

## How atomicity is tested

The integration suite starts with an empty Redis database, launches 1,000 checks
for the same key from a thread pool, and asserts that exactly the configured 100
are accepted. A sequential test would not expose the race.
