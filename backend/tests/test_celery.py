from app.workers.celery_app import celery_app
from app.workers.tasks import diagnostic_health_check, ping


def test_celery_configuration():
    """Asserts Celery application configuration adheres to standards."""
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_serializer == "json"


def test_ping_task_execution():
    """Validates local direct execution of the ping task."""
    result = ping.apply()
    assert result.get() == "pong"


def test_diagnostic_health_check_task():
    """Validates local execution of diagnostic health check task."""
    result = diagnostic_health_check.apply()
    data = result.get()
    assert data["status"] == "healthy"
    assert "executed_at" in data
