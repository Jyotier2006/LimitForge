-- LIMITFORGE_SLIDING_WINDOW_V1
-- KEYS[1] = hash key
-- ARGV = limit, window_ms, now_ms, cost
local limit = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local current_start = math.floor(now_ms / window_ms) * window_ms

local values = redis.call('HMGET', KEYS[1], 'start', 'current', 'previous')
local stored_start = tonumber(values[1])
local current = tonumber(values[2]) or 0
local previous = tonumber(values[3]) or 0

if stored_start == nil then
    stored_start = current_start
    current = 0
    previous = 0
elseif stored_start ~= current_start then
    local windows_passed = math.floor((current_start - stored_start) / window_ms)
    if windows_passed == 1 then
        previous = current
    else
        previous = 0
    end
    current = 0
    stored_start = current_start
end

local elapsed = math.max(0, now_ms - current_start)
local weight = math.max(0, 1 - (elapsed / window_ms))
local estimated_before = previous * weight + current
local allowed = 0
if estimated_before + cost <= limit then
    current = current + cost
    allowed = 1
end
local estimated_after = previous * weight + current

redis.call('HSET', KEYS[1],
    'start', stored_start,
    'current', current,
    'previous', previous
)
redis.call('PEXPIRE', KEYS[1], window_ms * 2)

local remaining = math.max(0, math.floor(limit - estimated_after))
local reset_after = math.max(0, current_start + window_ms - now_ms)
local retry_after = 0
if allowed == 0 then
    if previous <= 0 then
        retry_after = math.max(1, reset_after)
    else
        local target_weight = (limit - current - cost) / previous
        if target_weight < 0 then
            retry_after = math.max(1, reset_after)
        elseif target_weight >= 1 then
            retry_after = 0
        else
            local target_elapsed = math.ceil(window_ms * (1 - target_weight))
            retry_after = math.max(1, target_elapsed - elapsed)
        end
    end
end

-- Scale current by 1000 because Redis integer replies cannot preserve decimals.
return {allowed, remaining, retry_after, reset_after, math.floor(estimated_after * 1000)}
