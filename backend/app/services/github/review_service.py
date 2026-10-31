import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github import Repository
from app.models.pull_requests import PullRequest
from app.models.reviews import PRReview, ReviewRequest
from app.services.github.commit_service import resolve_or_create_github_account
from app.services.github.github_client import GitHubClient
from app.services.github.pull_request_service import parse_github_datetime

logger = structlog.get_logger(__name__)


async def ingest_pull_request_review_payload(
    db: AsyncSession,
    repository: Repository,
    pull_request: PullRequest,
    review_data: dict,
    action: str | None = None,
) -> PRReview:
    """Upserts a peer review submission on a pull request and updates TTFR metrics."""
    github_review_id = review_data.get("id")
    if not github_review_id:
        raise ValueError("Missing github_review_id in review payload")

    raw_state = review_data.get("state", "COMMENTED").upper()
    submitted_at = parse_github_datetime(review_data.get("submitted_at")) or datetime.now(UTC)
    commit_sha = review_data.get("commit_id")

    # Resolve reviewer identity
    reviewer_info = review_data.get("user") or {}
    reviewer_account_id: uuid.UUID | None = None
    if reviewer_info and repository.organization_id:
        reviewer_account = await resolve_or_create_github_account(
            db=db,
            organization_id=repository.organization_id,
            login=reviewer_info.get("login"),
            avatar_url=reviewer_info.get("avatar_url"),
            github_user_id=reviewer_info.get("id"),
        )
        reviewer_account_id = reviewer_account.id

    # Check for existing review
    query = select(PRReview).where(
        PRReview.pull_request_id == pull_request.id,
        PRReview.github_review_id == github_review_id,
    )
    res = await db.execute(query)
    review = res.scalar_one_or_none()

    if review:
        review.state = raw_state
        review.submitted_at = submitted_at
        if commit_sha:
            review.commit_sha = commit_sha
    else:
        review = PRReview(
            pull_request_id=pull_request.id,
            reviewer_account_id=reviewer_account_id,
            github_review_id=github_review_id,
            state=raw_state,
            submitted_at=submitted_at,
            commit_sha=commit_sha,
        )
        db.add(review)

    # Update TTFR on the pull request if this is the first non-author peer review
    is_peer_review = (
        reviewer_account_id is not None
        and reviewer_account_id != pull_request.author_account_id
        and raw_state in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED")
    )

    if is_peer_review:
        if pull_request.first_reviewed_at is None or submitted_at < pull_request.first_reviewed_at:
            pull_request.first_reviewed_at = submitted_at
            if pull_request.created_at_github:
                ttfr_sec = int((submitted_at - pull_request.created_at_github).total_seconds())
                if ttfr_sec >= 0:
                    pull_request.first_review_time_seconds = ttfr_sec

        # Fulfill pending review request if one exists for this reviewer
        if reviewer_account_id:
            req_q = select(ReviewRequest).where(
                ReviewRequest.pull_request_id == pull_request.id,
                ReviewRequest.reviewer_account_id == reviewer_account_id,
                ReviewRequest.status == "PENDING",
            )
            req_res = await db.execute(req_q)
            req = req_res.scalar_one_or_none()
            if req:
                req.status = "COMPLETED"
                req.fulfilled_at = submitted_at

    await db.commit()
    await db.refresh(review)
    logger.info(
        "review_ingested",
        pr_number=pull_request.number,
        state=raw_state,
        reviewer=reviewer_info.get("login"),
        action=action,
    )
    return review


async def sync_pull_request_reviews(
    db: AsyncSession,
    repository: Repository,
    pull_request: PullRequest,
) -> int:
    """Synchronizes all reviews for a specific pull request from GitHub REST API."""
    client = GitHubClient()
    api_reviews = await client.get_pull_request_reviews(
        repository.full_name, pull_request.number
    )
    if not api_reviews:
        return 0

    count = 0
    for item in api_reviews:
        try:
            await ingest_pull_request_review_payload(db, repository, pull_request, item)
            count += 1
        except Exception as exc:
            logger.warning(
                "sync_single_review_failed",
                error=str(exc),
                pr=pull_request.number,
                repo=repository.full_name,
            )

    return count
