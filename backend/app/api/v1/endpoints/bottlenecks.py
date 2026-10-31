import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DCPException
from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.models.bottlenecks import Bottleneck, BottleneckHistory
from app.schemas.bottlenecks import (
    BottleneckListResponse,
    BottleneckRecommendationItem,
    BottleneckRecommendationsResponse,
    BottleneckResponse,
    BottleneckStatusUpdateRequest,
    BottleneckSummaryResponse,
    BottleneckTrendPoint,
    BottleneckTrendsResponse,
    DetectionRunResponse,
    TriggerDetectionRequest,
)
from app.services.auth.dependencies import require_role
from app.services.bottlenecks.engine import BottleneckEngine

router = APIRouter(prefix="/bottlenecks", tags=["Bottleneck Intelligence"])


@router.get(
    "",
    response_model=BottleneckListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Bottlenecks",
    description="Retrieves a paginated list of identified workflow bottlenecks with tenant filtering.",
)
async def list_bottlenecks(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_id: Annotated[uuid.UUID | None, Query(description="Filter by repository")] = None,
    severity: Annotated[str | None, Query(description="LOW, MEDIUM, HIGH, CRITICAL")] = None,
    bottleneck_type: Annotated[str | None, Query(description="Specific bottleneck type")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="ACTIVE, ACKNOWLEDGED, RESOLVED, IGNORED")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BottleneckListResponse:
    query = (
        select(Bottleneck)
        .options(selectinload(Bottleneck.repository))
        .where(Bottleneck.organization_id == membership.organization_id)
    )

    if repository_id:
        query = query.where(Bottleneck.repository_id == repository_id)
    if severity:
        query = query.where(Bottleneck.severity == severity.upper())
    if bottleneck_type:
        query = query.where(Bottleneck.bottleneck_type == bottleneck_type)
    if status_filter:
        query = query.where(Bottleneck.status == status_filter.upper())

    # Count total query
    count_query = select(func.count(Bottleneck.id)).where(
        Bottleneck.organization_id == membership.organization_id
    )
    if repository_id:
        count_query = count_query.where(Bottleneck.repository_id == repository_id)
    if severity:
        count_query = count_query.where(Bottleneck.severity == severity.upper())
    if bottleneck_type:
        count_query = count_query.where(Bottleneck.bottleneck_type == bottleneck_type)
    if status_filter:
        count_query = count_query.where(Bottleneck.status == status_filter.upper())

    total_res = await db.execute(count_query)
    total = total_res.scalar_one() or 0

    offset = (page - 1) * size
    query = query.order_by(Bottleneck.detected_at.desc()).offset(offset).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 1

    return BottleneckListResponse(
        items=[
            BottleneckResponse(
                id=b.id,
                organization_id=b.organization_id,
                repository_id=b.repository_id,
                repository_name=b.repository.name if b.repository else None,
                bottleneck_type=b.bottleneck_type,
                severity=b.severity,
                confidence=b.confidence,
                title=b.title,
                description=b.description,
                evidence=b.evidence,
                recommendation=b.recommendation,
                detected_at=b.detected_at,
                first_observed_at=b.first_observed_at,
                last_observed_at=b.last_observed_at,
                status=b.status,
                fingerprint=b.fingerprint,
                resolved_at=b.resolved_at,
            )
            for b in items
        ],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/summary",
    response_model=BottleneckSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Bottleneck Summary Metrics",
    description="Calculates overview counts, severity distribution, and affected repositories.",
)
async def get_bottlenecks_summary(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_id: Annotated[uuid.UUID | None, Query()] = None,
) -> BottleneckSummaryResponse:
    query = select(Bottleneck).where(Bottleneck.organization_id == membership.organization_id)
    if repository_id:
        query = query.where(Bottleneck.repository_id == repository_id)

    res = await db.execute(query)
    bottlenecks = list(res.scalars().all())

    active_items = [b for b in bottlenecks if b.status in ("ACTIVE", "ACKNOWLEDGED")]
    resolved_count = sum(1 for b in bottlenecks if b.status == "RESOLVED")

    critical_count = sum(1 for b in active_items if b.severity == "CRITICAL")
    high_count = sum(1 for b in active_items if b.severity == "HIGH")
    medium_count = sum(1 for b in active_items if b.severity == "MEDIUM")
    low_count = sum(1 for b in active_items if b.severity == "LOW")

    affected_repo_ids = {b.repository_id for b in active_items if b.repository_id is not None}

    by_type: dict[str, int] = {}
    for b in active_items:
        by_type[b.bottleneck_type] = by_type.get(b.bottleneck_type, 0) + 1

    by_severity = {
        "CRITICAL": critical_count,
        "HIGH": high_count,
        "MEDIUM": medium_count,
        "LOW": low_count,
    }

    return BottleneckSummaryResponse(
        total_active=len(active_items),
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        affected_repositories_count=len(affected_repo_ids),
        resolved_count=resolved_count,
        by_type=by_type,
        by_severity=by_severity,
    )


@router.get(
    "/trends",
    response_model=BottleneckTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Bottleneck Historical Trends",
    description="Chronological volume trends of active, detected, and resolved bottlenecks.",
)
async def get_bottlenecks_trends(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_id: Annotated[uuid.UUID | None, Query()] = None,
    time_window: Annotated[str, Query()] = "30d",
) -> BottleneckTrendsResponse:
    now = datetime.now(UTC)
    days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
    days = days_map.get(time_window, 30)
    start_date = now - timedelta(days=days)

    query = (
        select(BottleneckHistory)
        .join(BottleneckHistory.bottleneck)
        .where(
            Bottleneck.organization_id == membership.organization_id,
            BottleneckHistory.recorded_at >= start_date,
        )
    )
    if repository_id:
        query = query.where(Bottleneck.repository_id == repository_id)

    res = await db.execute(query)
    history_entries = list(res.scalars().all())

    # Bucket entries by date (YYYY-MM-DD)
    date_buckets: dict[str, dict[str, int]] = {}
    for i in range(days):
        d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        date_buckets[d_str] = {"active": 0, "detected": 0, "resolved": 0}

    for h in history_entries:
        d_str = h.recorded_at.strftime("%Y-%m-%d")
        if d_str in date_buckets:
            date_buckets[d_str]["active"] += 1
            date_buckets[d_str]["detected"] += 1

    trends = [
        BottleneckTrendPoint(
            date=k,
            active_count=v["active"],
            detected_count=v["detected"],
            resolved_count=v["resolved"],
        )
        for k, v in sorted(date_buckets.items())
    ]

    return BottleneckTrendsResponse(time_window=time_window, trends=trends)


@router.get(
    "/recommendations",
    response_model=BottleneckRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Actionable Flow Recommendations",
    description="Aggregates and prioritizes evidence-backed workflow improvement recommendations.",
)
async def get_bottleneck_recommendations(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_id: Annotated[uuid.UUID | None, Query()] = None,
) -> BottleneckRecommendationsResponse:
    query = (
        select(Bottleneck)
        .options(selectinload(Bottleneck.repository))
        .where(
            Bottleneck.organization_id == membership.organization_id,
            Bottleneck.status.in_(["ACTIVE", "ACKNOWLEDGED"]),
        )
    )
    if repository_id:
        query = query.where(Bottleneck.repository_id == repository_id)

    res = await db.execute(query)
    active_bottlenecks = list(res.scalars().all())

    # Deduplicate recommendations by bottleneck_type
    rec_map: dict[str, BottleneckRecommendationItem] = {}
    severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

    for b in active_bottlenecks:
        b_type = b.bottleneck_type
        repo_name = b.repository.name if b.repository else "all"

        if b_type not in rec_map:
            impact_desc = (
                "Critical delivery blockage affecting cycle time"
                if b.severity == "CRITICAL"
                else "Elevated review friction slowing PR completion"
            )
            evidence_summary = (
                f"Observed value: {b.evidence.get('observed_value', 'N/A')} "
                f"({b.evidence.get('metric', 'workflow metric')})"
            )
            rec_map[b_type] = BottleneckRecommendationItem(
                bottleneck_type=b_type,
                title=b.title,
                recommendation=b.recommendation,
                severity=b.severity,
                impact=impact_desc,
                affected_repositories=[repo_name],
                evidence_summary=evidence_summary,
            )
        else:
            if repo_name not in rec_map[b_type].affected_repositories:
                rec_map[b_type].affected_repositories.append(repo_name)
            if severity_order.get(b.severity, 1) > severity_order.get(rec_map[b_type].severity, 1):
                rec_map[b_type].severity = b.severity
                rec_map[b_type].recommendation = b.recommendation

    rec_list = sorted(
        rec_map.values(),
        key=lambda r: severity_order.get(r.severity, 1),
        reverse=True,
    )

    return BottleneckRecommendationsResponse(
        total_recommendations=len(rec_list),
        recommendations=rec_list,
    )


@router.get(
    "/{id}",
    response_model=BottleneckResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Bottleneck Details",
    description="Retrieves a single bottleneck and its empirical evidence payload.",
)
async def get_bottleneck(
    id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BottleneckResponse:
    query = (
        select(Bottleneck)
        .options(selectinload(Bottleneck.repository))
        .where(
            Bottleneck.id == id,
            Bottleneck.organization_id == membership.organization_id,
        )
    )
    result = await db.execute(query)
    b = result.scalar_one_or_none()

    if not b:
        raise DCPException(
            title="Bottleneck Not Found",
            detail=f"Bottleneck with ID '{id}' was not found in this organization.",
            status_code=404,
            code="BOTTLENECK_NOT_FOUND",
        )

    return BottleneckResponse(
        id=b.id,
        organization_id=b.organization_id,
        repository_id=b.repository_id,
        repository_name=b.repository.name if b.repository else None,
        bottleneck_type=b.bottleneck_type,
        severity=b.severity,
        confidence=b.confidence,
        title=b.title,
        description=b.description,
        evidence=b.evidence,
        recommendation=b.recommendation,
        detected_at=b.detected_at,
        first_observed_at=b.first_observed_at,
        last_observed_at=b.last_observed_at,
        status=b.status,
        fingerprint=b.fingerprint,
        resolved_at=b.resolved_at,
    )


@router.post(
    "/detect",
    response_model=DetectionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Bottleneck Detection",
    description="Initiates an asynchronous or on-demand bottleneck detection run.",
)
async def trigger_detection(
    payload: TriggerDetectionRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DetectionRunResponse:
    engine = BottleneckEngine()
    run, detected = await engine.run_detection(
        db=db,
        organization_id=membership.organization_id,
        repository_id=payload.repository_id,
        time_window=payload.time_window,
    )

    return DetectionRunResponse(
        run_id=run.id,
        status=run.status,
        organization_id=run.organization_id,
        repository_id=run.repository_id,
        total_bottlenecks=len(detected),
        started_at=run.started_at,
        completed_at=run.completed_at,
        message=f"Detection run executed successfully. {len(detected)} bottlenecks identified.",
    )


@router.patch(
    "/{id}/status",
    response_model=BottleneckResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Bottleneck Status",
    description="Updates the lifecycle state (ACTIVE, ACKNOWLEDGED, RESOLVED, IGNORED) of a bottleneck.",
)
async def update_bottleneck_status(
    id: uuid.UUID,
    payload: BottleneckStatusUpdateRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.MEMBER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BottleneckResponse:
    query = (
        select(Bottleneck)
        .options(selectinload(Bottleneck.repository))
        .where(
            Bottleneck.id == id,
            Bottleneck.organization_id == membership.organization_id,
        )
    )
    result = await db.execute(query)
    b = result.scalar_one_or_none()

    if not b:
        raise DCPException(
            title="Bottleneck Not Found",
            detail=f"Bottleneck with ID '{id}' was not found in this organization.",
            status_code=404,
            code="BOTTLENECK_NOT_FOUND",
        )

    new_status = payload.status.upper()
    valid_statuses = {"ACTIVE", "ACKNOWLEDGED", "RESOLVED", "IGNORED"}
    if new_status not in valid_statuses:
        raise DCPException(
            title="Invalid Status",
            detail=f"Status '{payload.status}' is invalid. Allowed: {valid_statuses}",
            status_code=400,
            code="INVALID_BOTTLENECK_STATUS",
        )

    b.status = new_status
    if new_status == "RESOLVED":
        b.resolved_at = datetime.now(UTC)
    else:
        b.resolved_at = None

    await db.commit()
    await db.refresh(b)

    return BottleneckResponse(
        id=b.id,
        organization_id=b.organization_id,
        repository_id=b.repository_id,
        repository_name=b.repository.name if b.repository else None,
        bottleneck_type=b.bottleneck_type,
        severity=b.severity,
        confidence=b.confidence,
        title=b.title,
        description=b.description,
        evidence=b.evidence,
        recommendation=b.recommendation,
        detected_at=b.detected_at,
        first_observed_at=b.first_observed_at,
        last_observed_at=b.last_observed_at,
        status=b.status,
        fingerprint=b.fingerprint,
        resolved_at=b.resolved_at,
    )
