from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Asserts root endpoint returns metadata and status 200."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "Developers Code Pulse"
    assert "health" in data
    assert "ready" in data


@pytest.mark.asyncio
async def test_liveness_health_check(async_client: AsyncClient):
    """Asserts liveness probe returns healthy status."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "Developers Code Pulse"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_both_healthy(async_client: AsyncClient):
    """Asserts readiness probe returns 200 and ready when both Postgres and Redis are healthy."""
    with (
        patch("app.api.v1.endpoints.health.check_db_connectivity", return_value=(True, None)),
        patch("app.api.v1.endpoints.health.check_redis_connectivity", return_value=(True, None)),
    ):
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["dependencies"]["postgres"]["status"] == "healthy"
        assert data["dependencies"]["redis"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_db_unhealthy(async_client: AsyncClient):
    """Asserts readiness probe returns 503 when PostgreSQL fails connectivity check."""
    with (
        patch(
            "app.api.v1.endpoints.health.check_db_connectivity",
            return_value=(False, "Connection refused"),
        ),
        patch("app.api.v1.endpoints.health.check_redis_connectivity", return_value=(True, None)),
    ):
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["postgres"]["status"] == "unhealthy"
        assert data["dependencies"]["postgres"]["error"] == "Connection refused"
        assert data["dependencies"]["redis"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_redis_unhealthy(async_client: AsyncClient):
    """Asserts readiness probe returns 503 when Redis fails connectivity check."""
    with (
        patch("app.api.v1.endpoints.health.check_db_connectivity", return_value=(True, None)),
        patch(
            "app.api.v1.endpoints.health.check_redis_connectivity",
            return_value=(False, "Redis timeout"),
        ),
    ):
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["postgres"]["status"] == "healthy"
        assert data["dependencies"]["redis"]["status"] == "unhealthy"
        assert data["dependencies"]["redis"]["error"] == "Redis timeout"
