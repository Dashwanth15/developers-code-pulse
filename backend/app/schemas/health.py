from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response model."""

    status: str = Field(default="healthy", description="API process status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Current UTC timestamp")


class DependencyHealth(BaseModel):
    """Individual backing dependency health status."""

    status: str = Field(..., description="'healthy' or 'unhealthy'")
    error: str | None = Field(default=None, description="Error message if unhealthy")


class ReadyResponse(BaseModel):
    """Readiness probe response model."""

    status: str = Field(..., description="'ready' if all critical services pass, else 'not_ready'")
    dependencies: dict[str, DependencyHealth] = Field(
        ..., description="Status of database and cache dependencies"
    )
    timestamp: datetime = Field(..., description="Current UTC timestamp")
