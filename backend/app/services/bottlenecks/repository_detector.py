import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github import Repository
from app.services.analytics.pull_request_metrics import calculate_pull_request_analytics
from app.services.bottlenecks.confidence import evaluate_confidence
from app.services.bottlenecks.detector_base import BaseBottleneckDetector, DetectedBottleneck
from app.services.bottlenecks.recommendations import get_repository_backlog_recommendation
from app.services.bottlenecks.severity import determine_repository_workflow_severity


class RepositoryWorkflowDetector(BaseBottleneckDetector):
    """
    Detects macro repository delivery bottlenecks:
    - Persistently high PR cycle time (creation to merge > 48h).
    - Sub-optimal merge completion rate (<60%).
    - Disproportionate accumulation of open unmerged PR backlog.
    """

    bottleneck_type = "REPOSITORY_BACKLOG"

    async def detect(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        repository: Repository | None = None,
        time_window: str = "30d",
    ) -> list[DetectedBottleneck]:
        bottlenecks: list[DetectedBottleneck] = []
        repo_ids = [repository.id] if repository else None

        analytics = await calculate_pull_request_analytics(
            db=db,
            organization_id=organization_id,
            repository_ids=repo_ids,
            time_window=time_window,
        )

        summary = analytics.summary
        total_sample = summary.total_prs_opened + summary.total_prs_merged + summary.total_prs_closed_unmerged

        if total_sample < 3:
            return bottlenecks

        cycle_time = summary.median_cycle_time_hours or summary.median_merge_time_hours or 0.0
        merge_rate = summary.merge_rate_percentage
        open_prs = summary.currently_open_prs

        # Flag condition: High cycle time (>48h) OR (low merge rate < 60% and open PRs >= 3)
        has_cycle_friction = cycle_time >= 48.0
        has_backlog_friction = merge_rate < 60.0 and open_prs >= 3

        if has_cycle_friction or has_backlog_friction:
            severity = determine_repository_workflow_severity(cycle_time, merge_rate)
            confidence = evaluate_confidence(total_sample)
            fingerprint = self.compute_fingerprint(
                organization_id, repository.id if repository else None, "macro_pipeline_backlog"
            )
            recommendation = get_repository_backlog_recommendation(cycle_time, open_prs, merge_rate)

            repo_label = repository.name if repository else "all monitored repositories"
            title = f"High PR Cycle Time ({cycle_time:.1f}h) & Backlog Congestion in {repo_label}"
            description = (
                f"Repository workflow exhibits high delivery friction with a median cycle time of "
                f"{cycle_time:.1f} hours, a merge completion rate of {merge_rate:.1f}%, and "
                f"{open_prs} concurrently open pull requests."
            )

            evidence = {
                "metric": "repository_median_cycle_time_hours",
                "observed_value": cycle_time,
                "merge_rate_percentage": merge_rate,
                "currently_open_prs": open_prs,
                "total_prs_opened": summary.total_prs_opened,
                "total_prs_merged": summary.total_prs_merged,
                "total_prs_closed_unmerged": summary.total_prs_closed_unmerged,
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
                    observed_value=cycle_time,
                    baseline_value=24.0,
                    repository_id=repository.id if repository else None,
                )
            )

        return bottlenecks
