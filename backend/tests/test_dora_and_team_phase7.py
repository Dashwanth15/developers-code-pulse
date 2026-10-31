import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import create_application
from app.models.auth import OrganizationMember, Role, User
from app.models.dora import Deployment, Incident
from app.models.github import Repository
from app.models.pull_requests import PullRequest
from app.services.analytics.dora_metrics import (
    calculate_change_failure_rate,
    calculate_deployment_frequency,
    calculate_lead_time_for_changes,
    calculate_mean_time_to_recovery,
    calculate_percentile,
    determine_overall_performance,
)
from app.services.analytics.team_intelligence import (
    calculate_team_intelligence,
)
from app.services.auth.dependencies import get_current_org_membership, get_current_user
from app.services.github.deployment_service import (
    classify_environment,
    ingest_deployment_payload,
    ingest_incident_record,
)
from app.workers.tasks import (
    calculate_dora_snapshots_task,
    sync_deployments_task,
    sync_incidents_task,
)

# ==============================================================================
# 1. Percentile & Math Tests
# ==============================================================================


def test_calculate_percentile():
    assert calculate_percentile([], 50.0) is None
    assert calculate_percentile([42.0], 50.0) == 42.0
    assert calculate_percentile([10.0, 20.0, 30.0, 40.0, 50.0], 50.0) == 30.0
    assert calculate_percentile([10.0, 20.0, 30.0, 40.0], 75.0) == 32.5


# ==============================================================================
# 2. Environment Classification Tests
# ==============================================================================


def test_classify_environment():
    assert classify_environment("production") == "production"
    assert classify_environment("PROD") == "production"
    assert classify_environment("live") == "production"
    assert classify_environment("staging") == "staging"
    assert classify_environment("uat") == "staging"
    assert classify_environment("dev") == "development"
    assert classify_environment(None) == "development"


# ==============================================================================
# 3. DORA Deployment Frequency Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_deployment_frequency_insufficient_data():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    org_id = uuid.uuid4()
    detail = await calculate_deployment_frequency(
        db=mock_db, organization_id=org_id, time_window="30d"
    )

    assert detail.card.status == "INSUFFICIENT_DATA"
    assert detail.card.performance_level == "UNKNOWN"
    assert detail.card.formatted_value == "INSUFFICIENT_DATA"
    assert detail.total_deployments == 0
    assert detail.successful_deployments == 0


@pytest.mark.asyncio
async def test_deployment_frequency_calculated_elite():
    now = datetime.now(UTC)
    org_id = uuid.uuid4()

    # 60 successful production deployments over 30 days -> 2/day -> ELITE
    deployments = []
    for i in range(60):
        d = MagicMock(spec=Deployment)
        d.organization_id = org_id
        d.environment = "production"
        d.status = "SUCCESS"
        d.deployed_at = now - timedelta(hours=i * 10)
        deployments.append(d)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = deployments
    mock_db.execute.return_value = mock_res

    detail = await calculate_deployment_frequency(
        db=mock_db, organization_id=org_id, time_window="30d"
    )

    assert detail.card.status == "CALCULATED"
    assert detail.card.performance_level == "ELITE"
    assert detail.daily_deployments >= 1.0
    assert detail.successful_deployments == 60


# ==============================================================================
# 4. DORA Lead Time for Changes Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_lead_time_insufficient_data():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    org_id = uuid.uuid4()
    detail = await calculate_lead_time_for_changes(
        db=mock_db, organization_id=org_id, time_window="30d"
    )

    assert detail.card.status == "INSUFFICIENT_DATA"
    assert detail.card.performance_level == "UNKNOWN"
    assert detail.median_hours is None
    assert detail.sample_size == 0


@pytest.mark.asyncio
async def test_lead_time_calculated():
    now = datetime.now(UTC)
    org_id = uuid.uuid4()

    d1 = MagicMock(spec=Deployment)
    d1.organization_id = org_id
    d1.environment = "production"
    d1.status = "SUCCESS"
    d1.deployed_at = now - timedelta(days=2)
    d1.lead_time_seconds = 3600.0 * 12  # 12 hours -> HIGH tier
    d1.commit_sha = "abc1234"

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [d1]
    mock_db.execute.return_value = mock_res

    detail = await calculate_lead_time_for_changes(
        db=mock_db, organization_id=org_id, time_window="30d"
    )

    assert detail.card.status == "CALCULATED"
    assert detail.card.performance_level == "HIGH"
    assert detail.median_hours == 12.0
    assert detail.sample_size == 1


# ==============================================================================
# 5. DORA Change Failure Rate Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_change_failure_rate_calculated():
    now = datetime.now(UTC)
    org_id = uuid.uuid4()

    # 10 deployments: 1 failed, 9 success with no incidents -> 10% -> HIGH tier
    deployments = []
    for i in range(9):
        d = MagicMock(spec=Deployment)
        d.id = uuid.uuid4()
        d.organization_id = org_id
        d.environment = "production"
        d.status = "SUCCESS"
        d.deployed_at = now - timedelta(days=i)
        d.incident_links = []
        deployments.append(d)

    d_fail = MagicMock(spec=Deployment)
    d_fail.id = uuid.uuid4()
    d_fail.organization_id = org_id
    d_fail.environment = "production"
    d_fail.status = "FAILURE"
    d_fail.deployed_at = now - timedelta(days=1)
    d_fail.incident_links = []
    deployments.append(d_fail)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = deployments
    mock_db.execute.return_value = mock_res

    detail = await calculate_change_failure_rate(
        db=mock_db, organization_id=org_id, time_window="30d"
    )

    assert detail.card.status == "CALCULATED"
    assert detail.failure_rate_percent == 10.0
    assert detail.card.performance_level == "HIGH"
    assert detail.total_production_deployments == 10
    assert detail.failed_deployments == 1


# ==============================================================================
# 6. DORA MTTR Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_mttr_insufficient_data():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    org_id = uuid.uuid4()
    detail = await calculate_mean_time_to_recovery(
        db=mock_db, organization_id=org_id, time_window="30d"
    )

    assert detail.card.status == "INSUFFICIENT_DATA"
    assert detail.card.performance_level == "UNKNOWN"
    assert detail.median_hours is None


@pytest.mark.asyncio
async def test_mttr_calculated():
    now = datetime.now(UTC)
    org_id = uuid.uuid4()

    inc = MagicMock(spec=Incident)
    inc.organization_id = org_id
    inc.started_at = now - timedelta(hours=4)
    inc.resolved_at = now - timedelta(hours=2)
    inc.recovery_duration_seconds = 7200.0  # 2 hours -> HIGH tier (<24h)
    inc.status = "RESOLVED"

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [inc]
    mock_db.execute.return_value = mock_res

    detail = await calculate_mean_time_to_recovery(
        db=mock_db, organization_id=org_id, time_window="30d"
    )

    assert detail.card.status == "CALCULATED"
    assert detail.median_hours == 2.0
    assert detail.card.performance_level == "HIGH"
    assert detail.resolved_incidents == 1


# ==============================================================================
# 7. Overall DORA Performance Composite Tests
# ==============================================================================


def test_overall_dora_performance_tiers():
    c1 = MagicMock(status="CALCULATED", performance_level="ELITE")
    c2 = MagicMock(status="CALCULATED", performance_level="ELITE")
    c3 = MagicMock(status="CALCULATED", performance_level="HIGH")
    c4 = MagicMock(status="INSUFFICIENT_DATA", performance_level="UNKNOWN")

    assert determine_overall_performance([c1, c2, c3, c4]) == "ELITE"
    assert determine_overall_performance([c4]) == "UNKNOWN"


# ==============================================================================
# 8. Ingestion & Lead Time Traceability Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_ingest_deployment_and_correlate():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    org_id = uuid.uuid4()
    payload = {
        "id": "deploy-101",
        "environment": "production",
        "status": "SUCCESS",
        "deployed_at": datetime.now(UTC).isoformat(),
        "commit_sha": "a1b2c3d4",
        "source": "GITHUB_ACTIONS",
        "metadata": {"runner": "ubuntu-latest"},
    }

    deployment = await ingest_deployment_payload(
        db=mock_db,
        organization_id=org_id,
        repository=None,
        data=payload,
    )

    assert deployment.external_deployment_id == "deploy-101"
    assert deployment.environment == "production"
    assert deployment.status == "SUCCESS"
    assert deployment.source == "GITHUB_ACTIONS"
    mock_db.add.assert_called()


@pytest.mark.asyncio
async def test_ingest_incident_record():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    org_id = uuid.uuid4()
    started = datetime.now(UTC) - timedelta(hours=1)
    resolved = datetime.now(UTC)

    payload = {
        "id": "inc-202",
        "title": "API Gateway 502 Outage",
        "severity": "CRITICAL",
        "status": "RESOLVED",
        "started_at": started.isoformat(),
        "resolved_at": resolved.isoformat(),
        "source": "PAGERDUTY",
        "metadata": {"service": "gateway"},
    }

    incident = await ingest_incident_record(
        db=mock_db,
        organization_id=org_id,
        repository=None,
        data=payload,
    )

    assert incident.external_incident_id == "inc-202"
    assert incident.title == "API Gateway 502 Outage"
    assert incident.severity == "CRITICAL"
    assert incident.status == "RESOLVED"
    assert incident.recovery_duration_seconds is not None
    assert incident.recovery_duration_seconds > 0
    mock_db.add.assert_called()


# ==============================================================================
# 9. Team Intelligence Engine Tests (Anti-Surveillance Compliance)
# ==============================================================================


@pytest.mark.asyncio
async def test_team_intelligence_anti_surveillance_adherence():
    now = datetime.now(UTC)
    org_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = repo_id
    mock_repo.name = "core-backend"
    mock_repo.organization_id = org_id

    mock_pr = MagicMock(spec=PullRequest)
    mock_pr.id = uuid.uuid4()
    mock_pr.repository_id = repo_id
    mock_pr.created_at = now - timedelta(days=2)
    mock_pr.merged_at = now - timedelta(days=1)
    mock_pr.state = "MERGED"
    mock_pr.cycle_time_seconds = 86400.0
    mock_pr.reviews = []

    mock_db = AsyncMock()

    # Repos query
    repo_res = MagicMock()
    repo_res.scalars.return_value.all.return_value = [mock_repo]

    # PRs query
    pr_res = MagicMock()
    pr_res.scalars.return_value.all.return_value = [mock_pr]

    # Commits count
    mock_db.scalar.side_effect = [15]

    # Deployments & Bottlenecks
    dep_res = MagicMock()
    dep_res.scalars.return_value.all.return_value = []
    bot_res = MagicMock()
    bot_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [repo_res, pr_res, dep_res, bot_res]

    intel = await calculate_team_intelligence(
        db=mock_db,
        organization_id=org_id,
        time_window="30d",
    )

    # Validate strict Anti-Surveillance Manifesto adherence
    assert "developer surveillance" in intel.anti_surveillance_notice.lower()
    assert intel.throughput.total_prs_merged == 1
    assert intel.throughput.total_commits == 15
    assert len(intel.repository_trends) == 1
    assert intel.repository_trends[0].repository_name == "core-backend"


# ==============================================================================
# 10. REST API Endpoints Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_dora_overview_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.organization_id = org_id
    mock_membership.role = Role.VIEWER

    mock_db = AsyncMock()
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = empty_res
    mock_db.scalar.return_value = 0

    app.dependency_overrides[get_current_org_membership] = lambda: mock_membership
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/analytics/dora?time_window=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == str(org_id)
        assert "deployment_frequency" in data
        assert "lead_time_for_changes" in data
        assert "change_failure_rate" in data
        assert "mean_time_to_recovery" in data
        assert data["deployment_frequency"]["status"] == "INSUFFICIENT_DATA"


@pytest.mark.asyncio
async def test_get_team_intelligence_endpoint():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.organization_id = org_id
    mock_membership.role = Role.VIEWER

    mock_db = AsyncMock()
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = empty_res
    mock_db.scalar.return_value = 0

    app.dependency_overrides[get_current_org_membership] = lambda: mock_membership
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/analytics/team?time_window=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == str(org_id)
        assert "anti_surveillance_notice" in data
        assert "throughput" in data
        assert "delivery_cadence" in data


@pytest.mark.asyncio
async def test_deployments_list_and_create_endpoints():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.organization_id = org_id
    mock_membership.role = Role.ADMIN

    mock_db = AsyncMock()
    dep_mock = MagicMock(spec=Deployment)
    dep_mock.id = uuid.uuid4()
    dep_mock.organization_id = org_id
    dep_mock.repository_id = None
    dep_mock.repository = None
    dep_mock.external_deployment_id = "dep-test"
    dep_mock.environment = "production"
    dep_mock.status = "SUCCESS"
    dep_mock.deployed_at = datetime.now(UTC)
    dep_mock.completed_at = None
    dep_mock.commit_sha = "abc1234"
    dep_mock.ref_name = "main"
    dep_mock.source = "EXTERNAL_API"
    dep_mock.lead_time_seconds = 1800.0
    dep_mock.metadata_payload = {}
    dep_mock.created_at = datetime.now(UTC)

    list_res = MagicMock()
    list_res.scalars.return_value.all.return_value = [dep_mock]
    mock_db.execute.return_value = list_res
    mock_db.scalar.return_value = 1

    app.dependency_overrides[get_current_org_membership] = lambda: mock_membership
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/deployments?page=1&size=20")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["environment"] == "production"

        # Sync endpoint
        sync_resp = await client.post("/api/v1/deployments/sync", json={})
        assert sync_resp.status_code == 202
        assert sync_resp.json()["status"] == "PENDING"


@pytest.mark.asyncio
async def test_incidents_list_and_sync_endpoints():
    app = create_application()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    mock_membership = MagicMock(spec=OrganizationMember)
    mock_membership.organization_id = org_id
    mock_membership.role = Role.ADMIN

    mock_db = AsyncMock()
    inc_mock = MagicMock(spec=Incident)
    inc_mock.id = uuid.uuid4()
    inc_mock.organization_id = org_id
    inc_mock.repository_id = None
    inc_mock.repository = None
    inc_mock.external_incident_id = "inc-test"
    inc_mock.title = "High Latency Alert"
    inc_mock.severity = "HIGH"
    inc_mock.status = "OPEN"
    inc_mock.started_at = datetime.now(UTC)
    inc_mock.resolved_at = None
    inc_mock.recovery_duration_seconds = None
    inc_mock.source = "MANUAL"
    inc_mock.metadata_payload = {}
    inc_mock.created_at = datetime.now(UTC)

    list_res = MagicMock()
    list_res.scalars.return_value.all.return_value = [inc_mock]
    mock_db.execute.return_value = list_res
    mock_db.scalar.return_value = 1

    app.dependency_overrides[get_current_org_membership] = lambda: mock_membership
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/incidents?page=1&size=20")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "HIGH"

        # Sync endpoint
        sync_resp = await client.post("/api/v1/incidents/sync", json={})
        assert sync_resp.status_code == 202
        assert sync_resp.json()["status"] == "PENDING"


# ==============================================================================
# 11. Celery Task Tests
# ==============================================================================


def test_celery_task_definitions():
    assert sync_deployments_task.name == "app.workers.tasks.sync_deployments_task"
    assert sync_incidents_task.name == "app.workers.tasks.sync_incidents_task"
    assert calculate_dora_snapshots_task.name == "app.workers.tasks.calculate_dora_snapshots_task"
