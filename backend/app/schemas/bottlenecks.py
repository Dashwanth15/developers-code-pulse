import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BottleneckEvidence(BaseModel):
    """Structured empirical evidence underpinning an identified bottleneck."""

    metric_name: str
    observed_value: float | int | str
    baseline_value: float | int | str | None = None
    threshold_value: float | int | str | None = None
    affected_count: int = 0
    context: dict[str, Any] = Field(default_factory=dict)


class BottleneckResponse(BaseModel):
    """Full detail view of an identified workflow bottleneck."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    repository_id: uuid.UUID | None = None
    repository_name: str | None = None
    bottleneck_type: str
    severity: str
    confidence: str
    title: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    recommendation: str
    detected_at: datetime
    first_observed_at: datetime
    last_observed_at: datetime
    status: str
    fingerprint: str
    resolved_at: datetime | None = None


class BottleneckListResponse(BaseModel):
    """Paginated list of workflow bottlenecks with filtering metadata."""

    items: list[BottleneckResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 1


class BottleneckSummaryResponse(BaseModel):
    """Aggregated bottleneck overview metrics and distribution statistics."""

    total_active: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    affected_repositories_count: int = 0
    resolved_count: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)


class BottleneckTrendPoint(BaseModel):
    """Historical timeline data point for bottleneck occurrence."""

    date: str
    active_count: int = 0
    detected_count: int = 0
    resolved_count: int = 0


class BottleneckTrendsResponse(BaseModel):
    """Chronological bottleneck trends over a rolling observation window."""

    time_window: str = "30d"
    trends: list[BottleneckTrendPoint] = Field(default_factory=list)


class BottleneckRecommendationItem(BaseModel):
    """Actionable engineering workflow recommendation grounded in empirical evidence."""

    bottleneck_type: str
    title: str
    recommendation: str
    severity: str
    impact: str
    affected_repositories: list[str] = Field(default_factory=list)
    evidence_summary: str


class BottleneckRecommendationsResponse(BaseModel):
    """Aggregated prioritized recommendations to optimize engineering flow."""

    total_recommendations: int = 0
    recommendations: list[BottleneckRecommendationItem] = Field(default_factory=list)


class BottleneckStatusUpdateRequest(BaseModel):
    """Status lifecycle update payload for a bottleneck."""

    status: str = Field(
        ...,
        description="ACTIVE, ACKNOWLEDGED, RESOLVED, or IGNORED",
    )


class TriggerDetectionRequest(BaseModel):
    """Request payload to manually trigger a bottleneck detection evaluation."""

    repository_id: uuid.UUID | None = None
    time_window: str = Field(default="30d", description="Observation window (7d, 14d, 30d, 90d)")


class DetectionRunResponse(BaseModel):
    """Status record of a bottleneck detection execution."""

    run_id: uuid.UUID
    status: str
    organization_id: uuid.UUID
    repository_id: uuid.UUID | None = None
    total_bottlenecks: int = 0
    started_at: datetime
    completed_at: datetime | None = None
    message: str | None = None
