#!/usr/bin/env python3
"""Measure approximate incremental in-memory state per tracked key."""

from __future__ import annotations

import argparse
import gc
import platform
import sys
import tracemalloc
from pathlib import Path

from limitforge import ManualClock, RateLimiter, fixed_window, sliding_window, token_bucket
from limitforge.backends import InMemoryBackend


def measure(name: str, keys: int) -> tuple[int, float]:
    backend = InMemoryBackend(cleanup_interval=10**12)
    limiter = RateLimiter(backend, clock=ManualClock())
    policy = {
        "fixed_window": fixed_window(keys + 1, 60, namespace="mem-fixed"),
        "sliding_window": sliding_window(keys + 1, 60, namespace="mem-sliding"),
        "token_bucket": token_bucket(keys + 1, 60, namespace="mem-token"),
    }[name]
    gc.collect()
    tracemalloc.start()
    baseline, _ = tracemalloc.get_traced_memory()
    for index in range(keys):
        limiter.check(f"user-{index}", policy)
    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    incremental = current - baseline
    return incremental, incremental / keys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keys", type=int, default=20_000)
    parser.add_argument("--output", type=Path, default=Path("docs/memory-results.md"))
    args = parser.parse_args()
    if args.keys <= 0:
        parser.error("keys must be positive")

    rows = []
    for name in ("fixed_window", "sliding_window", "token_bucket"):
        total, per_key = measure(name, args.keys)
        rows.append((name, total, per_key))

    lines = [
        "# In-memory state measurement",
        "",
        "> Measured with Python `tracemalloc`; this is interpreter- and workload-specific.",
        "",
        f"- Python: {sys.version.split()[0]}",
        f"- Platform: {platform.platform()}",
        f"- Unique keys per algorithm: {args.keys:,}",
        "",
        "| Algorithm | Incremental bytes | Approx. bytes/key |",
        "|---|---:|---:|",
    ]
    for name, total, per_key in rows:
        lines.append(f"| {name} | {total:,} | {per_key:,.1f} |")
    lines.extend(
        [
            "",
            "The number includes Python dictionaries, strings, and state objects created during",
            "the measurement. It does not represent Redis memory usage.",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
