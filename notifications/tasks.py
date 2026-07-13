import logging
import redis
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from . import rate_limiter
from .models import FailedJob

logger = logging.getLogger(__name__)


class EmailProviderError(Exception):
    pass


def send_email_via_provider(payload):
    """Simulate sending an email. Raises on 'simulate_failure' flag."""
    if payload and payload.get("simulate_failure"):
        raise EmailProviderError("Provider returned 503")
    logger.info("Email sent: %s", payload)


@shared_task(bind=True, acks_late=True, max_retries=5)
def send_transactional_email(self, payload):
    """
    Rate-limited email task with exponential backoff and dead-letter queue.
    """
    backoff = 2 ** self.request.retries

    try:
        allowed = rate_limiter.allow("email_send", limit=200, window_ms=60_000)
    except redis.exceptions.RedisError as exc:
        raise self.retry(exc=exc, countdown=backoff)

    if not allowed:
        raise self.retry(countdown=backoff)

    try:
        send_email_via_provider(payload)
    except EmailProviderError as exc:
        try:
            raise self.retry(exc=exc, countdown=backoff)
        except MaxRetriesExceededError:
            FailedJob.objects.create(
                task_id=self.request.id or "unknown",
                task_name=self.name,
                payload=payload,
                error_message=f"Retries exhausted. Last error: {exc}",
            )
            raise
