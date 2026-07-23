#!/usr/bin/env python3
"""Reproducible latency and throughput benchmark for LimitForge.

This is intentionally a transparent benchmark rather than a marketing number.
Run it on the same machine before comparing revisions.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from limitforge import RateLimiter, fixed_window, sliding_window, token_bucket
from limitforge.backends import InMemoryBackend, RedisBackend


@dataclass(slots=True)
class BenchmarkResult:
    backend: str
    algorithm: str
    operations: int
    workers: int
    keyspace: int
    elapsed_seconds: float
    ops_per_second: float
    p50_us: float
    p95_us: float
    p99_us: float
    allowed: int


def percentile(values: list[int], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * p)))
    return ordered[index] / 1000


def make_policy(name: str):
    # Deliberately high limits prevent rejection from dominating measurements.
    if name == "fixed_window":
        return fixed_window(1_000_000_000, 60, namespace="bench-fixed")
    if name == "sliding_window":
        return sliding_window(1_000_000_000, 60, namespace="bench-sliding")
    if name == "token_bucket":
        return token_bucket(1_000_000_000, 60, namespace="bench-token")
    raise ValueError(name)


def run_one(
    *,
    backend_name: str,
    backend_factory: Callable[[], object],
    algorithm: str,
    operations: int,
    workers: int,
    keyspace: int,
    warmup: int,
) -> BenchmarkResult:
    backend = backend_factory()
    limiter = RateLimiter(backend)  # type: ignore[arg-type]
    policy = make_policy(algorithm)

    for index in range(warmup):
        limiter.check(f"warmup-{index % keyspace}", policy)

    latencies_ns: list[int] = []

    def perform(index: int) -> bool:
        started = time.perf_counter_ns()
        decision = limiter.check(f"key-{index % keyspace}", policy)
        latencies_ns.append(time.perf_counter_ns() - started)
        return decision.allowed

    started = time.perf_counter()
    if workers == 1:
        allowed = sum(perform(index) for index in range(operations))
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            allowed = sum(pool.map(perform, range(operations), chunksize=100))
    elapsed = time.perf_counter() - started

    return BenchmarkResult(
        backend=backend_name,
        algorithm=algorithm,
        operations=operations,
        workers=workers,
        keyspace=keyspace,
        elapsed_seconds=elapsed,
        ops_per_second=operations / elapsed,
        p50_us=percentile(latencies_ns, 0.50),
        p95_us=percentile(latencies_ns, 0.95),
        p99_us=percentile(latencies_ns, 0.99),
        allowed=allowed,
    )


def markdown(results: list[BenchmarkResult], metadata: dict[str, str]) -> str:
    lines = [
        "# Benchmark results",
        "",
        "> These numbers describe one machine and one revision. Re-run the benchmark",
        "> before placing them on a resume or comparing implementations.",
        "",
        "## Environment",
        "",
    ]
    lines.extend(f"- **{key}:** {value}" for key, value in metadata.items())
    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Backend | Algorithm | Workers | Operations | Ops/sec | p50 | p95 | p99 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in results:
        lines.append(
            f"| {item.backend} | {item.algorithm} | {item.workers} | "
            f"{item.operations:,} | {item.ops_per_second:,.0f} | "
            f"{item.p50_us:.2f} µs | {item.p95_us:.2f} µs | {item.p99_us:.2f} µs |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python scripts/benchmark.py --operations 100000 --workers 1 --output docs/benchmarks.md",
            "python scripts/benchmark.py --operations 50000 --workers 16 --redis-url redis://localhost:6379/0",
            "```",
            "",
            "The Redis result includes local network/client overhead. Production latency depends",
            "on deployment topology, persistence, TLS, Redis configuration, and contention.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operations", type=int, default=100_000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--keyspace", type=int, default=1_000)
    parser.add_argument("--warmup", type=int, default=5_000)
    parser.add_argument("--redis-url", default=os.getenv("LIMITFORGE_REDIS_URL"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if min(args.operations, args.workers, args.keyspace) <= 0 or args.warmup < 0:
        parser.error("operations, workers, and keyspace must be positive")

    backend_factories: list[tuple[str, Callable[[], object]]] = [
        ("in-memory", lambda: InMemoryBackend(cleanup_interval=10**12))
    ]
    if args.redis_url:
        backend_factories.append(
            ("redis", lambda: RedisBackend.from_url(args.redis_url, key_prefix="limitforge-bench"))
        )

    results = [
        run_one(
            backend_name=backend_name,
            backend_factory=factory,
            algorithm=algorithm,
            operations=args.operations,
            workers=args.workers,
            keyspace=args.keyspace,
            warmup=args.warmup,
        )
        for backend_name, factory in backend_factories
        for algorithm in ("fixed_window", "sliding_window", "token_bucket")
    ]
    metadata = {
        "Python": sys.version.split()[0],
        "Platform": platform.platform(),
        "Processor": platform.processor() or "not reported",
        "Revision": os.getenv("GITHUB_SHA", "local working tree"),
        "Keyspace": f"{args.keyspace:,}",
    }

    table = markdown(results, metadata)
    print(table)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(table, encoding="utf-8")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(
                {"metadata": metadata, "results": [asdict(item) for item in results]},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
