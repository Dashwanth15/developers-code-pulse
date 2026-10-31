import structlog
from celery import Celery

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

celery_app = Celery(
    "dcp_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=360,  # 6 minutes hard limit
    task_default_queue="webhooks",
    task_routes={
        "app.workers.tasks.ping": {"queue": "webhooks"},
        "app.workers.tasks.diagnostic_health_check": {"queue": "webhooks"},
    },
)

# Automatic task discovery
celery_app.autodiscover_tasks(["app.workers"])
