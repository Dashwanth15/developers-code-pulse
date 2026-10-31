import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.commits import GitHubAccount
    from app.models.pull_requests import PullRequest


class PRReview(Base, UUIDMixin, TimestampMixin):
    """Peer review submission record on a Pull Request."""

    __tablename__ = "pr_reviews"

    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("github_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    github_review_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship("PullRequest", back_populates="reviews")
    reviewer: Mapped["GitHubAccount | None"] = relationship("GitHubAccount", back_populates="reviews_conducted")

    __table_args__ = (
        Index("ix_pr_reviews_pr_submitted", "pull_request_id", "submitted_at"),
    )


class ReviewRequest(Base, UUIDMixin, TimestampMixin):
    """Formal review request assignment tracking for queue depth."""

    __tablename__ = "review_requests"

    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("github_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    fulfilled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        nullable=False,
        index=True,
    )  # PENDING, COMPLETED, REMOVED

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship("PullRequest", back_populates="review_requests")
    reviewer: Mapped["GitHubAccount"] = relationship("GitHubAccount")

    __table_args__ = (
        Index("ix_review_requests_pr_status", "pull_request_id", "status"),
    )
