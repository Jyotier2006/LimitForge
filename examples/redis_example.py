import os

from limitforge import RateLimiter, RedisBackend, token_bucket

backend = RedisBackend.from_url(
    os.getenv("LIMITFORGE_REDIS_URL", "redis://localhost:6379/0")
)
limiter = RateLimiter(backend)
policy = token_bucket(20, 60, namespace="uploads")

print(limiter.check("tenant:acme", policy, cost=3))
