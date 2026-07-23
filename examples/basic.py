from limitforge import RateLimiter, sliding_window

limiter = RateLimiter()
policy = sliding_window(3, 10, namespace="example")

for index in range(5):
    result = limiter.check("user:42", policy)
    print(
        index,
        "allowed=" + str(result.allowed),
        "remaining=" + str(result.remaining),
        "retry_after=" + str(result.retry_after),
    )
