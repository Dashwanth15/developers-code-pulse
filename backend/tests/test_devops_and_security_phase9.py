"""Phase 9 Automated Tests: Security Hardening, Observability Metrics, Logging, and Worker Reliability."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.logging import mask_sensitive_data_processor
from app.core.metrics import (
    DB_CONNECTION_STATUS,
    HTTP_REQUESTS_TOTAL,
    REDIS_CONNECTION_STATUS,
    get_metrics_response,
)
from app.main import app
from app.workers.celery_app import celery_app


@pytest.mark.asyncio
async def test_security_headers_middleware():
    """Verifies that security headers are attached to API responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        headers = res.headers

        # Verify critical security headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "0"
        assert "Content-Security-Policy" in headers
        assert "frame-ancestors 'none'" in headers.get("Content-Security-Policy")
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_request_size_limit_middleware_rejects_oversized_payloads():
    """Verifies that requests exceeding MAX_REQUEST_BODY_BYTES return HTTP 413."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Simulate payload exceeding 15MB limit via content-length header
        res = await client.post(
            "/api/v1/auth/login",
            content=b"test",
            headers={"content-length": str(20 * 1024 * 1024)},
        )
        assert res.status_code == 413
        data = res.json()
        assert data["code"] == "PAYLOAD_TOO_LARGE"
        assert "maximum permitted size" in data["detail"]


@pytest.mark.asyncio
async def test_rate_limiting_middleware_headers():
    """Verifies that rate limit tracking headers are attached to non-exempt requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        assert "X-RateLimit-Limit" in res.headers
        assert "X-RateLimit-Remaining" in res.headers
        assert int(res.headers["X-RateLimit-Remaining"]) >= 0


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    """Verifies that /metrics endpoint returns valid Prometheus telemetry format."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/metrics")
        assert res.status_code == 200
        content = res.text
        # Assert expected core metrics exist in exposition output
        assert "dcp_http_requests_total" in content
        assert "dcp_http_request_duration_seconds" in content
        assert "dcp_db_connection_status" in content
        assert "dcp_redis_connection_status" in content
        assert "dcp_celery_tasks_total" in content


def test_structured_logging_sensitive_data_masking():
    """Verifies that passwords, tokens, API keys, and secrets are masked in log events."""
    event_dict = {
        "event": "user_authenticated",
        "email": "lead@company.com",
        "password": "super_secret_password_123",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy",
        "refresh_token": "dummy_refresh_token_string",
        "github_token": "ghp_1234567890abcdef",
        "gemini_api_key": "AQ.Ab8RN6JLct-lf6vJWzQE4pNQx",
        "nested": {
            "client_secret": "raw_secret_here",
            "safe_metadata": "12345",
        },
    }

    sanitized = mask_sensitive_data_processor(None, "info", event_dict)

    assert sanitized["email"] == "lead@company.com"
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["access_token"] == "***REDACTED***"
    assert sanitized["refresh_token"] == "***REDACTED***"
    assert sanitized["github_token"] == "***REDACTED***"
    assert sanitized["gemini_api_key"] == "***REDACTED***"
    assert sanitized["nested"]["client_secret"] == "***REDACTED***"
    assert sanitized["nested"]["safe_metadata"] == "12345"


def test_celery_queue_routing_and_reliability_configuration():
    """Verifies Celery production queue isolation and reliability flags."""
    routes = celery_app.conf.task_routes

    # Check queue routing
    assert routes["app.workers.tasks.process_github_webhook"]["queue"] == "webhooks"
    assert routes["app.workers.tasks.sync_github_repository_data"]["queue"] == "repo_sync"
    assert routes["app.workers.tasks.run_bottleneck_detection"]["queue"] == "analytics_calc"
    assert routes["app.workers.tasks.calculate_dora_metrics_snapshot"]["queue"] == "analytics_calc"
    assert routes["app.workers.tasks.generate_report_task"]["queue"] == "report_gen"
    assert routes["app.workers.tasks.process_scheduled_reports_task"]["queue"] == "report_gen"

    # Check reliability flags
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert "process-scheduled-reports-hourly" in celery_app.conf.beat_schedule


def test_direct_prometheus_metrics_registry():
    """Verifies that gauge metrics and counter increments work correctly."""
    DB_CONNECTION_STATUS.set(1)
    REDIS_CONNECTION_STATUS.set(1)
    HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/health", status_code="200").inc()

    res = get_metrics_response()
    assert res.status_code == 200
    assert b"dcp_db_connection_status 1.0" in res.body
    assert b"dcp_redis_connection_status 1.0" in res.body
