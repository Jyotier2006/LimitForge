# Algorithms

## Fixed window

Split time into aligned windows and count accepted cost inside the current one.

```text
window 0          window 1
|-----------------|-----------------|
             5 requests  5 requests
```

With a limit of five, ten requests can be accepted in a short interval around
the boundary. This is not an implementation bug; it is the algorithm's burst
characteristic.

**Complexity:** O(1)  
**State:** counter plus expiry/start  
**Strength:** simple and memory-efficient  
**Weakness:** boundary burst

## Sliding-window counter

Store the previous and current fixed-window counters. Estimate the rolling usage
by weighting the previous counter according to how far the current window has
progressed:

```text
estimated = previous × (1 - elapsed/window) + current
```

The method smooths the boundary without storing every request timestamp. It is
an approximation: requests within the previous window are assumed to be spread
uniformly for weighting purposes.

**Complexity:** O(1)  
**State:** two counters plus current-window start  
**Strength:** smoother rolling behavior at low memory cost  
**Weakness:** estimated rather than exact

## Token bucket

The bucket starts with `capacity` tokens. Accepted work consumes tokens. Tokens
refill continuously at:

```text
refill rate = capacity / refill interval
```

A full bucket allows a burst up to its capacity. After depletion, future work is
accepted according to the refill rate.

**Complexity:** O(1)  
**State:** floating token balance plus refill timestamp  
**Strength:** explicit and configurable bursts  
**Weakness:** it controls average rate, not a strict rolling-window count

## Weighted cost

All policies accept an integer `cost`. This supports workloads where requests
consume unequal resources, for example one generated report costing ten units
and one metadata read costing one.

## Clock behavior

The in-memory implementation accepts an injected clock for deterministic tests.
The production clock uses Unix time in milliseconds so application processes and
Redis evaluate comparable timestamps. Deployments should keep host clocks
synchronized. The algorithms clamp negative elapsed time to zero, but a severely
moving clock can still distort rate behavior.
