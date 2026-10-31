import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DCPException
from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.models.pull_requests import PullRequest
from app.models.reviews import PRReview
from app.schemas.pull_requests import PullRequestListResponse, PullRequestResponse
from app.schemas.reviews import PRReviewDetailResponse
from app.services.auth.dependencies import require_role

router = APIRouter(prefix="/pull-requests", tags=["Pull Requests"])


@router.get(
    "",
    response_model=PullRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Pull Requests",
    description="Lists pull requests across tenant repositories with lifecycle metrics and pagination.",
)
async def list_pull_requests(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_id: Annotated[uuid.UUID | None, Query(description="Filter by specific repository")] = None,
    state: Annotated[str | None, Query(description="OPEN, CLOSED, or MERGED")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PullRequestListResponse:
    query = (
        select(PullRequest)
        .options(selectinload(PullRequest.author))
        .join(PullRequest.repository)
        .where(PullRequest.repository.has(organization_id=membership.organization_id))
    )

    if repository_id:
        query = query.where(PullRequest.repository_id == repository_id)
    if state:
        query = query.where(PullRequest.state == state.upper())

    # Count total
    count_query = (
        select(func.count(PullRequest.id))
        .join(PullRequest.repository)
        .where(PullRequest.repository.has(organization_id=membership.organization_id))
    )
    if repository_id:
        count_query = count_query.where(PullRequest.repository_id == repository_id)
    if state:
        count_query = count_query.where(PullRequest.state == state.upper())

    total_res = await db.execute(count_query)
    total = total_res.scalar_one() or 0

    # Paginate
    offset = (page - 1) * size
    query = query.order_by(PullRequest.created_at_github.desc()).offset(offset).limit(size)
    result = await db.execute(query)
    prs = result.scalars().all()

    items = [
        PullRequestResponse(
            id=pr.id,
            repository_id=pr.repository_id,
            github_pr_id=pr.github_pr_id,
            number=pr.number,
            title=pr.title,
            state=pr.state,
            is_draft=pr.is_draft,
            source_branch=pr.source_branch,
            target_branch=pr.target_branch,
            created_at_github=pr.created_at_github,
            updated_at_github=pr.updated_at_github,
            closed_at=pr.closed_at,
            merged_at=pr.merged_at,
            first_reviewed_at=pr.first_reviewed_at,
            additions=pr.additions,
            deletions=pr.deletions,
            changed_files=pr.changed_files,
            commit_count=pr.commit_count,
            cycle_time_seconds=pr.cycle_time_seconds,
            merge_time_seconds=pr.merge_time_seconds,
            first_review_time_seconds=pr.first_review_time_seconds,
            author_login=pr.author.login if pr.author else None,
            author_avatar=pr.author.avatar_url if pr.author else None,
        )
        for pr in prs
    ]

    pages = (total + size - 1) // size if total > 0 else 1
    return PullRequestListResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get(
    "/{id}",
    response_model=PullRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Pull Request Details",
    description="Retrieves a single pull request and its calculated flow metrics.",
)
async def get_pull_request(
    id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PullRequestResponse:
    query = (
        select(PullRequest)
        .options(selectinload(PullRequest.author))
        .join(PullRequest.repository)
        .where(
            PullRequest.id == id,
            PullRequest.repository.has(organization_id=membership.organization_id),
        )
    )
    result = await db.execute(query)
    pr = result.scalar_one_or_none()

    if not pr:
        raise DCPException(
            title="Pull Request Not Found",
            detail=f"Pull request with ID '{id}' was not found in this organization.",
            status_code=404,
            code="PULL_REQUEST_NOT_FOUND",
        )

    return PullRequestResponse(
        id=pr.id,
        repository_id=pr.repository_id,
        github_pr_id=pr.github_pr_id,
        number=pr.number,
        title=pr.title,
        state=pr.state,
        is_draft=pr.is_draft,
        source_branch=pr.source_branch,
        target_branch=pr.target_branch,
        created_at_github=pr.created_at_github,
        updated_at_github=pr.updated_at_github,
        closed_at=pr.closed_at,
        merged_at=pr.merged_at,
        first_reviewed_at=pr.first_reviewed_at,
        additions=pr.additions,
        deletions=pr.deletions,
        changed_files=pr.changed_files,
        commit_count=pr.commit_count,
        cycle_time_seconds=pr.cycle_time_seconds,
        merge_time_seconds=pr.merge_time_seconds,
        first_review_time_seconds=pr.first_review_time_seconds,
        author_login=pr.author.login if pr.author else None,
        author_avatar=pr.author.avatar_url if pr.author else None,
    )


@router.get(
    "/{id}/reviews",
    response_model=list[PRReviewDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Pull Request Reviews",
    description="Lists all peer reviews submitted for a specific pull request.",
)
async def get_pull_request_reviews(
    id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PRReviewDetailResponse]:
    pr_query = (
        select(PullRequest)
        .join(PullRequest.repository)
        .where(
            PullRequest.id == id,
            PullRequest.repository.has(organization_id=membership.organization_id),
        )
    )
    pr_result = await db.execute(pr_query)
    pr = pr_result.scalar_one_or_none()
    if not pr:
        raise DCPException(
            title="Pull Request Not Found",
            detail=f"Pull request with ID '{id}' was not found in this organization.",
            status_code=404,
            code="PULL_REQUEST_NOT_FOUND",
        )

    review_query = (
        select(PRReview)
        .options(selectinload(PRReview.reviewer))
        .where(PRReview.pull_request_id == id)
        .order_by(PRReview.submitted_at.asc())
    )
    result = await db.execute(review_query)
    reviews = result.scalars().all()

    return [
        PRReviewDetailResponse(
            id=rev.id,
            pull_request_id=rev.pull_request_id,
            reviewer_account_id=rev.reviewer_account_id,
            reviewer_login=rev.reviewer.login if rev.reviewer else None,
            reviewer_avatar=rev.reviewer.avatar_url if rev.reviewer else None,
            state=rev.state,
            submitted_at=rev.submitted_at,
            commit_sha=rev.commit_sha,
        )
        for rev in reviews
    ]

