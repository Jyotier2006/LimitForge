# Validation report

Generated for the `0.1.0` repository package on 23 July 2026.

## Completed in this environment

- `36` unit and package-level tests passed.
- `1` Redis integration module was skipped because Redis and redis-py were not
  available in this execution environment.
- Core branch-aware coverage measured `97.99%`; optional Django integration is
  excluded from the coverage threshold.
- Python bytecode compilation passed for source, tests, scripts, and examples.
- The in-memory contention demonstration admitted exactly `100` of `1,000`
  concurrent attempts.
- A wheel was built successfully.
- The built wheel was installed into an isolated target directory.
- The wheel smoke test verified limiting behavior and packaged Lua resources.
- A source distribution was built successfully.
- Sequential and 16-worker in-memory benchmarks were executed and stored under
  `docs/`.
- Memory-per-key measurements were executed with `tracemalloc`.

## Not executable here

This environment did not provide Docker, a Redis server, redis-py, Django,
Ruff, Mypy, Build, or Twine through its package mirror. Therefore:

- the real Redis Lua scripts were not executed locally;
- the Django demo was not started locally;
- Docker Compose was not run;
- Ruff, Mypy, and Twine were not run locally.

The GitHub Actions workflow installs those dependencies, starts Redis as a
service, executes the Redis atomicity suite, performs lint and type checks,
builds both distributions, and runs Twine validation. The first GitHub push
should be considered complete only after that workflow is green.

## Performance evidence

The committed in-memory numbers are actual measurements from this environment.
No Redis throughput or latency number has been fabricated. Generate Redis
results using the supplied benchmark workflow or local Docker command before
using Redis performance in a resume.
