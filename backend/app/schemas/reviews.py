import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TTFRMetrics(BaseModel):
    """Time to First Review (TTFR) duration percentiles and health benchmark."""

    median_hours: float | None = Field(default=None, description="P50 duration in hours")
    p75_hours: float | None = Field(default=None, description="P75 duration in hours")
    p90_hours: float | None = Field(default=None, description="P90 duration in hours")
    benchmark_comparison: str = Field(default="HEALTHY", description="HEALTHY, MODERATE, or CONGESTED")


class ApprovalTurnaroundMetrics(BaseModel):
    """Duration from first substantive review to approval."""

    median_hours: float | None = Field(default=None, description="P50 turnaround hours")
    p75_hours: float | None = Field(default=None, description="P75 turnaround hours")


class ReviewSummaryMetrics(BaseModel):
    """Core metrics quantifying review efficiency and rework iterations."""

    time_to_first_review: TTFRMetrics
    approval_turnaround: ApprovalTurnaroundMetrics
    average_review_rounds: float = Field(default=1.0, description="Average review iterations before merge")
    review_coverage_rate: float = Field(default=0.0, description="Percentage of PRs receiving at least 1 peer review")


class TurnaroundHistogramBucket(BaseModel):
    """Histogram bucket representing review latency ranges."""

    range: str
    count: int = 0


class ReviewAnalyticsResponse(BaseModel):
    """Comprehensive Review Intelligence dashboard response payload."""

    time_window: str = "30d"
    start_date: str
    end_date: str
    metrics: ReviewSummaryMetrics
    turnaround_histogram: list[TurnaroundHistogramBucket] = Field(default_factory=list)
    pending_queue_count: int = 0


class ReviewerWorkloadItem(BaseModel):
    """Review activity statistics for an individual team member."""

    account_id: uuid.UUID
    login: str
    name: str | None = None
    avatar_url: str | None = None
    reviews_conducted: int = 0
    approvals_given: int = 0
    changes_requested: int = 0
    review_share_percentage: float = 0.0


class ReviewWorkloadResponse(BaseModel):
    """Reviewer workload concentration analysis and Gini index."""

    time_window: str = "30d"
    gini_coefficient: float = Field(default=0.0, description="Gini index measuring review load concentration (0 to 1)")
    workload_balance_status: str = Field(default="BALANCED", description="BALANCED, MODERATE, or UNBALANCED")
    total_reviews: int = 0
    reviewers: list[ReviewerWorkloadItem] = Field(default_factory=list)


class PendingReviewItem(BaseModel):
    """Individual PR pending in the review queue."""

    pull_request_id: uuid.UUID
    number: int
    title: str
    repository_name: str
    author_login: str | None = None
    author_avatar: str | None = None
    waiting_hours: float = 0.0
    created_at: datetime
    requested_reviewers: list[str] = Field(default_factory=list)


class PendingReviewQueueResponse(BaseModel):
    """Queue of active PRs awaiting peer review."""

    total_pending: int = 0
    items: list[PendingReviewItem] = Field(default_factory=list)


class PRReviewDetailResponse(BaseModel):
    """Detailed record of a submitted PR review."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pull_request_id: uuid.UUID
    reviewer_account_id: uuid.UUID | None = None
    reviewer_login: str | None = None
    reviewer_avatar: str | None = None
    state: str
    submitted_at: datetime
    commit_sha: str | None = None
