import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommitAuthorResponse(BaseModel):
    """GitHub contributor profile for commit telemetry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    user_type: str = "User"


class CommitDetailResponse(BaseModel):
    """Single commit record with author and change volume."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    commit_sha: str
    message: str
    committed_at: datetime
    additions: int = 0
    deletions: int = 0
    total_changes: int = 0
    branch_name: str = "main"
    is_merge_commit: bool = False
    author: CommitAuthorResponse | None = None


class CommitCadencePoint(BaseModel):
    """Daily commit volume snapshot."""

    date: str = Field(description="ISO Date YYYY-MM-DD")
    commit_count: int
    additions: int = 0
    deletions: int = 0


class CommitHeatmapPoint(BaseModel):
    """Day and hour activity intensity point."""

    day_of_week: int = Field(description="0=Monday, 6=Sunday", ge=0, le=6)
    hour_of_day: int = Field(description="0 to 23", ge=0, le=23)
    commit_count: int


class CommitContributorSummary(BaseModel):
    """Aggregated contributor volume without surveillance or ranking."""

    author_id: str
    login: str
    name: str | None = None
    avatar_url: str | None = None
    commit_count: int
    additions: int
    deletions: int
    last_committed_at: datetime


class RepositoryCommitSummary(BaseModel):
    """Cross-repository commit comparison."""

    repository_id: uuid.UUID
    name: str
    commit_count: int
    additions: int
    deletions: int
    active_contributors_count: int


class CommitAnalyticsSummary(BaseModel):
    """Top-level commit intelligence aggregate KPIs."""

    total_commits: int
    daily_cadence: float
    weekday_cadence: float
    active_contributors: int
    total_additions: int
    total_deletions: int
    total_churn: int
    merge_commit_count: int


class CommitAnalyticsResponse(BaseModel):
    """Comprehensive Commit Intelligence payload."""

    time_window: str
    start_date: str
    end_date: str
    summary: CommitAnalyticsSummary
    cadence_trend: list[CommitCadencePoint]
    heatmap: list[CommitHeatmapPoint]
    top_contributors: list[CommitContributorSummary]
    repository_comparison: list[RepositoryCommitSummary]
