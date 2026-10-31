import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.auth import Organization, OrganizationMember, Role
from app.models.reports import AIInsight
from app.schemas.insights import (
    AIInsightGenerateRequest,
    AIInsightListResponse,
    AIInsightResponse,
)
from app.services.ai.factory import get_ai_provider
from app.services.analytics.dora_metrics import DORAMetricsService
from app.services.analytics.team_intelligence import TeamIntelligenceService
from app.services.auth.dependencies import require_role
from app.services.reports.report_engine import ReportEngine

router = APIRouter(prefix="/insights", tags=["AI Engineering Insights"])


@router.get(
    "",
    response_model=AIInsightListResponse,
    status_code=status.HTTP_200_OK,
    summary="List AI Insights",
    description="Retrieves evidence-backed AI insights, delivery diagnostics, and strategic recommendations.",
)
async def list_insights(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    insight_type: Annotated[str | None, Query(description="Filter by type")] = None,
    repository_id: Annotated[uuid.UUID | None, Query(description="Filter by repository")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status (ACTIVE, ARCHIVED)")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AIInsightListResponse:
    query = (
        select(AIInsight)
        .where(AIInsight.organization_id == membership.organization_id)
        .order_by(AIInsight.generated_at.desc())
        .limit(limit)
    )

    if insight_type:
        query = query.where(AIInsight.insight_type == insight_type.upper())
    if repository_id:
        query = query.where(AIInsight.repository_id == repository_id)
    if status_filter:
        query = query.where(AIInsight.status == status_filter.upper())

    results = (await db.execute(query)).scalars().all()
    provider = get_ai_provider()

    return AIInsightListResponse(
        items=[AIInsightResponse.model_validate(i) for i in results],
        total=len(results),
        executive_summary=results[0].explanation if results else None,
        ai_provider_configured=provider.is_available(),
        provider_name=getattr(provider, "model", "deterministic_rules_engine"),
    )


@router.post(
    "/generate",
    response_model=AIInsightListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI Insights",
    description="Analyzes live engineering flow metrics and generates structured, evidence-backed insights.",
)
async def generate_insights_endpoint(
    request: AIInsightGenerateRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.MEMBER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIInsightListResponse:
    cur_start, cur_end, _, _, period_label = ReportEngine.resolve_time_window(request.time_range)

    org_res = await db.execute(select(Organization).where(Organization.id == membership.organization_id))
    org = org_res.scalars().first()
    org_name = org.name if org else "Engineering Organization"

    team_service = TeamIntelligenceService(db)
    dora_service = DORAMetricsService(db)
    engine = ReportEngine(db)

    team_data = await team_service.get_team_intelligence(
        organization_id=membership.organization_id,
        repository_id=request.repository_id,
        start_date=cur_start,
        end_date=cur_end,
    )
    dora_data = await dora_service.get_dora_overview(
        organization_id=membership.organization_id,
        repository_id=request.repository_id,
        start_date=cur_start,
        end_date=cur_end,
    )
    bottlenecks = await engine._fetch_active_bottlenecks(membership.organization_id, request.repository_id)

    metrics_payload = {
        "team": team_data.model_dump(),
        "dora": dora_data.model_dump(),
        "bottlenecks": bottlenecks,
        "period_label": period_label,
        "recommendations": team_data.systemic_recommendations,
    }

    provider = get_ai_provider()
    raw_insights = await provider.generate_insights(
        metrics_payload=metrics_payload,
        organization_name=org_name,
        period_label=period_label,
        focus_areas=request.focus_areas,
    )
    exec_summary = await provider.generate_executive_summary(
        metrics_payload=metrics_payload,
        organization_name=org_name,
        period_label=period_label,
    )

    created_entities: list[AIInsight] = []
    for raw in raw_insights:
        entity = AIInsight(
            organization_id=membership.organization_id,
            repository_id=request.repository_id,
            insight_type=raw.get("insight_type", "HEALTH_DIAGNOSTIC"),
            title=raw.get("title", "Delivery Insight"),
            explanation=raw.get("explanation", ""),
            evidence=raw.get("evidence", {}),
            recommendation=raw.get("recommendation"),
            confidence=float(raw.get("confidence", 1.0)),
            provider=getattr(provider, "__class__", type).__name__,
            model=getattr(provider, "model", "rules_engine"),
            generated_at=datetime.now(UTC),
            status="ACTIVE",
        )
        db.add(entity)
        created_entities.append(entity)

    await db.commit()
    for e in created_entities:
        await db.refresh(e)

    return AIInsightListResponse(
        items=[AIInsightResponse.model_validate(e) for e in created_entities],
        total=len(created_entities),
        executive_summary=exec_summary,
        ai_provider_configured=provider.is_available(),
        provider_name=getattr(provider, "model", "deterministic_rules_engine"),
    )


@router.get(
    "/{insight_id}",
    response_model=AIInsightResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Insight Details",
    description="Retrieves a specific evidence-backed insight and its analytical citations.",
)
async def get_insight_details(
    insight_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIInsightResponse:
    query = select(AIInsight).where(
        AIInsight.id == insight_id,
        AIInsight.organization_id == membership.organization_id,
    )
    result = await db.execute(query)
    insight = result.scalars().first()
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI Insight not found",
        )
    return AIInsightResponse.model_validate(insight)
