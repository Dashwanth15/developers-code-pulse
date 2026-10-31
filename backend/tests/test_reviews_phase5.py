import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import create_application
from app.models.auth import OrganizationMember, Role, User
from app.models.commits import GitHubAccount
from app.models.github import Repository
from app.models.pull_requests import PullRequest
from app.models.reviews import PRReview, ReviewRequest
from app.schemas.reviews import (
    ApprovalTurnaroundMetrics,
    PendingReviewItem,
    PendingReviewQueueResponse,
    ReviewAnalyticsResponse,
    ReviewerWorkloadItem,
    ReviewSummaryMetrics,
    ReviewWorkloadResponse,
    TTFRMetrics,
    TurnaroundHistogramBucket,
)
from app.services.analytics.review_metrics import (
    calculate_gini_coefficient,
)
from app.services.auth.dependencies import get_current_org_membership, get_current_user
from app.services.github.review_service import (
    ingest_pull_request_review_payload,
    sync_pull_request_reviews,
)

# ==============================================================================
# Gini Coefficient & Metric Math Tests
# ==============================================================================


def test_calculate_gini_coefficient():
    # Empty list
    assert calculate_gini_coefficient([]) == 0.0

    # Single value
    assert calculate_gini_coefficient([42]) == 0.0

    # All zeros
    assert calculate_gini_coefficient([0, 0, 0, 0]) == 0.0

    # Perfectly equal distribution -> 0.0
    assert calculate_gini_coefficient([10, 10, 10, 10]) == 0.0

    # Moderate concentration: [10, 20, 30]
    # diffs: |10-20|=10, |10-30|=20, |20-10|=10, |20-30|=10, |30-10|=20, |30-20|=10 -> sum = 80
    # denominator: 2 * 3 * 60 = 360 -> 80 / 360 = 0.222
    assert calculate_gini_coefficient([10, 20, 30]) == 0.222

    # High concentration: [100, 0, 0, 0]
    # diffs: (100 - 0) * 6 = 600
    # denominator: 2 * 4 * 100 = 800 -> 600 / 800 = 0.75
    assert calculate_gini_coefficient([100, 0, 0, 0]) == 0.75


# ==============================================================================
# Review Ingestion & TTFR Calculation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_ingest_pull_request_review_self_review_ignored():
    """Verify that author self-reviews do NOT advance TTFR metrics."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    author_acc_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_repo = MagicMock(spec=Repository)
    mock_repo.organization_id = org_id
    mock_repo.full_name = "test-org/repo"

    created_at = datetime(2026, 10, 30, 10, 0, 0, tzinfo=UTC)
    mock_pr = MagicMock(spec=PullRequest)
    mock_pr.id = uuid.uuid4()
    mock_pr.number = 42
    mock_pr.author_account_id = author_acc_id
    mock_pr.created_at_github = created_at
    mock_pr.first_reviewed_at = None
    mock_pr.first_review_time_seconds = None

    # Reviewer account is the SAME as the author
    mock_author_acc = MagicMock(spec=GitHubAccount)
    mock_author_acc.id = author_acc_id
    mock_author_acc.user_type = "User"

    # Query returns no existing review
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    payload = {
        "id": 9991,
        "state": "APPROVED",
        "submitted_at": "2026-10-30T12:00:00Z",
        "commit_id": "abcdef123456",
        "user": {"id": 111, "login": "pr-author", "avatar_url": "https://avatar"},
    }

    with patch(
        "app.services.github.review_service.resolve_or_create_github_account",
        return_value=mock_author_acc,
    ):
        review = await ingest_pull_request_review_payload(
            db=mock_db,
            repository=mock_repo,
            pull_request=mock_pr,
            review_data=payload,
        )

        assert review.state == "APPROVED"
        assert review.github_review_id == 9991
        # Crucial check: TTFR was NOT updated for self-review
        assert mock_pr.first_reviewed_at is None
        assert mock_pr.first_review_time_seconds is None


@pytest.mark.asyncio
async def test_ingest_pull_request_review_peer_review_sets_ttfr():
    """Verify that peer reviews properly set TTFR and fulfill pending ReviewRequest."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    author_acc_id = uuid.uuid4()
    peer_acc_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_repo = MagicMock(spec=Repository)
    mock_repo.organization_id = org_id
    mock_repo.full_name = "test-org/repo"

    created_at = datetime(2026, 10, 30, 10, 0, 0, tzinfo=UTC)
    mock_pr = MagicMock(spec=PullRequest)
    mock_pr.id = uuid.uuid4()
    mock_pr.number = 43
    mock_pr.author_account_id = author_acc_id
    mock_pr.created_at_github = created_at
    mock_pr.first_reviewed_at = None
    mock_pr.first_review_time_seconds = None

    mock_peer_acc = MagicMock(spec=GitHubAccount)
    mock_peer_acc.id = peer_acc_id
    mock_peer_acc.user_type = "User"

    # Pending review request mock
    mock_req = MagicMock(spec=ReviewRequest)
    mock_req.status = "PENDING"
    mock_req.fulfilled_at = None

    def execute_side_effect(statement, *_args, **_kwargs):
        res = MagicMock()
        if "FROM pr_reviews" in str(statement):
            res.scalar_one_or_none.return_value = None
        else:
            res.scalar_one_or_none.return_value = mock_req
        return res

    mock_db.execute.side_effect = execute_side_effect

    payload = {
        "id": 9992,
        "state": "APPROVED",
        "submitted_at": "2026-10-30T14:30:00Z",
        "commit_id": "11223344",
        "user": {"id": 222, "login": "peer-reviewer", "avatar_url": "https://avatar2"},
    }

    with patch(
        "app.services.github.review_service.resolve_or_create_github_account",
        return_value=mock_peer_acc,
    ):
        review = await ingest_pull_request_review_payload(
            db=mock_db,
            repository=mock_repo,
            pull_request=mock_pr,
            review_data=payload,
        )

        assert review.state == "APPROVED"
        assert mock_pr.first_reviewed_at == datetime(2026, 10, 30, 14, 30, 0, tzinfo=UTC)
        # 4.5 hours = 16200 seconds
        assert mock_pr.first_review_time_seconds == 16200
        # Check review request fulfillment
        assert mock_req.status == "COMPLETED"
        assert mock_req.fulfilled_at == datetime(2026, 10, 30, 14, 30, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_sync_pull_request_reviews():
    mock_db = AsyncMock()
    mock_repo = MagicMock(spec=Repository)
    mock_repo.full_name = "test-org/repo"
    mock_repo.organization_id = uuid.uuid4()

    mock_pr = MagicMock(spec=PullRequest)
    mock_pr.id = uuid.uuid4()
    mock_pr.number = 77
    mock_pr.author_account_id = uuid.uuid4()
    mock_pr.created_at_github = datetime(2026, 10, 30, 10, 0, 0, tzinfo=UTC)
    mock_pr.first_reviewed_at = None

    api_reviews = [
        {"id": 1, "state": "COMMENTED", "submitted_at": "2026-10-30T11:00:00Z"},
        {"id": 2, "state": "APPROVED", "submitted_at": "2026-10-30T12:00:00Z"},
    ]

    with (
        patch(
            "app.services.github.review_service.GitHubClient.get_pull_request_reviews",
            return_value=api_reviews,
        ),
        patch(
            "app.services.github.review_service.ingest_pull_request_review_payload",
            return_value=MagicMock(),
        ) as mock_ingest,
    ):
        synced = await sync_pull_request_reviews(mock_db, mock_repo, mock_pr)
        assert synced == 2
        assert mock_ingest.call_count == 2


# ==============================================================================
# API Endpoint Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_review_analytics_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = "lead@company.com"

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.id = uuid.uuid4()
    mock_membership.organization_id = org_id
    mock_membership.role = Role.ADMIN

    mock_analytics = ReviewAnalyticsResponse(
        time_window="30d",
        start_date="2026-10-01",
        end_date="2026-10-31",
        metrics=ReviewSummaryMetrics(
            time_to_first_review=TTFRMetrics(
                median_hours=4.5,
                p75_hours=8.2,
                p90_hours=14.0,
                benchmark_comparison="HEALTHY",
            ),
            approval_turnaround=ApprovalTurnaroundMetrics(
                median_hours=3.1,
                p75_hours=6.5,
            ),
            average_review_rounds=1.4,
            review_coverage_rate=88.5,
        ),
        turnaround_histogram=[
            TurnaroundHistogramBucket(range="< 2h", count=12),
            TurnaroundHistogramBucket(range="2h - 6h", count=25),
            TurnaroundHistogramBucket(range="6h - 24h", count=8),
            TurnaroundHistogramBucket(range="24h - 48h", count=2),
            TurnaroundHistogramBucket(range="> 48h", count=1),
        ],
        pending_queue_count=3,
    )

    async def override_membership():
        return mock_membership

    async def override_user():
        return mock_user

    async def override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_org_membership] = override_membership
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with patch(
            "app.api.v1.endpoints.analytics.calculate_review_analytics",
            new=AsyncMock(return_value=mock_analytics),
        ):
            resp = await client.get("/api/v1/analytics/reviews?time_window=30d")

            assert resp.status_code == 200
            data = resp.json()
            assert data["time_window"] == "30d"
            assert data["metrics"]["time_to_first_review"]["benchmark_comparison"] == "HEALTHY"
            assert data["metrics"]["time_to_first_review"]["median_hours"] == 4.5
            assert data["metrics"]["review_coverage_rate"] == 88.5
            assert len(data["turnaround_histogram"]) == 5
            assert data["pending_queue_count"] == 3


@pytest.mark.asyncio
async def test_get_reviewer_workload_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = "lead@company.com"

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.id = uuid.uuid4()
    mock_membership.organization_id = org_id
    mock_membership.role = Role.ADMIN

    mock_workload = ReviewWorkloadResponse(
        time_window="30d",
        gini_coefficient=0.28,
        workload_balance_status="BALANCED",
        total_reviews=45,
        reviewers=[
            ReviewerWorkloadItem(
                account_id=uuid.uuid4(),
                login="alice",
                name="Alice Dev",
                reviews_conducted=20,
                approvals_given=16,
                changes_requested=4,
                review_share_percentage=44.4,
            ),
            ReviewerWorkloadItem(
                account_id=uuid.uuid4(),
                login="bob",
                name="Bob Dev",
                reviews_conducted=15,
                approvals_given=12,
                changes_requested=3,
                review_share_percentage=33.3,
            ),
            ReviewerWorkloadItem(
                account_id=uuid.uuid4(),
                login="charlie",
                name="Charlie Dev",
                reviews_conducted=10,
                approvals_given=8,
                changes_requested=2,
                review_share_percentage=22.2,
            ),
        ],
    )

    async def override_membership():
        return mock_membership

    async def override_user():
        return mock_user

    async def override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_org_membership] = override_membership
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with patch(
            "app.api.v1.endpoints.analytics.calculate_reviewer_workload",
            new=AsyncMock(return_value=mock_workload),
        ):
            resp = await client.get("/api/v1/analytics/reviews/workload?time_window=30d")

            assert resp.status_code == 200
            data = resp.json()
            assert data["gini_coefficient"] == 0.28
            assert data["workload_balance_status"] == "BALANCED"
            assert data["total_reviews"] == 45
            assert len(data["reviewers"]) == 3
            assert data["reviewers"][0]["login"] == "alice"


@pytest.mark.asyncio
async def test_get_pending_reviews_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = "lead@company.com"

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.id = uuid.uuid4()
    mock_membership.organization_id = org_id
    mock_membership.role = Role.ADMIN

    mock_pending = PendingReviewQueueResponse(
        total_pending=2,
        items=[
            PendingReviewItem(
                pull_request_id=uuid.uuid4(),
                number=101,
                title="feat: add telemetry engine",
                repository_name="core-service",
                author_login="david",
                waiting_hours=28.5,
                created_at=datetime(2026, 10, 30, 8, 0, 0, tzinfo=UTC),
                requested_reviewers=["alice", "bob"],
            ),
            PendingReviewItem(
                pull_request_id=uuid.uuid4(),
                number=102,
                title="fix: resolve cache eviction latency",
                repository_name="cache-proxy",
                author_login="emma",
                waiting_hours=14.2,
                created_at=datetime(2026, 10, 30, 22, 0, 0, tzinfo=UTC),
                requested_reviewers=["charlie"],
            ),
        ],
    )

    async def override_membership():
        return mock_membership

    async def override_user():
        return mock_user

    async def override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_org_membership] = override_membership
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with patch(
            "app.api.v1.endpoints.analytics.get_pending_review_queue",
            new=AsyncMock(return_value=mock_pending),
        ):
            resp = await client.get("/api/v1/analytics/reviews/pending")

            assert resp.status_code == 200
            data = resp.json()
            assert data["total_pending"] == 2
            assert data["items"][0]["number"] == 101
            assert data["items"][0]["waiting_hours"] == 28.5
            assert "alice" in data["items"][0]["requested_reviewers"]


@pytest.mark.asyncio
async def test_get_pull_request_reviews_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    pr_id = uuid.uuid4()
    review_id = uuid.uuid4()
    reviewer_acc_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = "lead@company.com"

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.id = uuid.uuid4()
    mock_membership.organization_id = org_id
    mock_membership.role = Role.ADMIN

    # Mock PR query response
    mock_pr = MagicMock(spec=PullRequest)
    mock_pr.id = pr_id

    # Mock Review query response
    mock_reviewer = MagicMock(spec=GitHubAccount)
    mock_reviewer.login = "alice"
    mock_reviewer.avatar_url = "https://avatar"

    mock_review = MagicMock(spec=PRReview)
    mock_review.id = review_id
    mock_review.pull_request_id = pr_id
    mock_review.reviewer_account_id = reviewer_acc_id
    mock_review.reviewer = mock_reviewer
    mock_review.state = "APPROVED"
    mock_review.submitted_at = datetime(2026, 10, 31, 14, 0, 0, tzinfo=UTC)
    mock_review.commit_sha = "abcd123"

    pr_res = MagicMock()
    pr_res.scalar_one_or_none.return_value = mock_pr

    reviews_res = MagicMock()
    reviews_res.scalars.return_value.all.return_value = [mock_review]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[pr_res, reviews_res])

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
        resp = await client.get(f"/api/v1/pull-requests/{pr_id}/reviews")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == str(review_id)
        assert data[0]["reviewer_login"] == "alice"
        assert data[0]["state"] == "APPROVED"
        assert data[0]["commit_sha"] == "abcd123"
