import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.auth import Organization, User
    from app.models.github import Repository


class Report(Base, UUIDMixin, TimestampMixin):
    """
    Generated executive, engineering, or team delivery report.
    Tracks report type, time window, compilation status, and rendered file reference.
    """

    __tablename__ = "reports"

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
    report_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # ENGINEERING_HEALTH, WEEKLY, MONTHLY, REPOSITORY_HEALTH, DORA
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    reporting_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    reporting_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )  # PENDING, GENERATING, COMPLETED, FAILED
    file_reference: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    repository: Mapped["Repository | None"] = relationship("Repository")
    creator: Mapped["User | None"] = relationship("User")
    sections: Mapped[list["ReportSection"]] = relationship(
        "ReportSection",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportSection.order_index",
    )

    __table_args__ = (
        Index("ix_reports_org_type_period", "organization_id", "report_type", "reporting_period_end"),
        Index("ix_reports_org_status", "organization_id", "status"),
    )


class ReportSection(Base, UUIDMixin, TimestampMixin):
    """
    Constituent section of an engineering report (e.g., Executive Summary,
    KPI Cards, Bottleneck Radar, DORA Stability, Systemic Recommendations).
    """

    __tablename__ = "report_sections"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # EXECUTIVE_SUMMARY, KPI_SUMMARY, THROUGHPUT, CADENCE, BOTTLENECK_ANALYSIS, DORA_METRICS, RECOMMENDATIONS, METHODOLOGY
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    evidence: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="sections")

    __table_args__ = (
        Index("ix_report_sections_report_order", "report_id", "order_index"),
    )


class AIInsight(Base, UUIDMixin, TimestampMixin):
    """
    Evidence-backed, AI-generated or deterministic engineering explanation.
    Correlates measured throughput, cycle times, bottleneck distributions,
    and DORA metrics with clear, verifiable rationale without hallucinating data.
    """

    __tablename__ = "ai_insights"

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
    insight_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # EXECUTIVE_SUMMARY, TREND_INTERPRETATION, BOTTLENECK_EXPLANATION, STRATEGIC_RECOMMENDATION, HEALTH_DIAGNOSTIC
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    recommendation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="deterministic",
    )  # gemini, openai, anthropic, deterministic
    model: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="gemini-1.5-flash",
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
    )  # ACTIVE, ARCHIVED, DISMISSED

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    repository: Mapped["Repository | None"] = relationship("Repository")

    __table_args__ = (
        Index("ix_ai_insights_org_type", "organization_id", "insight_type"),
        Index("ix_ai_insights_org_status", "organization_id", "status"),
    )


class ScheduledReport(Base, UUIDMixin, TimestampMixin):
    """
    Automated cron/periodic reporting cadence.
    Periodically generates designated report types and notifies distribution recipients.
    """

    __tablename__ = "scheduled_reports"

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
    report_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # ENGINEERING_HEALTH, WEEKLY, MONTHLY, REPOSITORY_HEALTH, DORA
    frequency: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # DAILY, WEEKLY, MONTHLY
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="UTC",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    recipients: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    repository: Mapped["Repository | None"] = relationship("Repository")
    creator: Mapped["User | None"] = relationship("User")

    __table_args__ = (
        Index("ix_scheduled_reports_org_enabled", "organization_id", "enabled", "next_run_at"),
    )
