import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import create_application
from app.models.auth import OrganizationMember, Role, User
from app.models.commits import Commit, GitHubAccount
from app.models.github import Repository
from app.schemas.commits import (
    CommitAnalyticsResponse,
    CommitAnalyticsSummary,
)
from app.services.analytics import commit_metrics
from app.services.auth.dependencies import get_current_org_membership, get_current_user
from app.services.github.commit_service import (
    ingest_push_payload,
    is_likely_merge_commit,
    resolve_or_create_github_account,
)

# ==============================================================================
# Commit Heuristics & Push Parsing Tests
# ==============================================================================


def test_is_likely_merge_commit():
    assert is_likely_merge_commit("Merge pull request #42 from org/feature") is True
    assert is_likely_merge_commit("Merge branch 'main' of github.com:org/repo") is True
    assert is_likely_merge_commit("Merge remote-tracking branch 'origin/main'") is True
    assert is_likely_merge_commit("Regular commit fixing typos", parents_count=2) is True
    assert is_likely_merge_commit("feat: implement analytics service", parents_count=1) is False
    assert is_likely_merge_commit("fix: handle edge case in parser") is False


@pytest.mark.asyncio
async def test_resolve_or_create_github_account():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()

    # Case 1: Account doesn't exist, create human user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    account = await resolve_or_create_github_account(
        db=mock_db,
        organization_id=org_id,
        login="octocat",
        name="The Octocat",
        email="octocat@github.com",
    )
    assert account.login == "octocat"
    assert account.user_type == "User"
    assert mock_db.add.called

    # Case 2: Bot account detection
    bot_account = await resolve_or_create_github_account(
        db=mock_db,
        organization_id=org_id,
        login="dependabot[bot]",
        name="Dependabot",
    )
    assert bot_account.user_type == "Bot"


@pytest.mark.asyncio
async def test_ingest_push_payload_saves_commits_and_deduplicates():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    repo = Repository(
        id=repo_id,
        organization_id=org_id,
        name="dcp-api",
        full_name="org/dcp-api",
        default_branch="main",
    )

    payload = {
        "ref": "refs/heads/main",
        "sender": {"login": "dev-alice", "avatar_url": "https://avatars.github.com/u/1"},
        "commits": [
            {
                "id": "1111222233334444555566667777888899990000",
                "message": "feat: add commit intelligence router",
                "timestamp": "2026-10-31T12:00:00Z",
                "author": {"name": "Alice Dev", "email": "alice@org.io", "username": "dev-alice"},
                "added": ["file1.py", "file2.py"],
                "removed": [],
                "modified": ["main.py"],
            },
            {
                "id": "2222333344445555666677778888999900001111",
                "message": "Merge pull request #10 from feature",
                "timestamp": "2026-10-31T12:30:00Z",
                "author": {"name": "Alice Dev", "email": "alice@org.io", "username": "dev-alice"},
                "added": [],
                "removed": [],
                "modified": [],
            },
        ],
    }

    # Mock no existing commit on first query
    mock_chk = MagicMock()
    mock_chk.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_chk

    saved = await ingest_push_payload(mock_db, repo, payload)
    assert saved == 2
    assert mock_db.commit.called


# ==============================================================================
# Analytics Engine Commit Calculation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_calculate_commit_analytics_empty_repo_state():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()

    # Return empty list of monitored repositories
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    res = await commit_metrics.calculate_commit_analytics(
        db=mock_db,
        organization_id=org_id,
        time_window="30d",
    )

    assert res.summary.total_commits == 0
    assert res.summary.daily_cadence == 0.0
    assert res.summary.active_contributors == 0
    assert len(res.cadence_trend) == 0


@pytest.mark.asyncio
async def test_calculate_commit_analytics_metrics_accuracy():
    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    repo = Repository(
        id=repo_id,
        organization_id=org_id,
        name="core-service",
        full_name="acme/core-service",
        is_monitored=True,
    )

    # Monitored repos result
    mock_repo_res = MagicMock()
    mock_repo_res.scalars.return_value.all.return_value = [repo]

    # Human contributor & bot contributor
    human_author = GitHubAccount(
        id=uuid.uuid4(),
        organization_id=org_id,
        login="engineer-jane",
        name="Jane",
        user_type="User",
    )
    bot_author = GitHubAccount(
        id=uuid.uuid4(),
        organization_id=org_id,
        login="dependabot[bot]",
        name="Dependabot",
        user_type="Bot",
    )

    now = datetime.now(UTC)

    # 3 Commits: 1 regular human, 1 merge commit, 1 bot commit
    commit_1 = Commit(
        id=uuid.uuid4(),
        repository_id=repo_id,
        author=human_author,
        commit_sha="a" * 40,
        message="feat: initial feature implementation",
        committed_at=now - timedelta(days=2),
        additions=120,
        deletions=15,
        is_merge_commit=False,
    )
    commit_2 = Commit(
        id=uuid.uuid4(),
        repository_id=repo_id,
        author=human_author,
        commit_sha="b" * 40,
        message="Merge branch 'main' into feature",
        committed_at=now - timedelta(days=1),
        additions=0,
        deletions=0,
        is_merge_commit=True,  # Merge commit must be excluded from total
    )
    commit_3 = Commit(
        id=uuid.uuid4(),
        repository_id=repo_id,
        author=bot_author,
        commit_sha="c" * 40,
        message="chore(deps): bump library",
        committed_at=now - timedelta(hours=5),
        additions=2,
        deletions=2,
        is_merge_commit=False,
    )

    mock_commits_res = MagicMock()
    mock_commits_res.scalars.return_value.all.return_value = [commit_1, commit_2, commit_3]

    mock_db.execute.side_effect = [mock_repo_res, mock_commits_res]

    analytics = await commit_metrics.calculate_commit_analytics(
        db=mock_db,
        organization_id=org_id,
        time_window="7d",
    )

    # Verify exclusions and calculations
    assert analytics.summary.total_commits == 2  # commit_1 + commit_3 (commit_2 excluded)
    assert analytics.summary.merge_commit_count == 1
    assert analytics.summary.total_additions == 122  # 120 + 2
    assert analytics.summary.total_deletions == 17  # 15 + 2
    assert analytics.summary.total_churn == 139
    # Bot contributor must be excluded from active_contributors count
    assert analytics.summary.active_contributors == 1
    assert len(analytics.top_contributors) == 1
    assert analytics.top_contributors[0].login == "engineer-jane"
    assert len(analytics.cadence_trend) == 8  # 7 days + boundary day
    assert len(analytics.heatmap) == 7 * 24  # 168 cells


# ==============================================================================
# REST API Endpoint Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_api_analytics_commits_endpoint():
    app = create_application()
    org_id = uuid.uuid4()

    user = User(
        id=uuid.uuid4(),
        email="viewer@org.com",
        full_name="Viewer User",
        hashed_password="hash",
    )
    membership = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org_id,
        user_id=user.id,
        role=Role.VIEWER,
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_org_membership] = lambda: membership
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_analytics_dto = CommitAnalyticsResponse(
        time_window="30d",
        start_date="2026-10-01",
        end_date="2026-10-31",
        summary=CommitAnalyticsSummary(
            total_commits=42,
            daily_cadence=1.4,
            weekday_cadence=1.9,
            active_contributors=5,
            total_additions=3200,
            total_deletions=450,
            total_churn=3650,
            merge_commit_count=6,
        ),
        cadence_trend=[],
        heatmap=[],
        top_contributors=[],
        repository_comparison=[],
    )

    with patch(
        "app.api.v1.endpoints.analytics.calculate_commit_analytics",
        new_callable=AsyncMock,
        return_value=mock_analytics_dto,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/analytics/commits?time_window=30d")
            assert response.status_code == 200
            data = response.json()
            assert data["summary"]["total_commits"] == 42
            assert data["summary"]["active_contributors"] == 5
            assert data["summary"]["total_churn"] == 3650


@pytest.mark.asyncio
async def test_api_repository_commits_not_found():
    app = create_application()
    org_id = uuid.uuid4()
    missing_repo_id = uuid.uuid4()

    user = User(
        id=uuid.uuid4(),
        email="member@org.com",
        full_name="Member User",
        hashed_password="hash",
    )
    membership = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org_id,
        user_id=user.id,
        role=Role.MEMBER,
    )

    mock_db = AsyncMock()
    # Mock repository not found
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_org_membership] = lambda: membership
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/repositories/{missing_repo_id}/commits")
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "REPOSITORY_NOT_FOUND"
