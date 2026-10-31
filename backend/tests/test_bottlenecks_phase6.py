import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import create_application
from app.models.auth import OrganizationMember, Role, User
from app.models.bottlenecks import Bottleneck
from app.models.github import Repository
from app.schemas.pull_requests import (
    PRAnalyticsResponse,
    PRAnalyticsSummary,
    PRSizeBucket,
    PRSizeDistribution,
)
from app.schemas.reviews import (
    ApprovalTurnaroundMetrics,
    PendingReviewQueueResponse,
    ReviewAnalyticsResponse,
    ReviewerWorkloadItem,
    ReviewSummaryMetrics,
    ReviewWorkloadResponse,
    TTFRMetrics,
    TurnaroundHistogramBucket,
)
from app.services.auth.dependencies import get_current_org_membership, get_current_user
from app.services.bottlenecks.approval_detector import ApprovalDelayDetector
from app.services.bottlenecks.confidence import ConfidenceLevel, evaluate_confidence
from app.services.bottlenecks.engine import BottleneckEngine
from app.services.bottlenecks.pr_size_detector import PRSizeBottleneckDetector
from app.services.bottlenecks.review_detector import ReviewDelayDetector
from app.services.bottlenecks.severity import (
    SeverityLevel,
    determine_approval_delay_severity,
    determine_merge_delay_severity,
    determine_pr_size_severity,
    determine_repository_workflow_severity,
    determine_review_delay_severity,
    determine_workload_severity,
)
from app.services.bottlenecks.workload_detector import ReviewerCapacityDetector

# ==============================================================================
# Severity & Confidence Classification Tests
# ==============================================================================


def test_severity_classification_rules():
    # Review delay
    assert determine_review_delay_severity(8.0) == SeverityLevel.LOW
    assert determine_review_delay_severity(14.0) == SeverityLevel.MEDIUM
    assert determine_review_delay_severity(30.0) == SeverityLevel.HIGH
    assert determine_review_delay_severity(55.0) == SeverityLevel.CRITICAL

    # Approval delay
    assert determine_approval_delay_severity(10.0, 1.2) == SeverityLevel.LOW
    assert determine_approval_delay_severity(20.0, 1.5) == SeverityLevel.MEDIUM
    assert determine_approval_delay_severity(40.0, 2.6) == SeverityLevel.HIGH
    assert determine_approval_delay_severity(80.0, 4.5) == SeverityLevel.CRITICAL

    # Merge delay
    assert determine_merge_delay_severity(6.0) == SeverityLevel.LOW
    assert determine_merge_delay_severity(15.0) == SeverityLevel.MEDIUM
    assert determine_merge_delay_severity(30.0) == SeverityLevel.HIGH
    assert determine_merge_delay_severity(50.0) == SeverityLevel.CRITICAL

    # Reviewer workload
    assert determine_workload_severity(0.25, 30.0) == SeverityLevel.LOW
    assert determine_workload_severity(0.38, 40.0) == SeverityLevel.MEDIUM
    assert determine_workload_severity(0.50, 48.0) == SeverityLevel.HIGH
    assert determine_workload_severity(0.65, 65.0) == SeverityLevel.CRITICAL

    # PR size divergence
    assert determine_pr_size_severity(1.8) == SeverityLevel.LOW
    assert determine_pr_size_severity(2.8) == SeverityLevel.MEDIUM
    assert determine_pr_size_severity(4.5) == SeverityLevel.HIGH

    # Repository workflow
    assert determine_repository_workflow_severity(15.0, 85.0) == SeverityLevel.LOW
    assert determine_repository_workflow_severity(30.0, 70.0) == SeverityLevel.MEDIUM
    assert determine_repository_workflow_severity(55.0, 50.0) == SeverityLevel.HIGH
    assert determine_repository_workflow_severity(100.0, 35.0) == SeverityLevel.CRITICAL


def test_confidence_evaluation_rules():
    # Insufficient data (< 5 items)
    c_low = evaluate_confidence(sample_size=3)
    assert c_low.level == ConfidenceLevel.LOW
    assert not c_low.is_baseline_established
    assert "Small sample size" in c_low.explanation

    # Moderate data (5-14 items)
    c_med = evaluate_confidence(sample_size=10)
    assert c_med.level == ConfidenceLevel.MEDIUM
    assert c_med.is_baseline_established

    # Robust data (>= 15 items)
    c_high = evaluate_confidence(sample_size=25)
    assert c_high.level == ConfidenceLevel.HIGH
    assert c_high.is_baseline_established


# ==============================================================================
# Detector Unit Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_review_delay_detector():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    detector = ReviewDelayDetector()

    # 1. Simulate high TTFR (28.5 hours)
    mock_analytics = ReviewAnalyticsResponse(
        time_window="30d",
        start_date="2026-10-01",
        end_date="2026-10-31",
        metrics=ReviewSummaryMetrics(
            time_to_first_review=TTFRMetrics(
                median_hours=28.5,
                p75_hours=36.0,
                p90_hours=48.0,
                benchmark_comparison="CONGESTED",
            ),
            approval_turnaround=ApprovalTurnaroundMetrics(median_hours=4.0, p75_hours=8.0),
            average_review_rounds=1.2,
            review_coverage_rate=80.0,
        ),
        turnaround_histogram=[
            TurnaroundHistogramBucket(range="< 2h", count=2),
            TurnaroundHistogramBucket(range="> 48h", count=10),
        ],
        pending_queue_count=1,
    )

    mock_queue = PendingReviewQueueResponse(total_pending=1, items=[])

    with (
        patch(
            "app.services.bottlenecks.review_detector.calculate_review_analytics",
            return_value=mock_analytics,
        ),
        patch(
            "app.services.bottlenecks.review_detector.get_pending_review_queue",
            return_value=mock_queue,
        ),
    ):
        results = await detector.detect(mock_db, org_id)
        assert len(results) == 1
        assert results[0].bottleneck_type == "PR_REVIEW_DELAY"
        assert results[0].severity == "HIGH"
        assert results[0].observed_value == 28.5
        assert "Time to First Review" in results[0].title


@pytest.mark.asyncio
async def test_approval_delay_detector():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    detector = ApprovalDelayDetector()

    # High approval turnaround (42.0 hours) and high rounds (2.8)
    mock_analytics = ReviewAnalyticsResponse(
        time_window="30d",
        start_date="2026-10-01",
        end_date="2026-10-31",
        metrics=ReviewSummaryMetrics(
            time_to_first_review=TTFRMetrics(median_hours=4.0, benchmark_comparison="HEALTHY"),
            approval_turnaround=ApprovalTurnaroundMetrics(median_hours=42.0, p75_hours=60.0),
            average_review_rounds=2.8,
            review_coverage_rate=90.0,
        ),
        turnaround_histogram=[TurnaroundHistogramBucket(range="2h - 6h", count=10)],
        pending_queue_count=0,
    )

    with patch(
        "app.services.bottlenecks.approval_detector.calculate_review_analytics",
        return_value=mock_analytics,
    ):
        results = await detector.detect(mock_db, org_id)
        assert len(results) == 1
        assert results[0].bottleneck_type == "APPROVAL_DELAY"
        assert results[0].severity == "HIGH"
        assert results[0].observed_value == 42.0


@pytest.mark.asyncio
async def test_reviewer_capacity_detector():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    detector = ReviewerCapacityDetector()

    # High Gini coefficient (0.52) and dominant single reviewer (58%)
    mock_workload = ReviewWorkloadResponse(
        time_window="30d",
        gini_coefficient=0.52,
        workload_balance_status="UNBALANCED",
        total_reviews=25,
        reviewers=[
            ReviewerWorkloadItem(
                account_id=uuid.uuid4(),
                login="senior-lead",
                reviews_conducted=15,
                approvals_given=12,
                changes_requested=3,
                review_share_percentage=60.0,
            ),
            ReviewerWorkloadItem(
                account_id=uuid.uuid4(),
                login="junior-dev",
                reviews_conducted=10,
                approvals_given=8,
                changes_requested=2,
                review_share_percentage=40.0,
            ),
        ],
    )

    with patch(
        "app.services.bottlenecks.workload_detector.calculate_reviewer_workload",
        return_value=mock_workload,
    ):
        results = await detector.detect(mock_db, org_id)
        assert len(results) == 1
        assert results[0].bottleneck_type == "REVIEWER_CONCENTRATION"
        assert results[0].severity in ("HIGH", "CRITICAL")
        assert results[0].observed_value == 0.52


@pytest.mark.asyncio
async def test_pr_size_bottleneck_detector():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    detector = PRSizeBottleneckDetector()

    # Large PRs take 36h vs Small PRs taking 8h (ratio 4.5x)
    mock_analytics = PRAnalyticsResponse(
        time_window="30d",
        start_date="2026-10-01",
        end_date="2026-10-31",
        summary=PRAnalyticsSummary(
            total_prs_opened=10,
            total_prs_merged=8,
            total_prs_closed_unmerged=1,
            currently_open_prs=1,
            merge_rate_percentage=88.9,
            median_merge_time_hours=14.0,
        ),
        cadence_trend=[],
        size_distribution=PRSizeDistribution(
            small_under_100_lines=PRSizeBucket(count=4, avg_merge_hours=8.0),
            medium_100_to_500_lines=PRSizeBucket(count=3, avg_merge_hours=16.0),
            large_over_500_lines=PRSizeBucket(count=3, avg_merge_hours=36.0),
        ),
    )

    with patch(
        "app.services.bottlenecks.pr_size_detector.calculate_pull_request_analytics",
        return_value=mock_analytics,
    ):
        results = await detector.detect(mock_db, org_id)
        assert len(results) == 1
        assert results[0].bottleneck_type == "PR_SIZE_OVERSIZED"
        assert results[0].severity == "HIGH"
        assert results[0].observed_value == 4.5


# ==============================================================================
# Engine Deduplication & Idempotency Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_bottleneck_engine_deduplication():
    """Verify that recurring runs with the same fingerprint update existing bottlenecks."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    org_id = uuid.uuid4()
    engine = BottleneckEngine()

    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = uuid.uuid4()
    mock_repo.organization_id = org_id
    mock_repo.full_name = "test-org/core-repo"

    # Mock DB query for repositories
    repo_res = MagicMock()
    repo_res.scalars.return_value.all.return_value = [mock_repo]

    # Existing bottleneck mock with same fingerprint
    mock_existing_bottleneck = MagicMock(spec=Bottleneck)
    mock_existing_bottleneck.id = uuid.uuid4()
    mock_existing_bottleneck.severity = "MEDIUM"
    mock_existing_bottleneck.last_observed_at = datetime(2026, 10, 25, 0, 0, 0, tzinfo=UTC)

    existing_res = MagicMock()
    existing_res.scalar_one_or_none.return_value = mock_existing_bottleneck

    mock_db.execute.side_effect = [repo_res, existing_res, existing_res, existing_res]

    # Mock one detector returning a result
    with patch.object(
        engine.detectors[0],
        "detect",
        return_value=[
            MagicMock(
                bottleneck_type="PR_REVIEW_DELAY",
                severity="HIGH",
                confidence="HIGH",
                title="Review Delay",
                description="Delay observed",
                evidence={"metric": "ttfr"},
                recommendation="Improve review cadence",
                fingerprint="fingerprint_12345",
                observed_value=25.0,
                baseline_value=8.0,
                repository_id=mock_repo.id,
            )
        ],
    ), patch.object(engine.detectors[1], "detect", return_value=[]), patch.object(
        engine.detectors[2], "detect", return_value=[]
    ), patch.object(
        engine.detectors[3], "detect", return_value=[]
    ), patch.object(
        engine.detectors[4], "detect", return_value=[]
    ), patch.object(
        engine.detectors[5], "detect", return_value=[]
    ):
        run, detected = await engine.run_detection(mock_db, org_id)

        assert run.status == "COMPLETED"
        assert len(detected) == 1
        # Crucial check: existing bottleneck updated rather than new one created
        assert mock_existing_bottleneck.severity == "HIGH"
        assert mock_existing_bottleneck.title == "Review Delay"


# ==============================================================================
# HTTP API Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_bottlenecks_list_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    b_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = "architect@company.com"

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.id = uuid.uuid4()
    mock_membership.organization_id = org_id
    mock_membership.role = Role.ADMIN

    mock_b = MagicMock(spec=Bottleneck)
    mock_b.id = b_id
    mock_b.organization_id = org_id
    mock_b.repository_id = None
    mock_b.repository = None
    mock_b.bottleneck_type = "PR_REVIEW_DELAY"
    mock_b.severity = "HIGH"
    mock_b.confidence = "HIGH"
    mock_b.title = "High TTFR in Core Service"
    mock_b.description = "Median review wait is 32 hours"
    mock_b.evidence = {"metric": "ttfr", "observed_value": 32.0}
    mock_b.recommendation = "Rotate code owners"
    mock_b.detected_at = datetime(2026, 10, 31, 10, 0, 0, tzinfo=UTC)
    mock_b.first_observed_at = datetime(2026, 10, 31, 10, 0, 0, tzinfo=UTC)
    mock_b.last_observed_at = datetime(2026, 10, 31, 10, 0, 0, tzinfo=UTC)
    mock_b.status = "ACTIVE"
    mock_b.fingerprint = "fp_abc123"
    mock_b.resolved_at = None

    mock_db = AsyncMock()
    count_res = MagicMock()
    count_res.scalar_one.return_value = 1

    items_res = MagicMock()
    items_res.scalars.return_value.all.return_value = [mock_b]

    mock_db.execute.side_effect = [count_res, items_res]

    async def override_membership():
        return mock_membership

    async def override_user():
        return mock_user

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_org_membership] = override_membership
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/bottlenecks?page=1&size=20")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "High TTFR in Core Service"
        assert data["items"][0]["severity"] == "HIGH"
        assert data["items"][0]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_get_bottlenecks_summary_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.organization_id = org_id
    mock_membership.role = Role.ADMIN

    mock_b1 = MagicMock(spec=Bottleneck)
    mock_b1.status = "ACTIVE"
    mock_b1.severity = "CRITICAL"
    mock_b1.bottleneck_type = "PR_REVIEW_DELAY"
    mock_b1.repository_id = uuid.uuid4()

    mock_b2 = MagicMock(spec=Bottleneck)
    mock_b2.status = "ACTIVE"
    mock_b2.severity = "HIGH"
    mock_b2.bottleneck_type = "REVIEWER_CONCENTRATION"
    mock_b2.repository_id = uuid.uuid4()

    mock_db = AsyncMock()
    query_res = MagicMock()
    query_res.scalars.return_value.all.return_value = [mock_b1, mock_b2]
    mock_db.execute.return_value = query_res

    app.dependency_overrides[get_current_org_membership] = lambda: mock_membership
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/bottlenecks/summary")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_active"] == 2
        assert data["critical_count"] == 1
        assert data["high_count"] == 1
        assert data["affected_repositories_count"] == 2
        assert data["by_type"]["PR_REVIEW_DELAY"] == 1


@pytest.mark.asyncio
async def test_update_bottleneck_status_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    b_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.organization_id = org_id
    mock_membership.role = Role.MEMBER

    mock_b = MagicMock(spec=Bottleneck)
    mock_b.id = b_id
    mock_b.organization_id = org_id
    mock_b.repository_id = None
    mock_b.repository = None
    mock_b.bottleneck_type = "PR_REVIEW_DELAY"
    mock_b.severity = "HIGH"
    mock_b.confidence = "HIGH"
    mock_b.title = "High TTFR"
    mock_b.description = "Test desc"
    mock_b.evidence = {}
    mock_b.recommendation = "Test rec"
    mock_b.detected_at = datetime(2026, 10, 31, 10, 0, 0, tzinfo=UTC)
    mock_b.first_observed_at = datetime(2026, 10, 31, 10, 0, 0, tzinfo=UTC)
    mock_b.last_observed_at = datetime(2026, 10, 31, 10, 0, 0, tzinfo=UTC)
    mock_b.status = "ACTIVE"
    mock_b.fingerprint = "fp_123"
    mock_b.resolved_at = None

    mock_db = AsyncMock()
    find_res = MagicMock()
    find_res.scalar_one_or_none.return_value = mock_b
    mock_db.execute.return_value = find_res

    app.dependency_overrides[get_current_org_membership] = lambda: mock_membership
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.patch(
            f"/api/v1/bottlenecks/{b_id}/status",
            json={"status": "RESOLVED"},
        )

        assert resp.status_code == 200
        assert mock_b.status == "RESOLVED"
        assert mock_b.resolved_at is not None
