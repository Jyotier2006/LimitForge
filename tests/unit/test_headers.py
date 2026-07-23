from limitforge import ManualClock, RateLimiter, fixed_window, rate_limit_headers


def test_http_headers_include_retry_after_when_blocked() -> None:
    limiter = RateLimiter(clock=ManualClock())
    policy = fixed_window(1, 10)
    limiter.check("u", policy)
    result = limiter.check("u", policy)
    headers = rate_limit_headers(result)
    assert headers["X-RateLimit-Limit"] == "1"
    assert headers["X-RateLimit-Remaining"] == "0"
    assert headers["Retry-After"] == "10"
