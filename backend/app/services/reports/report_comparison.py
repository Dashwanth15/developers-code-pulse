from typing import Any


def calculate_period_comparison(
    current_metrics: dict[str, Any],
    previous_metrics: dict[str, Any],
) -> dict[str, Any]:
    """
    Computes delta and percentage comparisons between the current reporting period
    and the immediately preceding baseline period without fabricating data.
    """
    deltas: dict[str, Any] = {}

    # Throughput deltas
    cur_tp = current_metrics.get("team", {}).get("throughput", {})
    prev_tp = previous_metrics.get("team", {}).get("throughput", {})

    cur_prs = cur_tp.get("total_prs_merged", 0)
    prev_prs = prev_tp.get("total_prs_merged", 0)
    pr_diff = cur_prs - prev_prs
    pr_pct = (pr_diff / prev_prs * 100.0) if prev_prs > 0 else (100.0 if cur_prs > 0 else 0.0)

    cur_mr = cur_tp.get("merge_rate", 0.0)
    prev_mr = prev_tp.get("merge_rate", 0.0)

    deltas["prs_merged"] = {
        "current": cur_prs,
        "previous": prev_prs,
        "delta": pr_diff,
        "percentage": round(pr_pct, 1),
    }
    deltas["merge_rate"] = {
        "current": cur_mr,
        "previous": prev_mr,
        "delta": round(cur_mr - prev_mr, 1),
    }

    # Cadence deltas (negative delta is positive improvement in turnaround latency)
    cur_cad = current_metrics.get("team", {}).get("cadence", {})
    prev_cad = previous_metrics.get("team", {}).get("cadence", {})

    cur_cycle = cur_cad.get("median_pr_cycle_time_hours")
    prev_cycle = prev_cad.get("median_pr_cycle_time_hours")
    if cur_cycle is not None and prev_cycle is not None:
        deltas["cycle_time_hours"] = {
            "current": cur_cycle,
            "previous": prev_cycle,
            "delta": round(cur_cycle - prev_cycle, 1),
            "improved": cur_cycle < prev_cycle,
        }

    cur_ttfr = cur_cad.get("median_time_to_first_review_hours")
    prev_ttfr = prev_cad.get("median_time_to_first_review_hours")
    if cur_ttfr is not None and prev_ttfr is not None:
        deltas["ttfr_hours"] = {
            "current": cur_ttfr,
            "previous": prev_ttfr,
            "delta": round(cur_ttfr - prev_ttfr, 1),
            "improved": cur_ttfr < prev_ttfr,
        }

    # DORA deltas
    cur_dora = current_metrics.get("dora", {})
    prev_dora = previous_metrics.get("dora", {})

    cur_df = cur_dora.get("deployment_frequency", {}).get("sample_size", 0)
    prev_df = prev_dora.get("deployment_frequency", {}).get("sample_size", 0)
    deltas["deployments"] = {
        "current": cur_df,
        "previous": prev_df,
        "delta": cur_df - prev_df,
    }

    return deltas
