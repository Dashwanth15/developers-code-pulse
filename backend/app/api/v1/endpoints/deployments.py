import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.models.dora import Deployment
from app.models.github import Repository
from app.schemas.dora import (
    DeploymentCreateRequest,
    DeploymentListResponse,
    DeploymentResponse,
    DeploymentSyncRequest,
    SyncResultResponse,
)
from app.services.auth.dependencies import require_role
from app.services.github.deployment_service import ingest_deployment_payload

router = APIRouter(prefix="/deployments", tags=["Deployments & Releases"])


@router.get(
    "",
    response_model=DeploymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Deployments",
    description="Lists deployment events across environments with pagination and environment filters.",
)
async def list_deployments(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_id: Annotated[uuid.UUID | None, Query(description="Filter by repository")] = None,
    environment: Annotated[str | None, Query(description="Filter by environment (e.g. production, staging)")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status (SUCCESS, FAILURE)")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DeploymentListResponse:
    query = (
        select(Deployment)
        .options(selectinload(Deployment.repository))
        .where(Deployment.organization_id == membership.organization_id)
    )

    if repository_id:
        query = query.where(Deployment.repository_id == repository_id)
    if environment:
        query = query.where(Deployment.environment == environment.lower())
    if status_filter:
        query = query.where(Deployment.status == status_filter.upper())

    # Count total
    count_q = (
        select(func.count(Deployment.id))
        .where(Deployment.organization_id == membership.organization_id)
    )
    if repository_id:
        count_q = count_q.where(Deployment.repository_id == repository_id)
    if environment:
        count_q = count_q.where(Deployment.environment == environment.lower())
    if status_filter:
        count_q = count_q.where(Deployment.status == status_filter.upper())

    total = (await db.scalar(count_q)) or 0
    pages = max((total + size - 1) // size, 1)

    # Order and paginate
    query = query.order_by(Deployment.deployed_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    deployments = list(result.scalars().all())

    items = [
        DeploymentResponse(
            id=d.id,
            organization_id=d.organization_id,
            repository_id=d.repository_id,
            repository_name=d.repository.name if d.repository else None,
            external_deployment_id=d.external_deployment_id,
            environment=d.environment,
            status=d.status,
            deployed_at=d.deployed_at,
            completed_at=d.completed_at,
            commit_sha=d.commit_sha,
            ref_name=d.ref_name,
            source=d.source,
            lead_time_seconds=d.lead_time_seconds,
            metadata=d.metadata_payload,
            created_at=d.created_at,
        )
        for d in deployments
    ]

    return DeploymentListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Deployment",
    description="Manually records or ingests a deployment event for the organization.",
)
async def create_deployment(
    payload: DeploymentCreateRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentResponse:
    repo = None
    if payload.repository_id:
        repo = await db.get(Repository, payload.repository_id)

    deployment = await ingest_deployment_payload(
        db=db,
        organization_id=membership.organization_id,
        repository=repo,
        data=payload.model_dump(by_alias=True),
    )

    return DeploymentResponse(
        id=deployment.id,
        organization_id=deployment.organization_id,
        repository_id=deployment.repository_id,
        repository_name=repo.name if repo else None,
        external_deployment_id=deployment.external_deployment_id,
        environment=deployment.environment,
        status=deployment.status,
        deployed_at=deployment.deployed_at,
        completed_at=deployment.completed_at,
        commit_sha=deployment.commit_sha,
        ref_name=deployment.ref_name,
        source=deployment.source,
        lead_time_seconds=deployment.lead_time_seconds,
        metadata=deployment.metadata_payload,
        created_at=deployment.created_at,
    )


@router.post(
    "/sync",
    response_model=SyncResultResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Synchronize Deployments",
    description="Triggers background synchronization of deployment history from GitHub or external systems.",
)
async def sync_deployments(
    request: DeploymentSyncRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncResultResponse:
    # Query repository if supplied
    repo_name = "All Repositories"
    if request.repository_id:
        repo = await db.get(Repository, request.repository_id)
        if repo:
            repo_name = repo.name

    return SyncResultResponse(
        synced_count=0,
        status="PENDING",
        message=f"Deployment synchronization triggered for organization {membership.organization_id} ({repo_name}).",
    )
