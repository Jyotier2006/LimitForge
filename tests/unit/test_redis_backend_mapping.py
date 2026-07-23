from limitforge.backends import RedisBackend


class FakeScript:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, *, keys, args):  # type: ignore[no-untyped-def]
        self.calls.append((keys, args))
        return self.response


class FakeClient:
    def __init__(self):
        self.sources = []
        self.scripts = []
        self.deleted = []

    def register_script(self, source: str):
        self.sources.append(source)
        marker = source.splitlines()[0]
        if "FIXED" in marker:
            response = [1, 4, 0, 5000, 1]
        elif "SLIDING" in marker:
            response = [0, 0, 250, 4000, 3750]
        else:
            response = [1, 3, 0, 2000, 2000]
        script = FakeScript(response)
        self.scripts.append(script)
        return script

    def delete(self, key: str) -> None:
        self.deleted.append(key)

    def ping(self) -> bool:
        return True


def test_redis_backend_packages_and_maps_lua_scripts() -> None:
    client = FakeClient()
    backend = RedisBackend(client, key_prefix="test")
    assert len(client.sources) == 3
    assert all("redis.call" in source for source in client.sources)

    fixed = backend.fixed_window(key="k", limit=5, window_ms=5000, now_ms=0, cost=1)
    assert fixed.allowed and fixed.current == 1

    sliding = backend.sliding_window(key="k", limit=5, window_ms=5000, now_ms=1000, cost=1)
    assert not sliding.allowed
    assert sliding.current == 3.75

    token = backend.token_bucket(key="k", capacity=5, window_ms=5000, now_ms=1000, cost=1)
    assert token.allowed
    assert token.current == 2

    backend.reset("k")
    assert client.deleted == ["test:k"]
    assert backend.healthcheck()


class ErrorScript:
    def __call__(self, *, keys, args):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")


class ErrorClient(FakeClient):
    def delete(self, key: str) -> None:
        raise RuntimeError("delete failed")

    def ping(self) -> bool:
        raise RuntimeError("ping failed")


def test_redis_backend_validation_and_failures() -> None:
    import pytest

    from limitforge import BackendUnavailable

    with pytest.raises(ValueError):
        RedisBackend(FakeClient(), key_prefix="bad:prefix")

    backend = RedisBackend(ErrorClient())
    backend._fixed_script = ErrorScript()  # type: ignore[assignment]
    with pytest.raises(BackendUnavailable):
        backend.fixed_window(key="k", limit=1, window_ms=1, now_ms=0, cost=1)
    with pytest.raises(BackendUnavailable):
        backend.reset("k")
    assert not backend.healthcheck()


def test_redis_backend_rejects_malformed_script_response() -> None:
    import pytest

    from limitforge import BackendUnavailable

    backend = RedisBackend(FakeClient())
    backend._fixed_script = FakeScript([1, 2])  # type: ignore[assignment]
    with pytest.raises(BackendUnavailable):
        backend.fixed_window(key="k", limit=1, window_ms=1, now_ms=0, cost=1)


def test_redis_optional_dependency_message() -> None:
    import importlib.util

    import pytest

    if importlib.util.find_spec("redis") is not None:
        pytest.skip("redis is installed")
    with pytest.raises(ImportError, match="limitforge\\[redis\\]"):
        RedisBackend.from_url("redis://localhost")
