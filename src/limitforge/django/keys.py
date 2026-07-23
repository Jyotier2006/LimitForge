"""Django request identity functions."""

from __future__ import annotations

from typing import Any


def user_or_ip(request: Any, *, trusted_proxy_depth: int = 0) -> str:
    """Prefer an authenticated user ID, otherwise use the client IP.

    ``X-Forwarded-For`` is ignored unless ``trusted_proxy_depth`` is configured.
    Set that value only when your deployment is behind a trusted proxy that
    overwrites, rather than appends untrusted, forwarding headers.
    """

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"user:{getattr(user, 'pk', getattr(user, 'id', str(user)))}"
    return f"ip:{client_ip(request, trusted_proxy_depth=trusted_proxy_depth)}"


def client_ip(request: Any, *, trusted_proxy_depth: int = 0) -> str:
    meta = getattr(request, "META", {})
    if trusted_proxy_depth > 0:
        forwarded = str(meta.get("HTTP_X_FORWARDED_FOR", ""))
        chain = [part.strip() for part in forwarded.split(",") if part.strip()]
        if len(chain) >= trusted_proxy_depth:
            return chain[-trusted_proxy_depth]
    return str(meta.get("REMOTE_ADDR", "unknown"))
