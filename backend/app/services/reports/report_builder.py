from typing import Any


class ReportSectionBuilder:
    """
    Builds structured, typed report sections tailored for each report variant:
    ENGINEERING_HEALTH, WEEKLY, MONTHLY, REPOSITORY_HEALTH, DORA.
    """

    @staticmethod
    def build_sections(
        report_type: str,
        metrics_data: dict[str, Any],
        executive_summary: str,
        comparison_data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        team = metrics_data.get("team", {})
        dora = metrics_data.get("dora", {})
        bottlenecks = metrics_data.get("bottlenecks", [])

        # Common Section 1: Executive Summary
        sections.append({
            "section_type": "EXECUTIVE_SUMMARY",
            "title": "Executive Summary & Engineering Diagnostic",
            "content": {
                "summary_text": executive_summary,
                "report_type": report_type,
            },
            "evidence": {
                "period": metrics_data.get("period_label", "Recent Period"),
                "total_prs": team.get("throughput", {}).get("total_prs_opened", 0),
            },
            "order_index": 1,
        })

        # Common Section 2: KPI & Throughput Overview
        sections.append({
            "section_type": "KPI_SUMMARY",
            "title": "Delivery Throughput & Flow Cadence",
            "content": {
                "throughput": team.get("throughput", {}),
                "cadence": team.get("cadence", {}),
                "comparison": comparison_data or {},
            },
            "evidence": {
                "prs_merged": team.get("throughput", {}).get("total_prs_merged", 0),
                "merge_rate": team.get("throughput", {}).get("merge_rate", 0.0),
            },
            "order_index": 2,
        })

        if report_type in ("ENGINEERING_HEALTH", "WEEKLY", "MONTHLY", "REPOSITORY_HEALTH"):
            # Section 3: Peer Review Intelligence & Collaboration
            sections.append({
                "section_type": "COLLABORATION_HEALTH",
                "title": "Peer Review Loops & Code Health Dynamics",
                "content": {
                    "collaboration": team.get("collaboration", {}),
                    "cadence": team.get("cadence", {}),
                },
                "evidence": {
                    "median_ttfr": team.get("cadence", {}).get("median_time_to_first_review_hours"),
                    "review_coverage": team.get("collaboration", {}).get("review_coverage", 0.0),
                },
                "order_index": 3,
            })

            # Section 4: Workflow Bottlenecks & Friction Points
            sections.append({
                "section_type": "BOTTLENECK_ANALYSIS",
                "title": "Process Friction & Bottleneck Radar",
                "content": {
                    "bottlenecks": bottlenecks,
                    "active_count": len(bottlenecks),
                    "high_severity_count": sum(1 for b in bottlenecks if b.get("severity") in ("CRITICAL", "HIGH")),
                },
                "evidence": {
                    "evaluated_rules": ["BOT-01", "BOT-02", "BOT-03", "BOT-04", "BOT-05", "BOT-06"],
                },
                "order_index": 4,
            })

        # DORA Section
        sections.append({
            "section_type": "DORA_METRICS",
            "title": "DORA Software Delivery Performance Pillars",
            "content": {
                "deployment_frequency": dora.get("deployment_frequency", {}),
                "lead_time_for_changes": dora.get("lead_time_for_changes", {}),
                "change_failure_rate": dora.get("change_failure_rate", {}),
                "mean_time_to_recovery": dora.get("mean_time_to_recovery", {}),
                "overall_tier": dora.get("overall_tier", "UNKNOWN"),
            },
            "evidence": {
                "provenance": "Verified production deployments and incident tracking",
                "insufficient_data": dora.get("deployment_frequency", {}).get("status") == "INSUFFICIENT_DATA",
            },
            "order_index": 5,
        })

        # Actionable Recommendations Section
        recommendations = metrics_data.get("recommendations", [])
        if not recommendations and bottlenecks:
            recommendations = [b.get("recommendation") for b in bottlenecks if b.get("recommendation")]

        sections.append({
            "section_type": "RECOMMENDATIONS",
            "title": "Actionable Systemic Recommendations",
            "content": {
                "recommendations": recommendations[:6],
                "anti_surveillance_charter": (
                    "DCP strictly guarantees zero individual developer rankings, surveillance scores, "
                    "or personal velocity quotas. All priorities address systemic team process health."
                ),
            },
            "evidence": {
                "source": "Aggregated team flow telemetry and bottleneck rules engine",
            },
            "order_index": 6,
        })

        # Methodology & Integrity Section
        sections.append({
            "section_type": "METHODOLOGY",
            "title": "Calculation Methodology & Data Limitations",
            "content": {
                "time_window": metrics_data.get("period_label", "Selected Window"),
                "provenance_standards": (
                    "All metrics are calculated via non-blocking asynchronous queries against verified "
                    "GitHub webhooks and CI/CD deployment status updates. No data is manufactured or estimated."
                ),
            },
            "evidence": {
                "integrity_guarantee": "Strictly honest provenance with explicit INSUFFICIENT_DATA states",
            },
            "order_index": 7,
        })

        return sections
