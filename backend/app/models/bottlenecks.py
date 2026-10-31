import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.auth import Organization
    from app.models.github import Repository


class Bottleneck(Base, UUIDMixin, TimestampMixin):
    """
    Identified workflow bottleneck indicating team delivery friction, review lag,
    or capacity congestion with empirical evidence and actionable recommendations.
    """

    __tablename__ = "bottlenecks"

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
    bottleneck_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # PR_REVIEW_DELAY, APPROVAL_DELAY, MERGE_DELAY, REVIEWER_CONCENTRATION, PR_SIZE_OVERSIZED, REPOSITORY_BACKLOG
    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )  # LOW, MEDIUM, HIGH, CRITICAL
    confidence: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )  # LOW, MEDIUM, HIGH
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )  # Observed values, baselines, affected entity IDs, metrics
    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    first_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="ACTIVE",
        nullable=False,
        index=True,
    )  # ACTIVE, ACKNOWLEDGED, RESOLVED, IGNORED
    fingerprint: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )  # Stable SHA-256 hash preventing duplicate active bottlenecks
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    repository: Mapped["Repository | None"] = relationship("Repository")
    history: Mapped[list["BottleneckHistory"]] = relationship(
        "BottleneckHistory",
        back_populates="bottleneck",
        cascade="all, delete-orphan",
        order_by="BottleneckHistory.recorded_at.desc()",
    )

    __table_args__ = (
        Index("ix_bottlenecks_org_status", "organization_id", "status"),
        Index("ix_bottlenecks_org_fingerprint", "organization_id", "fingerprint"),
        Index("ix_bottlenecks_repo_status", "repository_id", "status"),
    )


class BottleneckHistory(Base, UUIDMixin, TimestampMixin):
    """
    Time-series observations tracking metric evolution and resolution progression
    for an identified bottleneck.
    """

    __tablename__ = "bottleneck_history"

    bottleneck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bottlenecks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observed_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    baseline_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    observation_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    observation_window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Relationships
    bottleneck: Mapped["Bottleneck"] = relationship("Bottleneck", back_populates="history")


class DetectionRun(Base, UUIDMixin, TimestampMixin):
    """
    Audit record of automated or on-demand bottleneck detection execution runs.
    """

    __tablename__ = "detection_runs"

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
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        nullable=False,
        index=True,
    )  # PENDING, RUNNING, COMPLETED, FAILED
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    total_bottlenecks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
