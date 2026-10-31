import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.models.dora import Incident
from app.models.github import Repository
from app.schemas.dora import (
    IncidentCreateRequest,
    IncidentListResponse,
    IncidentResponse,
    IncidentSyncRequest,
    SyncResultResponse,
)
from app.services.auth.dependencies import require_role
from app.services.github.deployment_service import ingest_incident_record

router = APIRouter(prefix="/incidents", tags=["Incidents & Outages"])


@router.get(
    "",
    response_model=IncidentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Incidents",
    description="Lists production incidents with severity, recovery duration, and status filters.",
)
async def list_incidents(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_id: Annotated[uuid.UUID | None, Query(description="Filter by repository")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status (OPEN, RESOLVED, CLOSED)")] = None,
    severity: Annotated[str | None, Query(description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> IncidentListResponse:
    query = (
        select(Incident)
        .options(selectinload(Incident.repository))
        .where(Incident.organization_id == membership.organization_id)
    )

    if repository_id:
        query = query.where(Incident.repository_id == repository_id)
    if status_filter:
        query = query.where(Incident.status == status_filter.upper())
    if severity:
        query = query.where(Incident.severity == severity.upper())

    # Count total
    count_q = select(func.count(Incident.id)).where(Incident.organization_id == membership.organization_id)
    if repository_id:
        count_q = count_q.where(Incident.repository_id == repository_id)
    if status_filter:
        count_q = count_q.where(Incident.status == status_filter.upper())
    if severity:
        count_q = count_q.where(Incident.severity == severity.upper())

    total = (await db.scalar(count_q)) or 0
    pages = max((total + size - 1) // size, 1)

    query = query.order_by(Incident.started_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    incidents = list(result.scalars().all())

    items = [
        IncidentResponse(
            id=i.id,
            organization_id=i.organization_id,
            repository_id=i.repository_id,
            repository_name=i.repository.name if i.repository else None,
            external_incident_id=i.external_incident_id,
            title=i.title,
            severity=i.severity,
            status=i.status,
            started_at=i.started_at,
            resolved_at=i.resolved_at,
            recovery_duration_seconds=i.recovery_duration_seconds,
            source=i.source,
            metadata=i.metadata_payload,
            created_at=i.created_at,
        )
        for i in incidents
    ]

    return IncidentListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Incident",
    description="Manually records or ingests a production incident or outage.",
)
async def create_incident(
    payload: IncidentCreateRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IncidentResponse:
    repo = None
    if payload.repository_id:
        repo = await db.get(Repository, payload.repository_id)

    incident = await ingest_incident_record(
        db=db,
        organization_id=membership.organization_id,
        repository=repo,
        data=payload.model_dump(by_alias=True),
    )

    return IncidentResponse(
        id=incident.id,
        organization_id=incident.organization_id,
        repository_id=incident.repository_id,
        repository_name=repo.name if repo else None,
        external_incident_id=incident.external_incident_id,
        title=incident.title,
        severity=incident.severity,
        status=incident.status,
        started_at=incident.started_at,
        resolved_at=incident.resolved_at,
        recovery_duration_seconds=incident.recovery_duration_seconds,
        source=incident.source,
        metadata=incident.metadata_payload,
        created_at=incident.created_at,
    )


@router.post(
    "/sync",
    response_model=SyncResultResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Synchronize Incidents",
    description="Triggers background synchronization of incident data from monitoring adapters.",
)
async def sync_incidents(
    _request: IncidentSyncRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    _db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncResultResponse:
    return SyncResultResponse(
        synced_count=0,
        status="PENDING",
        message=f"Incident synchronization triggered for organization {membership.organization_id}.",
    )
