import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReportSectionBase(BaseModel):
    section_type: str
    title: str
    content: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    order_index: int = 0


class ReportSectionResponse(ReportSectionBase):
    id: uuid.UUID
    report_id: uuid.UUID
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReportBase(BaseModel):
    report_type: str
    title: str
    reporting_period_start: datetime
    reporting_period_end: datetime


class ReportGenerateRequest(BaseModel):
    report_type: str = Field(
        default="ENGINEERING_HEALTH",
        description="Type: ENGINEERING_HEALTH, WEEKLY, MONTHLY, REPOSITORY_HEALTH, DORA",
    )
    repository_id: uuid.UUID | None = None
    time_range: str = Field(
        default="30d",
        description="Time range preset: 7d, 14d, 30d, 90d, or custom",
    )
    start_date: datetime | None = None
    end_date: datetime | None = None
    title: str | None = None
    include_ai_insights: bool = True
    format: str = "pdf"


class ReportResponse(ReportBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    repository_id: uuid.UUID | None
    status: str
    file_reference: str | None = None
    download_url: str | None = None
    generated_at: datetime | None = None
    generated_by: uuid.UUID | None = None
    sections: list[ReportSectionResponse] = []
    metadata_payload: dict[str, Any] | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    limit: int
    offset: int


class ScheduledReportCreateRequest(BaseModel):
    report_type: str = Field(default="WEEKLY")
    repository_id: uuid.UUID | None = None
    frequency: str = Field(default="WEEKLY", description="DAILY, WEEKLY, MONTHLY")
    timezone: str = Field(default="UTC")
    recipients: list[str] = Field(default_factory=list)
    enabled: bool = True


class ScheduledReportUpdateRequest(BaseModel):
    frequency: str | None = None
    timezone: str | None = None
    recipients: list[str] | None = None
    enabled: bool | None = None


class ScheduledReportResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    repository_id: uuid.UUID | None
    report_type: str
    frequency: str
    next_run_at: datetime
    timezone: str
    enabled: bool
    recipients: list[str]
    created_by: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ScheduledReportListResponse(BaseModel):
    items: list[ScheduledReportResponse]
    total: int
