import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github import Repository
from app.models.pull_requests import PullRequest
from app.services.github.commit_service import resolve_or_create_github_account
from app.services.github.github_client import GitHubClient

logger = structlog.get_logger(__name__)


def parse_github_datetime(val: str | None) -> datetime | None:
    """Safely converts ISO-8601 GitHub datetime strings to UTC datetime."""
    if not val:
        return None
    try:
        # Handles 2026-10-31T17:00:00Z and offsets
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


async def ingest_pull_request_payload(
    db: AsyncSession,
    repository: Repository,
    pr_data: dict,
    action: str | None = None,
) -> PullRequest:
    """Normalizes and upserts a GitHub Pull Request payload from webhook or REST API."""
    github_pr_id = pr_data.get("id")
    if not github_pr_id:
        raise ValueError("Missing github_pr_id in pull request payload")

    pr_number = pr_data.get("number", 0)
    title = pr_data.get("title", f"PR #{pr_number}")
    is_draft = bool(pr_data.get("draft", False))

    raw_state = pr_data.get("state", "open").upper()
    merged_at = parse_github_datetime(pr_data.get("merged_at"))
    closed_at = parse_github_datetime(pr_data.get("closed_at"))

    if merged_at:
        state = "MERGED"
    elif raw_state == "CLOSED" or closed_at:
        state = "CLOSED"
    else:
        state = "OPEN"

    head_info = pr_data.get("head") or {}
    base_info = pr_data.get("base") or {}
    source_branch = head_info.get("ref") or "unknown"
    target_branch = base_info.get("ref") or repository.default_branch or "main"

    created_at_gh = parse_github_datetime(pr_data.get("created_at")) or datetime.now(UTC)
    updated_at_gh = parse_github_datetime(pr_data.get("updated_at")) or datetime.now(UTC)

    additions = int(pr_data.get("additions") or 0)
    deletions = int(pr_data.get("deletions") or 0)
    changed_files = int(pr_data.get("changed_files") or 0)
    commit_count = int(pr_data.get("commits") or 0)

    # Calculate turnaround duration in seconds
    merge_time_seconds: int | None = None
    cycle_time_seconds: int | None = None

    if merged_at and created_at_gh:
        duration = int((merged_at - created_at_gh).total_seconds())
        if duration >= 0:
            merge_time_seconds = duration
            cycle_time_seconds = duration  # baseline cycle time

    # Resolve author identity
    author_info = pr_data.get("user") or {}
    author_account_id: uuid.UUID | None = None
    if author_info and repository.organization_id:
        author_account = await resolve_or_create_github_account(
            db=db,
            organization_id=repository.organization_id,
            login=author_info.get("login"),
            avatar_url=author_info.get("avatar_url"),
            github_user_id=author_info.get("id"),
        )
        author_account_id = author_account.id

    # Check for existing PR by github_pr_id
    query = select(PullRequest).where(
        PullRequest.repository_id == repository.id,
        PullRequest.github_pr_id == github_pr_id,
    )
    res = await db.execute(query)
    pr = res.scalar_one_or_none()

    if not pr:
        # Check by repository and PR number as secondary guard
        query_num = select(PullRequest).where(
            PullRequest.repository_id == repository.id,
            PullRequest.number == pr_number,
        )
        res_num = await db.execute(query_num)
        pr = res_num.scalar_one_or_none()

    if pr:
        pr.title = title
        pr.state = state
        pr.is_draft = is_draft
        pr.source_branch = source_branch
        pr.target_branch = target_branch
        pr.updated_at_github = updated_at_gh
        pr.closed_at = closed_at
        pr.merged_at = merged_at
        pr.additions = additions
        pr.deletions = deletions
        pr.changed_files = changed_files
        pr.commit_count = commit_count
        if merge_time_seconds is not None:
            pr.merge_time_seconds = merge_time_seconds
        if cycle_time_seconds is not None:
            pr.cycle_time_seconds = cycle_time_seconds
        if author_account_id and not pr.author_account_id:
            pr.author_account_id = author_account_id
    else:
        pr = PullRequest(
            repository_id=repository.id,
            author_account_id=author_account_id,
            github_pr_id=github_pr_id,
            number=pr_number,
            title=title,
            state=state,
            is_draft=is_draft,
            source_branch=source_branch,
            target_branch=target_branch,
            created_at_github=created_at_gh,
            updated_at_github=updated_at_gh,
            closed_at=closed_at,
            merged_at=merged_at,
            additions=additions,
            deletions=deletions,
            changed_files=changed_files,
            commit_count=commit_count,
            merge_time_seconds=merge_time_seconds,
            cycle_time_seconds=cycle_time_seconds,
        )
        db.add(pr)

    repository.last_synced_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(pr)
    logger.info(
        "pull_request_ingested",
        repo=repository.name,
        pr_number=pr_number,
        state=state,
        action=action,
    )
    return pr


async def sync_repository_pull_requests(
    db: AsyncSession,
    repository: Repository,
    max_prs: int = 100,
) -> int:
    """Backfills recent pull requests for a repository via GitHub REST API."""
    client = GitHubClient()
    api_pulls = await client.get_repository_pull_requests(
        repository.full_name, state="all", per_page=max_prs
    )
    if not api_pulls:
        return 0

    saved_count = 0
    for item in api_pulls:
        try:
            await ingest_pull_request_payload(db, repository, item)
            saved_count += 1
        except Exception as exc:
            logger.warning("sync_single_pr_failed", error=str(exc), repo=repository.full_name)

    logger.info("repository_pull_requests_synced", repo=repository.name, count=saved_count)
    return saved_count
