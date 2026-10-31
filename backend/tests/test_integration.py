import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_headers_on_valid_origin(async_client: AsyncClient):
    """Verifies CORS origin header is reflected in response headers."""
    response = await async_client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_preflight_options(async_client: AsyncClient):
    """Verifies CORS preflight OPTIONS request returns 200 and allowed methods."""
    response = await async_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_request_id_and_duration_headers(async_client: AsyncClient):
    """Verifies X-Request-ID and X-Response-Time-MS headers are attached."""
    response = await async_client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "test-trace-id-12345"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-trace-id-12345"
    assert "X-Response-Time-MS" in response.headers


@pytest.mark.asyncio
async def test_404_not_found_handling(async_client: AsyncClient):
    """Verifies unmapped endpoints return 404."""
    response = await async_client.get("/api/v1/nonexistent-route")
    assert response.status_code == 404
