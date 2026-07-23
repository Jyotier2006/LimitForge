"""HTTP header helpers independent of any web framework."""

from __future__ import annotations

import math
from collections.abc import Mapping

from .models import RateLimitResult


def rate_limit_headers(
    result: RateLimitResult, *, prefix: str = "X-RateLimit"
) -> Mapping[str, str]:
    headers = {
        f"{prefix}-Limit": str(result.limit),
        f"{prefix}-Remaining": str(result.remaining),
        f"{prefix}-Reset": str(math.ceil(result.reset_after)),
        f"{prefix}-Policy": result.algorithm.value,
    }
    if not result.allowed:
        headers["Retry-After"] = str(max(1, math.ceil(result.retry_after)))
    return headers
