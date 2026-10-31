"""Prometheus metrics registry and definitions for Developers Code Pulse (DCP)."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# 1. HTTP Request Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "dcp_http_requests_total",
    "Total count of HTTP requests processed by DCP API",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "dcp_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# 2. Backing Infrastructure Health
DB_CONNECTION_STATUS = Gauge(
    "dcp_db_connection_status",
    "PostgreSQL database connectivity status (1 = connected, 0 = disconnected)",
)

REDIS_CONNECTION_STATUS = Gauge(
    "dcp_redis_connection_status",
    "Redis cache and broker connectivity status (1 = connected, 0 = disconnected)",
)

# 3. Background Task Processing
CELERY_TASKS_TOTAL = Counter(
    "dcp_celery_tasks_total",
    "Total count of Celery worker task executions",
    ["task_name", "status"],
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "dcp_celery_task_duration_seconds",
    "Celery task execution duration in seconds",
    ["task_name"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

# 4. Domain & Analytics Telemetry
REPORT_GENERATION_DURATION_SECONDS = Histogram(
    "dcp_report_generation_duration_seconds",
    "Duration of report generation and PDF compilation in seconds",
    ["report_type"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 45.0, 90.0),
)

WEBHOOK_INGESTIONS_TOTAL = Counter(
    "dcp_webhook_ingestions_total",
    "Total GitHub webhook events processed by the ingestion engine",
    ["event_type", "status"],
)

BOTTLENECKS_DETECTED_TOTAL = Counter(
    "dcp_bottlenecks_detected_total",
    "Total workflow bottlenecks identified by the detection engine",
    ["severity", "bottleneck_type"],
)


def get_metrics_response() -> Response:
    """Renders all registered Prometheus metrics in official exposition format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


async def prometheus_metrics_middleware(request: Request, call_next: Callable) -> Response:
    """
    HTTP middleware measuring request count and execution latency.
    Excludes the /metrics endpoint itself from request counts to avoid recursion.
    """
    path = request.url.path
    if path == "/metrics":
        return await call_next(request)

    # Sanitize high-cardinality paths (e.g. replace UUIDs with :id)
    sanitized_path = _sanitize_path(path)
    method = request.method
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
    except Exception:
        status_code = "500"
        raise
    finally:
        duration = time.perf_counter() - start_time
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=sanitized_path,
            status_code=status_code,
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            endpoint=sanitized_path,
        ).observe(duration)

    return response


def _sanitize_path(path: str) -> str:
    """Replaces UUIDs and raw IDs in URL paths with generic parameters to prevent label explosion."""
    parts = path.split("/")
    sanitized_parts = []
    for part in parts:
        # Check if segment resembles a UUID (36 chars with dashes) or integer ID
        if (len(part) == 36 and part.count("-") == 4) or part.isdigit():
            sanitized_parts.append(":id")
        else:
            sanitized_parts.append(part)
    return "/".join(sanitized_parts)
