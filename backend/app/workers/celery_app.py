"""Celery application configuration with queue isolation, reliability flags, and beat schedules."""

import structlog
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

celery_app = Celery(
    "dcp_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery Reliability & Production Configuration
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
    broker_connection_retry_on_startup=True,
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=360,  # 6 minutes hard limit
    task_default_queue="webhooks",
    task_routes={
        # Webhook Ingestion Queue
        "app.workers.tasks.ping": {"queue": "webhooks"},
        "app.workers.tasks.diagnostic_health_check": {"queue": "webhooks"},
        "app.workers.tasks.process_github_webhook": {"queue": "webhooks"},
        # Repository Synchronization Queue
        "app.workers.tasks.sync_github_repository_data": {"queue": "repo_sync"},
        # Analytics & Bottlenecks Calculation Queue
        "app.workers.tasks.run_bottleneck_detection": {"queue": "analytics_calc"},
        "app.workers.tasks.calculate_dora_metrics_snapshot": {"queue": "analytics_calc"},
        # Reporting Engine & AI Synthesis Queue
        "app.workers.tasks.generate_report_task": {"queue": "report_gen"},
        "app.workers.tasks.process_scheduled_reports_task": {"queue": "report_gen"},
    },
    beat_schedule_filename="storage/celerybeat-schedule",
    beat_schedule={
        # Process scheduled reports every hour
        "process-scheduled-reports-hourly": {
            "task": "app.workers.tasks.process_scheduled_reports_task",
            "schedule": crontab(minute=0),  # Top of every hour
        },
        # Daily diagnostic health ping at midnight UTC
        "daily-worker-health-ping": {
            "task": "app.workers.tasks.diagnostic_health_check",
            "schedule": crontab(minute=0, hour=0),
        },
    },
)

# Automatic task discovery
celery_app.autodiscover_tasks(["app.workers"])
