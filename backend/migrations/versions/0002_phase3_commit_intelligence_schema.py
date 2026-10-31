"""0002_phase3_commit_intelligence_schema

Revision ID: 0002_phase3_schema
Revises: 0001_phase2_schema
Create Date: 2026-10-31 16:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase3_schema"
down_revision: str | None = "0001_phase2_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. github_accounts table
    op.create_table(
        "github_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("github_user_id", sa.BigInteger(), nullable=True),
        sa.Column("login", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("user_type", sa.String(50), nullable=False, server_default="User"),
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
    op.create_index("ix_github_accounts_id", "github_accounts", ["id"])
    op.create_index("ix_github_accounts_organization_id", "github_accounts", ["organization_id"])
    op.create_index("ix_github_accounts_github_user_id", "github_accounts", ["github_user_id"])
    op.create_index("ix_github_accounts_login", "github_accounts", ["login"])
    op.create_index("ix_github_accounts_email", "github_accounts", ["email"])
    op.create_index("ix_github_accounts_org_login", "github_accounts", ["organization_id", "login"])

    # 2. commits table
    op.create_table(
        "commits",
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
        sa.Column("commit_sha", sa.String(40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("additions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_changes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("branch_name", sa.String(255), nullable=False, server_default="main"),
        sa.Column("is_merge_commit", sa.Boolean(), nullable=False, server_default=sa.false()),
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
    op.create_index("ix_commits_id", "commits", ["id"])
    op.create_index("ix_commits_repository_id", "commits", ["repository_id"])
    op.create_index("ix_commits_author_account_id", "commits", ["author_account_id"])
    op.create_index("ix_commits_commit_sha", "commits", ["commit_sha"])
    op.create_index("ix_commits_committed_at", "commits", ["committed_at"])
    op.create_index("ix_commits_repo_committed_at", "commits", ["repository_id", "committed_at"])
    op.create_index("ix_commits_repo_sha", "commits", ["repository_id", "commit_sha"], unique=True)


def downgrade() -> None:
    op.drop_table("commits")
    op.drop_table("github_accounts")
