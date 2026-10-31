import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DORATrendPoint(BaseModel):
    """Timestamped metric point for historical DORA trend series."""

    date: str
    value: float | None = None
    sample_size: int = 0


class DORAMetricCard(BaseModel):
    """Standardized representation for a single primary DORA metric."""

    metric_type: str
    title: str
    status: str  # CALCULATED, INSUFFICIENT_DATA, REQUIRES_INTEGRATION
    value: float | None = None
    formatted_value: str
    unit: str
    performance_level: str  # ELITE, HIGH, MEDIUM, LOW, UNKNOWN
    performance_label: str
    trend_direction: str = "NONE"  # IMPROVED, DEGRADED, STABLE, NONE
    trend_percentage: float | None = None
    sample_size: int = 0
    data_completeness: float = 1.0
    period: str
    data_source: str
    methodology: str
    context_message: str | None = None


class DeploymentFrequencyDetail(BaseModel):
    """Comprehensive details and trend for Deployment Frequency."""

    card: DORAMetricCard
    daily_deployments: float = 0.0
    weekly_deployments: float = 0.0
    monthly_deployments: float = 0.0
    total_deployments: int = 0
    successful_deployments: int = 0
    failed_deployments: int = 0
    history: list[DORATrendPoint] = Field(default_factory=list)
    environment_breakdown: dict[str, int] = Field(default_factory=dict)


class LeadTimeDetail(BaseModel):
    """Comprehensive details and trend for Lead Time for Changes."""

    card: DORAMetricCard
    median_hours: float | None = None
    p75_hours: float | None = None
    average_hours: float | None = None
    commit_to_merge_hours: float | None = None
    merge_to_deploy_hours: float | None = None
    sample_size: int = 0
    traceability_rate: float = 0.0
    history: list[DORATrendPoint] = Field(default_factory=list)


class ChangeFailureRateDetail(BaseModel):
    """Comprehensive details and trend for Change Failure Rate."""

    card: DORAMetricCard
    failure_rate_percent: float | None = None
    total_production_deployments: int = 0
    failed_deployments: int = 0
    incident_linked_deployments: int = 0
    degraded_deployments: int = 0
    history: list[DORATrendPoint] = Field(default_factory=list)


class RecoveryTimeDetail(BaseModel):
    """Comprehensive details and trend for Mean Time to Recovery (MTTR)."""

    card: DORAMetricCard
    median_hours: float | None = None
    p75_hours: float | None = None
    average_hours: float | None = None
    total_incidents: int = 0
    resolved_incidents: int = 0
    open_incidents: int = 0
    history: list[DORATrendPoint] = Field(default_factory=list)


class RepositoryDORAOverview(BaseModel):
    """DORA indicators calculated for an individual repository."""

    repository_id: uuid.UUID
    repository_name: str
    deployment_frequency: DORAMetricCard
    lead_time: DORAMetricCard
    change_failure_rate: DORAMetricCard
    mean_time_to_recovery: DORAMetricCard


class DORAOverviewResponse(BaseModel):
    """Consolidated organization DORA report across all four pillars."""

    organization_id: uuid.UUID
    time_window: str
    start_date: datetime
    end_date: datetime
    overall_performance: str  # ELITE, HIGH, MEDIUM, LOW, UNKNOWN
    deployment_frequency: DORAMetricCard
    lead_time_for_changes: DORAMetricCard
    change_failure_rate: DORAMetricCard
    mean_time_to_recovery: DORAMetricCard
    repository_breakdowns: list[RepositoryDORAOverview] = Field(default_factory=list)
    integration_status: dict[str, bool] = Field(
        default_factory=lambda: {
            "github_actions": True,
            "github_deployments": True,
            "incident_system": False,
        }
    )


class DeploymentResponse(BaseModel):
    """Deployment record detail view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    repository_id: uuid.UUID | None = None
    repository_name: str | None = None
    external_deployment_id: str | None = None
    environment: str
    status: str
    deployed_at: datetime
    completed_at: datetime | None = None
    commit_sha: str | None = None
    ref_name: str | None = None
    source: str
    lead_time_seconds: float | None = None
    metadata_payload: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    created_at: datetime


class DeploymentListResponse(BaseModel):
    """Paginated list of deployments."""

    items: list[DeploymentResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 1


class DeploymentCreateRequest(BaseModel):
    """Payload to register a deployment event manually or from external adapter."""

    repository_id: uuid.UUID | None = None
    external_deployment_id: str | None = None
    environment: str = "production"
    status: str = "SUCCESS"  # SUCCESS, FAILURE, IN_PROGRESS, CANCELLED
    deployed_at: datetime
    completed_at: datetime | None = None
    commit_sha: str | None = None
    ref_name: str | None = None
    source: str = "EXTERNAL_API"
    lead_time_seconds: float | None = None
    metadata_payload: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class IncidentResponse(BaseModel):
    """Incident record detail view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    repository_id: uuid.UUID | None = None
    repository_name: str | None = None
    external_incident_id: str | None = None
    title: str
    severity: str
    status: str
    started_at: datetime
    resolved_at: datetime | None = None
    recovery_duration_seconds: float | None = None
    source: str
    metadata_payload: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    created_at: datetime


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""

    items: list[IncidentResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 1


class IncidentCreateRequest(BaseModel):
    """Payload to register an incident manually or via webhook."""

    repository_id: uuid.UUID | None = None
    external_incident_id: str | None = None
    title: str
    severity: str = "MEDIUM"
    status: str = "OPEN"
    started_at: datetime
    resolved_at: datetime | None = None
    source: str = "MANUAL"
    deployment_id: uuid.UUID | None = None
    metadata_payload: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class DeploymentSyncRequest(BaseModel):
    """Trigger deployment ingestion synchronization."""

    repository_id: uuid.UUID | None = None
    environment: str | None = None
    force_resync: bool = False


class IncidentSyncRequest(BaseModel):
    """Trigger incident ingestion synchronization."""

    repository_id: uuid.UUID | None = None
    source: str | None = None


class SyncResultResponse(BaseModel):
    """Outcome of synchronization ingestion."""

    synced_count: int = 0
    status: str = "SUCCESS"
    message: str = "Synchronization completed successfully."
