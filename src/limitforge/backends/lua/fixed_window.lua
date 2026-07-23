-- LIMITFORGE_FIXED_WINDOW_V1
-- KEYS[1] = counter key
-- ARGV = limit, window_ms, cost
local limit = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])

local current = tonumber(redis.call('GET', KEYS[1]) or '0')
local ttl = redis.call('PTTL', KEYS[1])
if ttl < 0 then
    ttl = window_ms
end

local allowed = 0
if current + cost <= limit then
    current = redis.call('INCRBY', KEYS[1], cost)
    if current == cost then
        redis.call('PEXPIRE', KEYS[1], window_ms)
        ttl = window_ms
    else
        ttl = redis.call('PTTL', KEYS[1])
    end
    allowed = 1
end

local remaining = math.max(0, limit - current)
local retry_after = 0
if allowed == 0 then
    retry_after = math.max(1, ttl)
end
return {allowed, remaining, retry_after, math.max(0, ttl), current}
