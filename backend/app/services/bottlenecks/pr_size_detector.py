import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github import Repository
from app.services.analytics.pull_request_metrics import calculate_pull_request_analytics
from app.services.bottlenecks.confidence import evaluate_confidence
from app.services.bottlenecks.detector_base import BaseBottleneckDetector, DetectedBottleneck
from app.services.bottlenecks.recommendations import get_pr_size_recommendation
from app.services.bottlenecks.severity import determine_pr_size_severity


class PRSizeBottleneckDetector(BaseBottleneckDetector):
    """
    Detects flow impedance caused by oversized pull requests:
    - Analyzes latency divergence between Small (<100 lines) and Large (>500 lines) PRs.
    - Flags when large pull requests take >= 2.5x longer to merge than small PRs.
    """

    bottleneck_type = "PR_SIZE_OVERSIZED"

    async def detect(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        repository: Repository | None = None,
        time_window: str = "30d",
    ) -> list[DetectedBottleneck]:
        bottlenecks: list[DetectedBottleneck] = []
        repo_ids = [repository.id] if repository else None

        pr_analytics = await calculate_pull_request_analytics(
            db=db,
            organization_id=organization_id,
            repository_ids=repo_ids,
            time_window=time_window,
        )

        size_dist = pr_analytics.size_distribution
        small = size_dist.small_under_100_lines
        large = size_dist.large_over_500_lines

        # Need sufficient sample size of both small and large PRs
        if small.count >= 2 and large.count >= 2:
            small_hours = small.avg_merge_hours or 0.0
            large_hours = large.avg_merge_hours or 0.0

            if small_hours > 0 and large_hours > 0:
                ratio = large_hours / small_hours
                if ratio >= 2.5:
                    severity = determine_pr_size_severity(ratio)
                    total_sample = small.count + large.count
                    confidence = evaluate_confidence(total_sample)
                    fingerprint = self.compute_fingerprint(
                        organization_id, repository.id if repository else None, "pr_size_latency_divergence"
                    )
                    recommendation = get_pr_size_recommendation(large_hours, small_hours, ratio)

                    repo_label = repository.name if repository else "organization-wide"
                    title = f"Oversized PR Merge Penalty ({ratio:.1f}x Latency) in {repo_label}"
                    description = (
                        f"Large pull requests (>500 lines) average {large_hours:.1f}h to merge, "
                        f"which is {ratio:.1f}x longer than small PRs (<100 lines at {small_hours:.1f}h). "
                        "Note: Correlation indicates review cognitive friction rather than developer speed."
                    )

                    evidence = {
                        "metric": "pr_size_merge_latency_ratio",
                        "observed_value": round(ratio, 2),
                        "small_prs_count": small.count,
                        "small_prs_avg_merge_hours": small_hours,
                        "large_prs_count": large.count,
                        "large_prs_avg_merge_hours": large_hours,
                        "medium_prs_count": size_dist.medium_100_to_500_lines.count,
                        "medium_prs_avg_merge_hours": size_dist.medium_100_to_500_lines.avg_merge_hours,
                        "sample_size": total_sample,
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
                            observed_value=round(ratio, 2),
                            baseline_value=1.5,
                            repository_id=repository.id if repository else None,
                        )
                    )

        return bottlenecks
