import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MacroThroughput(BaseModel):
    """Aggregate pull request, merge, and commit throughput across the organization."""

    total_prs_opened: int = 0
    total_prs_merged: int = 0
    total_prs_closed: int = 0
    merge_rate_percent: float = 0.0
    total_commits: int = 0
    total_reviews: int = 0


class DeliveryCadence(BaseModel):
    """Macro delivery cadence and speed indicators."""

    deployments_count: int = 0
    median_lead_time_hours: float | None = None
    median_review_turnaround_hours: float | None = None
    median_merge_latency_hours: float | None = None


class BottleneckDistributionSummary(BaseModel):
    """Aggregated bottleneck pressure points across teams and repositories."""

    total_active: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)


class CollaborationPattern(BaseModel):
    """Macro team collaboration and code health indicators without developer surveillance."""

    multi_reviewer_pr_rate: float = 0.0  # Percentage of PRs with >= 2 reviewers
    cross_repo_collaboration_index: float = 0.0
    average_review_comments_per_pr: float = 0.0
    review_coverage_rate: float = 0.0  # Percentage of merged PRs that had formal peer reviews


class RepoDeliveryTrend(BaseModel):
    """Cross-repository delivery performance and systemic friction overview."""

    repository_id: uuid.UUID
    repository_name: str
    pr_throughput: int = 0
    merge_rate: float = 0.0
    median_cycle_time_hours: float | None = None
    deployment_count: int = 0
    active_bottlenecks: int = 0


class TeamTrendSeriesPoint(BaseModel):
    """Historical timeline point for macro team delivery rhythm."""

    date: str
    prs_opened: int = 0
    prs_merged: int = 0
    reviews_completed: int = 0
    deployments: int = 0


class TeamIntelligenceResponse(BaseModel):
    """Comprehensive Team Intelligence report complying strictly with Anti-Surveillance Manifesto."""

    organization_id: uuid.UUID
    time_window: str
    start_date: datetime
    end_date: datetime
    anti_surveillance_notice: str = (
        "Developers Code Pulse evaluates macro system throughput, delivery friction, and team workflow health. "
        "It strictly forbids individual developer surveillance, personal velocity quotas, or individual rankings."
    )
    throughput: MacroThroughput
    delivery_cadence: DeliveryCadence
    bottlenecks: BottleneckDistributionSummary
    collaboration: CollaborationPattern
    repository_trends: list[RepoDeliveryTrend] = Field(default_factory=list)
    systemic_recommendations: list[dict[str, Any]] = Field(default_factory=list)


class TeamTrendsResponse(BaseModel):
    """Historical team delivery trends across time windows."""

    organization_id: uuid.UUID
    time_window: str
    series: list[TeamTrendSeriesPoint] = Field(default_factory=list)
