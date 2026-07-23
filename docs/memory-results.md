# In-memory state measurement

> Measured with Python `tracemalloc`; this is interpreter- and workload-specific.

- Python: 3.13.5
- Platform: Linux-6.12.13-x86_64-with-glibc2.41
- Unique keys per algorithm: 20,000

| Algorithm | Incremental bytes | Approx. bytes/key |
|---|---:|---:|
| fixed_window | 3,004,722 | 150.2 |
| sliding_window | 3,244,818 | 162.2 |
| token_bucket | 3,644,746 | 182.2 |

The number includes Python dictionaries, strings, and state objects created during
the measurement. It does not represent Redis memory usage.
