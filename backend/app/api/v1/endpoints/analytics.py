import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.schemas.commits import CommitAnalyticsResponse
from app.schemas.pull_requests import PRAnalyticsResponse
from app.services.analytics.commit_metrics import calculate_commit_analytics
from app.services.analytics.pull_request_metrics import calculate_pull_request_analytics
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
