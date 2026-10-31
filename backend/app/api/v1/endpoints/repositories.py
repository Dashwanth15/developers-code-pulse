import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DCPException
from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.models.commits import Commit
from app.models.github import Repository
from app.models.pull_requests import PullRequest
from app.schemas.commits import CommitDetailResponse
from app.schemas.github import (
    ConnectRepositoryRequest,
    RepositoryResponse,
    ToggleMonitoringRequest,
)
from app.schemas.pull_requests import PullRequestResponse
from app.services.auth.dependencies import (
    get_current_org_membership,
    require_role,
)
from app.services.github.commit_service import sync_repository_commits
from app.services.github.github_service import (
    connect_repository,
    list_organization_repositories,
    toggle_repository_monitoring,
)
from app.services.github.pull_request_service import sync_repository_pull_requests

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get(
    "",
    response_model=list[RepositoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List Connected Repositories",
    description="Returns all monitored repositories in the current organization.",
)
async def get_repositories(
    membership: Annotated[OrganizationMember, Depends(get_current_org_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RepositoryResponse]:
    return await list_organization_repositories(db, membership.organization_id)


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect Repository",
    description="Enables monitoring for a discovered GitHub repository in the current organization.",
)
async def add_repository(
    request: ConnectRepositoryRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryResponse:
    return await connect_repository(db, membership.organization_id, request)


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Repository Details",
    description="Retrieves metadata for a connected repository.",
)
async def get_repository_by_id(
    repository_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(get_current_org_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryResponse:
    query = select(Repository).where(
        Repository.id == repository_id,
        Repository.organization_id == membership.organization_id,
    )
    result = await db.execute(query)
    repo = result.scalar_one_or_none()
    if not repo:
        raise DCPException(
            title="Repository Not Found",
            detail=f"Repository '{repository_id}' does not exist in this organization.",
            status_code=404,
            code="REPOSITORY_NOT_FOUND",
        )
    return RepositoryResponse.model_validate(repo)


@router.patch(
    "/{repository_id}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle Monitoring",
    description="Enables or pauses metric collection for a repository.",
)
async def toggle_monitoring(
    repository_id: uuid.UUID,
    request: ToggleMonitoringRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryResponse:
    return await toggle_repository_monitoring(
        db,
        membership.organization_id,
        repository_id,
        request.is_monitored,
    )


@router.get(
    "/{repository_id}/commits",
    response_model=list[CommitDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="List Repository Commits",
    description="Returns recent commits for a monitored repository with author details.",
)
async def get_repository_commits(
    repository_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(get_current_org_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    branch: Annotated[str | None, Query()] = None,
) -> list[CommitDetailResponse]:
    # Ensure repository belongs to caller's organization
    repo_q = select(Repository).where(
        Repository.id == repository_id,
        Repository.organization_id == membership.organization_id,
    )
    repo_res = await db.execute(repo_q)
    if not repo_res.scalar_one_or_none():
        raise DCPException(
            title="Repository Not Found",
            detail=f"Repository '{repository_id}' does not exist in this organization.",
            status_code=404,
            code="REPOSITORY_NOT_FOUND",
        )

    commit_q = (
        select(Commit)
        .options(selectinload(Commit.author))
        .where(Commit.repository_id == repository_id)
    )
    if branch:
        commit_q = commit_q.where(Commit.branch_name == branch)

    commit_q = commit_q.order_by(Commit.committed_at.desc()).limit(limit).offset(offset)
    res = await db.execute(commit_q)
    commits = res.scalars().all()
    return [CommitDetailResponse.model_validate(c) for c in commits]


@router.post(
    "/{repository_id}/sync-commits",
    status_code=status.HTTP_200_OK,
    summary="Trigger Commit Synchronization",
    description="Backfills recent commits for a repository from GitHub API.",
)
async def trigger_commit_sync(
    repository_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | int]:
    repo_q = select(Repository).where(
        Repository.id == repository_id,
        Repository.organization_id == membership.organization_id,
    )
    repo_res = await db.execute(repo_q)
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise DCPException(
            title="Repository Not Found",
            detail=f"Repository '{repository_id}' does not exist in this organization.",
            status_code=404,
            code="REPOSITORY_NOT_FOUND",
        )

    count = await sync_repository_commits(db, repo)
    return {
        "status": "success",
        "repository_id": str(repository_id),
        "synced_commits": count,
    }


@router.get(
    "/{repository_id}/pull-requests",
    response_model=list[PullRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List Repository Pull Requests",
    description="Returns recent pull requests for a monitored repository with lifecycle metrics.",
)
async def get_repository_pull_requests_endpoint(
    repository_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(get_current_org_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    state: Annotated[str | None, Query(description="OPEN, CLOSED, or MERGED")] = None,
) -> list[PullRequestResponse]:
    repo_q = select(Repository).where(
        Repository.id == repository_id,
        Repository.organization_id == membership.organization_id,
    )
    repo_res = await db.execute(repo_q)
    if not repo_res.scalar_one_or_none():
        raise DCPException(
            title="Repository Not Found",
            detail=f"Repository '{repository_id}' does not exist in this organization.",
            status_code=404,
            code="REPOSITORY_NOT_FOUND",
        )

    pr_q = (
        select(PullRequest)
        .options(selectinload(PullRequest.author))
        .where(PullRequest.repository_id == repository_id)
    )
    if state:
        pr_q = pr_q.where(PullRequest.state == state.upper())

    pr_q = pr_q.order_by(PullRequest.created_at_github.desc()).limit(limit).offset(offset)
    res = await db.execute(pr_q)
    prs = res.scalars().all()

    return [
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


@router.post(
    "/{repository_id}/sync-prs",
    status_code=status.HTTP_200_OK,
    summary="Trigger Pull Request Synchronization",
    description="Backfills recent pull requests for a repository from GitHub API.",
)
async def trigger_pr_sync(
    repository_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | int]:
    repo_q = select(Repository).where(
        Repository.id == repository_id,
        Repository.organization_id == membership.organization_id,
    )
    repo_res = await db.execute(repo_q)
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise DCPException(
            title="Repository Not Found",
            detail=f"Repository '{repository_id}' does not exist in this organization.",
            status_code=404,
            code="REPOSITORY_NOT_FOUND",
        )

    count = await sync_repository_pull_requests(db, repo)
    return {
        "status": "success",
        "repository_id": str(repository_id),
        "synced_pull_requests": count,
    }
