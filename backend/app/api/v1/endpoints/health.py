from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.database.session import check_db_connectivity, check_redis_connectivity
from app.schemas.health import DependencyHealth, HealthResponse, ReadyResponse

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Reports whether the FastAPI HTTP worker process is alive and accepting requests.",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Liveness probe returning application metadata and timestamp."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadyResponse,
            "description": "One or more critical dependencies (PostgreSQL, Redis) are unavailable.",
        }
    },
    summary="Readiness Probe",
    description="Verifies operational readiness by actively pinging PostgreSQL and Redis. Returns 503 if any dependency fails.",
    tags=["System"],
)
async def readiness_check(response: Response) -> ReadyResponse:
    """Readiness probe validating connectivity to PostgreSQL and Redis."""
    db_ok, db_err = await check_db_connectivity()
    redis_ok, redis_err = await check_redis_connectivity()

    dependencies = {
        "postgres": DependencyHealth(
            status="healthy" if db_ok else "unhealthy",
            error=db_err,
        ),
        "redis": DependencyHealth(
            status="healthy" if redis_ok else "unhealthy",
            error=redis_err,
        ),
    }

    all_ready = db_ok and redis_ok

    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning(
            "readiness_probe_failed",
            postgres_healthy=db_ok,
            redis_healthy=redis_ok,
            db_error=db_err,
            redis_error=redis_err,
        )

    return ReadyResponse(
        status="ready" if all_ready else "not_ready",
        dependencies=dependencies,
        timestamp=datetime.now(UTC),
    )
