"""0004_phase5_review_intelligence_schema

Revision ID: 0004_phase5_schema
Revises: 0003_phase4_schema
Create Date: 2026-10-31 17:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase5_schema"
down_revision: str | None = "0003_phase4_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. pr_reviews table
    op.create_table(
        "pr_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pull_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pull_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("github_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("github_review_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("commit_sha", sa.String(40), nullable=True),
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

    op.create_index("ix_pr_reviews_pull_request_id", "pr_reviews", ["pull_request_id"])
    op.create_index("ix_pr_reviews_reviewer_account_id", "pr_reviews", ["reviewer_account_id"])
    op.create_index("ix_pr_reviews_github_review_id", "pr_reviews", ["github_review_id"])
    op.create_index("ix_pr_reviews_state", "pr_reviews", ["state"])
    op.create_index("ix_pr_reviews_submitted_at", "pr_reviews", ["submitted_at"])
    op.create_index("ix_pr_reviews_pr_submitted", "pr_reviews", ["pull_request_id", "submitted_at"])

    # 2. review_requests table
    op.create_table(
        "review_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pull_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pull_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("github_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
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

    op.create_index("ix_review_requests_pull_request_id", "review_requests", ["pull_request_id"])
    op.create_index("ix_review_requests_reviewer_account_id", "review_requests", ["reviewer_account_id"])
    op.create_index("ix_review_requests_status", "review_requests", ["status"])
    op.create_index(
        "ix_review_requests_pr_status", "review_requests", ["pull_request_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_review_requests_pr_status", table_name="review_requests")
    op.drop_index("ix_review_requests_status", table_name="review_requests")
    op.drop_index("ix_review_requests_reviewer_account_id", table_name="review_requests")
    op.drop_index("ix_review_requests_pull_request_id", table_name="review_requests")
    op.drop_table("review_requests")

    op.drop_index("ix_pr_reviews_pr_submitted", table_name="pr_reviews")
    op.drop_index("ix_pr_reviews_submitted_at", table_name="pr_reviews")
    op.drop_index("ix_pr_reviews_state", table_name="pr_reviews")
    op.drop_index("ix_pr_reviews_github_review_id", table_name="pr_reviews")
    op.drop_index("ix_pr_reviews_reviewer_account_id", table_name="pr_reviews")
    op.drop_index("ix_pr_reviews_pull_request_id", table_name="pr_reviews")
    op.drop_table("pr_reviews")
