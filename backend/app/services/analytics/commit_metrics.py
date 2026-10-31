import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commits import Commit
from app.models.github import Repository
from app.schemas.commits import (
    CommitAnalyticsResponse,
    CommitAnalyticsSummary,
    CommitCadencePoint,
    CommitContributorSummary,
    CommitHeatmapPoint,
    RepositoryCommitSummary,
)


def parse_time_window(
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[datetime, datetime]:
    """Resolves ISO UTC datetime bounds from time window or custom date parameters."""
    now = datetime.now(UTC)

    if start_date and end_date:
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)
        return start_dt, end_dt

    days_map = {
        "7d": 7,
        "14d": 14,
        "30d": 30,
        "90d": 90,
    }
    days = days_map.get(time_window, 30)
    start_dt = now - timedelta(days=days)
    return start_dt, now


async def calculate_commit_analytics(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> CommitAnalyticsResponse:
    """
    Computes rigorous commit velocity, cadence trends, heatmaps, and churn.
    Adheres strictly to Anti-Surveillance Manifesto (team-level metrics, zero employee ranking).
    """
    start_dt, end_dt = parse_time_window(time_window, start_date, end_date)

    # 1. Fetch monitored repositories for organization
    repo_query = select(Repository).where(
        Repository.organization_id == organization_id,
        Repository.is_monitored.is_(True),
    )
    if repository_ids:
        repo_query = repo_query.where(Repository.id.in_(repository_ids))

    repo_res = await db.execute(repo_query)
    repositories = repo_res.scalars().all()
    monitored_repo_ids = [r.id for r in repositories]
    repo_map = {r.id: r.name for r in repositories}

    if not monitored_repo_ids:
        # Honest empty state if no monitored repositories exist
        return CommitAnalyticsResponse(
            time_window=time_window,
            start_date=start_dt.strftime("%Y-%m-%d"),
            end_date=end_dt.strftime("%Y-%m-%d"),
            summary=CommitAnalyticsSummary(
                total_commits=0,
                daily_cadence=0.0,
                weekday_cadence=0.0,
                active_contributors=0,
                total_additions=0,
                total_deletions=0,
                total_churn=0,
                merge_commit_count=0,
            ),
            cadence_trend=[],
            heatmap=[],
            top_contributors=[],
            repository_comparison=[],
        )

    # 2. Query commits within date range
    commit_query = (
        select(Commit)
        .options(selectinload(Commit.author))
        .where(
            and_(
                Commit.repository_id.in_(monitored_repo_ids),
                Commit.committed_at >= start_dt,
                Commit.committed_at <= end_dt,
            )
        )
        .order_by(Commit.committed_at.asc())
    )
    commit_res = await db.execute(commit_query)
    commits = commit_res.scalars().all()

    # 3. Metric Calculations
    total_commits = 0
    merge_commit_count = 0
    total_additions = 0
    total_deletions = 0
    active_human_authors: set[uuid.UUID] = set()

    # Buckets for trend and heatmap
    daily_buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"commits": 0, "additions": 0, "deletions": 0}
    )
    heatmap_matrix: dict[tuple[int, int], int] = defaultdict(int)
    author_stats: dict[uuid.UUID, dict] = {}
    repo_stats: dict[uuid.UUID, dict] = defaultdict(
        lambda: {"commits": 0, "additions": 0, "deletions": 0, "authors": set()}
    )

    for c in commits:
        if c.is_merge_commit:
            merge_commit_count += 1
            continue  # Exclude merge commits from cadence & volume per specification

        total_commits += 1
        total_additions += c.additions
        total_deletions += c.deletions

        # Day bucket
        day_str = c.committed_at.strftime("%Y-%m-%d")
        daily_buckets[day_str]["commits"] += 1
        daily_buckets[day_str]["additions"] += c.additions
        daily_buckets[day_str]["deletions"] += c.deletions

        # Heatmap matrix (day of week: 0=Mon, 6=Sun; hour: 0-23)
        dow = c.committed_at.weekday()
        hr = c.committed_at.hour
        heatmap_matrix[(dow, hr)] += 1

        # Author aggregation (exclude bot accounts)
        author = c.author
        is_bot = author is not None and (
            author.user_type.lower() == "bot"
            or author.login.endswith("[bot]")
            or "bot" in author.login.lower()
        )
        if author and not is_bot:
            active_human_authors.add(author.id)

            if author.id not in author_stats:
                author_stats[author.id] = {
                    "author_id": str(author.id),
                    "login": author.login,
                    "name": author.name,
                    "avatar_url": author.avatar_url,
                    "commit_count": 0,
                    "additions": 0,
                    "deletions": 0,
                    "last_committed_at": c.committed_at,
                }
            author_stats[author.id]["commit_count"] += 1
            author_stats[author.id]["additions"] += c.additions
            author_stats[author.id]["deletions"] += c.deletions
            if c.committed_at > author_stats[author.id]["last_committed_at"]:
                author_stats[author.id]["last_committed_at"] = c.committed_at

            repo_stats[c.repository_id]["authors"].add(author.id)

        repo_stats[c.repository_id]["commits"] += 1
        repo_stats[c.repository_id]["additions"] += c.additions
        repo_stats[c.repository_id]["deletions"] += c.deletions

    # Fill date gaps in cadence trend
    cur_date = start_dt.date()
    end_date_limit = end_dt.date()
    total_calendar_days = 0
    total_weekdays = 0
    cadence_trend: list[CommitCadencePoint] = []

    while cur_date <= end_date_limit:
        total_calendar_days += 1
        if cur_date.weekday() < 5:  # Monday to Friday
            total_weekdays += 1

        d_str = cur_date.strftime("%Y-%m-%d")
        b = daily_buckets.get(d_str, {"commits": 0, "additions": 0, "deletions": 0})
        cadence_trend.append(
            CommitCadencePoint(
                date=d_str,
                commit_count=b["commits"],
                additions=b["additions"],
                deletions=b["deletions"],
            )
        )
        cur_date += timedelta(days=1)

    daily_cadence = round(total_commits / max(1, total_calendar_days), 2)
    weekday_cadence = round(total_commits / max(1, total_weekdays), 2)

    # Build 7x24 heatmap point list
    heatmap: list[CommitHeatmapPoint] = []
    for d in range(7):
        for h in range(24):
            heatmap.append(
                CommitHeatmapPoint(
                    day_of_week=d,
                    hour_of_day=h,
                    commit_count=heatmap_matrix.get((d, h), 0),
                )
            )

    # Repository comparison summary
    repo_comparison: list[RepositoryCommitSummary] = []
    for r_id in monitored_repo_ids:
        st = repo_stats[r_id]
        repo_comparison.append(
            RepositoryCommitSummary(
                repository_id=r_id,
                name=repo_map.get(r_id, "Unknown"),
                commit_count=st["commits"],
                additions=st["additions"],
                deletions=st["deletions"],
                active_contributors_count=len(st["authors"]),
            )
        )

    # Contributors list sorted by volume (team metrics only)
    top_contributors = [
        CommitContributorSummary(**data)
        for data in sorted(author_stats.values(), key=lambda x: x["commit_count"], reverse=True)
    ]

    return CommitAnalyticsResponse(
        time_window=time_window,
        start_date=start_dt.strftime("%Y-%m-%d"),
        end_date=end_dt.strftime("%Y-%m-%d"),
        summary=CommitAnalyticsSummary(
            total_commits=total_commits,
            daily_cadence=daily_cadence,
            weekday_cadence=weekday_cadence,
            active_contributors=len(active_human_authors),
            total_additions=total_additions,
            total_deletions=total_deletions,
            total_churn=total_additions + total_deletions,
            merge_commit_count=merge_commit_count,
        ),
        cadence_trend=cadence_trend,
        heatmap=heatmap,
        top_contributors=top_contributors,
        repository_comparison=repo_comparison,
    )
