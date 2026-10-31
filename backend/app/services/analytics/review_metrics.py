import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pull_requests import PullRequest
from app.models.reviews import PRReview, ReviewRequest
from app.schemas.reviews import (
    ApprovalTurnaroundMetrics,
    PendingReviewItem,
    PendingReviewQueueResponse,
    ReviewAnalyticsResponse,
    ReviewerWorkloadItem,
    ReviewSummaryMetrics,
    ReviewWorkloadResponse,
    TTFRMetrics,
    TurnaroundHistogramBucket,
)
from app.services.analytics.pull_request_metrics import calculate_percentile


def calculate_gini_coefficient(values: list[int]) -> float:
    """
    Calculates the Gini coefficient measuring statistical dispersion of review workloads.
    G = sum(|Ri - Rj|) / (2 * n * sum(Ri))
    Returns 0.0 for perfectly equal distribution, approaching 1.0 for extreme concentration.
    """
    n = len(values)
    if n <= 1:
        return 0.0
    total = sum(values)
    if total == 0:
        return 0.0

    diff_sum = 0
    for i in range(n):
        for j in range(n):
            diff_sum += abs(values[i] - values[j])

    gini = diff_sum / (2.0 * n * total)
    return round(min(max(gini, 0.0), 1.0), 3)


async def calculate_review_analytics(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
) -> ReviewAnalyticsResponse:
    """Calculates Time to First Review (TTFR), approval turnaround, and review coverage."""
    now = datetime.now(UTC)
    days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
    days = days_map.get(time_window, 30)
    start_date = now - timedelta(days=days)

    query = (
        select(PullRequest)
        .options(
            selectinload(PullRequest.reviews).selectinload(PRReview.reviewer),
            selectinload(PullRequest.author),
        )
        .join(PullRequest.repository)
        .where(
            PullRequest.repository.has(organization_id=organization_id),
            PullRequest.created_at_github >= start_date,
        )
    )
    if repository_ids:
        query = query.where(PullRequest.repository_id.in_(repository_ids))

    res = await db.execute(query)
    prs = list(res.scalars().all())

    ttfr_hours_list: list[float] = []
    approval_turnaround_hours: list[float] = []
    total_rounds_list: list[int] = []
    reviewed_prs_count = 0

    histogram_counts = {
        "< 2h": 0,
        "2h - 6h": 0,
        "6h - 24h": 0,
        "24h - 48h": 0,
        "> 48h": 0,
    }

    for pr in prs:
        # Filter valid peer reviews (non-self, non-bot)
        peer_reviews = [
            r
            for r in pr.reviews
            if r.reviewer_account_id != pr.author_account_id
            and (not r.reviewer or r.reviewer.user_type == "User")
            and r.state in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED")
        ]

        if peer_reviews:
            reviewed_prs_count += 1
            total_rounds_list.append(len(peer_reviews))

            # 1. First review time
            first_review = min(peer_reviews, key=lambda r: r.submitted_at)
            ttfr = (first_review.submitted_at - pr.created_at_github).total_seconds() / 3600.0
            if ttfr >= 0:
                ttfr_hours_list.append(ttfr)

                # Histogram bucketing
                if ttfr < 2.0:
                    histogram_counts["< 2h"] += 1
                elif ttfr < 6.0:
                    histogram_counts["2h - 6h"] += 1
                elif ttfr < 24.0:
                    histogram_counts["6h - 24h"] += 1
                elif ttfr < 48.0:
                    histogram_counts["24h - 48h"] += 1
                else:
                    histogram_counts["> 48h"] += 1

            # 2. Approval turnaround
            approvals = [r for r in peer_reviews if r.state == "APPROVED"]
            if approvals:
                first_approval = min(approvals, key=lambda r: r.submitted_at)
                turnaround = (first_approval.submitted_at - first_review.submitted_at).total_seconds() / 3600.0
                if turnaround >= 0:
                    approval_turnaround_hours.append(turnaround)

    # Calculate TTFR stats
    median_ttfr = calculate_percentile(ttfr_hours_list, 50.0)
    p75_ttfr = calculate_percentile(ttfr_hours_list, 75.0)
    p90_ttfr = calculate_percentile(ttfr_hours_list, 90.0)

    # Benchmark comparison
    if median_ttfr is None or median_ttfr < 8.0:
        benchmark = "HEALTHY"
    elif median_ttfr <= 24.0:
        benchmark = "MODERATE"
    else:
        benchmark = "CONGESTED"

    ttfr_metrics = TTFRMetrics(
        median_hours=median_ttfr,
        p75_hours=p75_ttfr,
        p90_hours=p90_ttfr,
        benchmark_comparison=benchmark,
    )

    approval_metrics = ApprovalTurnaroundMetrics(
        median_hours=calculate_percentile(approval_turnaround_hours, 50.0),
        p75_hours=calculate_percentile(approval_turnaround_hours, 75.0),
    )

    avg_rounds = (
        round(sum(total_rounds_list) / len(total_rounds_list), 1) if total_rounds_list else 1.0
    )
    coverage = round((reviewed_prs_count / len(prs)) * 100.0, 1) if prs else 0.0

    summary_metrics = ReviewSummaryMetrics(
        time_to_first_review=ttfr_metrics,
        approval_turnaround=approval_metrics,
        average_review_rounds=avg_rounds,
        review_coverage_rate=coverage,
    )

    turnaround_hist = [
        TurnaroundHistogramBucket(range=r, count=c)
        for r, c in histogram_counts.items()
    ]

    # Calculate pending queue count
    pending_res = await get_pending_review_queue(db, organization_id, repository_ids)

    return ReviewAnalyticsResponse(
        time_window=time_window,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=now.strftime("%Y-%m-%d"),
        metrics=summary_metrics,
        turnaround_histogram=turnaround_hist,
        pending_queue_count=pending_res.total_pending,
    )


async def calculate_reviewer_workload(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
) -> ReviewWorkloadResponse:
    """Calculates review distribution and Gini coefficient across team members."""
    now = datetime.now(UTC)
    days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
    days = days_map.get(time_window, 30)
    start_date = now - timedelta(days=days)

    query = (
        select(PRReview)
        .options(selectinload(PRReview.reviewer))
        .join(PRReview.pull_request)
        .join(PullRequest.repository)
        .where(
            PullRequest.repository.has(organization_id=organization_id),
            PRReview.submitted_at >= start_date,
        )
    )
    if repository_ids:
        query = query.where(PullRequest.repository_id.in_(repository_ids))

    res = await db.execute(query)
    reviews = list(res.scalars().all())

    # Map per reviewer account
    reviewer_map: dict[uuid.UUID, dict] = {}
    for r in reviews:
        if not r.reviewer_account_id or not r.reviewer:
            continue
        if r.reviewer.user_type != "User":
            continue

        acc_id = r.reviewer_account_id
        if acc_id not in reviewer_map:
            reviewer_map[acc_id] = {
                "account_id": acc_id,
                "login": r.reviewer.login,
                "name": r.reviewer.name,
                "avatar_url": r.reviewer.avatar_url,
                "conducted": 0,
                "approvals": 0,
                "changes_requested": 0,
            }

        reviewer_map[acc_id]["conducted"] += 1
        if r.state == "APPROVED":
            reviewer_map[acc_id]["approvals"] += 1
        elif r.state == "CHANGES_REQUESTED":
            reviewer_map[acc_id]["changes_requested"] += 1

    total_reviews = sum(item["conducted"] for item in reviewer_map.values())
    review_counts = [item["conducted"] for item in reviewer_map.values()]

    # Gini coefficient
    gini = calculate_gini_coefficient(review_counts)
    if gini <= 0.30:
        status_str = "BALANCED"
    elif gini <= 0.45:
        status_str = "MODERATE"
    else:
        status_str = "UNBALANCED"

    reviewers_list = [
        ReviewerWorkloadItem(
            account_id=v["account_id"],
            login=v["login"],
            name=v["name"],
            avatar_url=v["avatar_url"],
            reviews_conducted=v["conducted"],
            approvals_given=v["approvals"],
            changes_requested=v["changes_requested"],
            review_share_percentage=(
                round((v["conducted"] / total_reviews) * 100.0, 1)
                if total_reviews > 0
                else 0.0
            ),
        )
        for v in sorted(reviewer_map.values(), key=lambda x: x["conducted"], reverse=True)
    ]

    return ReviewWorkloadResponse(
        time_window=time_window,
        gini_coefficient=gini,
        workload_balance_status=status_str,
        total_reviews=total_reviews,
        reviewers=reviewers_list,
    )


async def get_pending_review_queue(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
) -> PendingReviewQueueResponse:
    """Fetches real-time queue of open, non-draft PRs waiting >= 12h for peer review."""
    now = datetime.now(UTC)

    query = (
        select(PullRequest)
        .options(
            selectinload(PullRequest.author),
            selectinload(PullRequest.repository),
            selectinload(PullRequest.reviews),
            selectinload(PullRequest.review_requests).selectinload(ReviewRequest.reviewer),
        )
        .join(PullRequest.repository)
        .where(
            PullRequest.repository.has(organization_id=organization_id),
            PullRequest.state == "OPEN",
            PullRequest.is_draft.is_(False),
        )
    )
    if repository_ids:
        query = query.where(PullRequest.repository_id.in_(repository_ids))

    res = await db.execute(query)
    open_prs = list(res.scalars().all())

    pending_items: list[PendingReviewItem] = []
    for pr in open_prs:
        waiting_hours = (now - pr.created_at_github).total_seconds() / 3600.0

        # Substantive peer review check
        has_review = any(
            r.reviewer_account_id != pr.author_account_id
            and r.state in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED")
            for r in pr.reviews
        )

        if waiting_hours >= 12.0 and not has_review:
            requested = [
                req.reviewer.login
                for req in pr.review_requests
                if req.status == "PENDING" and req.reviewer
            ]
            pending_items.append(
                PendingReviewItem(
                    pull_request_id=pr.id,
                    number=pr.number,
                    title=pr.title,
                    repository_name=pr.repository.name if pr.repository else "unknown",
                    author_login=pr.author.login if pr.author else None,
                    author_avatar=pr.author.avatar_url if pr.author else None,
                    waiting_hours=round(waiting_hours, 1),
                    created_at=pr.created_at_github,
                    requested_reviewers=requested,
                )
            )

    pending_items.sort(key=lambda x: x.waiting_hours, reverse=True)
    return PendingReviewQueueResponse(total_pending=len(pending_items), items=pending_items)
