from enum import StrEnum


class SeverityLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def determine_review_delay_severity(observed_hours: float) -> SeverityLevel:
    """Classifies severity based on review waiting duration or median TTFR."""
    if observed_hours >= 48.0:
        return SeverityLevel.CRITICAL
    if observed_hours >= 24.0:
        return SeverityLevel.HIGH
    if observed_hours >= 12.0:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def determine_approval_delay_severity(turnaround_hours: float, review_rounds: float) -> SeverityLevel:
    """Classifies approval latency and rework churn severity."""
    if turnaround_hours >= 72.0 or review_rounds >= 4.0:
        return SeverityLevel.CRITICAL
    if turnaround_hours >= 36.0 or review_rounds >= 2.5:
        return SeverityLevel.HIGH
    if turnaround_hours >= 18.0 or review_rounds >= 2.0:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def determine_merge_delay_severity(merge_lag_hours: float) -> SeverityLevel:
    """Classifies delay between approval and final merge."""
    if merge_lag_hours >= 48.0:
        return SeverityLevel.CRITICAL
    if merge_lag_hours >= 24.0:
        return SeverityLevel.HIGH
    if merge_lag_hours >= 12.0:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def determine_workload_severity(gini_coefficient: float, max_share_pct: float) -> SeverityLevel:
    """Classifies reviewer load concentration without individual developer ranking."""
    if gini_coefficient >= 0.60 or max_share_pct >= 60.0:
        return SeverityLevel.CRITICAL
    if gini_coefficient >= 0.45 or max_share_pct >= 45.0:
        return SeverityLevel.HIGH
    if gini_coefficient >= 0.35:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def determine_pr_size_severity(large_to_small_ratio: float) -> SeverityLevel:
    """Classifies turnaround divergence between oversized PRs and small PRs."""
    if large_to_small_ratio >= 4.0:
        return SeverityLevel.HIGH
    if large_to_small_ratio >= 2.5:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def determine_repository_workflow_severity(cycle_time_hours: float, merge_rate_pct: float) -> SeverityLevel:
    """Classifies overall repository lifecycle friction."""
    if cycle_time_hours >= 96.0 or (merge_rate_pct < 40.0 and cycle_time_hours >= 48.0):
        return SeverityLevel.CRITICAL
    if cycle_time_hours >= 48.0 or merge_rate_pct < 60.0:
        return SeverityLevel.HIGH
    if cycle_time_hours >= 24.0 or merge_rate_pct < 75.0:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW
