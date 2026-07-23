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
| in-memory | fixed_window | 16 | 50,000 | 70,504 | 3.50 µs | 4.15 µs | 6.72 µs |
| in-memory | sliding_window | 16 | 50,000 | 72,619 | 3.80 µs | 4.63 µs | 13.00 µs |
| in-memory | token_bucket | 16 | 50,000 | 66,653 | 3.77 µs | 5.42 µs | 13.00 µs |

## Reproduce

```bash
python scripts/benchmark.py --operations 100000 --workers 1 --output docs/benchmarks.md
python scripts/benchmark.py --operations 50000 --workers 16 --redis-url redis://localhost:6379/0
```

The Redis result includes local network/client overhead. Production latency depends
on deployment topology, persistence, TLS, Redis configuration, and contention.
