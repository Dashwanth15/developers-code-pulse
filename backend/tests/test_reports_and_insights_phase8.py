import os
import tempfile
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import create_application
from app.models.auth import OrganizationMember, Role, User
from app.models.reports import AIInsight, Report, ReportSection, ScheduledReport
from app.services.ai.deterministic_provider import DeterministicAIProvider
from app.services.ai.gemini_provider import GeminiAIProvider
from app.services.auth.dependencies import get_current_org_membership, get_current_user
from app.services.reports.pdf_generator import PDFReportGenerator
from app.services.reports.report_builder import ReportSectionBuilder
from app.services.reports.report_comparison import calculate_period_comparison
from app.services.reports.report_engine import ReportEngine

# ==============================================================================
# 1. PDF Generation Tests
# ==============================================================================


def test_pdf_report_generator_creates_valid_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        generator = PDFReportGenerator(storage_dir=tmp_dir)
        report_id = uuid.uuid4()
        now = datetime.now(UTC)

        metrics = {
            "team": {
                "throughput": {
                    "total_prs_opened": 15,
                    "total_prs_merged": 12,
                    "merge_rate": 80.0,
                    "total_production_deployments": 4,
                },
                "cadence": {
                    "median_pr_cycle_time_hours": 14.5,
                    "median_time_to_first_review_hours": 3.2,
                },
                "collaboration": {
                    "review_coverage": 100.0,
                    "multi_reviewer_rate": 45.0,
                },
            },
            "dora": {
                "deployment_frequency": {
                    "status": "CALCULATED",
                    "formatted_value": "0.4 / day",
                    "performance_level": "HIGH",
                    "sample_size": 4,
                },
                "lead_time_for_changes": {
                    "status": "CALCULATED",
                    "formatted_value": "4.2 hours",
                    "performance_level": "HIGH",
                    "sample_size": 4,
                },
                "change_failure_rate": {
                    "status": "CALCULATED",
                    "formatted_value": "0.0%",
                    "performance_level": "ELITE",
                    "sample_size": 4,
                },
                "mean_time_to_recovery": {
                    "status": "INSUFFICIENT_DATA",
                    "formatted_value": "N/A",
                    "performance_level": "UNKNOWN",
                    "sample_size": 0,
                },
            },
            "bottlenecks": [
                {
                    "rule_id": "BOT-01",
                    "category": "REVIEW_DELAY",
                    "severity": "MEDIUM",
                    "description": "First review turnaround took 16.5 hours on 2 PRs.",
                    "recommendation": "Institute automated review triage.",
                }
            ],
            "recommendations": [
                "Implement automated code review routing.",
                "Maintain trunk-based release cadences.",
            ],
        }

        file_path = generator.generate_pdf(
            report_id=report_id,
            report_type="ENGINEERING_HEALTH",
            title="Weekly Engineering Diagnostic",
            organization_name="Acme Corp",
            period_start=now,
            period_end=now,
            metrics_data=metrics,
            executive_summary="Team throughput is strong with healthy merge rates.",
            sections_data=[],
            ai_provider_name="Deterministic Rules Engine",
        )

        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) > 1024  # Valid PDF size


# ==============================================================================
# 2. Deterministic AI Insights Provider Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_deterministic_ai_provider_summary_and_insights():
    provider = DeterministicAIProvider()
    assert provider.is_available() is True

    metrics = {
        "team": {
            "throughput": {"total_prs_merged": 20, "merge_rate": 85.0},
            "cadence": {
                "median_pr_cycle_time_hours": 18.0,
                "median_time_to_first_review_hours": 4.5,
            },
            "collaboration": {"review_coverage": 90.0, "multi_reviewer_rate": 50.0},
        },
        "dora": {
            "deployment_frequency": {
                "status": "CALCULATED",
                "formatted_value": "1.2 / day",
                "performance_level": "ELITE",
                "sample_size": 25,
            },
            "lead_time_for_changes": {"formatted_value": "3.5h"},
            "change_failure_rate": {"formatted_value": "4.0%"},
            "mean_time_to_recovery": {"formatted_value": "45m"},
        },
        "bottlenecks": [],
    }

    summary = await provider.generate_executive_summary(metrics, "TechCorp", "Last 30 Days")
    assert "TechCorp" in summary
    assert "20 pull requests merged" in summary
    assert "85.0%" in summary
    assert "Anti-Surveillance" in summary

    insights = await provider.generate_insights(metrics, "TechCorp", "Last 30 Days")
    assert len(insights) >= 3

    # Check positive trend insight
    trend_insight = next((i for i in insights if i["insight_type"] == "POSITIVE_TREND"), None)
    assert trend_insight is not None
    assert "85.0%" in trend_insight["explanation"]
    assert trend_insight["evidence"]["prs_merged"] == 20


@pytest.mark.asyncio
async def test_deterministic_ai_provider_insufficient_data():
    provider = DeterministicAIProvider()
    metrics = {
        "team": {
            "throughput": {"total_prs_merged": 0, "merge_rate": 0.0},
            "cadence": {},
            "collaboration": {},
        },
        "dora": {
            "deployment_frequency": {"status": "INSUFFICIENT_DATA"},
        },
        "bottlenecks": [],
    }

    insights = await provider.generate_insights(metrics, "EmptyOrg", "Last 7 Days")
    dora_notice = next((i for i in insights if i["insight_type"] == "DATA_INTEGRITY_NOTICE"), None)
    assert dora_notice is not None
    assert dora_notice["evidence"]["status"] == "INSUFFICIENT_DATA"
    assert "strictly prevents manufactured" in dora_notice["explanation"]


# ==============================================================================
# 3. Gemini AI Provider Mock Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_gemini_provider_success_and_fallback():
    provider = GeminiAIProvider(api_key="mock_key", model="gemini-1.5-flash")
    assert provider.is_available() is True

    # 1. Successful structured mock
    mock_json_response = (
        '```json\n'
        '[\n'
        '  {\n'
        '    "insight_type": "POSITIVE_TREND",\n'
        '    "title": "Merge Efficiency Surge",\n'
        '    "explanation": "PR merge velocity increased by 20% across main repos.",\n'
        '    "evidence": {"delta": 20},\n'
        '    "recommendation": "Keep small PR scopes.",\n'
        '    "confidence": 0.95\n'
        '  }\n'
        ']\n'
        '```'
    )

    with patch.object(provider, "_call_gemini", AsyncMock(return_value=mock_json_response)):
        insights = await provider.generate_insights({}, "Org", "Window")
        assert len(insights) == 1
        assert insights[0]["title"] == "Merge Efficiency Surge"

    # 2. Network error / None response -> falls back to deterministic provider
    with patch.object(provider, "_call_gemini", AsyncMock(return_value=None)):
        fallback_insights = await provider.generate_insights(
            {"team": {"throughput": {"total_prs_merged": 5, "merge_rate": 80.0}, "cadence": {}}, "dora": {}},
            "Org",
            "Window",
        )
        assert len(fallback_insights) > 0
        assert fallback_insights[0]["confidence"] >= 0.8


# ==============================================================================
# 4. Period Comparison Tests
# ==============================================================================


def test_calculate_period_comparison():
    current = {
        "team": {
            "throughput": {"total_prs_merged": 15, "merge_rate": 85.0},
            "cadence": {
                "median_pr_cycle_time_hours": 12.0,
                "median_time_to_first_review_hours": 3.0,
            },
        },
        "dora": {
            "deployment_frequency": {"sample_size": 6},
        },
    }
    previous = {
        "team": {
            "throughput": {"total_prs_merged": 10, "merge_rate": 70.0},
            "cadence": {
                "median_pr_cycle_time_hours": 18.0,
                "median_time_to_first_review_hours": 5.0,
            },
        },
        "dora": {
            "deployment_frequency": {"sample_size": 4},
        },
    }

    deltas = calculate_period_comparison(current, previous)
    assert deltas["prs_merged"]["delta"] == 5
    assert deltas["prs_merged"]["percentage"] == 50.0
    assert deltas["merge_rate"]["delta"] == 15.0
    assert deltas["cycle_time_hours"]["delta"] == -6.0
    assert deltas["cycle_time_hours"]["improved"] is True
    assert deltas["deployments"]["delta"] == 2


# ==============================================================================
# 5. Report Section Builder Tests
# ==============================================================================


def test_report_section_builder_structure():
    metrics = {
        "period_label": "Last 30 Days",
        "team": {
            "throughput": {"total_prs_opened": 20, "total_prs_merged": 18, "merge_rate": 90.0},
            "cadence": {"median_pr_cycle_time_hours": 14.0},
            "collaboration": {"review_coverage": 100.0},
        },
        "dora": {
            "deployment_frequency": {"status": "CALCULATED"},
            "overall_tier": "HIGH",
        },
        "bottlenecks": [
            {
                "rule_id": "BOT-01",
                "severity": "HIGH",
                "title": "Review Queue Stall",
                "recommendation": "Assign peer triage slots.",
            }
        ],
    }

    sections = ReportSectionBuilder.build_sections(
        report_type="WEEKLY",
        metrics_data=metrics,
        executive_summary="Excellent team delivery flow.",
    )

    types = [s["section_type"] for s in sections]
    assert "EXECUTIVE_SUMMARY" in types
    assert "KPI_SUMMARY" in types
    assert "COLLABORATION_HEALTH" in types
    assert "BOTTLENECK_ANALYSIS" in types
    assert "DORA_METRICS" in types
    assert "RECOMMENDATIONS" in types
    assert "METHODOLOGY" in types


# ==============================================================================
# 6. ReportEngine Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_report_engine_generate_report():
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    # Mock Org query
    mock_org = MagicMock()
    mock_org.name = "Engineering Corp"
    mock_org_res = MagicMock()
    mock_org_res.scalars.return_value.first.return_value = mock_org
    mock_db.execute.return_value = mock_org_res

    engine = ReportEngine(mock_db)
    # Mock team & dora services
    mock_team_res = MagicMock()
    mock_team_res.model_dump.return_value = {
        "throughput": {"total_prs_merged": 10, "merge_rate": 80.0},
        "cadence": {"median_pr_cycle_time_hours": 12.0},
        "collaboration": {"review_coverage": 100.0},
    }
    mock_team_res.systemic_recommendations = ["Keep PRs small."]
    engine.team_service.get_team_intelligence = AsyncMock(return_value=mock_team_res)

    mock_dora_res = MagicMock()
    mock_dora_res.model_dump.return_value = {
        "deployment_frequency": {"status": "CALCULATED", "formatted_value": "1.0 / day"},
        "overall_tier": "ELITE",
    }
    engine.dora_service.get_dora_overview = AsyncMock(return_value=mock_dora_res)
    engine._fetch_active_bottlenecks = AsyncMock(return_value=[])

    with tempfile.TemporaryDirectory() as tmp_dir:
        engine.pdf_generator = PDFReportGenerator(storage_dir=tmp_dir)

        report = await engine.generate_report(
            organization_id=uuid.uuid4(),
            report_type="ENGINEERING_HEALTH",
            time_range="30d",
        )

        assert report.status == "COMPLETED"
        assert report.file_reference is not None
        assert os.path.exists(report.file_reference)


# ==============================================================================
# 7. FastAPI API Endpoints Tests
# ==============================================================================


@pytest.fixture
def mock_user_membership():
    user = User(
        id=uuid.uuid4(),
        email="lead@devpulse.io",
        full_name="Lead Engineer",
        hashed_password="hash",
    )
    membership = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=user.id,
        role=Role.ADMIN,
    )
    return user, membership


@pytest.mark.asyncio
async def test_list_reports_api(mock_user_membership):
    user, membership = mock_user_membership
    app = create_application()

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    # Mock count total
    count_res = MagicMock()
    count_res.scalar.return_value = 1

    # Mock query list
    report_entity = Report(
        id=uuid.uuid4(),
        organization_id=membership.organization_id,
        report_type="ENGINEERING_HEALTH",
        title="Acme Engineering Health",
        reporting_period_start=datetime.now(UTC),
        reporting_period_end=datetime.now(UTC),
        status="COMPLETED",
        file_reference="storage/reports/test.pdf",
        sections=[],
    )
    list_res = MagicMock()
    list_res.scalars.return_value.all.return_value = [report_entity]

    mock_db.execute.side_effect = [count_res, list_res]

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_org_membership] = lambda: membership
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Acme Engineering Health"
        assert data["items"][0]["download_url"] is not None


@pytest.mark.asyncio
async def test_get_report_details_and_download_api(mock_user_membership):
    user, membership = mock_user_membership
    app = create_application()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 mock pdf content")
        temp_pdf_path = f.name

    try:
        report_id = uuid.uuid4()
        report_entity = Report(
            id=report_id,
            organization_id=membership.organization_id,
            report_type="WEEKLY",
            title="Weekly Diagnostic",
            reporting_period_start=datetime.now(UTC),
            reporting_period_end=datetime.now(UTC),
            status="COMPLETED",
            file_reference=temp_pdf_path,
            sections=[
                ReportSection(
                    id=uuid.uuid4(),
                    report_id=report_id,
                    section_type="EXECUTIVE_SUMMARY",
                    title="Summary",
                    content={"summary_text": "Good flow"},
                    order_index=1,
                )
            ],
        )

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        rep_res = MagicMock()
        rep_res.scalars.return_value.first.return_value = report_entity
        mock_db.execute.return_value = rep_res

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_current_org_membership] = lambda: membership
        app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Get Details
            detail_resp = await client.get(f"/api/v1/reports/{report_id}")
            assert detail_resp.status_code == 200
            assert detail_resp.json()["title"] == "Weekly Diagnostic"
            assert len(detail_resp.json()["sections"]) == 1

            # 2. Download PDF
            dl_resp = await client.get(f"/api/v1/reports/{report_id}/download")
            assert dl_resp.status_code == 200
            assert dl_resp.headers["content-type"] == "application/pdf"
            assert dl_resp.content == b"%PDF-1.4 mock pdf content"
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


@pytest.mark.asyncio
async def test_scheduled_reports_crud_api(mock_user_membership):
    user, membership = mock_user_membership
    app = create_application()

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.delete = AsyncMock()

    sched_id = uuid.uuid4()
    sched_entity = ScheduledReport(
        id=sched_id,
        organization_id=membership.organization_id,
        report_type="WEEKLY",
        frequency="WEEKLY",
        next_run_at=datetime.now(UTC),
        timezone="UTC",
        enabled=True,
        recipients=["devs@acme.com"],
        created_by=user.id,
    )

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_org_membership] = lambda: membership
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Scheduled
        create_resp = await client.post(
            "/api/v1/reports/scheduled",
            json={
                "report_type": "WEEKLY",
                "frequency": "WEEKLY",
                "timezone": "UTC",
                "recipients": ["team@acme.com"],
                "enabled": True,
            },
        )
        assert create_resp.status_code == 201
        assert create_resp.json()["frequency"] == "WEEKLY"

        # 2. Update Scheduled
        sched_res = MagicMock()
        sched_res.scalars.return_value.first.return_value = sched_entity
        mock_db.execute.return_value = sched_res

        patch_resp = await client.patch(
            f"/api/v1/reports/scheduled/{sched_id}",
            json={"enabled": False, "frequency": "MONTHLY"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["enabled"] is False

        # 3. Delete Scheduled
        del_resp = await client.delete(f"/api/v1/reports/scheduled/{sched_id}")
        assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_insights_api(mock_user_membership):
    user, membership = mock_user_membership
    app = create_application()

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    insight = AIInsight(
        id=uuid.uuid4(),
        organization_id=membership.organization_id,
        insight_type="POSITIVE_TREND",
        title="Velocity Improvement",
        explanation="PR cycle time dropped 15%",
        confidence=0.95,
        provider="GeminiAIProvider",
        model="gemini-1.5-flash",
        generated_at=datetime.now(UTC),
        status="ACTIVE",
    )
    ins_res = MagicMock()
    ins_res.scalars.return_value.all.return_value = [insight]
    mock_db.execute.return_value = ins_res

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_org_membership] = lambda: membership
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/insights")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Velocity Improvement"
        assert data["ai_provider_configured"] is True
