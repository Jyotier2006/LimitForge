# Benchmark methodology

## What is measured

`scripts/benchmark.py` records elapsed throughput and individual operation
latency around `RateLimiter.check`.

The in-memory result includes:

- key construction;
- clock lookup;
- lock acquisition;
- algorithm calculation;
- state update;
- result-object construction.

The Redis result additionally includes redis-py serialization, local or remote
network round-trip, Redis script execution, and response decoding.

## What is not measured

The benchmark does not prove:

- production HTTP request throughput;
- behavior under a real key distribution;
- Redis persistence or TLS cost unless configured;
- multi-host clock quality;
- long-term memory fragmentation;
- performance against other libraries unless run under identical conditions.

## Recommended benchmark matrix

Run each algorithm with:

1. one worker and one hot key;
2. one worker and 1,000 keys;
3. 16 workers and one hot key;
4. 16 workers and 1,000 keys;
5. in-memory and local Redis;
6. Redis over the same topology used in deployment.

## Resume rules

Only quote a number when:

- the command and environment are committed;
- the result can be reproduced;
- the backend and concurrency level are stated;
- the number is not generalized beyond that setup.

Use “measured” rather than “guarantees.” Do not quote the generated Redis
placeholder until Redis has actually been benchmarked.
