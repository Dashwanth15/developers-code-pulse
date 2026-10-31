import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bottlenecks import Bottleneck, BottleneckHistory, DetectionRun
from app.models.github import Repository
from app.services.bottlenecks.approval_detector import ApprovalDelayDetector
from app.services.bottlenecks.detector_base import BaseBottleneckDetector, DetectedBottleneck
from app.services.bottlenecks.merge_detector import MergeDelayDetector
from app.services.bottlenecks.pr_size_detector import PRSizeBottleneckDetector
from app.services.bottlenecks.repository_detector import RepositoryWorkflowDetector
from app.services.bottlenecks.review_detector import ReviewDelayDetector
from app.services.bottlenecks.workload_detector import ReviewerCapacityDetector

logger = structlog.get_logger(__name__)


class BottleneckEngine:
    """
    Central orchestration engine for engineering bottleneck detection.
    Coordinates specialized detectors, enforces tenant isolation, handles
    fingerprint deduplication, historical tracking, and idempotent persistence.
    """

    def __init__(self) -> None:
        self.detectors: list[BaseBottleneckDetector] = [
            ReviewDelayDetector(),
            ApprovalDelayDetector(),
            MergeDelayDetector(),
            ReviewerCapacityDetector(),
            PRSizeBottleneckDetector(),
            RepositoryWorkflowDetector(),
        ]

    async def run_detection(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        repository_id: uuid.UUID | None = None,
        time_window: str = "30d",
    ) -> tuple[DetectionRun, list[Bottleneck]]:
        """
        Executes end-to-end bottleneck detection for an organization or specific repository.
        Idempotent: updates existing active bottlenecks and persists historical data points.
        """
        now = datetime.now(UTC)
        days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
        window_days = days_map.get(time_window, 30)
        window_start = now - timedelta(days=window_days)

        # 1. Initialize DetectionRun record
        run = DetectionRun(
            organization_id=organization_id,
            repository_id=repository_id,
            status="RUNNING",
            started_at=now,
        )
        db.add(run)
        await db.flush()

        try:
            # 2. Resolve target repositories
            repo_query = select(Repository).where(Repository.organization_id == organization_id)
            if repository_id:
                repo_query = repo_query.where(Repository.id == repository_id)

            repo_res = await db.execute(repo_query)
            target_repositories = list(repo_res.scalars().all())

            raw_detected: list[DetectedBottleneck] = []

            # 3. Run detectors at organization-wide scope
            if not repository_id:
                for detector in self.detectors:
                    try:
                        results = await detector.detect(
                            db=db,
                            organization_id=organization_id,
                            repository=None,
                            time_window=time_window,
                        )
                        raw_detected.extend(results)
                    except Exception as exc:
                        logger.error(
                            "detector_execution_failed",
                            detector=detector.__class__.__name__,
                            org_id=str(organization_id),
                            error=str(exc),
                        )

            # 4. Run detectors for each repository individually
            for repo in target_repositories:
                for detector in self.detectors:
                    try:
                        results = await detector.detect(
                            db=db,
                            organization_id=organization_id,
                            repository=repo,
                            time_window=time_window,
                        )
                        raw_detected.extend(results)
                    except Exception as exc:
                        logger.error(
                            "repo_detector_failed",
                            detector=detector.__class__.__name__,
                            repo=repo.full_name,
                            error=str(exc),
                        )

            # 5. Deduplicate and persist bottlenecks
            persisted_bottlenecks: list[Bottleneck] = []
            unique_detected: dict[str, DetectedBottleneck] = {}
            for item in raw_detected:
                unique_detected[item.fingerprint] = item

            for item in unique_detected.values():
                # Query existing active/acknowledged bottleneck by (organization_id, fingerprint)
                existing_q = (
                    select(Bottleneck)
                    .options(selectinload(Bottleneck.history))
                    .where(
                        Bottleneck.organization_id == organization_id,
                        Bottleneck.fingerprint == item.fingerprint,
                        Bottleneck.status.in_(["ACTIVE", "ACKNOWLEDGED"]),
                    )
                )
                existing_res = await db.execute(existing_q)
                bottleneck = existing_res.scalar_one_or_none()

                if bottleneck:
                    # Update existing record
                    bottleneck.severity = item.severity
                    bottleneck.confidence = item.confidence
                    bottleneck.title = item.title
                    bottleneck.description = item.description
                    bottleneck.evidence = item.evidence
                    bottleneck.recommendation = item.recommendation
                    bottleneck.last_observed_at = now
                else:
                    # Create new bottleneck
                    bottleneck = Bottleneck(
                        organization_id=organization_id,
                        repository_id=item.repository_id,
                        bottleneck_type=item.bottleneck_type,
                        severity=item.severity,
                        confidence=item.confidence,
                        title=item.title,
                        description=item.description,
                        evidence=item.evidence,
                        recommendation=item.recommendation,
                        detected_at=now,
                        first_observed_at=now,
                        last_observed_at=now,
                        status="ACTIVE",
                        fingerprint=item.fingerprint,
                    )
                    db.add(bottleneck)
                    await db.flush()

                # Record historical time-series observation
                history_entry = BottleneckHistory(
                    bottleneck_id=bottleneck.id,
                    observed_value=item.observed_value,
                    baseline_value=item.baseline_value,
                    observation_window_start=window_start,
                    observation_window_end=now,
                    recorded_at=now,
                )
                db.add(history_entry)
                persisted_bottlenecks.append(bottleneck)

            # 6. Finalize DetectionRun status
            run.status = "COMPLETED"
            run.completed_at = datetime.now(UTC)
            run.total_bottlenecks = len(persisted_bottlenecks)
            await db.commit()

            logger.info(
                "bottleneck_detection_completed",
                org_id=str(organization_id),
                total_detected=len(persisted_bottlenecks),
                run_id=str(run.id),
            )
            return run, persisted_bottlenecks

        except Exception as exc:
            await db.rollback()
            run.status = "FAILED"
            run.completed_at = datetime.now(UTC)
            run.error_message = str(exc)
            db.add(run)
            await db.commit()
            logger.error(
                "bottleneck_detection_run_failed",
                org_id=str(organization_id),
                error=str(exc),
            )
            raise
