"""Drop-in Django rate-limiting middleware."""

from __future__ import annotations

import inspect
from typing import Any

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async
from django.conf import settings
from django.http import JsonResponse

from ..backends import InMemoryBackend, RedisBackend
from ..headers import rate_limit_headers
from ..limiter import RateLimiter
from ..models import RateLimit, RateLimitResult
from .config import load_config


class RateLimitMiddleware:
    """Rate-limit Django requests before they reach the selected view."""

    sync_capable = True
    async_capable = True

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response
        self.config = load_config(getattr(settings, "LIMITFORGE", None))
        if self.config.backend_type == "redis":
            backend = RedisBackend.from_url(
                self.config.redis_url, key_prefix=self.config.key_prefix
            )
        else:
            backend = InMemoryBackend()
        self.limiter = RateLimiter(backend, fail_open=self.config.fail_open)
        self._is_async = iscoroutinefunction(get_response)
        if self._is_async:
            markcoroutinefunction(self)

    def __call__(self, request: Any) -> Any:
        if self._is_async:
            return self.__acall__(request)
        decision = self._evaluate(request)
        if decision is not None and not decision.allowed:
            return self._rejected(decision)
        response = self.get_response(request)
        if decision is not None:
            self._apply_headers(response, decision)
        return response

    async def __acall__(self, request: Any) -> Any:
        decision = await sync_to_async(self._evaluate, thread_sensitive=False)(request)
        if decision is not None and not decision.allowed:
            return self._rejected(decision)
        response = await self.get_response(request)
        if decision is not None:
            self._apply_headers(response, decision)
        return response

    def _evaluate(self, request: Any) -> RateLimitResult | None:
        path = str(getattr(request, "path", "/"))
        if any(path.startswith(prefix) for prefix in self.config.exempt_paths):
            return None
        method = str(getattr(request, "method", "GET")).upper()
        policy = self._policy_for(path, method)
        identity = self._identity(request)
        key = f"{method}:{path}:{identity}" if self.config.include_path_in_key else identity
        return self.limiter.check(key, policy)

    def _policy_for(self, path: str, method: str) -> RateLimit:
        for rule in self.config.rules:
            if rule.matches(path, method):
                return rule.policy
        return self.config.default_policy

    def _identity(self, request: Any) -> str:
        function = self.config.key_function
        parameters = inspect.signature(function).parameters
        if "trusted_proxy_depth" in parameters:
            return str(
                function(
                    request, trusted_proxy_depth=self.config.trusted_proxy_depth
                )
            )
        return str(function(request))

    def _rejected(self, result: RateLimitResult) -> JsonResponse:
        response = JsonResponse(
            {
                "detail": "Rate limit exceeded.",
                "retry_after": result.retry_after,
                "algorithm": result.algorithm.value,
            },
            status=429,
        )
        self._apply_headers(response, result)
        return response

    def _apply_headers(self, response: Any, result: RateLimitResult) -> None:
        for name, value in rate_limit_headers(
            result, prefix=self.config.header_prefix
        ).items():
            response[name] = value
