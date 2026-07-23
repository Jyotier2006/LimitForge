# Design decisions

## 1. Algorithm-level backend contract

**Decision:** expose atomic policy operations instead of generic storage CRUD.

**Reason:** correctness is part of the backend contract. Generic CRUD would make
client-side read/modify/write races easy to introduce.

**Trade-off:** adding an algorithm requires changes to the backend protocol and
every backend.

## 2. No mandatory runtime dependencies

**Decision:** the in-memory core installs without Redis or Django.

**Reason:** small applications should not pay dependency cost for integrations
they do not use.

**Trade-off:** optional modules must provide clear errors when extras are absent.

## 3. Integer request cost

**Decision:** cost must be a positive integer.

**Reason:** integer cost gives predictable counters and avoids policy ambiguity.
Token balance remains floating-point internally because refill is continuous.

## 4. Fail closed by default

**Decision:** backend failure raises unless `fail_open=True` is explicit.

**Reason:** silently bypassing a protection mechanism is unsafe for sensitive
routes.

**Trade-off:** strict behavior can reduce service availability during Redis
outages.

## 5. Sliding-window counter, not request log

**Decision:** ship the counter approximation as the default rolling algorithm.

**Reason:** an exact log stores one timestamp per request and requires pruning.
The counter gives O(1) state per identity.

**Trade-off:** estimated usage can differ from an exact rolling count.

## 6. Lock striping

**Decision:** use a fixed set of locks instead of one lock per key.

**Reason:** lock memory remains bounded even under attacker-controlled key
cardinality.

**Trade-off:** unrelated keys occasionally share a lock and serialize briefly.
