import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import create_application
from app.models.auth import OrganizationMember, Role, User
from app.models.github import Repository
from app.models.pull_requests import PullRequest
from app.schemas.pull_requests import (
    PRAnalyticsResponse,
    PRAnalyticsSummary,
)
from app.services.analytics.pull_request_metrics import (
    calculate_percentile,
    calculate_pull_request_analytics,
)
from app.services.auth.dependencies import get_current_org_membership, get_current_user
from app.services.github.pull_request_service import (
    ingest_pull_request_payload,
    parse_github_datetime,
    sync_repository_pull_requests,
)

# ==============================================================================
# Helper & Math Metric Tests
# ==============================================================================


def test_calculate_percentile():
    # Empty list
    assert calculate_percentile([], 50.0) is None

    # Single value
    assert calculate_percentile([42.0], 50.0) == 42.0
    assert calculate_percentile([42.0], 90.0) == 42.0

    # Sorted list: [10.0, 20.0, 30.0, 40.0, 50.0]
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert calculate_percentile(vals, 50.0) == 30.0
    assert calculate_percentile(vals, 0.0) == 10.0
    assert calculate_percentile(vals, 100.0) == 50.0
    assert calculate_percentile(vals, 75.0) == 40.0


def test_parse_github_datetime():
    dt = parse_github_datetime("2026-10-31T17:00:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 10
    assert dt.day == 31
    assert dt.hour == 17

    assert parse_github_datetime(None) is None
    assert parse_github_datetime("invalid-date-string") is None


# ==============================================================================
# Pull Request Ingestion Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_ingest_pull_request_payload_creates_new_pr():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = repo_id
    mock_repo.name = "test-repo"
    mock_repo.organization_id = org_id
    mock_repo.default_branch = "main"

    # Mock DB queries returning no existing PR
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    payload = {
        "id": 12345678,
        "number": 42,
        "title": "feat: add user authentication",
        "state": "open",
        "draft": False,
        "created_at": "2026-10-25T10:00:00Z",
        "updated_at": "2026-10-25T11:00:00Z",
        "head": {"ref": "feature/auth"},
        "base": {"ref": "main"},
        "additions": 150,
        "deletions": 25,
        "changed_files": 5,
        "commits": 3,
        "user": {
            "login": "octocat",
            "id": 583231,
            "avatar_url": "https://avatars.githubusercontent.com/u/583231",
        },
    }

    with patch(
        "app.services.github.pull_request_service.resolve_or_create_github_account",
        new=AsyncMock(return_value=MagicMock(id=uuid.uuid4())),
    ):
        pr = await ingest_pull_request_payload(mock_db, mock_repo, payload)

    assert pr.github_pr_id == 12345678
    assert pr.number == 42
    assert pr.title == "feat: add user authentication"
    assert pr.state == "OPEN"
    assert pr.is_draft is False
    assert pr.source_branch == "feature/auth"
    assert pr.target_branch == "main"
    assert pr.additions == 150
    assert pr.deletions == 25
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_ingest_pull_request_payload_updates_to_merged():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = repo_id
    mock_repo.name = "test-repo"
    mock_repo.organization_id = org_id
    mock_repo.default_branch = "main"

    existing_pr = MagicMock(spec=PullRequest)
    existing_pr.id = uuid.uuid4()
    existing_pr.github_pr_id = 12345678
    existing_pr.number = 42
    existing_pr.state = "OPEN"
    existing_pr.created_at_github = datetime(2026, 10, 25, 10, 0, tzinfo=UTC)

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_pr
    mock_db.execute.return_value = mock_res

    payload = {
        "id": 12345678,
        "number": 42,
        "title": "feat: add user authentication",
        "state": "closed",
        "draft": False,
        "created_at": "2026-10-25T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
        "merged_at": "2026-10-26T10:00:00Z",
        "closed_at": "2026-10-26T10:00:00Z",
        "head": {"ref": "feature/auth"},
        "base": {"ref": "main"},
        "additions": 150,
        "deletions": 25,
        "changed_files": 5,
        "commits": 3,
        "user": {"login": "octocat"},
    }

    with patch(
        "app.services.github.pull_request_service.resolve_or_create_github_account",
        new=AsyncMock(return_value=MagicMock(id=uuid.uuid4())),
    ):
        updated_pr = await ingest_pull_request_payload(mock_db, mock_repo, payload)

    assert updated_pr.state == "MERGED"
    assert updated_pr.merged_at is not None
    assert updated_pr.merge_time_seconds == 86400  # 24 hours
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_sync_repository_pull_requests():
    mock_db = AsyncMock()
    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = uuid.uuid4()
    mock_repo.name = "test-repo"
    mock_repo.full_name = "org/test-repo"

    raw_prs = [
        {"id": 101, "number": 1, "title": "PR 1", "state": "open"},
        {"id": 102, "number": 2, "title": "PR 2", "state": "closed"},
    ]

    with patch(
        "app.services.github.pull_request_service.GitHubClient.get_repository_pull_requests",
        new=AsyncMock(return_value=raw_prs),
    ), patch(
        "app.services.github.pull_request_service.ingest_pull_request_payload",
        new=AsyncMock(),
    ) as mock_ingest:
        count = await sync_repository_pull_requests(mock_db, mock_repo, max_prs=10)
        assert count == 2
        assert mock_ingest.call_count == 2


# ==============================================================================
# Analytics Engine Mathematical Verification
# ==============================================================================


@pytest.mark.asyncio
async def test_calculate_pull_request_analytics_metrics():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    now = datetime.now(UTC)

    # Synthetic PR dataset
    # PR 1: Opened 20 days ago, merged 18 days ago (merge duration: 48 hours = 172800s, 50 lines -> small)
    pr1 = MagicMock(spec=PullRequest)
    pr1.created_at_github = now - timedelta(days=20)
    pr1.merged_at = now - timedelta(days=18)
    pr1.closed_at = now - timedelta(days=18)
    pr1.state = "MERGED"
    pr1.merge_time_seconds = 172800
    pr1.cycle_time_seconds = 172800
    pr1.additions = 30
    pr1.deletions = 20

    # PR 2: Opened 15 days ago, merged 14 days ago (merge duration: 24 hours = 86400s, 250 lines -> medium)
    pr2 = MagicMock(spec=PullRequest)
    pr2.created_at_github = now - timedelta(days=15)
    pr2.merged_at = now - timedelta(days=14)
    pr2.closed_at = now - timedelta(days=14)
    pr2.state = "MERGED"
    pr2.merge_time_seconds = 86400
    pr2.cycle_time_seconds = 86400
    pr2.additions = 200
    pr2.deletions = 50

    # PR 3: Opened 10 days ago, closed without merging 9 days ago (15 lines -> small)
    pr3 = MagicMock(spec=PullRequest)
    pr3.created_at_github = now - timedelta(days=10)
    pr3.merged_at = None
    pr3.closed_at = now - timedelta(days=9)
    pr3.state = "CLOSED"
    pr3.merge_time_seconds = None
    pr3.cycle_time_seconds = None
    pr3.additions = 10
    pr3.deletions = 5

    # PR 4: Currently open, opened 5 days ago (800 lines -> large)
    pr4 = MagicMock(spec=PullRequest)
    pr4.created_at_github = now - timedelta(days=5)
    pr4.merged_at = None
    pr4.closed_at = None
    pr4.state = "OPEN"
    pr4.merge_time_seconds = None
    pr4.cycle_time_seconds = None
    pr4.additions = 500
    pr4.deletions = 300

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [pr1, pr2, pr3, pr4]
    mock_db.execute.return_value = mock_res

    res = await calculate_pull_request_analytics(
        db=mock_db,
        organization_id=org_id,
        time_window="30d",
    )

    assert isinstance(res, PRAnalyticsResponse)
    assert res.summary.total_prs_opened == 4
    assert res.summary.total_prs_merged == 2
    assert res.summary.total_prs_closed_unmerged == 1
    assert res.summary.currently_open_prs == 1

    # Merge rate: 2 / (2 + 1) = 66.7%
    assert res.summary.merge_rate_percentage == 66.7

    # Median merge time: median of [24.0, 48.0] = 36.0h
    assert res.summary.median_merge_time_hours == 36.0

    # Size distribution counts
    assert res.size_distribution.small_under_100_lines.count == 2
    assert res.size_distribution.medium_100_to_500_lines.count == 1
    assert res.size_distribution.large_over_500_lines.count == 1


# ==============================================================================
# HTTP API Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_pull_request_analytics_endpoint():
    app = create_application()
    transport = ASGITransport(app=app)

    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_user.email = "lead@example.com"

    mock_member = MagicMock(spec=OrganizationMember)
    mock_member.organization_id = uuid.uuid4()
    mock_member.role = Role.ADMIN

    mock_response = PRAnalyticsResponse(
        time_window="30d",
        start_date="2026-10-01",
        end_date="2026-10-31",
        summary=PRAnalyticsSummary(
            total_prs_opened=10,
            total_prs_merged=8,
            total_prs_closed_unmerged=1,
            currently_open_prs=3,
            merge_rate_percentage=88.9,
            median_merge_time_hours=14.5,
            p75_merge_time_hours=28.0,
            median_cycle_time_hours=20.0,
        ),
        cadence_trend=[],
    )

    async def override_membership():
        return mock_member

    async def override_user():
        return mock_user

    async def override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_org_membership] = override_membership
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    with patch(
        "app.api.v1.endpoints.analytics.calculate_pull_request_analytics",
        new=AsyncMock(return_value=mock_response),
    ):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/api/v1/analytics/pull-requests?time_window=30d")
            assert resp.status_code == 200
            data = resp.json()
            assert data["time_window"] == "30d"
            assert data["summary"]["total_prs_merged"] == 8
            assert data["summary"]["merge_rate_percentage"] == 88.9
            assert data["summary"]["median_merge_time_hours"] == 14.5


@pytest.mark.asyncio
async def test_get_repository_pull_requests_and_sync_endpoints():
    app = create_application()
    transport = ASGITransport(app=app)

    repo_id = uuid.uuid4()
    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = repo_id
    mock_repo.organization_id = uuid.uuid4()

    mock_member = MagicMock(spec=OrganizationMember)
    mock_member.organization_id = mock_repo.organization_id
    mock_member.role = Role.ADMIN

    mock_db = AsyncMock()

    # Query mock: first execute finds repo, second execute finds PRs
    mock_repo_res = MagicMock()
    mock_repo_res.scalar_one_or_none.return_value = mock_repo

    mock_pr = MagicMock(spec=PullRequest)
    mock_pr.id = uuid.uuid4()
    mock_pr.repository_id = repo_id
    mock_pr.github_pr_id = 999
    mock_pr.number = 7
    mock_pr.title = "feat: add pr analytics"
    mock_pr.state = "OPEN"
    mock_pr.is_draft = False
    mock_pr.source_branch = "feat/pr"
    mock_pr.target_branch = "main"
    mock_pr.created_at_github = datetime(2026, 10, 30, tzinfo=UTC)
    mock_pr.updated_at_github = datetime(2026, 10, 30, tzinfo=UTC)
    mock_pr.closed_at = None
    mock_pr.merged_at = None
    mock_pr.first_reviewed_at = None
    mock_pr.additions = 100
    mock_pr.deletions = 10
    mock_pr.changed_files = 3
    mock_pr.commit_count = 2
    mock_pr.cycle_time_seconds = None
    mock_pr.merge_time_seconds = None
    mock_pr.first_review_time_seconds = None
    mock_pr.author = None

    mock_prs_res = MagicMock()
    mock_prs_res.scalars.return_value.all.return_value = [mock_pr]

    mock_db.execute.side_effect = [mock_repo_res, mock_prs_res]

    async def override_membership():
        return mock_member

    async def override_user():
        return MagicMock(id=uuid.uuid4(), email="admin@example.com")

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_org_membership] = override_membership
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test GET /repositories/{id}/pull-requests
        resp = await client.get(f"/api/v1/repositories/{repo_id}/pull-requests")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["title"] == "feat: add pr analytics"

        # 2. Test POST /repositories/{id}/sync-prs
        with patch(
            "app.api.v1.endpoints.repositories.sync_repository_pull_requests",
            new=AsyncMock(return_value=3),
        ):
            mock_db.execute.side_effect = [mock_repo_res]
            sync_resp = await client.post(f"/api/v1/repositories/{repo_id}/sync-prs")
            assert sync_resp.status_code == 200
            assert sync_resp.json()["synced_pull_requests"] == 3
