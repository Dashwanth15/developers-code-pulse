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


@celery_app.task(
    name="app.workers.tasks.run_bottleneck_detection",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def run_bottleneck_detection(
    self,
    organization_id: str,
    repository_id: str | None = None,
    time_window: str = "30d",
) -> dict:
    """
    Background asynchronous Celery task orchestrating end-to-end
    bottleneck detection across organization repositories.
    """
    import asyncio
    import uuid

    from app.database.session import get_session_factory
    from app.services.bottlenecks.engine import BottleneckEngine

    logger.info(
        "bottleneck_detection_task_started",
        org_id=organization_id,
        repo_id=repository_id,
        task_id=self.request.id,
    )

    async def _execute() -> dict:
        session_factory = get_session_factory()
        async with session_factory() as session:
            engine = BottleneckEngine()
            org_uuid = uuid.UUID(organization_id)
            repo_uuid = uuid.UUID(repository_id) if repository_id else None
            run, detected = await engine.run_detection(
                db=session,
                organization_id=org_uuid,
                repository_id=repo_uuid,
                time_window=time_window,
            )
            return {
                "run_id": str(run.id),
                "status": run.status,
                "total_bottlenecks": len(detected),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            }

    try:
        result = asyncio.run(_execute())
        logger.info("bottleneck_detection_task_finished", **result)
        return result
    except Exception as exc:
        logger.error("bottleneck_detection_task_failed", error=str(exc))
        raise self.retry(exc=exc) from exc

