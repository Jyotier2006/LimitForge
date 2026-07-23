-- LIMITFORGE_TOKEN_BUCKET_V1
-- KEYS[1] = hash key
-- ARGV = capacity, window_ms, now_ms, cost
local capacity = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local refill_per_ms = capacity / window_ms

local values = redis.call('HMGET', KEYS[1], 'tokens', 'last_refill')
local tokens = tonumber(values[1])
local last_refill = tonumber(values[2])
if tokens == nil then
    tokens = capacity
    last_refill = now_ms
end

local elapsed = math.max(0, now_ms - last_refill)
tokens = math.min(capacity, tokens + elapsed * refill_per_ms)
local allowed = 0
if tokens + 0.000000000001 >= cost then
    tokens = tokens - cost
    allowed = 1
end

redis.call('HSET', KEYS[1], 'tokens', tokens, 'last_refill', now_ms)
local idle_ttl = math.max(1000, math.ceil((capacity / refill_per_ms) * 2))
redis.call('PEXPIRE', KEYS[1], idle_ttl)

local remaining = math.max(0, math.floor(tokens))
local retry_after = 0
if allowed == 0 then
    retry_after = math.ceil(math.max(0, cost - tokens) / refill_per_ms)
end
local reset_after = math.ceil(math.max(0, capacity - tokens) / refill_per_ms)
local used = capacity - tokens
return {allowed, remaining, retry_after, reset_after, math.floor(used * 1000)}
