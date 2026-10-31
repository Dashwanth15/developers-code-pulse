import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DCPException
from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.models.github import Repository
from app.schemas.github import (
    ConnectRepositoryRequest,
    RepositoryResponse,
    ToggleMonitoringRequest,
)
from app.services.auth.dependencies import (
    get_current_org_membership,
    require_role,
)
from app.services.github.github_service import (
    connect_repository,
    list_organization_repositories,
    toggle_repository_monitoring,
)

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
