from types import SimpleNamespace

import pytest

from limitforge import Algorithm
from limitforge.django.config import load_config
from limitforge.django.keys import client_ip, user_or_ip


def test_django_config_defaults_and_rule_matching() -> None:
    config = load_config(
        {
            "BACKEND": {"type": "memory"},
            "DEFAULT": {"limit": 10, "window_seconds": 60},
            "RULES": [
                {
                    "name": "login",
                    "pattern": r"^/login/$",
                    "methods": ["POST"],
                    "algorithm": "fixed_window",
                    "limit": 2,
                    "window_seconds": 10,
                }
            ],
        }
    )
    assert config.default_policy.algorithm is Algorithm.SLIDING_WINDOW
    assert config.rules[0].matches("/login/", "POST")
    assert not config.rules[0].matches("/login/", "GET")


def test_django_config_validation() -> None:
    with pytest.raises(ValueError):
        load_config({"BACKEND": {"type": "unknown"}})
    with pytest.raises(ValueError):
        load_config({"TRUSTED_PROXY_DEPTH": -1})
    with pytest.raises(ValueError):
        load_config({"RULES": [{"name": "bad:name"}]})


def test_identity_prefers_user_and_handles_trusted_proxy() -> None:
    authenticated = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=True, pk=42),
        META={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert user_or_ip(authenticated) == "user:42"

    anonymous = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=False),
        META={
            "REMOTE_ADDR": "10.0.0.8",
            "HTTP_X_FORWARDED_FOR": "198.51.100.10, 10.0.0.2",
        },
    )
    assert client_ip(anonymous) == "10.0.0.8"
    assert client_ip(anonymous, trusted_proxy_depth=2) == "198.51.100.10"
    assert user_or_ip(anonymous, trusted_proxy_depth=1) == "ip:10.0.0.2"


def test_lazy_django_import_has_helpful_error_without_extra() -> None:
    import importlib.util

    import limitforge.django as integration

    if importlib.util.find_spec("django") is not None:
        pytest.skip("Django is installed")
    with pytest.raises(ImportError, match="limitforge\\[django\\]"):
        _ = integration.RateLimitMiddleware
    with pytest.raises(AttributeError):
        _ = integration.unknown
