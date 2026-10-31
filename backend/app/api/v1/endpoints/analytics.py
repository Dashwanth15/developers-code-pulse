import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.schemas.commits import CommitAnalyticsResponse
from app.schemas.dora import (
    ChangeFailureRateDetail,
    DeploymentFrequencyDetail,
    DORAOverviewResponse,
    LeadTimeDetail,
    RecoveryTimeDetail,
)
from app.schemas.pull_requests import PRAnalyticsResponse
from app.schemas.reviews import (
    PendingReviewQueueResponse,
    ReviewAnalyticsResponse,
    ReviewWorkloadResponse,
)
from app.schemas.team import TeamIntelligenceResponse, TeamTrendsResponse
from app.services.analytics.commit_metrics import calculate_commit_analytics
from app.services.analytics.dora_metrics import (
    calculate_change_failure_rate,
    calculate_deployment_frequency,
    calculate_dora_overview,
    calculate_lead_time_for_changes,
    calculate_mean_time_to_recovery,
)
from app.services.analytics.pull_request_metrics import calculate_pull_request_analytics
from app.services.analytics.review_metrics import (
    calculate_review_analytics,
    calculate_reviewer_workload,
    get_pending_review_queue,
)
from app.services.analytics.team_intelligence import (
    calculate_team_intelligence,
    calculate_team_trends,
)
from app.services.auth.dependencies import require_role

router = APIRouter(prefix="/analytics", tags=["Analytics & Intelligence"])


@router.get(
    "/commits",
    response_model=CommitAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Commit Intelligence & Cadence Analytics",
    description="Calculates commit velocity, cadence trends, heatmaps, and churn within the organization.",
)
async def get_commit_analytics(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> CommitAnalyticsResponse:
    return await calculate_commit_analytics(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/pull-requests",
    response_model=PRAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Pull Request Lifecycle & Flow Analytics",
    description="Calculates PR throughput, merge rates, cycle times, and size distributions within the organization.",
)
async def get_pull_request_analytics(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> PRAnalyticsResponse:
    return await calculate_pull_request_analytics(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date_str=start_date.isoformat() if start_date else None,
        end_date_str=end_date.isoformat() if end_date else None,
    )


@router.get(
    "/reviews",
    response_model=ReviewAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Review Turnaround & Latency Intelligence",
    description="Calculates Time to First Review (TTFR), approval turnaround, and turnaround distribution.",
)
async def get_review_analytics(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
) -> ReviewAnalyticsResponse:
    return await calculate_review_analytics(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
    )


@router.get(
    "/reviews/workload",
    response_model=ReviewWorkloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Reviewer Workload & Gini Index",
    description="Calculates peer review load distribution and team Gini concentration coefficient.",
)
async def get_reviewer_workload(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
) -> ReviewWorkloadResponse:
    return await calculate_reviewer_workload(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
    )


@router.get(
    "/reviews/pending",
    response_model=PendingReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Urgent Pending Review Queue",
    description="Real-time list of open pull requests waiting >= 12h for peer review.",
)
async def get_pending_reviews(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
) -> PendingReviewQueueResponse:
    return await get_pending_review_queue(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
    )


# ---------------------------------------------------------
# Phase 7: Team Intelligence & DORA Metrics
# ---------------------------------------------------------


@router.get(
    "/team",
    response_model=TeamIntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Team Intelligence & System Throughput",
    description="Macro-level team throughput, review health, bottleneck pressure, and cross-repo delivery trends without individual surveillance.",
)
async def get_team_intelligence(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> TeamIntelligenceResponse:
    return await calculate_team_intelligence(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/team/trends",
    response_model=TeamTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Team Delivery Flow Trends",
    description="Historical timeline of pull requests, peer reviews, and production rollouts.",
)
async def get_team_trends(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> TeamTrendsResponse:
    return await calculate_team_trends(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/dora",
    response_model=DORAOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Four DORA Metrics Overview",
    description="Evaluates Deployment Frequency, Lead Time, Change Failure Rate, and MTTR with industry tier classifications.",
)
async def get_dora_overview(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> DORAOverviewResponse:
    return await calculate_dora_overview(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/dora/deployment-frequency",
    response_model=DeploymentFrequencyDetail,
    status_code=status.HTTP_200_OK,
    summary="DORA Deployment Frequency",
    description="Daily, weekly, and monthly rates of successful production rollouts.",
)
async def get_deployment_frequency(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> DeploymentFrequencyDetail:
    return await calculate_deployment_frequency(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/dora/lead-time",
    response_model=LeadTimeDetail,
    status_code=status.HTTP_200_OK,
    summary="DORA Lead Time for Changes",
    description="End-to-end latency from code commit and PR merge to successful production deployment.",
)
async def get_lead_time_for_changes(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> LeadTimeDetail:
    return await calculate_lead_time_for_changes(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/dora/change-failure-rate",
    response_model=ChangeFailureRateDetail,
    status_code=status.HTTP_200_OK,
    summary="DORA Change Failure Rate",
    description="Percentage of production deployments resulting in an incident or failure.",
)
async def get_change_failure_rate(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> ChangeFailureRateDetail:
    return await calculate_change_failure_rate(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/dora/mean-time-to-recovery",
    response_model=RecoveryTimeDetail,
    status_code=status.HTTP_200_OK,
    summary="DORA Mean Time to Recovery (MTTR)",
    description="Elapsed time from production incident onset to documented service restoration.",
)
async def get_mean_time_to_recovery(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    time_window: Annotated[str, Query(description="7d, 14d, 30d, 90d")] = "30d",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> RecoveryTimeDetail:
    return await calculate_mean_time_to_recovery(
        db=db,
        organization_id=membership.organization_id,
        repository_ids=repository_ids,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date,
    )
