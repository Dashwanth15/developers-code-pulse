import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PullRequestResponse(BaseModel):
    """Schema representing a single pull request with lifecycle metrics."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    github_pr_id: int
    number: int
    title: str
    state: str
    is_draft: bool
    source_branch: str
    target_branch: str
    created_at_github: datetime
    updated_at_github: datetime
    closed_at: datetime | None = None
    merged_at: datetime | None = None
    first_reviewed_at: datetime | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    commit_count: int = 0
    cycle_time_seconds: int | None = None
    merge_time_seconds: int | None = None
    first_review_time_seconds: int | None = None
    author_login: str | None = None
    author_avatar: str | None = None


class PRAnalyticsSummary(BaseModel):
    """High-level summary of pull request throughput, latency, and merge performance."""

    total_prs_opened: int = Field(default=0, description="Total PRs opened within the time window")
    total_prs_merged: int = Field(default=0, description="Total PRs successfully merged")
    total_prs_closed_unmerged: int = Field(default=0, description="Total PRs closed without merge")
    currently_open_prs: int = Field(default=0, description="Currently active open PRs")
    merge_rate_percentage: float = Field(default=0.0, description="Percentage of closed/merged PRs successfully merged")
    median_merge_time_hours: float | None = Field(default=None, description="P50 merge duration in hours")
    p75_merge_time_hours: float | None = Field(default=None, description="P75 merge duration in hours")
    median_cycle_time_hours: float | None = Field(default=None, description="P50 cycle duration in hours")


class PRCadenceTrendPoint(BaseModel):
    """Daily PR activity point for throughput visualization."""

    date: str
    opened: int = 0
    merged: int = 0
    closed: int = 0


class PRSizeBucket(BaseModel):
    """PR size segment volume and associated turnaround time."""

    count: int = 0
    avg_merge_hours: float | None = None


class PRSizeDistribution(BaseModel):
    """Segmentation of PRs by lines changed (additions + deletions)."""

    small_under_100_lines: PRSizeBucket = Field(default_factory=PRSizeBucket)
    medium_100_to_500_lines: PRSizeBucket = Field(default_factory=PRSizeBucket)
    large_over_500_lines: PRSizeBucket = Field(default_factory=PRSizeBucket)


class PRAnalyticsResponse(BaseModel):
    """Complete Pull Request analytics response payload."""

    time_window: str = "30d"
    start_date: str
    end_date: str
    summary: PRAnalyticsSummary
    cadence_trend: list[PRCadenceTrendPoint] = Field(default_factory=list)
    size_distribution: PRSizeDistribution = Field(default_factory=PRSizeDistribution)


class PullRequestListResponse(BaseModel):
    """Paginated collection of pull requests."""

    items: list[PullRequestResponse]
    total: int
    page: int = 1
    size: int = 20
    pages: int = 1
