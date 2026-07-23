from limitforge.backends import InMemoryBackend


def test_prune_removes_idle_keys() -> None:
    backend = InMemoryBackend(idle_ttl_seconds=1, cleanup_interval=100)
    backend.fixed_window(key="a", limit=1, window_ms=1000, now_ms=0, cost=1)
    backend.token_bucket(key="b", capacity=1, window_ms=1000, now_ms=0, cost=1)
    assert backend.tracked_keys() == 2
    assert backend.prune(now_ms=2000) == 2
    assert backend.tracked_keys() == 0


def test_approximate_memory_is_observable() -> None:
    backend = InMemoryBackend()
    empty = backend.approximate_memory_bytes()
    backend.fixed_window(key="key", limit=1, window_ms=1000, now_ms=0, cost=1)
    assert backend.approximate_memory_bytes() > empty


def test_constructor_validation_and_health() -> None:
    import pytest

    for kwargs in (
        {"lock_stripes": 0},
        {"cleanup_interval": 0},
        {"idle_ttl_seconds": 0},
    ):
        with pytest.raises(ValueError):
            InMemoryBackend(**kwargs)
    backend = InMemoryBackend()
    assert backend.healthcheck()


def test_reset_deletes_every_algorithm_state() -> None:
    backend = InMemoryBackend()
    backend.fixed_window(key="same", limit=10, window_ms=1000, now_ms=0, cost=1)
    backend.sliding_window(key="same", limit=10, window_ms=1000, now_ms=0, cost=1)
    backend.token_bucket(key="same", capacity=10, window_ms=1000, now_ms=0, cost=1)
    backend.reset("same")
    assert backend.tracked_keys() == 0


def test_lazy_cleanup_runs_on_configured_interval() -> None:
    backend = InMemoryBackend(cleanup_interval=1, idle_ttl_seconds=1)
    backend.fixed_window(key="old", limit=10, window_ms=1000, now_ms=0, cost=1)
    backend.fixed_window(key="new", limit=10, window_ms=1000, now_ms=2001, cost=1)
    assert backend.tracked_keys() == 1


def test_sliding_window_forgets_usage_after_multiple_windows() -> None:
    backend = InMemoryBackend()
    backend.sliding_window(key="u", limit=2, window_ms=1000, now_ms=0, cost=2)
    result = backend.sliding_window(key="u", limit=2, window_ms=1000, now_ms=3000, cost=2)
    assert result.allowed


def test_backend_cost_validation() -> None:
    import pytest

    backend = InMemoryBackend()
    calls = [
        lambda: backend.fixed_window(key="k", limit=1, window_ms=1, now_ms=0, cost=0),
        lambda: backend.sliding_window(key="k", limit=1, window_ms=1, now_ms=0, cost=True),
        lambda: backend.token_bucket(key="k", capacity=1, window_ms=1, now_ms=0, cost=-1),
    ]
    for call in calls:
        with pytest.raises(ValueError):
            call()
