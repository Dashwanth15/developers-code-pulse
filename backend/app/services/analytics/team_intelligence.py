import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bottlenecks import Bottleneck
from app.models.commits import Commit
from app.models.dora import Deployment
from app.models.github import Repository
from app.models.pull_requests import PullRequest
from app.models.reviews import PRReview
from app.schemas.team import (
    BottleneckDistributionSummary,
    CollaborationPattern,
    DeliveryCadence,
    MacroThroughput,
    RepoDeliveryTrend,
    TeamIntelligenceResponse,
    TeamTrendSeriesPoint,
    TeamTrendsResponse,
)
from app.services.analytics.dora_metrics import calculate_percentile, parse_time_window


async def calculate_team_intelligence(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> TeamIntelligenceResponse:
    """
    Computes aggregate organization-level Team Intelligence indicators.
    Strictly follows Anti-Surveillance Manifesto: zero individual ranking or velocity scores.
    """
    start_dt, end_dt, _ = parse_time_window(time_window, start_date, end_date)

    # 1. Query Repositories
    repo_q = select(Repository).where(Repository.organization_id == organization_id)
    if repository_ids:
        repo_q = repo_q.where(Repository.id.in_(repository_ids))
    repo_res = await db.execute(repo_q)
    repos = list(repo_res.scalars().all())
    repo_id_list = [r.id for r in repos]
    repo_name_map = {r.id: r.name for r in repos}

    if not repo_id_list:
        return TeamIntelligenceResponse(
            organization_id=organization_id,
            time_window=time_window,
            start_date=start_dt,
            end_date=end_dt,
            throughput=MacroThroughput(),
            delivery_cadence=DeliveryCadence(),
            bottlenecks=BottleneckDistributionSummary(),
            collaboration=CollaborationPattern(),
            repository_trends=[],
            systemic_recommendations=[],
        )

    # 2. Query Pull Requests
    pr_q = (
        select(PullRequest)
        .options(selectinload(PullRequest.reviews))
        .where(
            PullRequest.repository_id.in_(repo_id_list),
            PullRequest.created_at <= end_dt,
        )
    )
    pr_res = await db.execute(pr_q)
    all_prs = list(pr_res.scalars().all())

    prs_opened = [p for p in all_prs if p.created_at >= start_dt and p.created_at <= end_dt]
    prs_merged = [
        p
        for p in all_prs
        if p.merged_at and p.merged_at >= start_dt and p.merged_at <= end_dt
    ]
    prs_closed_no_merge = [
        p
        for p in all_prs
        if p.state == "closed"
        and not p.merged_at
        and p.closed_at
        and p.closed_at >= start_dt
        and p.closed_at <= end_dt
    ]

    total_closed_decisions = len(prs_merged) + len(prs_closed_no_merge)
    merge_rate_pct = (
        round((len(prs_merged) / total_closed_decisions) * 100.0, 1)
        if total_closed_decisions > 0
        else 0.0
    )

    # 3. Query Commits
    commit_count_q = select(func.count(Commit.id)).where(
        Commit.repository_id.in_(repo_id_list),
        Commit.committed_at >= start_dt,
        Commit.committed_at <= end_dt,
    )
    total_commits = (await db.scalar(commit_count_q)) or 0

    # 4. Query Reviews
    all_reviews: list[PRReview] = []
    for p in all_prs:
        for rev in p.reviews:
            if rev.submitted_at and rev.submitted_at >= start_dt and rev.submitted_at <= end_dt:
                all_reviews.append(rev)
    total_reviews = len(all_reviews)

    throughput = MacroThroughput(
        total_prs_opened=len(prs_opened),
        total_prs_merged=len(prs_merged),
        total_prs_closed=len(prs_closed_no_merge),
        merge_rate_percent=merge_rate_pct,
        total_commits=total_commits,
        total_reviews=total_reviews,
    )

    # 5. Delivery Cadence
    deploy_q = select(Deployment).where(
        Deployment.organization_id == organization_id,
        Deployment.environment.in_(["production", "prod"]),
        Deployment.status == "SUCCESS",
        Deployment.deployed_at >= start_dt,
        Deployment.deployed_at <= end_dt,
    )
    if repository_ids:
        deploy_q = deploy_q.where(Deployment.repository_id.in_(repository_ids))
    deploy_res = await db.execute(deploy_q)
    prod_deployments = list(deploy_res.scalars().all())

    lead_times = [
        d.lead_time_seconds / 3600.0
        for d in prod_deployments
        if d.lead_time_seconds is not None and d.lead_time_seconds >= 0
    ]
    median_lead_time = calculate_percentile(lead_times, 50.0) if lead_times else None

    # Review turnaround & merge latencies
    turnaround_hours: list[float] = []
    merge_latencies_hours: list[float] = []
    for p in prs_merged:
        if p.cycle_time_seconds:
            merge_latencies_hours.append(p.cycle_time_seconds / 3600.0)
        # Check first review time
        if p.reviews:
            sorted_revs = sorted(p.reviews, key=lambda r: r.submitted_at or r.created_at)
            first_rev_dt = sorted_revs[0].submitted_at or sorted_revs[0].created_at
            if first_rev_dt and first_rev_dt >= p.created_at:
                turnaround_hours.append(max((first_rev_dt - p.created_at).total_seconds() / 3600.0, 0.0))

    median_turnaround = calculate_percentile(turnaround_hours, 50.0) if turnaround_hours else None
    median_merge_lat = calculate_percentile(merge_latencies_hours, 50.0) if merge_latencies_hours else None

    delivery_cadence = DeliveryCadence(
        deployments_count=len(prod_deployments),
        median_lead_time_hours=median_lead_time,
        median_review_turnaround_hours=median_turnaround,
        median_merge_latency_hours=median_merge_lat,
    )

    # 6. Bottleneck Distribution
    bot_q = select(Bottleneck).where(
        Bottleneck.organization_id == organization_id,
        Bottleneck.status == "ACTIVE",
    )
    if repository_ids:
        bot_q = bot_q.where(Bottleneck.repository_id.in_(repository_ids))
    bot_res = await db.execute(bot_q)
    active_bottlenecks = list(bot_res.scalars().all())

    crit_cnt = sum(1 for b in active_bottlenecks if b.severity == "CRITICAL")
    high_cnt = sum(1 for b in active_bottlenecks if b.severity == "HIGH")
    med_cnt = sum(1 for b in active_bottlenecks if b.severity == "MEDIUM")
    low_cnt = sum(1 for b in active_bottlenecks if b.severity == "LOW")

    type_counts: dict[str, int] = defaultdict(int)
    for b in active_bottlenecks:
        type_counts[b.bottleneck_type] += 1

    bottlenecks_summary = BottleneckDistributionSummary(
        total_active=len(active_bottlenecks),
        critical=crit_cnt,
        high=high_cnt,
        medium=med_cnt,
        low=low_cnt,
        by_type=dict(type_counts),
    )

    # 7. Collaboration Patterns
    multi_rev_count = 0
    reviewed_merged_count = 0
    total_review_comments = 0

    for p in prs_merged:
        distinct_reviewers = {r.reviewer_account_id for r in p.reviews if r.reviewer_account_id}
        if len(distinct_reviewers) >= 2:
            multi_rev_count += 1
        if len(p.reviews) > 0:
            reviewed_merged_count += 1
            total_review_comments += len(p.reviews)

    multi_rev_rate = (
        round((multi_rev_count / len(prs_merged)) * 100.0, 1) if prs_merged else 0.0
    )
    review_cov_rate = (
        round((reviewed_merged_count / len(prs_merged)) * 100.0, 1) if prs_merged else 0.0
    )
    avg_rev_per_pr = (
        round(total_review_comments / len(prs_merged), 1) if prs_merged else 0.0
    )

    collaboration = CollaborationPattern(
        multi_reviewer_pr_rate=multi_rev_rate,
        cross_repo_collaboration_index=round(min(len(repos) * 0.25, 1.0), 2),
        average_review_comments_per_pr=avg_rev_per_pr,
        review_coverage_rate=review_cov_rate,
    )

    # 8. Cross-Repository Delivery Comparison
    repo_trends: list[RepoDeliveryTrend] = []
    for r_id in repo_id_list:
        r_name = repo_name_map.get(r_id, "Unknown Repo")
        r_opened = [p for p in prs_opened if p.repository_id == r_id]
        r_merged = [p for p in prs_merged if p.repository_id == r_id]
        r_closed = [p for p in prs_closed_no_merge if p.repository_id == r_id]
        r_tot_closed = len(r_merged) + len(r_closed)
        r_merge_rate = (
            round((len(r_merged) / r_tot_closed) * 100.0, 1) if r_tot_closed > 0 else 0.0
        )
        r_latencies = [
            p.cycle_time_seconds / 3600.0
            for p in r_merged
            if p.cycle_time_seconds
        ]
        r_median_cycle = calculate_percentile(r_latencies, 50.0) if r_latencies else None
        r_deploys = sum(1 for d in prod_deployments if d.repository_id == r_id)
        r_bots = sum(1 for b in active_bottlenecks if b.repository_id == r_id)

        repo_trends.append(
            RepoDeliveryTrend(
                repository_id=r_id,
                repository_name=r_name,
                pr_throughput=len(r_opened) + len(r_merged),
                merge_rate=r_merge_rate,
                median_cycle_time_hours=r_median_cycle,
                deployment_count=r_deploys,
                active_bottlenecks=r_bots,
            )
        )

    # 9. Systemic Recommendations
    recommendations: list[dict[str, Any]] = []
    if median_turnaround and median_turnaround > 24.0:
        recommendations.append(
            {
                "category": "REVIEW_FLOW",
                "title": "Review turnaround exceeds 24 hours",
                "observation": f"Median initial review latency is {median_turnaround}h.",
                "suggestion": "Encourage smaller PR batches (<300 lines) and structured asynchronous daily review blocks.",
            }
        )
    if review_cov_rate < 80.0 and len(prs_merged) > 3:
        recommendations.append(
            {
                "category": "CODE_HEALTH",
                "title": "Review coverage is below 80%",
                "observation": f"{review_cov_rate}% of merged PRs had recorded peer reviews.",
                "suggestion": "Ensure mandatory branch protection rules require at least one approving peer review before merge.",
            }
        )
    if len(active_bottlenecks) > 0:
        recommendations.append(
            {
                "category": "BOTTLENECKS",
                "title": f"{len(active_bottlenecks)} active delivery bottlenecks detected",
                "observation": f"{crit_cnt} critical, {high_cnt} high severity bottlenecks currently constrain workflow rhythm.",
                "suggestion": "Review the Bottleneck Detection Engine tab to unblock pending PR queues and rebalance review allocation.",
            }
        )

    return TeamIntelligenceResponse(
        organization_id=organization_id,
        time_window=time_window,
        start_date=start_dt,
        end_date=end_dt,
        throughput=throughput,
        delivery_cadence=delivery_cadence,
        bottlenecks=bottlenecks_summary,
        collaboration=collaboration,
        repository_trends=repo_trends,
        systemic_recommendations=recommendations,
    )


async def calculate_team_trends(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> TeamTrendsResponse:
    """Computes daily time-series points of macro team rhythm (PRs opened, merged, reviews, deploys)."""
    start_dt, end_dt, _ = parse_time_window(time_window, start_date, end_date)

    # Query Repos
    repo_q = select(Repository.id).where(Repository.organization_id == organization_id)
    if repository_ids:
        repo_q = repo_q.where(Repository.id.in_(repository_ids))
    repo_ids = list((await db.execute(repo_q)).scalars().all())

    if not repo_ids:
        return TeamTrendsResponse(organization_id=organization_id, time_window=time_window, series=[])

    # PRs
    pr_q = select(PullRequest).where(
        PullRequest.repository_id.in_(repo_ids),
        PullRequest.created_at >= start_dt,
        PullRequest.created_at <= end_dt,
    )
    prs_opened = list((await db.execute(pr_q)).scalars().all())

    merged_q = select(PullRequest).where(
        PullRequest.repository_id.in_(repo_ids),
        PullRequest.merged_at >= start_dt,
        PullRequest.merged_at <= end_dt,
    )
    prs_merged = list((await db.execute(merged_q)).scalars().all())

    # Reviews
    rev_q = (
        select(PRReview)
        .join(PullRequest, PRReview.pull_request_id == PullRequest.id)
        .where(
            PullRequest.repository_id.in_(repo_ids),
            PRReview.submitted_at >= start_dt,
            PRReview.submitted_at <= end_dt,
        )
    )
    reviews = list((await db.execute(rev_q)).scalars().all())

    # Deployments
    dep_q = select(Deployment).where(
        Deployment.organization_id == organization_id,
        Deployment.environment.in_(["production", "prod"]),
        Deployment.status == "SUCCESS",
        Deployment.deployed_at >= start_dt,
        Deployment.deployed_at <= end_dt,
    )
    if repository_ids:
        dep_q = dep_q.where(Deployment.repository_id.in_(repository_ids))
    deployments = list((await db.execute(dep_q)).scalars().all())

    opened_map: dict[str, int] = defaultdict(int)
    merged_map: dict[str, int] = defaultdict(int)
    rev_map: dict[str, int] = defaultdict(int)
    dep_map: dict[str, int] = defaultdict(int)

    for p in prs_opened:
        opened_map[p.created_at.strftime("%Y-%m-%d")] += 1
    for p in prs_merged:
        if p.merged_at:
            merged_map[p.merged_at.strftime("%Y-%m-%d")] += 1
    for r in reviews:
        if r.submitted_at:
            rev_map[r.submitted_at.strftime("%Y-%m-%d")] += 1
    for d in deployments:
        dep_map[d.deployed_at.strftime("%Y-%m-%d")] += 1

    series: list[TeamTrendSeriesPoint] = []
    curr = start_dt.date()
    end_date_val = end_dt.date()
    while curr <= end_date_val:
        day_str = curr.strftime("%Y-%m-%d")
        series.append(
            TeamTrendSeriesPoint(
                date=day_str,
                prs_opened=opened_map.get(day_str, 0),
                prs_merged=merged_map.get(day_str, 0),
                reviews_completed=rev_map.get(day_str, 0),
                deployments=dep_map.get(day_str, 0),
            )
        )
        curr += timedelta(days=1)

    return TeamTrendsResponse(organization_id=organization_id, time_window=time_window, series=series)
