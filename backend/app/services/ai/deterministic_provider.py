from typing import Any

from app.services.ai.base import BaseAIProvider


class DeterministicAIProvider(BaseAIProvider):
    """
    Deterministic, rule-driven engineering insights engine.
    Ensures Developers Code Pulse always delivers high-fidelity, evidence-backed
    explanations even when external generative AI APIs are offline or unconfigured.
    """

    def is_available(self) -> bool:
        return True

    async def generate_executive_summary(
        self,
        metrics_payload: dict[str, Any],
        organization_name: str,
        period_label: str,
    ) -> str:
        team_data = metrics_payload.get("team", {})
        throughput = team_data.get("throughput", {})
        cadence = team_data.get("cadence", {})
        dora = metrics_payload.get("dora", {})
        bottlenecks = metrics_payload.get("bottlenecks", [])

        prs_merged = throughput.get("total_prs_merged", 0)
        merge_rate = throughput.get("merge_rate", 0.0)
        median_cycle_time = cadence.get("median_pr_cycle_time_hours")
        active_bottlenecks_count = len(bottlenecks)

        df_status = dora.get("deployment_frequency", {}).get("status", "INSUFFICIENT_DATA")
        df_val = dora.get("deployment_frequency", {}).get("formatted_value", "N/A")

        summary_parts = [
            f"During {period_label}, {organization_name} recorded {prs_merged} pull requests merged "
            f"with an overall merge closure rate of {merge_rate:.1f}%."
        ]

        if median_cycle_time is not None:
            summary_parts.append(
                f"The team sustained a median delivery turnaround cycle time of {median_cycle_time:.1f} hours."
            )

        if df_status == "CALCULATED":
            summary_parts.append(f"Production deployment cadence registered at {df_val}.")
        else:
            summary_parts.append(
                "Production deployment telemetry currently reports insufficient external CI/CD data."
            )

        if active_bottlenecks_count > 0:
            critical_count = sum(1 for b in bottlenecks if b.get("severity") in ("CRITICAL", "HIGH"))
            summary_parts.append(
                f"Workflow analysis detected {active_bottlenecks_count} active process friction point(s), "
                f"including {critical_count} high or critical priority constraint(s) impacting team flow."
            )
        else:
            summary_parts.append(
                "Workflow health is optimal with zero active delivery bottlenecks detected across pipelines."
            )

        summary_parts.append(
            "Note: Insights are strictly computed from aggregate organization flow and peer review dynamics "
            "in compliance with DCP's Anti-Surveillance Ethics Charter."
        )

        return " ".join(summary_parts)

    async def generate_insights(
        self,
        metrics_payload: dict[str, Any],
        organization_name: str,
        period_label: str,
        focus_areas: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        _ = (organization_name, focus_areas)
        insights: list[dict[str, Any]] = []

        team_data = metrics_payload.get("team", {})
        throughput = team_data.get("throughput", {})
        cadence = team_data.get("cadence", {})
        collaboration = team_data.get("collaboration", {})
        dora = metrics_payload.get("dora", {})
        bottlenecks = metrics_payload.get("bottlenecks", [])

        # 1. Macro Throughput & Cadence Flow
        prs_merged = throughput.get("total_prs_merged", 0)
        merge_rate = throughput.get("merge_rate", 0.0)
        median_cycle_time = cadence.get("median_pr_cycle_time_hours")

        if prs_merged > 0:
            cycle_desc = f" with a median cycle time of {median_cycle_time:.1f} hours" if median_cycle_time else ""
            if merge_rate >= 75.0:
                insights.append({
                    "insight_type": "POSITIVE_TREND",
                    "title": "Healthy Pull Request Closure Cadence",
                    "explanation": (
                        f"The engineering organization achieved a high merge rate of {merge_rate:.1f}% "
                        f"({prs_merged} PRs merged){cycle_desc}, indicating minimal unmerged rework and focused branch delivery."
                    ),
                    "evidence": {
                        "prs_merged": prs_merged,
                        "merge_rate": merge_rate,
                        "sample_size": prs_merged,
                        "period": period_label,
                    },
                    "recommendation": "Maintain current branch hygiene and small incremental PR scopes.",
                    "confidence": 0.95,
                })
            else:
                insights.append({
                    "insight_type": "DETERIORATING_TREND",
                    "title": "Elevated Pull Request Churn or Stalled Branches",
                    "explanation": (
                        f"Merge rate dropped to {merge_rate:.1f}%, indicating that a notable fraction of opened "
                        f"pull requests are closed unmerged or experience protracted stalls."
                    ),
                    "evidence": {
                        "prs_merged": prs_merged,
                        "merge_rate": merge_rate,
                        "period": period_label,
                    },
                    "recommendation": (
                        "Standardize definition-of-ready criteria before PR creation to prevent abandoned feature branches."
                    ),
                    "confidence": 0.88,
                })

        # 2. Peer Review Turnaround
        ttfr = cadence.get("median_time_to_first_review_hours")
        if ttfr is not None:
            if ttfr <= 6.0:
                insights.append({
                    "insight_type": "POSITIVE_TREND",
                    "title": "Rapid Peer Review Feedback Loops",
                    "explanation": (
                        f"Median Time to First Review (TTFR) is {ttfr:.1f} hours, demonstrating responsive peer review "
                        f"practices that keep author momentum high."
                    ),
                    "evidence": {
                        "median_ttfr_hours": ttfr,
                        "benchmark_hours": 12.0,
                    },
                    "recommendation": "Continue prioritizing peer review queues during morning engineering syncs.",
                    "confidence": 0.92,
                })
            elif ttfr > 16.0:
                insights.append({
                    "insight_type": "WORKFLOW_BOTTLENECK",
                    "title": "Protracted Review Response Latency",
                    "explanation": (
                        f"Median Time to First Review is {ttfr:.1f} hours, significantly exceeding the 12-hour "
                        f"healthy threshold and contributing to delivery lag."
                    ),
                    "evidence": {
                        "median_ttfr_hours": ttfr,
                        "healthy_threshold": 12.0,
                    },
                    "recommendation": (
                        "Institute automated code review routing (CODEOWNERS or round-robin PR assignment) "
                        "and establish dedicated review office hours."
                    ),
                    "confidence": 0.90,
                })

        # 3. Peer Collaboration Health
        multi_reviewer_rate = collaboration.get("multi_reviewer_rate", 0.0)
        review_coverage = collaboration.get("review_coverage", 0.0)
        if review_coverage > 0:
            insights.append({
                "insight_type": "HEALTH_DIAGNOSTIC",
                "title": "Code Review Participation & Coverage",
                "explanation": (
                    f"{review_coverage:.1f}% of merged pull requests received formal peer review, with "
                    f"{multi_reviewer_rate:.1f}% engaging multiple peer reviewers."
                ),
                "evidence": {
                    "review_coverage": review_coverage,
                    "multi_reviewer_rate": multi_reviewer_rate,
                },
                "recommendation": (
                    "Ensure high-complexity architectural PRs maintain dual-approval policies while allowing "
                    "low-risk changes to merge with single approval to avoid throughput drag."
                ),
                "confidence": 0.85,
            })

        # 4. Critical Bottlenecks Prioritization
        sorted_bottlenecks = sorted(
            bottlenecks,
            key=lambda b: {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(b.get("severity", "LOW"), 0),
            reverse=True,
        )
        for b in sorted_bottlenecks[:3]:
            insights.append({
                "insight_type": "BOTTLENECK_EXPLANATION",
                "title": f"Process Constraint: {b.get('title', 'Workflow Friction')}",
                "explanation": (
                    f"[{b.get('severity', 'MEDIUM')}] {b.get('description', '')}. "
                    f"This systemic constraint introduces measurable delay in delivery throughput."
                ),
                "evidence": {
                    "category": b.get("category"),
                    "severity": b.get("severity"),
                    "rule_id": b.get("rule_id"),
                    "evidence": b.get("evidence"),
                },
                "recommendation": b.get("recommendation", "Review workflow queue dynamics."),
                "confidence": float(b.get("confidence", 0.9)),
            })

        # 5. DORA Performance Highlights
        dora_df = dora.get("deployment_frequency", {})
        dora_lt = dora.get("lead_time_for_changes", {})
        dora_cfr = dora.get("change_failure_rate", {})
        dora_mttr = dora.get("mean_time_to_recovery", {})

        if dora_df.get("status") == "CALCULATED":
            lt_val = dora_lt.get("formatted_value", "N/A")
            cfr_val = dora_cfr.get("formatted_value", "N/A")
            mttr_val = dora_mttr.get("formatted_value", "N/A")
            insights.append({
                "insight_type": "DORA_EVALUATION",
                "title": f"DORA Delivery Profile: {dora_df.get('performance_level', 'UNKNOWN')}",
                "explanation": (
                    f"Production rollouts occur at {dora_df.get('formatted_value')} ({dora_df.get('performance_level')}). "
                    f"Lead time: {lt_val}, Change failure rate: {cfr_val}, MTTR: {mttr_val}."
                ),
                "evidence": {
                    "metric_type": "DORA_OVERVIEW",
                    "deployment_frequency": dora_df.get("formatted_value"),
                    "lead_time": lt_val,
                    "change_failure_rate": cfr_val,
                    "mttr": mttr_val,
                },
                "recommendation": "Maintain deployment automation and trunk-based integration practices.",
                "confidence": 0.95,
            })
        else:
            insights.append({
                "insight_type": "DATA_INTEGRITY_NOTICE",
                "title": "DORA Metrics: Additional Integration Required",
                "explanation": (
                    "DCP strictly prevents manufactured or placeholder deployment statistics. "
                    "Connect GitHub Actions production release workflows or deploy webhooks to calculate live DORA pillars."
                ),
                "evidence": {
                    "status": "INSUFFICIENT_DATA",
                    "required_source": "GitHub Actions / Production Deployments API",
                },
                "recommendation": "Configure production environment tags in repository release pipelines.",
                "confidence": 1.0,
            })

        return insights
