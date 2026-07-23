import pytest

from limitforge import Algorithm, RateLimit


def test_rate_limit_validation() -> None:
    with pytest.raises(ValueError):
        RateLimit(0, 60)
    with pytest.raises(ValueError):
        RateLimit(10, 0)
    with pytest.raises(ValueError):
        RateLimit(10, 60, namespace="bad:name")


def test_window_conversion() -> None:
    policy = RateLimit(10, 1.25, Algorithm.FIXED_WINDOW)
    assert policy.window_ms == 1250


def test_result_millisecond_properties() -> None:
    from limitforge import RateLimitResult

    result = RateLimitResult(
        allowed=False,
        limit=1,
        remaining=0,
        retry_after=1.2346,
        reset_after=-1,
        current=1,
        algorithm=Algorithm.FIXED_WINDOW,
        key="u",
    )
    assert result.retry_after_ms == 1235
    assert result.reset_after_ms == 0


def test_manual_clock_rejects_negative_advance() -> None:
    from limitforge import ManualClock

    clock = ManualClock()
    with pytest.raises(ValueError):
        clock.advance(milliseconds=-1)
