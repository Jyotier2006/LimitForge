"""Django configuration parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from ..models import Algorithm, RateLimit


@dataclass(frozen=True, slots=True)
class DjangoRule:
    name: str
    pattern: re.Pattern[str]
    methods: frozenset[str]
    policy: RateLimit

    def matches(self, path: str, method: str) -> bool:
        return (not self.methods or method.upper() in self.methods) and bool(
            self.pattern.search(path)
        )


@dataclass(frozen=True, slots=True)
class DjangoConfig:
    backend_type: str
    redis_url: str
    key_prefix: str
    default_policy: RateLimit
    rules: tuple[DjangoRule, ...]
    exempt_paths: tuple[str, ...]
    fail_open: bool
    key_function: Any
    include_path_in_key: bool
    header_prefix: str
    trusted_proxy_depth: int


def load_config(settings_dict: dict[str, Any] | None) -> DjangoConfig:
    raw = settings_dict or {}
    backend = raw.get("BACKEND", {})
    backend_type = str(backend.get("type", "memory")).lower()
    if backend_type not in {"memory", "redis"}:
        raise ValueError("LIMITFORGE BACKEND.type must be 'memory' or 'redis'")

    default_raw = raw.get("DEFAULT", {})
    default_policy = _parse_policy(default_raw, namespace="django-default")
    rules = tuple(
        _parse_rule(index, value) for index, value in enumerate(raw.get("RULES", []))
    )
    proxy_depth = int(raw.get("TRUSTED_PROXY_DEPTH", 0))
    if proxy_depth < 0:
        raise ValueError("TRUSTED_PROXY_DEPTH cannot be negative")

    return DjangoConfig(
        backend_type=backend_type,
        redis_url=str(backend.get("url", "redis://localhost:6379/0")),
        key_prefix=str(backend.get("key_prefix", "limitforge")),
        default_policy=default_policy,
        rules=rules,
        exempt_paths=tuple(str(path) for path in raw.get("EXEMPT_PATHS", ())),
        fail_open=bool(raw.get("FAIL_OPEN", False)),
        key_function=_import_string(
            str(raw.get("KEY_FUNCTION", "limitforge.django.keys.user_or_ip"))
        ),
        include_path_in_key=bool(raw.get("INCLUDE_PATH_IN_KEY", True)),
        header_prefix=str(raw.get("HEADER_PREFIX", "X-RateLimit")),
        trusted_proxy_depth=proxy_depth,
    )


def _parse_rule(index: int, raw: dict[str, Any]) -> DjangoRule:
    name = str(raw.get("name", f"rule-{index}"))
    if not name or ":" in name:
        raise ValueError("rule name must be non-empty and cannot contain ':'")
    pattern = re.compile(str(raw.get("pattern", ".*")))
    methods = frozenset(str(value).upper() for value in raw.get("methods", ()))
    return DjangoRule(
        name=name,
        pattern=pattern,
        methods=methods,
        policy=_parse_policy(raw, namespace=f"django-{name}"),
    )


def _parse_policy(raw: dict[str, Any], *, namespace: str) -> RateLimit:
    algorithm = Algorithm(str(raw.get("algorithm", Algorithm.SLIDING_WINDOW.value)))
    return RateLimit(
        limit=int(raw.get("limit", 100)),
        window_seconds=float(raw.get("window_seconds", 60)),
        algorithm=algorithm,
        namespace=str(raw.get("namespace", namespace)),
    )


def _import_string(path: str) -> Any:
    module_name, separator, attribute = path.rpartition(".")
    if not separator:
        raise ValueError(f"invalid import path: {path!r}")
    module = import_module(module_name)
    return getattr(module, attribute)
