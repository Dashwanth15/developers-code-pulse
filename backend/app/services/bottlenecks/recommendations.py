def get_review_delay_recommendation(observed_hours: float, pending_count: int) -> str:
    if pending_count > 5:
        return (
            f"Review queue backlog currently holds {pending_count} PRs with average review wait "
            f"of {observed_hours:.1f}h. Institute daily review triage blocks at standup and activate "
            "round-robin CODEOWNERS assignments to unblock inbound flow."
        )
    return (
        f"Initial review turnaround ({observed_hours:.1f}h) exceeds the 8-hour delivery SLA. "
        "Adopt team review pairing and configure GitHub review request notifications in team Slack/Discord "
        "channels to shorten time-to-first-review."
    )


def get_approval_delay_recommendation(turnaround_hours: float, review_rounds: float) -> str:
    if review_rounds >= 2.5:
        return (
            f"PRs are undergoing an average of {review_rounds:.1f} review iterations before approval. "
            "High rework churn indicates ambiguity in architectural requirements or test expectations. "
            "Introduce synchronous design huddles prior to coding and enforce automated lint/test pre-commit hooks."
        )
    return (
        f"Approval latency is averaging {turnaround_hours:.1f}h after initial review. Establish explicit "
        "sign-off criteria and clarify whether comments are blocking vs non-blocking suggestions to accelerate sign-offs."
    )


def get_merge_delay_recommendation(merge_lag_hours: float, approved_unmerged_count: int) -> str:
    if approved_unmerged_count > 3:
        return (
            f"{approved_unmerged_count} approved pull requests remain unmerged with an average lag of "
            f"{merge_lag_hours:.1f}h. Enable GitHub auto-merge or introduce a merge queue to deploy changes "
            "as soon as required approvals and continuous integration checks pass."
        )
    return (
        f"Approved changes linger {merge_lag_hours:.1f}h before merging into the trunk. Streamline CI "
        "pipeline duration and empower authors to merge immediately upon green build verification."
    )


def get_reviewer_workload_recommendation(gini_coefficient: float, max_share_pct: float) -> str:
    return (
        f"Reviewer workload Gini index ({gini_coefficient:.3f}) indicates extreme peer review concentration, "
        f"with a single senior engineer handling {max_share_pct:.1f}% of all reviews. Rotate primary code "
        "ownership, encourage junior/mid-level peer reviews with senior shadowing, and eliminate single-point-of-failure bottlenecks."
    )


def get_pr_size_recommendation(large_merge_hours: float, small_merge_hours: float, ratio: float) -> str:
    return (
        f"Large pull requests (>500 lines) require {large_merge_hours:.1f}h to merge compared to "
        f"{small_merge_hours:.1f}h for small PRs ({ratio:.1f}x latency divergence). Decompose large features "
        "into atomic stacked pull requests under 200 lines to accelerate review velocity and reduce cognitive overhead."
    )


def get_repository_backlog_recommendation(cycle_time_hours: float, open_pr_count: int, merge_rate: float) -> str:
    return (
        f"Repository cycle time ({cycle_time_hours:.1f}h) and low merge completion rate ({merge_rate:.1f}%) "
        f"with {open_pr_count} open pull requests indicate systemic pipeline friction. Conduct a team work-in-progress (WIP) "
        "audit, limit concurrent open feature branches, and prioritize unblocking existing changes before opening new work."
    )
