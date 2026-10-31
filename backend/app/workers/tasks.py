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
