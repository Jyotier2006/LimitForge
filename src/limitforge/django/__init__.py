"""Optional Django integration.

Imports are lazy so installing the core package does not require Django.
"""

from __future__ import annotations

from typing import Any

__all__ = ["RateLimitMiddleware", "client_ip", "rate_limit_view", "user_or_ip"]


def __getattr__(name: str) -> Any:
    if name in {"client_ip", "user_or_ip"}:
        from .keys import client_ip, user_or_ip

        return {"client_ip": client_ip, "user_or_ip": user_or_ip}[name]
    if name == "RateLimitMiddleware":
        try:
            from .middleware import RateLimitMiddleware
        except ImportError as exc:
            raise ImportError(
                "Django integration requires `pip install limitforge[django]`"
            ) from exc
        return RateLimitMiddleware
    if name == "rate_limit_view":
        try:
            from .decorators import rate_limit_view
        except ImportError as exc:
            raise ImportError(
                "Django integration requires `pip install limitforge[django]`"
            ) from exc
        return rate_limit_view
    raise AttributeError(name)
