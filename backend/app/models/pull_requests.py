import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.commits import GitHubAccount
    from app.models.github import Repository
    from app.models.reviews import PRReview, ReviewRequest


class PullRequest(Base, UUIDMixin, TimestampMixin):
    """Pull Request telemetry and lifecycle analytics record."""

    __tablename__ = "pull_requests"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("github_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    github_pr_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        index=True,
    )
    number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        default="OPEN",
        nullable=False,
        index=True,
    )
    is_draft: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    source_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at_github: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    updated_at_github: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    merged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    first_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    additions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    deletions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    changed_files: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    commit_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    cycle_time_seconds: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    merge_time_seconds: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    first_review_time_seconds: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="pull_requests")
    author: Mapped["GitHubAccount | None"] = relationship("GitHubAccount", back_populates="pull_requests")
    reviews: Mapped[list["PRReview"]] = relationship(
        "PRReview",
        back_populates="pull_request",
        cascade="all, delete-orphan",
    )
    review_requests: Mapped[list["ReviewRequest"]] = relationship(
        "ReviewRequest",
        back_populates="pull_request",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_pull_requests_repo_state_created", "repository_id", "state", "created_at_github"),
        Index("ix_pull_requests_repo_merged", "repository_id", "merged_at"),
        Index("ix_pull_requests_repo_number", "repository_id", "number"),
    )
