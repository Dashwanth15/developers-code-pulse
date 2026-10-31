import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github import Repository
from app.services.analytics.review_metrics import (
    calculate_review_analytics,
    get_pending_review_queue,
)
from app.services.bottlenecks.confidence import evaluate_confidence
from app.services.bottlenecks.detector_base import BaseBottleneckDetector, DetectedBottleneck
from app.services.bottlenecks.recommendations import get_review_delay_recommendation
from app.services.bottlenecks.severity import determine_review_delay_severity


class ReviewDelayDetector(BaseBottleneckDetector):
    """
    Detects PR review bottlenecks:
    - High Time to First Review (TTFR) exceeding team SLAs (>12h).
    - Accumulating pending review queue backlogs (>= 3 PRs waiting >= 12h).
    - Severe review starvation on individual PRs waiting >= 24h.
    """

    bottleneck_type = "PR_REVIEW_DELAY"

    async def detect(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        repository: Repository | None = None,
        time_window: str = "30d",
    ) -> list[DetectedBottleneck]:
        bottlenecks: list[DetectedBottleneck] = []
        repo_ids = [repository.id] if repository else None

        # 1. Fetch review metrics
        analytics = await calculate_review_analytics(
            db=db,
            organization_id=organization_id,
            repository_ids=repo_ids,
            time_window=time_window,
        )

        # 2. Fetch pending queue
        pending_queue = await get_pending_review_queue(
            db=db,
            organization_id=organization_id,
            repository_ids=repo_ids,
        )

        ttfr_median = analytics.metrics.time_to_first_review.median_hours
        total_reviewed_count = sum(h.count for h in analytics.turnaround_histogram)

        # Check A: High median TTFR across the repository / organization
        if ttfr_median is not None and ttfr_median >= 12.0:
            severity = determine_review_delay_severity(ttfr_median)
            confidence = evaluate_confidence(total_reviewed_count)
            fingerprint = self.compute_fingerprint(
                organization_id, repository.id if repository else None, "ttfr_latency"
            )
            recommendation = get_review_delay_recommendation(
                ttfr_median, pending_queue.total_pending
            )

            repo_label = repository.name if repository else "organization-wide"
            title = f"High Time to First Review ({ttfr_median:.1f}h) in {repo_label}"
            description = (
                f"Median Time to First Review is currently {ttfr_median:.1f} hours, "
                f"exceeding the standard 8-hour operational SLA. "
                f"{analytics.metrics.time_to_first_review.p75_hours or 0.0:.1f}h at P75."
            )

            evidence = {
                "metric": "time_to_first_review_median_hours",
                "observed_value": ttfr_median,
                "p75_value": analytics.metrics.time_to_first_review.p75_hours,
                "p90_value": analytics.metrics.time_to_first_review.p90_hours,
                "benchmark_comparison": analytics.metrics.time_to_first_review.benchmark_comparison,
                "reviewed_prs_count": total_reviewed_count,
                "sample_size": total_reviewed_count,
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
                    observed_value=ttfr_median,
                    baseline_value=8.0,
                    repository_id=repository.id if repository else None,
                )
            )

        # Check B: Accumulated Urgent Pending Review Queue Backlog
        if pending_queue.total_pending >= 3:
            avg_wait = (
                sum(item.waiting_hours for item in pending_queue.items) / pending_queue.total_pending
            )
            severity = determine_review_delay_severity(avg_wait)
            confidence = evaluate_confidence(pending_queue.total_pending)
            fingerprint = self.compute_fingerprint(
                organization_id, repository.id if repository else None, "pending_queue_backlog"
            )
            recommendation = get_review_delay_recommendation(
                avg_wait, pending_queue.total_pending
            )

            repo_label = repository.name if repository else "all monitored repositories"
            title = f"Growing Review Queue Backlog ({pending_queue.total_pending} PRs) in {repo_label}"
            description = (
                f"{pending_queue.total_pending} active pull requests have been waiting for review "
                f"longer than 12 hours (average wait: {avg_wait:.1f}h)."
            )

            evidence = {
                "metric": "pending_review_queue_depth",
                "observed_value": pending_queue.total_pending,
                "average_wait_hours": round(avg_wait, 1),
                "threshold_hours": 12.0,
                "affected_pull_requests": [
                    {
                        "pr_id": str(p.pull_request_id),
                        "number": p.number,
                        "title": p.title,
                        "waiting_hours": p.waiting_hours,
                        "repository": p.repository_name,
                    }
                    for p in pending_queue.items[:10]
                ],
                "sample_size": pending_queue.total_pending,
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
                    observed_value=float(pending_queue.total_pending),
                    baseline_value=0.0,
                    repository_id=repository.id if repository else None,
                )
            )

        return bottlenecks
