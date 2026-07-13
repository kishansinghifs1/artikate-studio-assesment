from django.db import models

class FailedJob(models.Model):
    """
    Dead-Letter Queue (DLQ) model to record background jobs that failed
    permanently after exhausting all retries.
    """
    task_id = models.CharField(max_length=255, unique=True)
    task_name = models.CharField(max_length=255)
    payload = models.JSONField()
    error_message = models.TextField()
    failed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task_name} ({self.task_id}) failed: {self.error_message[:50]}"
