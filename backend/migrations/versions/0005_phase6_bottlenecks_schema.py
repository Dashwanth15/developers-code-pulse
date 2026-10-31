"""0005_phase6_bottlenecks_schema

Revision ID: 0005_phase6_schema
Revises: 0004_phase5_schema
Create Date: 2026-10-31 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase6_schema"
down_revision: str | None = "0004_phase5_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. bottlenecks table
    op.create_table(
        "bottlenecks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("bottleneck_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index("ix_bottlenecks_id", "bottlenecks", ["id"])
    op.create_index("ix_bottlenecks_organization_id", "bottlenecks", ["organization_id"])
    op.create_index("ix_bottlenecks_repository_id", "bottlenecks", ["repository_id"])
    op.create_index("ix_bottlenecks_bottleneck_type", "bottlenecks", ["bottleneck_type"])
    op.create_index("ix_bottlenecks_severity", "bottlenecks", ["severity"])
    op.create_index("ix_bottlenecks_confidence", "bottlenecks", ["confidence"])
    op.create_index("ix_bottlenecks_detected_at", "bottlenecks", ["detected_at"])
    op.create_index("ix_bottlenecks_status", "bottlenecks", ["status"])
    op.create_index("ix_bottlenecks_fingerprint", "bottlenecks", ["fingerprint"])
    op.create_index("ix_bottlenecks_org_status", "bottlenecks", ["organization_id", "status"])
    op.create_index("ix_bottlenecks_org_fingerprint", "bottlenecks", ["organization_id", "fingerprint"])
    op.create_index("ix_bottlenecks_repo_status", "bottlenecks", ["repository_id", "status"])

    # 2. bottleneck_history table
    op.create_table(
        "bottleneck_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bottleneck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bottlenecks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("observation_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index("ix_bottleneck_history_id", "bottleneck_history", ["id"])
    op.create_index("ix_bottleneck_history_bottleneck_id", "bottleneck_history", ["bottleneck_id"])
    op.create_index("ix_bottleneck_history_recorded_at", "bottleneck_history", ["recorded_at"])

    # 3. detection_runs table
    op.create_table(
        "detection_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_bottlenecks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index("ix_detection_runs_id", "detection_runs", ["id"])
    op.create_index("ix_detection_runs_organization_id", "detection_runs", ["organization_id"])
    op.create_index("ix_detection_runs_repository_id", "detection_runs", ["repository_id"])
    op.create_index("ix_detection_runs_status", "detection_runs", ["status"])
    op.create_index("ix_detection_runs_started_at", "detection_runs", ["started_at"])


def downgrade() -> None:
    # 1. detection_runs
    op.drop_index("ix_detection_runs_started_at", table_name="detection_runs")
    op.drop_index("ix_detection_runs_status", table_name="detection_runs")
    op.drop_index("ix_detection_runs_repository_id", table_name="detection_runs")
    op.drop_index("ix_detection_runs_organization_id", table_name="detection_runs")
    op.drop_index("ix_detection_runs_id", table_name="detection_runs")
    op.drop_table("detection_runs")

    # 2. bottleneck_history
    op.drop_index("ix_bottleneck_history_recorded_at", table_name="bottleneck_history")
    op.drop_index("ix_bottleneck_history_bottleneck_id", table_name="bottleneck_history")
    op.drop_index("ix_bottleneck_history_id", table_name="bottleneck_history")
    op.drop_table("bottleneck_history")

    # 3. bottlenecks
    op.drop_index("ix_bottlenecks_repo_status", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_org_fingerprint", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_org_status", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_fingerprint", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_status", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_detected_at", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_confidence", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_severity", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_bottleneck_type", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_repository_id", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_organization_id", table_name="bottlenecks")
    op.drop_index("ix_bottlenecks_id", table_name="bottlenecks")
    op.drop_table("bottlenecks")
