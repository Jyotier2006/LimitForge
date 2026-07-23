# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
this project uses semantic versioning.

## [Unreleased]

### Planned

- ASGI-native middleware adapter
- Prometheus metrics hooks
- Redis Cluster key-tag guidance

## [0.1.0] - 2026-07-23

### Added

- Fixed-window, sliding-window-counter, and token-bucket algorithms
- Thread-safe in-memory backend with striped locks and lazy cleanup
- Distributed Redis backend with atomic Lua scripts
- Sync and async function decorators
- Django middleware and per-view decorator
- HTTP rate-limit response headers
- Deterministic clocks for testing
- Concurrency, integration, benchmark, and memory-measurement suites
- GitHub Actions CI and trusted PyPI publishing workflow
