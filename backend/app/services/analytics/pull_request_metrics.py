import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pull_requests import PullRequest
from app.schemas.pull_requests import (
    PRAnalyticsResponse,
    PRAnalyticsSummary,
    PRCadenceTrendPoint,
    PRSizeBucket,
    PRSizeDistribution,
)


def calculate_percentile(values: list[float], percentile: float) -> float | None:
    """Calculates percentile using linear interpolation."""
    if not values:
        return None
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 1)
    k = (len(sorted_vals) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1
    if c < len(sorted_vals):
        return round(sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f]), 1)
    return round(sorted_vals[-1], 1)


async def calculate_pull_request_analytics(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date_str: str | None = None,
    end_date_str: str | None = None,
) -> PRAnalyticsResponse:
    """Computes comprehensive Pull Request analytics, cycle times, and size distributions."""
    now = datetime.now(UTC)

    # 1. Parse window dates
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=UTC
            )
        except ValueError:
            start_date = now - timedelta(days=30)
            end_date = now
    else:
        days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
        days = days_map.get(time_window, 30)
        start_date = now - timedelta(days=days)
        end_date = now

    # 2. Query pull requests for tenant's repositories
    query = (
        select(PullRequest)
        .options(selectinload(PullRequest.author))
        .join(PullRequest.repository)
        .where(PullRequest.repository.has(organization_id=organization_id))
    )

    if repository_ids:
        query = query.where(PullRequest.repository_id.in_(repository_ids))

    result = await db.execute(query)
    all_prs = list(result.scalars().all())

    # 3. Categorize PRs in the analysis window
    prs_opened_in_window = [
        pr for pr in all_prs if start_date <= pr.created_at_github <= end_date
    ]
    prs_merged_in_window = [
        pr for pr in all_prs if pr.merged_at and (start_date <= pr.merged_at <= end_date)
    ]
    prs_closed_unmerged_in_window = [
        pr
        for pr in all_prs
        if pr.state == "CLOSED"
        and not pr.merged_at
        and pr.closed_at
        and (start_date <= pr.closed_at <= end_date)
    ]
    currently_open_prs = [pr for pr in all_prs if pr.state == "OPEN"]

    # 4. Turnaround Latencies
    merge_hours_list: list[float] = []
    cycle_hours_list: list[float] = []

    for pr in prs_merged_in_window:
        if pr.merge_time_seconds is not None and pr.merge_time_seconds > 0:
            merge_hours_list.append(pr.merge_time_seconds / 3600.0)
        elif pr.merged_at and pr.created_at_github:
            delta = (pr.merged_at - pr.created_at_github).total_seconds()
            if delta > 0:
                merge_hours_list.append(delta / 3600.0)

        if pr.cycle_time_seconds is not None and pr.cycle_time_seconds > 0:
            cycle_hours_list.append(pr.cycle_time_seconds / 3600.0)
        elif pr.merge_time_seconds is not None and pr.merge_time_seconds > 0:
            cycle_hours_list.append(pr.merge_time_seconds / 3600.0)

    total_closed_or_merged = len(prs_merged_in_window) + len(prs_closed_unmerged_in_window)
    merge_rate = (
        round((len(prs_merged_in_window) / total_closed_or_merged) * 100.0, 1)
        if total_closed_or_merged > 0
        else 0.0
    )

    summary = PRAnalyticsSummary(
        total_prs_opened=len(prs_opened_in_window),
        total_prs_merged=len(prs_merged_in_window),
        total_prs_closed_unmerged=len(prs_closed_unmerged_in_window),
        currently_open_prs=len(currently_open_prs),
        merge_rate_percentage=merge_rate,
        median_merge_time_hours=calculate_percentile(merge_hours_list, 50.0),
        p75_merge_time_hours=calculate_percentile(merge_hours_list, 75.0),
        median_cycle_time_hours=calculate_percentile(cycle_hours_list, 50.0),
    )

    # 5. Daily Cadence Trend
    day_count = (end_date.date() - start_date.date()).days + 1
    dates = [(start_date.date() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(day_count)]
    trend_map: dict[str, dict[str, int]] = {
        d: {"opened": 0, "merged": 0, "closed": 0} for d in dates
    }

    for pr in prs_opened_in_window:
        d_str = pr.created_at_github.strftime("%Y-%m-%d")
        if d_str in trend_map:
            trend_map[d_str]["opened"] += 1

    for pr in prs_merged_in_window:
        if pr.merged_at:
            d_str = pr.merged_at.strftime("%Y-%m-%d")
            if d_str in trend_map:
                trend_map[d_str]["merged"] += 1

    for pr in prs_closed_unmerged_in_window:
        if pr.closed_at:
            d_str = pr.closed_at.strftime("%Y-%m-%d")
            if d_str in trend_map:
                trend_map[d_str]["closed"] += 1

    cadence_trend = [
        PRCadenceTrendPoint(
            date=d,
            opened=trend_map[d]["opened"],
            merged=trend_map[d]["merged"],
            closed=trend_map[d]["closed"],
        )
        for d in dates
    ]

    # 6. Size Distribution & Turnaround by Size
    small_prs: list[float] = []
    med_prs: list[float] = []
    large_prs: list[float] = []

    small_count = 0
    med_count = 0
    large_count = 0

    for pr in prs_opened_in_window:
        lines = pr.additions + pr.deletions
        m_time: float | None = None
        if pr.merged_at and pr.created_at_github:
            m_time = (pr.merged_at - pr.created_at_github).total_seconds() / 3600.0

        if lines < 100:
            small_count += 1
            if m_time is not None:
                small_prs.append(m_time)
        elif lines <= 500:
            med_count += 1
            if m_time is not None:
                med_prs.append(m_time)
        else:
            large_count += 1
            if m_time is not None:
                large_prs.append(m_time)

    size_distribution = PRSizeDistribution(
        small_under_100_lines=PRSizeBucket(
            count=small_count,
            avg_merge_hours=round(sum(small_prs) / len(small_prs), 1) if small_prs else None,
        ),
        medium_100_to_500_lines=PRSizeBucket(
            count=med_count,
            avg_merge_hours=round(sum(med_prs) / len(med_prs), 1) if med_prs else None,
        ),
        large_over_500_lines=PRSizeBucket(
            count=large_count,
            avg_merge_hours=round(sum(large_prs) / len(large_prs), 1) if large_prs else None,
        ),
    )

    return PRAnalyticsResponse(
        time_window=time_window,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        summary=summary,
        cadence_trend=cadence_trend,
        size_distribution=size_distribution,
    )
