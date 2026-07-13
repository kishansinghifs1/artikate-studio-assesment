import time
import redis
from django.conf import settings

_redis = redis.Redis.from_url(settings.CELERY_BROKER_URL)

# Lua script ensures strict atomicity (no race conditions)
# It is loaded onto the Redis server once and cached.
_lua_rate_limit = _redis.register_script("""
    local key = KEYS[1]
    local window_start = tonumber(ARGV[1])
    local now_ms = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])

    -- Clean old entries
    redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
    
    -- Count remaining
    local current_count = redis.call('ZCARD', key)

    -- Conditionally insert
    if current_count < limit then
        redis.call('ZADD', key, now_ms, now_ms .. ':' .. current_count)
        redis.call('PEXPIRE', key, tonumber(ARGV[4]))
        return 1
    end
    return 0
""")

def allow(key: str, limit: int, window_ms: int) -> bool:
    """
    Sliding-window rate limiter using a Redis sorted set.

    Returns True if allowed, False if throttled.
    Raises redis.exceptions.RedisError if Redis is down (fail-closed).
    """
    now_ms = int(time.time() * 1000)
    window_start = now_ms - window_ms

    return bool(_lua_rate_limit(
        keys=[key],
        args=[window_start, now_ms, limit, window_ms]
    ))
