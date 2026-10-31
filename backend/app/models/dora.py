import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.auth import Organization
    from app.models.github import Repository


class Deployment(Base, UUIDMixin, TimestampMixin):
    """
    Production and environment deployment event, tracking code releases,
    workflow runs, execution statuses, and end-to-end lead times.
    """

    __tablename__ = "deployments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_deployment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    environment: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="production",
        index=True,
    )  # production, staging, development
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SUCCESS",
        index=True,
    )  # SUCCESS, FAILURE, IN_PROGRESS, CANCELLED, QUEUED
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )
    ref_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="GITHUB_ACTIONS",
        index=True,
    )  # GITHUB_ACTIONS, GITHUB_DEPLOYMENT, GITHUB_RELEASE, EXTERNAL_API, WEBHOOK
    lead_time_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        lazy="selectin",
    )
    repository: Mapped["Repository | None"] = relationship(
        "Repository",
        lazy="selectin",
    )
    incident_links: Mapped[list["DeploymentIncident"]] = relationship(
        "DeploymentIncident",
        back_populates="deployment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_deployments_org_env_deployed", "organization_id", "environment", "deployed_at"),
        Index("ix_deployments_org_repo_env", "organization_id", "repository_id", "environment"),
    )


class Incident(Base, UUIDMixin, TimestampMixin):
    """
    Production incident or outage record used to calculate Mean Time to Recovery (MTTR)
    and Change Failure Rate (CFR).
    """

    __tablename__ = "incidents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_incident_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="MEDIUM",
        index=True,
    )  # LOW, MEDIUM, HIGH, CRITICAL
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="OPEN",
        index=True,
    )  # OPEN, INVESTIGATING, RESOLVED, CLOSED
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    recovery_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="MANUAL",
        index=True,
    )  # MANUAL, GITHUB_ISSUE, PAGERDUTY, OPSGENIE, DATADOG, EXTERNAL_API
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        lazy="selectin",
    )
    repository: Mapped["Repository | None"] = relationship(
        "Repository",
        lazy="selectin",
    )
    deployment_links: Mapped[list["DeploymentIncident"]] = relationship(
        "DeploymentIncident",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_incidents_org_started", "organization_id", "started_at"),
        Index("ix_incidents_org_status", "organization_id", "status"),
    )


class DeploymentIncident(Base, UUIDMixin, TimestampMixin):
    """
    Correlation entity linking production deployments to incidents that they caused
    or that were detected immediately after rollout.
    """

    __tablename__ = "deployment_incidents"

    deployment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="CAUSED_BY",
    )  # CAUSED_BY, DETECTED_AFTER, RESOLVED_BY
    confidence: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="HIGH",
    )  # HIGH, MEDIUM, LOW
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    deployment: Mapped["Deployment"] = relationship(
        "Deployment",
        back_populates="incident_links",
    )
    incident: Mapped["Incident"] = relationship(
        "Incident",
        back_populates="deployment_links",
    )

    __table_args__ = (
        UniqueConstraint("deployment_id", "incident_id", name="uq_deployment_incident"),
    )


class DORAMetricSnapshot(Base, UUIDMixin, TimestampMixin):
    """
    Periodic aggregation snapshot storing computed DORA metrics, performance tiers,
    sample sizes, and data completeness.
    """

    __tablename__ = "dora_metric_snapshots"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metric_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # DEPLOYMENT_FREQUENCY, LEAD_TIME_FOR_CHANGES, CHANGE_FAILURE_RATE, MEAN_TIME_TO_RECOVERY
    metric_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="CALCULATED",
        index=True,
    )  # CALCULATED, INSUFFICIENT_DATA, REQUIRES_INTEGRATION
    performance_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="UNKNOWN",
        index=True,
    )  # ELITE, HIGH, MEDIUM, LOW, UNKNOWN
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    sample_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    data_completeness: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    methodology_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="v1.0",
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        Index("ix_dora_snapshots_org_type_period", "organization_id", "metric_type", "period_start", "period_end"),
    )
