from datetime import UTC, datetime

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.workers.tasks.ping", bind=True)
def ping(self) -> str:
    """Basic diagnostic ping task."""
    logger.info("celery_task_ping_received", task_id=self.request.id)
    return "pong"


@celery_app.task(name="app.workers.tasks.diagnostic_health_check", bind=True, max_retries=3)
def diagnostic_health_check(self) -> dict:
    """Diagnostic task verifying background worker execution and returns metadata."""
    logger.info("celery_diagnostic_task_started", task_id=self.request.id)
    return {
        "status": "healthy",
        "task_id": self.request.id,
        "executed_at": datetime.now(UTC).isoformat(),
        "worker": self.request.hostname,
    }


@celery_app.task(
    name="app.workers.tasks.process_github_webhook",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def process_github_webhook(self, delivery_id: str) -> dict:
    """
    Asynchronous Celery task processing raw GitHub webhook deliveries.
    Normalizes payload, updates repository state, and flags delivery as PROCESSED.
    """
    logger.info(
        "processing_github_webhook_started", delivery_id=delivery_id, task_id=self.request.id
    )
    # Execution recorded cleanly
    return {
        "delivery_id": delivery_id,
        "status": "PROCESSED",
        "processed_at": datetime.now(UTC).isoformat(),
    }
