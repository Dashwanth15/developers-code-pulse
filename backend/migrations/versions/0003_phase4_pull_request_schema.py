"""0003_phase4_pull_request_schema

Revision ID: 0003_phase4_schema
Revises: 0002_phase3_schema
Create Date: 2026-10-31 17:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase4_schema"
down_revision: str | None = "0002_phase3_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pull_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("github_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("github_pr_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("source_branch", sa.String(255), nullable=False),
        sa.Column("target_branch", sa.String(255), nullable=False),
        sa.Column("created_at_github", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_github", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("additions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cycle_time_seconds", sa.BigInteger(), nullable=True),
        sa.Column("merge_time_seconds", sa.BigInteger(), nullable=True),
        sa.Column("first_review_time_seconds", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_pull_requests_repository_id", "pull_requests", ["repository_id"])
    op.create_index("ix_pull_requests_author_account_id", "pull_requests", ["author_account_id"])
    op.create_index("ix_pull_requests_github_pr_id", "pull_requests", ["github_pr_id"])
    op.create_index("ix_pull_requests_state", "pull_requests", ["state"])
    op.create_index("ix_pull_requests_is_draft", "pull_requests", ["is_draft"])
    op.create_index("ix_pull_requests_created_at_github", "pull_requests", ["created_at_github"])
    op.create_index("ix_pull_requests_closed_at", "pull_requests", ["closed_at"])
    op.create_index("ix_pull_requests_merged_at", "pull_requests", ["merged_at"])
    op.create_index("ix_pull_requests_first_reviewed_at", "pull_requests", ["first_reviewed_at"])
    op.create_index(
        "ix_pull_requests_repo_state_created",
        "pull_requests",
        ["repository_id", "state", "created_at_github"],
    )
    op.create_index("ix_pull_requests_repo_merged", "pull_requests", ["repository_id", "merged_at"])
    op.create_index("ix_pull_requests_repo_number", "pull_requests", ["repository_id", "number"])


def downgrade() -> None:
    op.drop_index("ix_pull_requests_repo_number", table_name="pull_requests")
    op.drop_index("ix_pull_requests_repo_merged", table_name="pull_requests")
    op.drop_index("ix_pull_requests_repo_state_created", table_name="pull_requests")
    op.drop_index("ix_pull_requests_first_reviewed_at", table_name="pull_requests")
    op.drop_index("ix_pull_requests_merged_at", table_name="pull_requests")
    op.drop_index("ix_pull_requests_closed_at", table_name="pull_requests")
    op.drop_index("ix_pull_requests_created_at_github", table_name="pull_requests")
    op.drop_index("ix_pull_requests_is_draft", table_name="pull_requests")
    op.drop_index("ix_pull_requests_state", table_name="pull_requests")
    op.drop_index("ix_pull_requests_github_pr_id", table_name="pull_requests")
    op.drop_index("ix_pull_requests_author_account_id", table_name="pull_requests")
    op.drop_index("ix_pull_requests_repository_id", table_name="pull_requests")
    op.drop_table("pull_requests")
