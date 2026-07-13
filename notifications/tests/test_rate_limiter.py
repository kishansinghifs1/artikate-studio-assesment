import time
import pytest
import redis
from unittest.mock import patch
from django.conf import settings
from notifications import rate_limiter


@pytest.fixture(autouse=True)
def clear_redis():
    """Clears the test Redis key before and after each test."""
    client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    client.delete("test_limiter_key")
    yield
    client.delete("test_limiter_key")


def test_allows_up_to_limit_then_blocks(db):
    """3 allowed, 4th blocked."""
    key = "test_limiter_key"
    assert rate_limiter.allow(key, limit=3, window_ms=5000) is True
    assert rate_limiter.allow(key, limit=3, window_ms=5000) is True
    assert rate_limiter.allow(key, limit=3, window_ms=5000) is True
    assert rate_limiter.allow(key, limit=3, window_ms=5000) is False


def test_sliding_window_resets(db):
    """After the window elapses, requests are allowed again."""
    key = "test_limiter_key"
    assert rate_limiter.allow(key, limit=2, window_ms=1000) is True
    assert rate_limiter.allow(key, limit=2, window_ms=1000) is True
    assert rate_limiter.allow(key, limit=2, window_ms=1000) is False

    time.sleep(1.1)  # wait for window to slide

    assert rate_limiter.allow(key, limit=2, window_ms=1000) is True


def test_raises_on_redis_failure(db):
    """Test task retries (fail-closed) on Redis connection error."""
    with patch(
        "redis.client.Script.__call__",
        side_effect=redis.exceptions.ConnectionError("down"),
    ):
        with pytest.raises(redis.exceptions.RedisError):
            rate_limiter.allow("test_limiter_key", limit=5, window_ms=1000)
