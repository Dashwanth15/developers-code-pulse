import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.auth import Organization
    from app.models.github import Repository
    from app.models.pull_requests import PullRequest


class GitHubAccount(Base, UUIDMixin, TimestampMixin):
    """Normalized GitHub contributor or bot identity scoped to an Organization."""

    __tablename__ = "github_accounts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    github_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
    )
    login: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    user_type: Mapped[str] = mapped_column(String(50), default="User", nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    commits: Mapped[list["Commit"]] = relationship(
        "Commit",
        back_populates="author",
        cascade="all, delete-orphan",
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(
        "PullRequest",
        back_populates="author",
    )

    __table_args__ = (Index("ix_github_accounts_org_login", "organization_id", "login"),)


class Commit(Base, UUIDMixin, TimestampMixin):
    """Commit telemetry record within a monitored repository."""

    __tablename__ = "commits"

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
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    additions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_changes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    branch_name: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    is_merge_commit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="commits")
    author: Mapped[GitHubAccount | None] = relationship("GitHubAccount", back_populates="commits")

    __table_args__ = (
        Index("ix_commits_repo_committed_at", "repository_id", "committed_at"),
        Index("ix_commits_repo_sha", "repository_id", "commit_sha", unique=True),
    )
