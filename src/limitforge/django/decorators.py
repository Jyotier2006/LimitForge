"""Per-view Django decorator."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from django.http import JsonResponse

from ..headers import rate_limit_headers
from ..limiter import RateLimiter
from ..models import RateLimit
from .keys import user_or_ip


def rate_limit_view(
    limiter: RateLimiter,
    policy: RateLimit,
    *,
    key_function: Callable[[Any], str] = user_or_ip,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Apply a specific policy to one Django view."""

    def decorate(view: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(view):

            @functools.wraps(view)
            async def async_wrapper(request: Any, *args: Any, **kwargs: Any) -> Any:
                result = limiter.check(key_function(request), policy)
                if not result.allowed:
                    return _rejected(result)
                response = await view(request, *args, **kwargs)
                _headers(response, result)
                return response

            return async_wrapper

        @functools.wraps(view)
        def sync_wrapper(request: Any, *args: Any, **kwargs: Any) -> Any:
            result = limiter.check(key_function(request), policy)
            if not result.allowed:
                return _rejected(result)
            response = view(request, *args, **kwargs)
            _headers(response, result)
            return response

        return sync_wrapper

    return decorate


def _rejected(result: Any) -> JsonResponse:
    response = JsonResponse(
        {"detail": "Rate limit exceeded.", "retry_after": result.retry_after},
        status=429,
    )
    _headers(response, result)
    return response


def _headers(response: Any, result: Any) -> None:
    for name, value in rate_limit_headers(result).items():
        response[name] = value
