"""0006_phase7_dora_and_team_schema

Revision ID: 0006_phase7_schema
Revises: 0005_phase6_schema
Create Date: 2026-10-31 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase7_schema"
down_revision: str | None = "0005_phase6_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. deployments table
    op.create_table(
        "deployments",
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
        sa.Column("external_deployment_id", sa.String(255), nullable=True),
        sa.Column("environment", sa.String(64), nullable=False, server_default="production"),
        sa.Column("status", sa.String(32), nullable=False, server_default="SUCCESS"),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("commit_sha", sa.String(40), nullable=True),
        sa.Column("ref_name", sa.String(255), nullable=True),
        sa.Column("source", sa.String(64), nullable=False, server_default="GITHUB_ACTIONS"),
        sa.Column("lead_time_seconds", sa.Float(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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

    op.create_index("ix_deployments_id", "deployments", ["id"])
    op.create_index("ix_deployments_organization_id", "deployments", ["organization_id"])
    op.create_index("ix_deployments_repository_id", "deployments", ["repository_id"])
    op.create_index("ix_deployments_external_deployment_id", "deployments", ["external_deployment_id"])
    op.create_index("ix_deployments_environment", "deployments", ["environment"])
    op.create_index("ix_deployments_status", "deployments", ["status"])
    op.create_index("ix_deployments_deployed_at", "deployments", ["deployed_at"])
    op.create_index("ix_deployments_commit_sha", "deployments", ["commit_sha"])
    op.create_index("ix_deployments_source", "deployments", ["source"])
    op.create_index(
        "ix_deployments_org_env_deployed",
        "deployments",
        ["organization_id", "environment", "deployed_at"],
    )
    op.create_index(
        "ix_deployments_org_repo_env",
        "deployments",
        ["organization_id", "repository_id", "environment"],
    )

    # 2. incidents table
    op.create_table(
        "incidents",
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
        sa.Column("external_incident_id", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recovery_duration_seconds", sa.Float(), nullable=True),
        sa.Column("source", sa.String(64), nullable=False, server_default="MANUAL"),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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

    op.create_index("ix_incidents_id", "incidents", ["id"])
    op.create_index("ix_incidents_organization_id", "incidents", ["organization_id"])
    op.create_index("ix_incidents_repository_id", "incidents", ["repository_id"])
    op.create_index("ix_incidents_external_incident_id", "incidents", ["external_incident_id"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_started_at", "incidents", ["started_at"])
    op.create_index("ix_incidents_resolved_at", "incidents", ["resolved_at"])
    op.create_index("ix_incidents_source", "incidents", ["source"])
    op.create_index("ix_incidents_org_started", "incidents", ["organization_id", "started_at"])
    op.create_index("ix_incidents_org_status", "incidents", ["organization_id", "status"])

    # 3. deployment_incidents table
    op.create_table(
        "deployment_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deployment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deployments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(32), nullable=False, server_default="CAUSED_BY"),
        sa.Column("confidence", sa.String(16), nullable=False, server_default="HIGH"),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.UniqueConstraint("deployment_id", "incident_id", name="uq_deployment_incident"),
    )

    op.create_index("ix_deployment_incidents_id", "deployment_incidents", ["id"])
    op.create_index("ix_deployment_incidents_deployment_id", "deployment_incidents", ["deployment_id"])
    op.create_index("ix_deployment_incidents_incident_id", "deployment_incidents", ["incident_id"])

    # 4. dora_metric_snapshots table
    op.create_table(
        "dora_metric_snapshots",
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
        sa.Column("metric_type", sa.String(64), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="CALCULATED"),
        sa.Column("performance_level", sa.String(32), nullable=False, server_default="UNKNOWN"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_completeness", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("methodology_version", sa.String(32), nullable=False, server_default="v1.0"),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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

    op.create_index("ix_dora_snapshots_id", "dora_metric_snapshots", ["id"])
    op.create_index("ix_dora_snapshots_organization_id", "dora_metric_snapshots", ["organization_id"])
    op.create_index("ix_dora_snapshots_repository_id", "dora_metric_snapshots", ["repository_id"])
    op.create_index("ix_dora_snapshots_metric_type", "dora_metric_snapshots", ["metric_type"])
    op.create_index("ix_dora_snapshots_status", "dora_metric_snapshots", ["status"])
    op.create_index("ix_dora_snapshots_performance_level", "dora_metric_snapshots", ["performance_level"])
    op.create_index(
        "ix_dora_snapshots_org_type_period",
        "dora_metric_snapshots",
        ["organization_id", "metric_type", "period_start", "period_end"],
    )


def downgrade() -> None:
    # 4. dora_metric_snapshots
    op.drop_index("ix_dora_snapshots_org_type_period", table_name="dora_metric_snapshots")
    op.drop_index("ix_dora_snapshots_performance_level", table_name="dora_metric_snapshots")
    op.drop_index("ix_dora_snapshots_status", table_name="dora_metric_snapshots")
    op.drop_index("ix_dora_snapshots_metric_type", table_name="dora_metric_snapshots")
    op.drop_index("ix_dora_snapshots_repository_id", table_name="dora_metric_snapshots")
    op.drop_index("ix_dora_snapshots_organization_id", table_name="dora_metric_snapshots")
    op.drop_index("ix_dora_snapshots_id", table_name="dora_metric_snapshots")
    op.drop_table("dora_metric_snapshots")

    # 3. deployment_incidents
    op.drop_index("ix_deployment_incidents_incident_id", table_name="deployment_incidents")
    op.drop_index("ix_deployment_incidents_deployment_id", table_name="deployment_incidents")
    op.drop_index("ix_deployment_incidents_id", table_name="deployment_incidents")
    op.drop_table("deployment_incidents")

    # 2. incidents
    op.drop_index("ix_incidents_org_status", table_name="incidents")
    op.drop_index("ix_incidents_org_started", table_name="incidents")
    op.drop_index("ix_incidents_source", table_name="incidents")
    op.drop_index("ix_incidents_resolved_at", table_name="incidents")
    op.drop_index("ix_incidents_started_at", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_external_incident_id", table_name="incidents")
    op.drop_index("ix_incidents_repository_id", table_name="incidents")
    op.drop_index("ix_incidents_organization_id", table_name="incidents")
    op.drop_index("ix_incidents_id", table_name="incidents")
    op.drop_table("incidents")

    # 1. deployments
    op.drop_index("ix_deployments_org_repo_env", table_name="deployments")
    op.drop_index("ix_deployments_org_env_deployed", table_name="deployments")
    op.drop_index("ix_deployments_source", table_name="deployments")
    op.drop_index("ix_deployments_commit_sha", table_name="deployments")
    op.drop_index("ix_deployments_deployed_at", table_name="deployments")
    op.drop_index("ix_deployments_status", table_name="deployments")
    op.drop_index("ix_deployments_environment", table_name="deployments")
    op.drop_index("ix_deployments_external_deployment_id", table_name="deployments")
    op.drop_index("ix_deployments_repository_id", table_name="deployments")
    op.drop_index("ix_deployments_organization_id", table_name="deployments")
    op.drop_index("ix_deployments_id", table_name="deployments")
    op.drop_table("deployments")
