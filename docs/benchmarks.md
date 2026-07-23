# Benchmark results

> These numbers describe one machine and one revision. Re-run the benchmark
> before placing them on a resume or comparing implementations.

## Environment

- **Python:** 3.13.5
- **Platform:** Linux-6.12.13-x86_64-with-glibc2.41
- **Processor:** not reported
- **Revision:** local working tree
- **Keyspace:** 1,000

## Results

| Backend | Algorithm | Workers | Operations | Ops/sec | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| in-memory | fixed_window | 1 | 100,000 | 254,834 | 3.35 µs | 5.49 µs | 6.48 µs |
| in-memory | sliding_window | 1 | 100,000 | 234,439 | 3.63 µs | 5.90 µs | 6.79 µs |
| in-memory | token_bucket | 1 | 100,000 | 259,673 | 3.54 µs | 3.75 µs | 5.20 µs |

## Reproduce

```bash
python scripts/benchmark.py --operations 100000 --workers 1 --output docs/benchmarks.md
python scripts/benchmark.py --operations 50000 --workers 16 --redis-url redis://localhost:6379/0
```

The Redis result includes local network/client overhead. Production latency depends
on deployment topology, persistence, TLS, Redis configuration, and contention.
