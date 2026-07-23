# Django integration

## Middleware order

Place LimitForge after authentication middleware when using the default
`user_or_ip` identity function:

```python
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "limitforge.django.RateLimitMiddleware",
]
```

If it runs before authentication, every request falls back to IP identity.

## Settings reference

```python
LIMITFORGE = {
    "BACKEND": {
        "type": "memory",              # memory | redis
        "url": "redis://localhost:6379/0",
        "key_prefix": "limitforge",
    },
    "DEFAULT": {
        "algorithm": "sliding_window",
        "limit": 100,
        "window_seconds": 60,
        "namespace": "optional-custom-name",
    },
    "RULES": [],
    "EXEMPT_PATHS": ["/health/"],
    "FAIL_OPEN": False,
    "KEY_FUNCTION": "limitforge.django.keys.user_or_ip",
    "INCLUDE_PATH_IN_KEY": True,
    "HEADER_PREFIX": "X-RateLimit",
    "TRUSTED_PROXY_DEPTH": 0,
}
```

Rules are evaluated in order. The first matching path regex and method set wins.
Use a narrow expensive-route rule before a broad API rule.

## Keys and privacy

The default key is either `user:<primary-key>` or `ip:<address>`. Avoid placing
email addresses, API tokens, session IDs, or other secrets in Redis keys. A
one-way HMAC key function can be used when identifiers should not appear in
backend inspection tools.

## Forwarded IP security

An internet client can send an arbitrary `X-Forwarded-For` header. Keep
`TRUSTED_PROXY_DEPTH = 0` unless a controlled reverse proxy overwrites the
header. Configure the depth according to the number of trusted proxy hops from
the application, not by guessing.

## Per-view policy

```python
from limitforge import RateLimiter, fixed_window
from limitforge.django import rate_limit_view

limiter = RateLimiter()

@rate_limit_view(limiter, fixed_window(5, 60, namespace="password-reset"))
def password_reset(request):
    ...
```

## Sync and async views

The middleware supports synchronous and asynchronous Django request handlers.
Backend checks are synchronous; the async middleware offloads the check to a
worker thread so it does not directly block the event loop. A future native
async Redis backend could remove that adapter overhead.
