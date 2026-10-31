import sys
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend root is on sys.path if main.py is invoked directly
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import (
    DCPException,
    dcp_exception_handler,
    unhandled_exception_handler,
)
from app.core.logging import setup_logging
from app.core.metrics import get_metrics_response, prometheus_metrics_middleware
from app.core.security_middleware import (
    rate_limiting_middleware,
    request_size_limit_middleware,
    security_headers_middleware,
)
from app.database.session import close_engine, get_engine

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and graceful shutdown lifecycles."""
    setup_logging(service_name="dcp-api")
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    # Eagerly initialize DB engine connection pool
    get_engine()
    yield
    # Graceful shutdown: close active pools
    logger.info("application_shutting_down")
    await close_engine()


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Developer Productivity and Team Engineering Intelligence Platform API",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Prometheus Metrics Middleware
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next) -> Response:
        return await prometheus_metrics_middleware(request, call_next)

    # 3. Request Tracing & Structured Logging Middleware
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        start_time = time.perf_counter()

        logger.info(
            "http_request_started",
            method=request.method,
            path=str(request.url.path),
            trace_id=trace_id,
        )

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        response.headers["X-Request-ID"] = trace_id
        response.headers["X-Response-Time-MS"] = f"{duration_ms:.2f}"

        logger.info(
            "http_request_completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            trace_id=trace_id,
        )
        return response

    # 4. Request Size Limit Middleware (protect against payload exhaustion)
    @app.middleware("http")
    async def size_limit_middleware(request: Request, call_next) -> Response:
        return await request_size_limit_middleware(request, call_next)

    # 5. Sliding Window Rate Limiting Middleware
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next) -> Response:
        return await rate_limiting_middleware(request, call_next)

    # 6. Security Headers Middleware (outermost: applies to all responses)
    @app.middleware("http")
    async def sec_headers_middleware(request: Request, call_next) -> Response:
        return await security_headers_middleware(request, call_next)

    # Exception Handlers
    app.add_exception_handler(DCPException, dcp_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Root Metadata Endpoint
    @app.get("/", tags=["System"])
    async def root() -> dict:
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "tagline": "Understand your team's workflow. Build better software. Ship faster together.",
            "docs": f"{settings.API_V1_STR}/docs",
            "health": f"{settings.API_V1_STR}/health",
            "ready": f"{settings.API_V1_STR}/ready",
            "metrics": "/metrics",
        }

    # Prometheus Scraping Endpoint
    @app.get("/metrics", tags=["System"], summary="Prometheus Metrics")
    async def metrics_endpoint() -> Response:
        """Prometheus metrics endpoint scraped by monitoring systems."""
        return get_metrics_response()

    # Mount API v1 Routes
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
