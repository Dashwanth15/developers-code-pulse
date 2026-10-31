import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github import Repository
from app.services.analytics.review_metrics import calculate_reviewer_workload
from app.services.bottlenecks.confidence import evaluate_confidence
from app.services.bottlenecks.detector_base import BaseBottleneckDetector, DetectedBottleneck
from app.services.bottlenecks.recommendations import get_reviewer_workload_recommendation
from app.services.bottlenecks.severity import determine_workload_severity


class ReviewerCapacityDetector(BaseBottleneckDetector):
    """
    Detects team reviewer capacity and load dispersion bottlenecks:
    - High Gini concentration index (> 0.35) measuring review load inequality.
    - Single point of failure where a single engineer handles >= 45% of reviews.
    - Operates strictly on aggregate team distribution without individual rankings.
    """

    bottleneck_type = "REVIEWER_CONCENTRATION"

    async def detect(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        repository: Repository | None = None,
        time_window: str = "30d",
    ) -> list[DetectedBottleneck]:
        bottlenecks: list[DetectedBottleneck] = []
        repo_ids = [repository.id] if repository else None

        workload = await calculate_reviewer_workload(
            db=db,
            organization_id=organization_id,
            repository_ids=repo_ids,
            time_window=time_window,
        )

        if workload.total_reviews < 5 or not workload.reviewers:
            return bottlenecks

        gini = workload.gini_coefficient
        top_reviewer = workload.reviewers[0]
        max_share = top_reviewer.review_share_percentage

        # Trigger if Gini > 0.35 or top reviewer share >= 45%
        if gini > 0.35 or max_share >= 45.0:
            severity = determine_workload_severity(gini, max_share)
            confidence = evaluate_confidence(workload.total_reviews)
            fingerprint = self.compute_fingerprint(
                organization_id, repository.id if repository else None, "workload_concentration_gini"
            )
            recommendation = get_reviewer_workload_recommendation(gini, max_share)

            repo_label = repository.name if repository else "team-wide"
            title = f"High Reviewer Load Concentration (Gini: {gini:.3f}) in {repo_label}"
            description = (
                f"Team review workload shows high statistical concentration (Gini coefficient: {gini:.3f}, "
                f"status: {workload.workload_balance_status}). The primary reviewer handles {max_share:.1f}% "
                f"of all peer reviews across {workload.total_reviews} total submissions."
            )

            evidence = {
                "metric": "reviewer_gini_coefficient",
                "observed_value": gini,
                "max_reviewer_share_percentage": max_share,
                "total_reviews": workload.total_reviews,
                "active_reviewers_count": len(workload.reviewers),
                "workload_balance_status": workload.workload_balance_status,
                "distribution_shares": [
                    {"login": r.login, "share_pct": r.review_share_percentage, "count": r.reviews_conducted}
                    for r in workload.reviewers
                ],
                "sample_size": workload.total_reviews,
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
                    observed_value=gini,
                    baseline_value=0.30,
                    repository_id=repository.id if repository else None,
                )
            )

        return bottlenecks
