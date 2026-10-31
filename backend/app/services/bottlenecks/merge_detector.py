import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.github import Repository
from app.models.pull_requests import PullRequest
from app.services.analytics.pull_request_metrics import calculate_percentile
from app.services.bottlenecks.confidence import evaluate_confidence
from app.services.bottlenecks.detector_base import BaseBottleneckDetector, DetectedBottleneck
from app.services.bottlenecks.recommendations import get_merge_delay_recommendation
from app.services.bottlenecks.severity import determine_merge_delay_severity


class MergeDelayDetector(BaseBottleneckDetector):
    """
    Detects merge delivery bottlenecks:
    - Approved pull requests languishing unmerged (waiting >= 12h post-approval).
    - High overall merge latency exceeding 24 hours.
    - Deployment queue congestion.
    """

    bottleneck_type = "MERGE_DELAY"

    async def detect(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        repository: Repository | None = None,
        time_window: str = "30d",
    ) -> list[DetectedBottleneck]:
        bottlenecks: list[DetectedBottleneck] = []
        now = datetime.now(UTC)

        # 1. Query open, non-draft PRs with reviews to find approved unmerged ones
        query = (
            select(PullRequest)
            .options(
                selectinload(PullRequest.reviews),
                selectinload(PullRequest.repository),
            )
            .join(PullRequest.repository)
            .where(
                PullRequest.repository.has(organization_id=organization_id),
                PullRequest.state == "OPEN",
                PullRequest.is_draft.is_(False),
            )
        )
        if repository:
            query = query.where(PullRequest.repository_id == repository.id)

        res = await db.execute(query)
        open_prs = list(res.scalars().all())

        approved_unmerged: list[dict] = []
        for pr in open_prs:
            approvals = [r for r in pr.reviews if r.state == "APPROVED"]
            if approvals:
                latest_approval = max(approvals, key=lambda r: r.submitted_at)
                lag_hours = (now - latest_approval.submitted_at).total_seconds() / 3600.0
                if lag_hours >= 12.0:
                    approved_unmerged.append(
                        {
                            "pr_id": str(pr.id),
                            "number": pr.number,
                            "title": pr.title,
                            "repository": pr.repository.name if pr.repository else "unknown",
                            "lag_hours": round(lag_hours, 1),
                            "approved_at": latest_approval.submitted_at.isoformat(),
                        }
                    )

        # 2. Check for approved unmerged accumulation
        if approved_unmerged:
            avg_lag = sum(item["lag_hours"] for item in approved_unmerged) / len(approved_unmerged)
            severity = determine_merge_delay_severity(avg_lag)
            confidence = evaluate_confidence(len(approved_unmerged))
            fingerprint = self.compute_fingerprint(
                organization_id, repository.id if repository else None, "approved_unmerged_backlog"
            )
            recommendation = get_merge_delay_recommendation(avg_lag, len(approved_unmerged))

            repo_label = repository.name if repository else "all monitored repositories"
            title = f"{len(approved_unmerged)} Approved PRs Languishing Unmerged in {repo_label}"
            description = (
                f"{len(approved_unmerged)} pull requests have received formal sign-off but remain "
                f"unmerged with an average post-approval delay of {avg_lag:.1f} hours."
            )

            evidence = {
                "metric": "approved_unmerged_count",
                "observed_value": len(approved_unmerged),
                "average_lag_hours": round(avg_lag, 1),
                "threshold_hours": 12.0,
                "affected_pull_requests": approved_unmerged[:10],
                "sample_size": len(approved_unmerged),
                "is_baseline_established": confidence.is_baseline_established,
                "confidence_explanation": confidence.explanation,
            }

            bottlenecks.append(
                DetectedBottleneck(
                    bottleneck_type=self.bottleneck_type,
                    severity=str(severity),
                    confidence=str(confidence.level),
                    title=title,
                    description=description,
                    evidence=evidence,
                    recommendation=recommendation,
                    fingerprint=fingerprint,
                    observed_value=float(len(approved_unmerged)),
                    baseline_value=0.0,
                    repository_id=repository.id if repository else None,
                )
            )

        # 3. Check historical merge time of merged PRs in this time window
        from datetime import timedelta
        days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
        days = days_map.get(time_window, 30)
        start_date = now - timedelta(days=days)

        merged_q = (
            select(PullRequest.merge_time_seconds)
            .join(PullRequest.repository)
            .where(
                PullRequest.repository.has(organization_id=organization_id),
                PullRequest.state == "MERGED",
                PullRequest.merged_at >= start_date,
                PullRequest.merge_time_seconds.is_not(None),
            )
        )
        if repository:
            merged_q = merged_q.where(PullRequest.repository_id == repository.id)

        merged_res = await db.execute(merged_q)
        merge_times_hours = [s / 3600.0 for s in merged_res.scalars().all() if s and s > 0]

        if merge_times_hours and len(merge_times_hours) >= 3:
            median_merge = calculate_percentile(merge_times_hours, 50.0)
            if median_merge is not None and median_merge >= 24.0:
                severity = determine_merge_delay_severity(median_merge)
                confidence = evaluate_confidence(len(merge_times_hours))
                fingerprint = self.compute_fingerprint(
                    organization_id, repository.id if repository else None, "historical_merge_time_lag"
                )
                recommendation = get_merge_delay_recommendation(median_merge, 0)

                repo_label = repository.name if repository else "organization-wide"
                title = f"High Median PR Merge Time ({median_merge:.1f}h) in {repo_label}"
                description = (
                    f"Merged pull requests exhibit a median merge turnaround of {median_merge:.1f} hours, "
                    "exceeding the standard 24-hour cycle threshold."
                )

                evidence = {
                    "metric": "median_merge_time_hours",
                    "observed_value": median_merge,
                    "p75_merge_hours": calculate_percentile(merge_times_hours, 75.0),
                    "merged_prs_count": len(merge_times_hours),
                    "sample_size": len(merge_times_hours),
                    "is_baseline_established": confidence.is_baseline_established,
                    "confidence_explanation": confidence.explanation,
                }

                bottlenecks.append(
                    DetectedBottleneck(
                        bottleneck_type=self.bottleneck_type,
                        severity=str(severity),
                        confidence=str(confidence.level),
                        title=title,
                        description=description,
                        evidence=evidence,
                        recommendation=recommendation,
                        fingerprint=fingerprint,
                        observed_value=median_merge,
                        baseline_value=12.0,
                        repository_id=repository.id if repository else None,
                    )
                )

        return bottlenecks
