"""Distributed Redis backend powered by atomic Lua scripts."""

from __future__ import annotations

from importlib.resources import files
from typing import Any, Callable, cast

from ..exceptions import BackendUnavailable
from .base import BackendDecision


class RedisBackend:
    """Redis-backed rate-limit state shared across processes and machines.

    The constructor accepts any redis-py compatible client exposing
    ``register_script``, ``delete``, and ``ping``. Use :meth:`from_url` for the
    normal redis-py setup.
    """

    def __init__(self, client: Any, *, key_prefix: str = "limitforge") -> None:
        if not key_prefix or ":" in key_prefix:
            raise ValueError("key_prefix must be non-empty and cannot contain ':'")
        self.client = client
        self.key_prefix = key_prefix
        self._fixed_script = self._register("fixed_window.lua")
        self._sliding_script = self._register("sliding_window.lua")
        self._token_script = self._register("token_bucket.lua")

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        key_prefix: str = "limitforge",
        socket_timeout: float = 1.0,
        socket_connect_timeout: float = 1.0,
        **kwargs: Any,
    ) -> "RedisBackend":
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ImportError(
                "Redis support requires `pip install limitforge[redis]`"
            ) from exc

        client = redis.Redis.from_url(
            url,
            decode_responses=False,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            **kwargs,
        )
        return cls(client, key_prefix=key_prefix)

    def _register(self, filename: str) -> Callable[..., list[Any]]:
        script_path = files("limitforge.backends.lua").joinpath(filename)
        source = script_path.read_text(encoding="utf-8")
        registered = self.client.register_script(source)
        return cast(Callable[..., list[Any]], registered)

    def _key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def fixed_window(
        self, *, key: str, limit: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision:
        raw = self._execute(
            self._fixed_script,
            key=key,
            args=[limit, window_ms, cost],
            scaled_current=False,
        )
        return raw

    def sliding_window(
        self, *, key: str, limit: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision:
        return self._execute(
            self._sliding_script,
            key=key,
            args=[limit, window_ms, now_ms, cost],
            scaled_current=True,
        )

    def token_bucket(
        self, *, key: str, capacity: int, window_ms: int, now_ms: int, cost: int
    ) -> BackendDecision:
        return self._execute(
            self._token_script,
            key=key,
            args=[capacity, window_ms, now_ms, cost],
            scaled_current=True,
        )

    def _execute(
        self,
        script: Callable[..., Any],
        *,
        key: str,
        args: list[int],
        scaled_current: bool,
    ) -> BackendDecision:
        try:
            values = script(keys=[self._key(key)], args=args)
        except Exception as exc:  # redis exceptions are optional at import time
            raise BackendUnavailable(f"Redis rate-limit operation failed: {exc}") from exc
        if not isinstance(values, (list, tuple)) or len(values) != 5:
            raise BackendUnavailable(f"unexpected Redis script response: {values!r}")
        current = float(values[4]) / 1000 if scaled_current else float(values[4])
        return BackendDecision(
            allowed=bool(int(values[0])),
            remaining=max(0, int(values[1])),
            retry_after_ms=max(0, int(values[2])),
            reset_after_ms=max(0, int(values[3])),
            current=current,
        )

    def reset(self, key: str) -> None:
        try:
            self.client.delete(self._key(key))
        except Exception as exc:
            raise BackendUnavailable(f"Redis reset failed: {exc}") from exc

    def healthcheck(self) -> bool:
        try:
            return bool(self.client.ping())
        except Exception:
            return False
