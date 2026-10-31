import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github import Repository
from app.services.analytics.review_metrics import calculate_review_analytics
from app.services.bottlenecks.confidence import evaluate_confidence
from app.services.bottlenecks.detector_base import BaseBottleneckDetector, DetectedBottleneck
from app.services.bottlenecks.recommendations import get_approval_delay_recommendation
from app.services.bottlenecks.severity import determine_approval_delay_severity


class ApprovalDelayDetector(BaseBottleneckDetector):
    """
    Detects approval bottlenecks:
    - Long latency from first review feedback to final approval (>18h).
    - Excessive review iterations/rework churn before merge (>2.0 rounds).
    """

    bottleneck_type = "APPROVAL_DELAY"

    async def detect(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        repository: Repository | None = None,
        time_window: str = "30d",
    ) -> list[DetectedBottleneck]:
        bottlenecks: list[DetectedBottleneck] = []
        repo_ids = [repository.id] if repository else None

        analytics = await calculate_review_analytics(
            db=db,
            organization_id=organization_id,
            repository_ids=repo_ids,
            time_window=time_window,
        )

        approval_median = analytics.metrics.approval_turnaround.median_hours
        avg_rounds = analytics.metrics.average_review_rounds
        total_reviewed_count = sum(h.count for h in analytics.turnaround_histogram)

        # Check: Delayed approval turnaround (>18h) or excessive review rounds (>= 2.0)
        has_latency_issue = approval_median is not None and approval_median >= 18.0
        has_churn_issue = avg_rounds >= 2.0 and total_reviewed_count >= 3

        if has_latency_issue or has_churn_issue:
            turnaround_val = approval_median if approval_median is not None else 0.0
            severity = determine_approval_delay_severity(turnaround_val, avg_rounds)
            confidence = evaluate_confidence(total_reviewed_count)
            fingerprint = self.compute_fingerprint(
                organization_id, repository.id if repository else None, "approval_turnaround_friction"
            )
            recommendation = get_approval_delay_recommendation(turnaround_val, avg_rounds)

            repo_label = repository.name if repository else "organization-wide"
            title = f"Approval Turnaround Lag ({turnaround_val:.1f}h) & Review Churn in {repo_label}"
            description = (
                f"PR approval turnaround median is {turnaround_val:.1f}h after first review, "
                f"with an average of {avg_rounds:.1f} review rounds before sign-off."
            )

            evidence = {
                "metric": "approval_turnaround_median_hours",
                "observed_value": turnaround_val,
                "p75_turnaround_hours": analytics.metrics.approval_turnaround.p75_hours,
                "average_review_rounds": avg_rounds,
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
                    observed_value=turnaround_val,
                    baseline_value=12.0,
                    repository_id=repository.id if repository else None,
                )
            )

        return bottlenecks
