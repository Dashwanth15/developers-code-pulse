import re
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commits import Commit, GitHubAccount
from app.models.github import Repository
from app.services.github.github_client import GitHubClient

logger = structlog.get_logger(__name__)


def is_likely_merge_commit(message: str, parents_count: int | None = None) -> bool:
    """Heuristic to detect merge commits from parent count or standard git messages."""
    if parents_count is not None and parents_count > 1:
        return True
    msg = message.strip().lower()
    return (
        msg.startswith("merge pull request")
        or msg.startswith("merge branch")
        or bool(re.match(r"^merge remote-tracking branch", msg))
    )


async def resolve_or_create_github_account(
    db: AsyncSession,
    organization_id: uuid.UUID,
    login: str | None = None,
    name: str | None = None,
    email: str | None = None,
    avatar_url: str | None = None,
    github_user_id: int | None = None,
) -> GitHubAccount:
    """Finds or creates a normalized GitHubAccount identity within the tenant organization."""
    account_login = (login or email or "unknown-committer").lower().strip()

    # Query existing account by organization and login
    query = select(GitHubAccount).where(
        GitHubAccount.organization_id == organization_id,
        GitHubAccount.login == account_login,
    )
    res = await db.execute(query)
    account = res.scalar_one_or_none()

    if account:
        # Update metadata if missing
        if not account.name and name:
            account.name = name
        if not account.avatar_url and avatar_url:
            account.avatar_url = avatar_url
        if not account.email and email:
            account.email = email
        return account

    # Determine user type
    user_type = "User"
    if account_login.endswith("[bot]") or "bot" in account_login.lower():
        user_type = "Bot"

    account = GitHubAccount(
        organization_id=organization_id,
        github_user_id=github_user_id,
        login=account_login,
        name=name,
        email=email,
        avatar_url=avatar_url,
        user_type=user_type,
    )
    db.add(account)
    await db.flush()
    return account


async def ingest_push_payload(
    db: AsyncSession,
    repository: Repository,
    payload: dict,
) -> int:
    """
    Parses and ingests GitHub 'push' event payload into the commits table.
    Returns the count of newly saved commits.
    """
    raw_commits = payload.get("commits", [])
    if not raw_commits:
        return 0

    branch_ref = payload.get("ref", "")
    branch_name = branch_ref.replace("refs/heads/", "") if branch_ref else "main"

    saved_count = 0
    for raw_c in raw_commits:
        sha = raw_c.get("id")
        if not sha:
            continue

        # Check for existing commit to guarantee idempotency
        chk_query = select(Commit.id).where(
            Commit.repository_id == repository.id,
            Commit.commit_sha == sha,
        )
        chk_res = await db.execute(chk_query)
        if chk_res.scalar_one_or_none():
            continue

        # Resolve author
        raw_author = raw_c.get("author", {})
        login = (
            raw_author.get("username")
            or payload.get("sender", {}).get("login")
            or raw_author.get("email")
        )
        name = raw_author.get("name")
        email = raw_author.get("email")
        avatar_url = payload.get("sender", {}).get("avatar_url")

        author_account = await resolve_or_create_github_account(
            db=db,
            organization_id=repository.organization_id,
            login=login,
            name=name,
            email=email,
            avatar_url=avatar_url,
        )

        # Parse committed timestamp
        raw_ts = raw_c.get("timestamp")
        if raw_ts:
            try:
                committed_at = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            except ValueError:
                committed_at = datetime.now(UTC)
        else:
            committed_at = datetime.now(UTC)

        message = raw_c.get("message", "No commit message")
        added = len(raw_c.get("added", []))
        removed = len(raw_c.get("removed", []))
        modified = len(raw_c.get("modified", []))
        total_changes = added + removed + modified

        # Check if merge commit
        is_merge = is_likely_merge_commit(message)

        commit = Commit(
            repository_id=repository.id,
            author_account_id=author_account.id,
            commit_sha=sha,
            message=message,
            committed_at=committed_at,
            additions=added,
            deletions=removed,
            total_changes=total_changes,
            branch_name=branch_name,
            is_merge_commit=is_merge,
        )
        db.add(commit)
        saved_count += 1

    repository.last_synced_at = datetime.now(UTC)
    await db.commit()
    logger.info("push_commits_ingested", repo=repository.name, count=saved_count)
    return saved_count


async def sync_repository_commits(
    db: AsyncSession,
    repository: Repository,
    max_commits: int = 100,
) -> int:
    """
    Backfills recent commits for a repository via GitHub REST API.
    """
    client = GitHubClient()
    parts = repository.full_name.split("/")
    if len(parts) != 2:
        return 0
    owner, repo_name = parts[0], parts[1]

    endpoint = f"/repos/{owner}/{repo_name}/commits?per_page={min(max_commits, 100)}"
    response = await client._client.get(endpoint)
    if response.status_code != 200:
        logger.warning(
            "github_commits_sync_failed",
            status_code=response.status_code,
            repo=repository.full_name,
        )
        return 0

    api_commits = response.json()
    saved_count = 0

    for item in api_commits:
        sha = item.get("sha")
        if not sha:
            continue

        # Check existing
        chk_query = select(Commit.id).where(
            Commit.repository_id == repository.id,
            Commit.commit_sha == sha,
        )
        chk_res = await db.execute(chk_query)
        if chk_res.scalar_one_or_none():
            continue

        raw_c = item.get("commit", {})
        message = raw_c.get("message", "")
        author_info = raw_c.get("author", {})
        github_author = item.get("author") or {}

        login = github_author.get("login") or author_info.get("email") or "unknown"
        name = author_info.get("name")
        email = author_info.get("email")
        avatar_url = github_author.get("avatar_url")
        user_type = github_author.get("type", "User")
        github_user_id = github_author.get("id")

        author_account = await resolve_or_create_github_account(
            db=db,
            organization_id=repository.organization_id,
            login=login,
            name=name,
            email=email,
            avatar_url=avatar_url,
            github_user_id=github_user_id,
        )
        author_account.user_type = user_type

        # Parse timestamp
        raw_date = author_info.get("date")
        if raw_date:
            try:
                committed_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                committed_at = datetime.now(UTC)
        else:
            committed_at = datetime.now(UTC)

        parents_count = len(item.get("parents", []))
        is_merge = is_likely_merge_commit(message, parents_count)

        commit = Commit(
            repository_id=repository.id,
            author_account_id=author_account.id,
            commit_sha=sha,
            message=message,
            committed_at=committed_at,
            additions=0,
            deletions=0,
            total_changes=0,
            branch_name=repository.default_branch,
            is_merge_commit=is_merge,
        )
        db.add(commit)
        saved_count += 1

    repository.last_synced_at = datetime.now(UTC)
    await db.commit()
    logger.info("repository_commits_backfilled", repo=repository.name, count=saved_count)
    return saved_count
