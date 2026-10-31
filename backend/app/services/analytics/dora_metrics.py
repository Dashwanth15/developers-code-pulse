import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commits import Commit
from app.models.dora import Deployment, DORAMetricSnapshot, Incident
from app.models.github import Repository
from app.schemas.dora import (
    ChangeFailureRateDetail,
    DeploymentFrequencyDetail,
    DORAMetricCard,
    DORAOverviewResponse,
    DORATrendPoint,
    LeadTimeDetail,
    RecoveryTimeDetail,
    RepositoryDORAOverview,
)


def calculate_percentile(values: list[float], percentile: float) -> float | None:
    """Calculates percentile using linear interpolation."""
    if not values:
        return None
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 2)
    k = (len(sorted_vals) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1
    if c < len(sorted_vals):
        return round(sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f]), 2)
    return round(sorted_vals[-1], 2)


def parse_time_window(
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[datetime, datetime, int]:
    """Resolves start and end UTC timestamps and number of days."""
    now = datetime.now(UTC)
    if start_date and end_date:
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)
        days = max((end_dt - start_dt).days, 1)
        return start_dt, end_dt, days

    days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
    days = days_map.get(time_window, 30)
    start_dt = now - timedelta(days=days)
    end_dt = now
    return start_dt, end_dt, days


async def calculate_deployment_frequency(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> DeploymentFrequencyDetail:
    """
    Computes Deployment Frequency: Successful production deployments per day, week, month.
    Excludes staging and development environments.
    """
    start_dt, end_dt, days = parse_time_window(time_window, start_date, end_date)
    prev_start_dt = start_dt - timedelta(days=days)

    query = select(Deployment).where(
        Deployment.organization_id == organization_id,
        Deployment.deployed_at >= prev_start_dt,
        Deployment.deployed_at <= end_dt,
    )
    if repository_ids:
        query = query.where(Deployment.repository_id.in_(repository_ids))

    result = await db.execute(query)
    all_deployments = list(result.scalars().all())

    # Current window deployments
    current_deployments = [d for d in all_deployments if d.deployed_at >= start_dt]
    prev_deployments = [d for d in all_deployments if d.deployed_at < start_dt]

    # Environment breakdown in current window
    env_breakdown: dict[str, int] = defaultdict(int)
    for d in current_deployments:
        env_breakdown[d.environment.lower()] += 1

    # Filter successful production deployments
    prod_successful = [
        d
        for d in current_deployments
        if d.environment.lower() in ("production", "prod") and d.status.upper() == "SUCCESS"
    ]
    prod_failed = [
        d
        for d in current_deployments
        if d.environment.lower() in ("production", "prod") and d.status.upper() in ("FAILURE", "CANCELLED")
    ]

    prev_prod_successful = [
        d
        for d in prev_deployments
        if d.environment.lower() in ("production", "prod") and d.status.upper() == "SUCCESS"
    ]

    total_prod = len(prod_successful) + len(prod_failed)
    has_any_data = len(all_deployments) > 0

    if not has_any_data:
        status_val = "INSUFFICIENT_DATA"
        perf_level = "UNKNOWN"
        perf_label = "Unknown"
        formatted_val = "INSUFFICIENT_DATA"
        daily_rate = 0.0
        weekly_rate = 0.0
        monthly_rate = 0.0
        trend_dir = "NONE"
        trend_pct = None
        context_msg = "No deployment events found. Connect GitHub Actions or external deployment webhooks."
    else:
        status_val = "CALCULATED"
        daily_rate = round(len(prod_successful) / days, 2)
        weekly_rate = round(daily_rate * 7, 2)
        monthly_rate = round(daily_rate * 30, 2)

        # Classification based on DORA thresholds:
        if daily_rate >= 1.0:
            perf_level = "ELITE"
            perf_label = "Elite (Multiple / day)"
            formatted_val = f"{daily_rate}/day"
        elif weekly_rate >= 1.0:
            perf_level = "HIGH"
            perf_label = "High (Weekly)"
            formatted_val = f"{weekly_rate}/week"
        elif monthly_rate >= 1.0:
            perf_level = "MEDIUM"
            perf_label = "Medium (Monthly)"
            formatted_val = f"{monthly_rate}/month"
        else:
            perf_level = "LOW"
            perf_label = "Low (< Monthly)"
            formatted_val = f"{monthly_rate}/month"

        # Trend calculation
        prev_daily = len(prev_prod_successful) / days if days > 0 else 0.0
        if prev_daily > 0:
            pct = round(((daily_rate - prev_daily) / prev_daily) * 100, 1)
            trend_pct = pct
            trend_dir = "IMPROVED" if pct > 0 else ("DEGRADED" if pct < 0 else "STABLE")
        else:
            trend_pct = None
            trend_dir = "NONE"

        context_msg = f"{len(prod_successful)} successful production deployments out of {total_prod} attempts."

    # Historical timeline aggregation by day
    history_map: dict[str, int] = defaultdict(int)
    for d in prod_successful:
        day_str = d.deployed_at.strftime("%Y-%m-%d")
        history_map[day_str] += 1

    history: list[DORATrendPoint] = []
    curr_day = start_dt.date()
    end_date_val = end_dt.date()
    while curr_day <= end_date_val:
        day_str = curr_day.strftime("%Y-%m-%d")
        count = history_map.get(day_str, 0)
        history.append(DORATrendPoint(date=day_str, value=float(count), sample_size=count))
        curr_day += timedelta(days=1)

    card = DORAMetricCard(
        metric_type="DEPLOYMENT_FREQUENCY",
        title="Deployment Frequency",
        status=status_val,
        value=weekly_rate if status_val == "CALCULATED" else None,
        formatted_value=formatted_val,
        unit="deploys/week" if status_val == "CALCULATED" else "",
        performance_level=perf_level,
        performance_label=perf_label,
        trend_direction=trend_dir,
        trend_percentage=trend_pct,
        sample_size=len(prod_successful),
        data_completeness=1.0 if has_any_data else 0.0,
        period=f"Last {days} Days",
        data_source="GitHub Actions & Deployments",
        methodology="Count of successful deployments targeting production environment divided by time window duration.",
        context_message=context_msg,
    )

    return DeploymentFrequencyDetail(
        card=card,
        daily_deployments=daily_rate,
        weekly_deployments=weekly_rate,
        monthly_deployments=monthly_rate,
        total_deployments=len(current_deployments),
        successful_deployments=len(prod_successful),
        failed_deployments=len(prod_failed),
        history=history,
        environment_breakdown=dict(env_breakdown),
    )


async def calculate_lead_time_for_changes(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> LeadTimeDetail:
    """
    Computes Lead Time for Changes: Elapsed time from code commit/PR merge to production deployment.
    Traceability path: Commit -> Pull Request -> Deployment.
    """
    start_dt, end_dt, days = parse_time_window(time_window, start_date, end_date)
    prev_start_dt = start_dt - timedelta(days=days)

    query = (
        select(Deployment)
        .options(selectinload(Deployment.repository))
        .where(
            Deployment.organization_id == organization_id,
            Deployment.environment.in_(["production", "prod"]),
            Deployment.status == "SUCCESS",
            Deployment.deployed_at >= prev_start_dt,
            Deployment.deployed_at <= end_dt,
        )
    )
    if repository_ids:
        query = query.where(Deployment.repository_id.in_(repository_ids))

    result = await db.execute(query)
    all_deployments = list(result.scalars().all())

    current_deploys = [d for d in all_deployments if d.deployed_at >= start_dt]
    prev_deploys = [d for d in all_deployments if d.deployed_at < start_dt]

    lead_times_hours: list[float] = []
    history_map: dict[str, list[float]] = defaultdict(list)
    traced_count = 0

    for d in current_deploys:
        # Precomputed or correlated lead time
        lead_sec = d.lead_time_seconds
        if lead_sec is None and d.commit_sha:
            # Query commit or PR
            c_res = await db.execute(
                select(Commit)
                .join(Repository, Commit.repository_id == Repository.id)
                .where(
                    Commit.commit_sha == d.commit_sha,
                    Repository.organization_id == organization_id,
                )
            )
            commit = c_res.scalars().first()
            if commit and commit.committed_at:
                lead_sec = max((d.deployed_at - commit.committed_at).total_seconds(), 0.0)

        if lead_sec is not None and lead_sec >= 0:
            traced_count += 1
            hours = round(lead_sec / 3600.0, 2)
            lead_times_hours.append(hours)
            day_str = d.deployed_at.strftime("%Y-%m-%d")
            history_map[day_str].append(hours)

    sample_size = len(lead_times_hours)
    traceability_rate = round(traced_count / len(current_deploys), 2) if current_deploys else 0.0

    if sample_size == 0:
        status_val = "INSUFFICIENT_DATA"
        perf_level = "UNKNOWN"
        perf_label = "Unknown"
        formatted_val = "INSUFFICIENT_DATA"
        median_hours = None
        p75_hours = None
        avg_hours = None
        trend_dir = "NONE"
        trend_pct = None
        context_msg = "No deployments linked to traceable commits or PR merges in this window."
    else:
        status_val = "CALCULATED"
        median_hours = calculate_percentile(lead_times_hours, 50.0)
        p75_hours = calculate_percentile(lead_times_hours, 75.0)
        avg_hours = round(sum(lead_times_hours) / sample_size, 2)

        # Classification based on DORA thresholds:
        # Elite: < 1 hour, High: 1 day to 1 week (< 168h), Medium: 1 week to 1 month (< 720h), Low: > 1 month
        check_val = median_hours if median_hours is not None else 0.0
        if check_val < 1.0:
            perf_level = "ELITE"
            perf_label = "Elite (< 1 hour)"
            formatted_val = f"{int(check_val * 60)} min"
        elif check_val <= 168.0:
            perf_level = "HIGH"
            perf_label = "High (1d - 1w)"
            formatted_val = f"{check_val:.1f} hrs"
        elif check_val <= 720.0:
            perf_level = "MEDIUM"
            perf_label = "Medium (1w - 1mo)"
            formatted_val = f"{round(check_val / 24.0, 1)} days"
        else:
            perf_level = "LOW"
            perf_label = "Low (> 1 month)"
            formatted_val = f"{round(check_val / 24.0, 1)} days"

        # Previous period comparison
        prev_lead_times = [
            d.lead_time_seconds / 3600.0
            for d in prev_deploys
            if d.lead_time_seconds is not None and d.lead_time_seconds >= 0
        ]
        prev_median = calculate_percentile(prev_lead_times, 50.0) if prev_lead_times else None

        if prev_median and prev_median > 0 and median_hours is not None:
            pct = round(((median_hours - prev_median) / prev_median) * 100, 1)
            trend_pct = pct
            # For lead time, lower is better
            trend_dir = "IMPROVED" if pct < 0 else ("DEGRADED" if pct > 0 else "STABLE")
        else:
            trend_pct = None
            trend_dir = "NONE"

        context_msg = f"Median lead time of {median_hours}h across {sample_size} production deployments (P75: {p75_hours}h)."

    history: list[DORATrendPoint] = []
    curr_day = start_dt.date()
    end_date_val = end_dt.date()
    while curr_day <= end_date_val:
        day_str = curr_day.strftime("%Y-%m-%d")
        day_vals = history_map.get(day_str, [])
        med = calculate_percentile(day_vals, 50.0) if day_vals else None
        history.append(DORATrendPoint(date=day_str, value=med, sample_size=len(day_vals)))
        curr_day += timedelta(days=1)

    card = DORAMetricCard(
        metric_type="LEAD_TIME_FOR_CHANGES",
        title="Lead Time for Changes",
        status=status_val,
        value=median_hours,
        formatted_value=formatted_val,
        unit="hours" if status_val == "CALCULATED" else "",
        performance_level=perf_level,
        performance_label=perf_label,
        trend_direction=trend_dir,
        trend_percentage=trend_pct,
        sample_size=sample_size,
        data_completeness=traceability_rate,
        period=f"Last {days} Days",
        data_source="Commit & PR Traceability to Production Deployment",
        methodology="Elapsed time between code commit authoring / merge time and successful production deployment.",
        context_message=context_msg,
    )

    return LeadTimeDetail(
        card=card,
        median_hours=median_hours,
        p75_hours=p75_hours,
        average_hours=avg_hours,
        sample_size=sample_size,
        traceability_rate=traceability_rate,
        history=history,
    )


async def calculate_change_failure_rate(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> ChangeFailureRateDetail:
    """
    Computes Change Failure Rate: Percentage of production deployments resulting in an incident or failure.
    CFR = (Failed Production Deployments + Deployments Causing Production Incidents) / Total Production Deployments.
    """
    start_dt, end_dt, days = parse_time_window(time_window, start_date, end_date)
    prev_start_dt = start_dt - timedelta(days=days)

    query = (
        select(Deployment)
        .options(selectinload(Deployment.incident_links))
        .where(
            Deployment.organization_id == organization_id,
            Deployment.environment.in_(["production", "prod"]),
            Deployment.deployed_at >= prev_start_dt,
            Deployment.deployed_at <= end_dt,
        )
    )
    if repository_ids:
        query = query.where(Deployment.repository_id.in_(repository_ids))

    result = await db.execute(query)
    all_deployments = list(result.scalars().all())

    current_deploys = [d for d in all_deployments if d.deployed_at >= start_dt]
    prev_deploys = [d for d in all_deployments if d.deployed_at < start_dt]

    total_prod = len(current_deploys)
    failed_count = 0
    incident_linked_count = 0
    degraded_ids: set[uuid.UUID] = set()

    history_totals: dict[str, int] = defaultdict(int)
    history_fails: dict[str, int] = defaultdict(int)

    for d in current_deploys:
        day_str = d.deployed_at.strftime("%Y-%m-%d")
        history_totals[day_str] += 1
        is_failed = d.status.upper() in ("FAILURE", "CANCELLED")
        has_incidents = len(d.incident_links) > 0

        if is_failed:
            failed_count += 1
            degraded_ids.add(d.id)
            history_fails[day_str] += 1
        elif has_incidents:
            incident_linked_count += 1
            degraded_ids.add(d.id)
            history_fails[day_str] += 1

    total_degraded = len(degraded_ids)

    if total_prod == 0:
        status_val = "INSUFFICIENT_DATA"
        perf_level = "UNKNOWN"
        perf_label = "Unknown"
        formatted_val = "INSUFFICIENT_DATA"
        rate_pct = None
        trend_dir = "NONE"
        trend_pct = None
        context_msg = "No production deployments recorded in this time window."
    else:
        status_val = "CALCULATED"
        rate_pct = round((total_degraded / total_prod) * 100.0, 1)

        # Classification based on DORA thresholds:
        # Elite: 0-5%, High: 5.1-15%, Medium: 15.1-30%, Low: > 30%
        if rate_pct <= 5.0:
            perf_level = "ELITE"
            perf_label = "Elite (0 - 5%)"
        elif rate_pct <= 15.0:
            perf_level = "HIGH"
            perf_label = "High (5 - 15%)"
        elif rate_pct <= 30.0:
            perf_level = "MEDIUM"
            perf_label = "Medium (15 - 30%)"
        else:
            perf_level = "LOW"
            perf_label = "Low (> 30%)"

        formatted_val = f"{rate_pct}%"

        # Previous period comparison
        prev_total = len(prev_deploys)
        prev_degraded = len(
            [
                d
                for d in prev_deploys
                if d.status.upper() in ("FAILURE", "CANCELLED") or len(d.incident_links) > 0
            ]
        )
        prev_rate = (prev_degraded / prev_total) * 100.0 if prev_total > 0 else None

        if prev_rate is not None:
            pct_diff = round(rate_pct - prev_rate, 1)
            trend_pct = pct_diff
            # For failure rate, lower is better
            trend_dir = "IMPROVED" if pct_diff < 0 else ("DEGRADED" if pct_diff > 0 else "STABLE")
        else:
            trend_pct = None
            trend_dir = "NONE"

        context_msg = f"{total_degraded} failures out of {total_prod} deployments ({failed_count} failed status, {incident_linked_count} linked incidents)."

    history: list[DORATrendPoint] = []
    curr_day = start_dt.date()
    end_date_val = end_dt.date()
    while curr_day <= end_date_val:
        day_str = curr_day.strftime("%Y-%m-%d")
        tot = history_totals.get(day_str, 0)
        fl = history_fails.get(day_str, 0)
        rate = round((fl / tot) * 100.0, 1) if tot > 0 else None
        history.append(DORATrendPoint(date=day_str, value=rate, sample_size=tot))
        curr_day += timedelta(days=1)

    card = DORAMetricCard(
        metric_type="CHANGE_FAILURE_RATE",
        title="Change Failure Rate",
        status=status_val,
        value=rate_pct,
        formatted_value=formatted_val,
        unit="%" if status_val == "CALCULATED" else "",
        performance_level=perf_level,
        performance_label=perf_label,
        trend_direction=trend_dir,
        trend_percentage=trend_pct,
        sample_size=total_prod,
        data_completeness=1.0 if total_prod > 0 else 0.0,
        period=f"Last {days} Days",
        data_source="Production Deployments & Linked Incident Outages",
        methodology="Ratio of failed rollouts and incident-inducing deployments to total production deployments.",
        context_message=context_msg,
    )

    return ChangeFailureRateDetail(
        card=card,
        failure_rate_percent=rate_pct,
        total_production_deployments=total_prod,
        failed_deployments=failed_count,
        incident_linked_deployments=incident_linked_count,
        degraded_deployments=total_degraded,
        history=history,
    )


async def calculate_mean_time_to_recovery(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> RecoveryTimeDetail:
    """
    Computes Mean Time to Recovery (MTTR) / Time to Restore Service:
    Elapsed time between production incident start and resolution.
    Shows INSUFFICIENT_DATA if no incident data source is present.
    """
    start_dt, end_dt, days = parse_time_window(time_window, start_date, end_date)
    prev_start_dt = start_dt - timedelta(days=days)

    query = select(Incident).where(
        Incident.organization_id == organization_id,
        Incident.started_at >= prev_start_dt,
        Incident.started_at <= end_dt,
    )
    if repository_ids:
        query = query.where(Incident.repository_id.in_(repository_ids))

    result = await db.execute(query)
    all_incidents = list(result.scalars().all())

    current_incidents = [i for i in all_incidents if i.started_at >= start_dt]
    prev_incidents = [i for i in all_incidents if i.started_at < start_dt]

    resolved_in_window = [i for i in current_incidents if i.resolved_at and i.status.upper() in ("RESOLVED", "CLOSED")]
    open_in_window = [i for i in current_incidents if i.status.upper() in ("OPEN", "INVESTIGATING")]

    durations_hours: list[float] = []
    history_map: dict[str, list[float]] = defaultdict(list)

    for inc in resolved_in_window:
        dur_sec = inc.recovery_duration_seconds
        if dur_sec is None and inc.resolved_at:
            dur_sec = max((inc.resolved_at - inc.started_at).total_seconds(), 0.0)
        if dur_sec is not None:
            hours = round(dur_sec / 3600.0, 2)
            durations_hours.append(hours)
            day_str = inc.started_at.strftime("%Y-%m-%d")
            history_map[day_str].append(hours)

    sample_size = len(durations_hours)

    if sample_size == 0:
        status_val = "INSUFFICIENT_DATA"
        perf_level = "UNKNOWN"
        perf_label = "Unknown"
        formatted_val = "INSUFFICIENT_DATA"
        median_hours = None
        p75_hours = None
        avg_hours = None
        trend_dir = "NONE"
        trend_pct = None
        context_msg = "No resolved production incidents found. Configure incident integrations to track MTTR."
    else:
        status_val = "CALCULATED"
        median_hours = calculate_percentile(durations_hours, 50.0)
        p75_hours = calculate_percentile(durations_hours, 75.0)
        avg_hours = round(sum(durations_hours) / sample_size, 2)

        check_val = median_hours if median_hours is not None else 0.0
        # Elite: < 1 hour, High: < 1 day (24h), Medium: < 1 week (168h), Low: >= 1 week
        if check_val < 1.0:
            perf_level = "ELITE"
            perf_label = "Elite (< 1 hour)"
            formatted_val = f"{int(check_val * 60)} min"
        elif check_val < 24.0:
            perf_level = "HIGH"
            perf_label = "High (< 24h)"
            formatted_val = f"{check_val:.1f} hrs"
        elif check_val < 168.0:
            perf_level = "MEDIUM"
            perf_label = "Medium (< 1 week)"
            formatted_val = f"{round(check_val / 24.0, 1)} days"
        else:
            perf_level = "LOW"
            perf_label = "Low (> 1 week)"
            formatted_val = f"{round(check_val / 24.0, 1)} days"

        # Previous period comparison
        prev_durations = [
            (i.recovery_duration_seconds or (i.resolved_at - i.started_at).total_seconds()) / 3600.0
            for i in prev_incidents
            if i.resolved_at and i.status.upper() in ("RESOLVED", "CLOSED")
        ]
        prev_median = calculate_percentile(prev_durations, 50.0) if prev_durations else None

        if prev_median and prev_median > 0 and median_hours is not None:
            pct = round(((median_hours - prev_median) / prev_median) * 100, 1)
            trend_pct = pct
            trend_dir = "IMPROVED" if pct < 0 else ("DEGRADED" if pct > 0 else "STABLE")
        else:
            trend_pct = None
            trend_dir = "NONE"

        context_msg = f"Median recovery of {median_hours}h across {sample_size} resolved incidents (P75: {p75_hours}h)."

    history: list[DORATrendPoint] = []
    curr_day = start_dt.date()
    end_date_val = end_dt.date()
    while curr_day <= end_date_val:
        day_str = curr_day.strftime("%Y-%m-%d")
        day_vals = history_map.get(day_str, [])
        med = calculate_percentile(day_vals, 50.0) if day_vals else None
        history.append(DORATrendPoint(date=day_str, value=med, sample_size=len(day_vals)))
        curr_day += timedelta(days=1)

    card = DORAMetricCard(
        metric_type="MEAN_TIME_TO_RECOVERY",
        title="Time to Restore Service (MTTR)",
        status=status_val,
        value=median_hours,
        formatted_value=formatted_val,
        unit="hours" if status_val == "CALCULATED" else "",
        performance_level=perf_level,
        performance_label=perf_label,
        trend_direction=trend_dir,
        trend_percentage=trend_pct,
        sample_size=sample_size,
        data_completeness=1.0 if sample_size > 0 else 0.0,
        period=f"Last {days} Days",
        data_source="Incident Outage Management",
        methodology="Elapsed time between incident start timestamp and documented resolution timestamp.",
        context_message=context_msg,
    )

    return RecoveryTimeDetail(
        card=card,
        median_hours=median_hours,
        p75_hours=p75_hours,
        average_hours=avg_hours,
        total_incidents=len(current_incidents),
        resolved_incidents=len(resolved_in_window),
        open_incidents=len(open_in_window),
        history=history,
    )


def determine_overall_performance(cards: list[DORAMetricCard]) -> str:
    """Evaluates the composite DORA performance level across active pillars."""
    calculated_cards = [c for c in cards if c.status == "CALCULATED" and c.performance_level != "UNKNOWN"]
    if not calculated_cards:
        return "UNKNOWN"

    score_map = {"ELITE": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    scores = [score_map.get(c.performance_level, 1) for c in calculated_cards]
    avg_score = sum(scores) / len(scores)

    if avg_score >= 3.5:
        return "ELITE"
    if avg_score >= 2.5:
        return "HIGH"
    if avg_score >= 1.5:
        return "MEDIUM"
    return "LOW"


async def calculate_dora_overview(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_ids: list[uuid.UUID] | None = None,
    time_window: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
) -> DORAOverviewResponse:
    """Consolidated organization DORA report across all four pillars and repository breakdowns."""
    start_dt, end_dt, _ = parse_time_window(time_window, start_date, end_date)

    df_detail = await calculate_deployment_frequency(
        db, organization_id, repository_ids, time_window, start_date, end_date
    )
    lt_detail = await calculate_lead_time_for_changes(
        db, organization_id, repository_ids, time_window, start_date, end_date
    )
    cfr_detail = await calculate_change_failure_rate(
        db, organization_id, repository_ids, time_window, start_date, end_date
    )
    mttr_detail = await calculate_mean_time_to_recovery(
        db, organization_id, repository_ids, time_window, start_date, end_date
    )

    cards = [
        df_detail.card,
        lt_detail.card,
        cfr_detail.card,
        mttr_detail.card,
    ]
    overall_tier = determine_overall_performance(cards)

    # Repository breakdowns
    repos_query = select(Repository).where(Repository.organization_id == organization_id)
    if repository_ids:
        repos_query = repos_query.where(Repository.id.in_(repository_ids))
    repos_res = await db.execute(repos_query)
    repositories = list(repos_res.scalars().all())

    repo_overviews: list[RepositoryDORAOverview] = []
    for r in repositories:
        r_df = await calculate_deployment_frequency(db, organization_id, [r.id], time_window, start_date, end_date)
        r_lt = await calculate_lead_time_for_changes(db, organization_id, [r.id], time_window, start_date, end_date)
        r_cfr = await calculate_change_failure_rate(db, organization_id, [r.id], time_window, start_date, end_date)
        r_mttr = await calculate_mean_time_to_recovery(db, organization_id, [r.id], time_window, start_date, end_date)

        repo_overviews.append(
            RepositoryDORAOverview(
                repository_id=r.id,
                repository_name=r.name,
                deployment_frequency=r_df.card,
                lead_time=r_lt.card,
                change_failure_rate=r_cfr.card,
                mean_time_to_recovery=r_mttr.card,
            )
        )

    # Integration status detection
    has_incidents = (
        await db.scalar(
            select(func.count(Incident.id)).where(Incident.organization_id == organization_id)
        )
        or 0
    ) > 0
    has_deployments = (
        await db.scalar(
            select(func.count(Deployment.id)).where(Deployment.organization_id == organization_id)
        )
        or 0
    ) > 0

    return DORAOverviewResponse(
        organization_id=organization_id,
        time_window=time_window,
        start_date=start_dt,
        end_date=end_dt,
        overall_performance=overall_tier,
        deployment_frequency=df_detail.card,
        lead_time_for_changes=lt_detail.card,
        change_failure_rate=cfr_detail.card,
        mean_time_to_recovery=mttr_detail.card,
        repository_breakdowns=repo_overviews,
        integration_status={
            "github_actions": True,
            "github_deployments": has_deployments,
            "incident_system": has_incidents,
        },
    )


async def generate_and_save_dora_snapshots(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_id: uuid.UUID | None = None,
    time_window: str = "30d",
) -> list[DORAMetricSnapshot]:
    """Generates and persists DORAMetricSnapshot records for historical tracking and caching."""
    repo_ids = [repository_id] if repository_id else None
    overview = await calculate_dora_overview(db, organization_id, repo_ids, time_window)
    now = datetime.now(UTC)

    snapshots: list[DORAMetricSnapshot] = []
    metric_cards = [
        overview.deployment_frequency,
        overview.lead_time_for_changes,
        overview.change_failure_rate,
        overview.mean_time_to_recovery,
    ]

    for card in metric_cards:
        snapshot = DORAMetricSnapshot(
            id=uuid.uuid4(),
            organization_id=organization_id,
            repository_id=repository_id,
            metric_type=card.metric_type,
            metric_value=card.value,
            status=card.status,
            performance_level=card.performance_level,
            period_start=overview.start_date,
            period_end=overview.end_date,
            sample_size=card.sample_size,
            data_completeness=card.data_completeness,
            calculated_at=now,
            methodology_version="v1.0",
            details={
                "formatted_value": card.formatted_value,
                "unit": card.unit,
                "trend_direction": card.trend_direction,
                "trend_percentage": card.trend_percentage,
                "data_source": card.data_source,
            },
        )
        db.add(snapshot)
        snapshots.append(snapshot)

    await db.commit()
    return snapshots
