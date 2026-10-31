import os
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.models.reports import Report, ScheduledReport
from app.schemas.reports import (
    ReportGenerateRequest,
    ReportListResponse,
    ReportResponse,
    ScheduledReportCreateRequest,
    ScheduledReportListResponse,
    ScheduledReportResponse,
    ScheduledReportUpdateRequest,
)
from app.services.auth.dependencies import require_role
from app.services.reports.report_engine import ReportEngine

router = APIRouter(prefix="/reports", tags=["Reporting Engine"])


@router.get(
    "",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Reports",
    description="Retrieves historical generated engineering reports for the authenticated organization.",
)
async def list_reports(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    report_type: Annotated[str | None, Query(description="Filter by type")] = None,
    repository_id: Annotated[uuid.UUID | None, Query(description="Filter by repository")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReportListResponse:
    query = (
        select(Report)
        .options(selectinload(Report.sections))
        .where(Report.organization_id == membership.organization_id)
        .order_by(Report.created_at.desc())
    )

    if report_type:
        query = query.where(Report.report_type == report_type.upper())
    if repository_id:
        query = query.where(Report.repository_id == repository_id)
    if status_filter:
        query = query.where(Report.status == status_filter.upper())

    count_q = (
        select(func.count(Report.id))
        .where(Report.organization_id == membership.organization_id)
    )
    if report_type:
        count_q = count_q.where(Report.report_type == report_type.upper())
    if repository_id:
        count_q = count_q.where(Report.repository_id == repository_id)
    if status_filter:
        count_q = count_q.where(Report.status == status_filter.upper())

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * size
    results = (await db.execute(query.offset(offset).limit(size))).scalars().all()

    items = []
    for r in results:
        resp = ReportResponse.model_validate(r)
        if r.file_reference:
            resp.download_url = f"/api/v1/reports/{r.id}/download"
        items.append(resp)

    return ReportListResponse(
        items=items,
        total=total,
        limit=size,
        offset=offset,
    )


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Report",
    description="Asynchronously compiles a structured engineering report and renders a downloadable PDF document.",
)
async def generate_report_endpoint(
    request: ReportGenerateRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.MEMBER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    engine = ReportEngine(db)
    report = await engine.generate_report(
        organization_id=membership.organization_id,
        report_type=request.report_type,
        repository_id=request.repository_id,
        time_range=request.time_range,
        start_date=request.start_date,
        end_date=request.end_date,
        title=request.title,
        generated_by=membership.user_id,
        include_ai_insights=request.include_ai_insights,
    )

    resp = ReportResponse.model_validate(report)
    if report.file_reference:
        resp.download_url = f"/api/v1/reports/{report.id}/download"
    return resp


@router.get(
    "/scheduled",
    response_model=ScheduledReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Scheduled Reports",
    description="Lists automated periodic report schedules for the authenticated organization.",
)
async def list_scheduled_reports(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduledReportListResponse:
    query = (
        select(ScheduledReport)
        .where(ScheduledReport.organization_id == membership.organization_id)
        .order_by(ScheduledReport.created_at.desc())
    )
    result = await db.execute(query)
    items = result.scalars().all()
    return ScheduledReportListResponse(
        items=[ScheduledReportResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post(
    "/scheduled",
    response_model=ScheduledReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Scheduled Report",
    description="Registers a recurring periodic report generation cadence (WEEKLY, MONTHLY, DAILY).",
)
async def create_scheduled_report(
    request: ScheduledReportCreateRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.MEMBER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduledReportResponse:
    now = datetime.now(UTC)
    scheduled = ScheduledReport(
        id=uuid.uuid4(),
        organization_id=membership.organization_id,
        repository_id=request.repository_id,
        report_type=request.report_type.upper(),
        frequency=request.frequency.upper(),
        next_run_at=now,
        timezone=request.timezone,
        enabled=request.enabled,
        recipients=request.recipients,
        created_by=membership.user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(scheduled)
    await db.commit()
    await db.refresh(scheduled)
    return ScheduledReportResponse.model_validate(scheduled)


@router.patch(
    "/scheduled/{scheduled_id}",
    response_model=ScheduledReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Scheduled Report",
    description="Updates cadence parameters or active status of a scheduled report.",
)
async def update_scheduled_report(
    scheduled_id: uuid.UUID,
    request: ScheduledReportUpdateRequest,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.MEMBER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduledReportResponse:
    query = select(ScheduledReport).where(
        ScheduledReport.id == scheduled_id,
        ScheduledReport.organization_id == membership.organization_id,
    )
    result = await db.execute(query)
    scheduled = result.scalars().first()
    if not scheduled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report configuration not found",
        )

    if request.frequency is not None:
        scheduled.frequency = request.frequency.upper()
    if request.timezone is not None:
        scheduled.timezone = request.timezone
    if request.recipients is not None:
        scheduled.recipients = request.recipients
    if request.enabled is not None:
        scheduled.enabled = request.enabled

    await db.commit()
    await db.refresh(scheduled)
    return ScheduledReportResponse.model_validate(scheduled)


@router.delete(
    "/scheduled/{scheduled_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Scheduled Report",
    description="Removes an automated scheduled report configuration.",
)
async def delete_scheduled_report(
    scheduled_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.MEMBER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    query = select(ScheduledReport).where(
        ScheduledReport.id == scheduled_id,
        ScheduledReport.organization_id == membership.organization_id,
    )
    result = await db.execute(query)
    scheduled = result.scalars().first()
    if not scheduled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report not found",
        )
    await db.delete(scheduled)
    await db.commit()


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Report Details",
    description="Retrieves a specific report along with its structured analytical sections.",
)
async def get_report_details(
    report_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    query = (
        select(Report)
        .options(selectinload(Report.sections))
        .where(
            Report.id == report_id,
            Report.organization_id == membership.organization_id,
        )
    )
    result = await db.execute(query)
    report = result.scalars().first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    resp = ReportResponse.model_validate(report)
    if report.file_reference:
        resp.download_url = f"/api/v1/reports/{report.id}/download"
    return resp


@router.get(
    "/{report_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download PDF Report",
    description="Securely downloads the compiled PDF document for the designated report.",
)
async def download_report_pdf(
    report_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    query = select(Report).where(
        Report.id == report_id,
        Report.organization_id == membership.organization_id,
    )
    result = await db.execute(query)
    report = result.scalars().first()
    if not report or not report.file_reference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF document not found for this report",
        )

    if not os.path.exists(report.file_reference):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored PDF file is missing or expired",
        )

    clean_filename = f"{report.title.replace(' ', '_').replace('/', '_')}.pdf"
    return FileResponse(
        path=report.file_reference,
        media_type="application/pdf",
        filename=clean_filename,
    )
