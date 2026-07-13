import pytest
from unittest.mock import patch
from celery.exceptions import Retry, MaxRetriesExceededError
import redis
from notifications.models import FailedJob
from notifications.tasks import send_transactional_email, EmailProviderError


@pytest.fixture(autouse=True)
def clear_dlq(db):
    FailedJob.objects.all().delete()


def test_sends_when_allowed(db):
    """Test email is sent when rate limit allows."""
    payload = {"to": "user@example.com", "body": "hello"}

    with patch("notifications.rate_limiter.allow", return_value=True), \
         patch("notifications.tasks.send_email_via_provider") as mock_send:
        send_transactional_email.apply(args=[payload]).get()
        mock_send.assert_called_once_with(payload)


def test_retries_when_rate_limited(db):
    """Test task retries when rate limited."""
    with patch("notifications.rate_limiter.allow", return_value=False), \
         patch.object(send_transactional_email, "retry", side_effect=Retry()):
        with pytest.raises(Retry):
            send_transactional_email({"to": "a@b.com"})


def test_retries_when_redis_down(db):
    """Test task retries (fail-closed) on Redis connection error."""
    with patch("notifications.rate_limiter.allow", side_effect=redis.exceptions.ConnectionError), \
         patch.object(send_transactional_email, "retry", side_effect=Retry()):
        with pytest.raises(Retry):
            send_transactional_email({"to": "a@b.com"})


def test_retries_when_provider_fails(db):
    """Test task retries on email provider failure."""
    with patch("notifications.rate_limiter.allow", return_value=True), \
         patch.object(send_transactional_email, "retry", side_effect=Retry()):
        with pytest.raises(Retry):
            send_transactional_email({"simulate_failure": True})


def test_dlq_on_max_retries(db):
    """Test task is saved to FailedJob DLQ after max retries."""
    payload = {"to": "a@b.com", "simulate_failure": True}

    with patch("notifications.rate_limiter.allow", return_value=True), \
         patch.object(send_transactional_email, "retry",
                      side_effect=MaxRetriesExceededError("exhausted")):
        with pytest.raises(MaxRetriesExceededError):
            send_transactional_email(payload)

    assert FailedJob.objects.count() == 1
    job = FailedJob.objects.first()
    assert job.payload == payload
    assert "Retries exhausted" in job.error_message
