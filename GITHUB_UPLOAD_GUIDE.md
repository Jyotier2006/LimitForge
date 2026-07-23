# GitHub upload and launch guide

## 1. Final local verification

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
docker compose up -d redis
make quality
make test-redis
make build
```

The initial commit should contain no generated virtual environment, `.env`,
coverage output, or Redis data.

## 2. Create the repository

Create a public GitHub repository named `limitforge` without generating a README
or license because both already exist here.

```bash
git init
git add .
git commit -m "feat: publish LimitForge rate-limiting library"
git branch -M main
git remote add origin https://github.com/Jyotier2006/limitforge.git
git push -u origin main
```

## 3. Repository metadata

**Description**

```text
Concurrency-safe Python rate limiter with fixed-window, sliding-window, and token-bucket policies over in-memory and atomic Redis backends.
```

**Topics**

```text
python django redis rate-limiter token-bucket sliding-window middleware
concurrency distributed-systems lua pypi low-level-design system-design
```

Enable Issues, private vulnerability reporting, Dependabot alerts, and automatic
security updates.

## 4. Branch protection

Protect `main` with:

- pull request required before merging;
- CI `quality` job required;
- branch must be up to date;
- force pushes and deletion disabled;
- one approval when collaborators join.

For your first solo release, use a feature branch and open a pull request anyway.
It provides visible engineering history.

## 5. First pull requests

Suggested sequence:

```text
PR 1: feat(core): add three rate-limiting algorithms
PR 2: feat(redis): make distributed decisions atomic with Lua
PR 3: feat(django): add middleware and endpoint rules
PR 4: test(concurrency): verify exact admission under contention
PR 5: bench: publish reproducible latency and memory results
```

The prepared repository is already complete, so you can recreate this history
only if you have not pushed yet. Do not manufacture fake dates or contributors.

## 6. Run the Redis benchmark

The packaged benchmark contains actual in-memory results but no invented Redis
number. After installing Docker:

```bash
docker compose up -d redis
python scripts/benchmark.py \
  --operations 100000 \
  --workers 1 \
  --redis-url redis://localhost:6379/0 \
  --output docs/benchmarks-redis.md \
  --json-output docs/benchmarks-redis.json
```

Run a contended case too:

```bash
python scripts/benchmark.py \
  --operations 50000 \
  --workers 16 \
  --keyspace 1 \
  --redis-url redis://localhost:6379/0 \
  --output docs/benchmarks-redis-hot-key.md
```

Commit the machine details and exact command with the result.

## 7. Create evidence for the README

Add terminal captures showing:

1. `36 passed` plus the Redis integration suite;
2. `accepted=100, rejected=900` from the concurrency demo;
3. the benchmark table;
4. Django receiving HTTP 429 and rate-limit headers;
5. the GitHub Actions green build.

Store images under `docs/images/`. Avoid giant screenshots; crop to the evidence.

## 8. TestPyPI and PyPI

Follow `docs/publishing.md`. Do not publish directly to production PyPI before:

- building both wheel and source distribution;
- running `twine check`;
- installing the wheel in a clean environment;
- testing the TestPyPI artifact;
- confirming the distribution name immediately before release.

## 9. Release

```bash
git tag -a v0.1.0 -m "LimitForge 0.1.0"
git push origin v0.1.0
```

Create a GitHub release using the tag. The trusted-publishing workflow runs on a
published release after the PyPI publisher is configured.

## 10. Profile and resume

Pin the repository. Add the PyPI and GitHub links only after they work. Use
measured numbers from your machine, not placeholders or numbers from the build
environment without understanding the setup.
