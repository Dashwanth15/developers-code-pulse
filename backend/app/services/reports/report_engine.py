import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Organization
from app.models.bottlenecks import Bottleneck
from app.models.reports import AIInsight, Report, ReportSection
from app.services.ai.factory import get_ai_provider
from app.services.analytics.dora_metrics import DORAMetricsService
from app.services.analytics.team_intelligence import TeamIntelligenceService
from app.services.reports.pdf_generator import PDFReportGenerator
from app.services.reports.report_builder import ReportSectionBuilder
from app.services.reports.report_comparison import calculate_period_comparison

logger = logging.getLogger(__name__)


class ReportEngine:
    """
    Central orchestrator for the Developers Code Pulse Reporting and AI Insights Module.
    Gathers metrics across Team Intelligence, DORA Pillars, and Bottlenecks;
    synthesizes executive insights via AI/deterministic engines; builds report sections;
    and renders downloadable PDF documents.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.team_service = TeamIntelligenceService(db)
        self.dora_service = DORAMetricsService(db)
        self.pdf_generator = PDFReportGenerator()
        self.ai_provider = get_ai_provider()

    @staticmethod
    def resolve_time_window(
        time_range: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[datetime, datetime, datetime, datetime, str]:
        """
        Resolves current observation window and immediately preceding baseline window.
        Returns: (cur_start, cur_end, prev_start, prev_end, label)
        """
        now = datetime.now(UTC)
        if start_date and end_date:
            cur_start = start_date if start_date.tzinfo else start_date.replace(tzinfo=UTC)
            cur_end = end_date if end_date.tzinfo else end_date.replace(tzinfo=UTC)
            duration = cur_end - cur_start
            prev_end = cur_start
            prev_start = prev_end - duration
            label = f"{cur_start.strftime('%b %d')} - {cur_end.strftime('%b %d, %Y')}"
            return cur_start, cur_end, prev_start, prev_end, label

        days_map = {
            "7d": 7,
            "14d": 14,
            "30d": 30,
            "90d": 90,
            "weekly": 7,
            "monthly": 30,
        }
        days = days_map.get(time_range.lower(), 30)
        cur_end = now
        cur_start = cur_end - timedelta(days=days)
        prev_end = cur_start
        prev_start = prev_end - timedelta(days=days)
        label = f"Last {days} Days"
        return cur_start, cur_end, prev_start, prev_end, label

    async def _fetch_active_bottlenecks(
        self,
        organization_id: uuid.UUID,
        repository_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        query = select(Bottleneck).where(
            Bottleneck.organization_id == organization_id,
            Bottleneck.status == "ACTIVE",
        )
        if repository_id:
            query = query.where(Bottleneck.repository_id == repository_id)

        result = await self.db.execute(query)
        bottlenecks = result.scalars().all()
        return [
            {
                "id": str(b.id),
                "rule_id": b.rule_id,
                "category": b.category,
                "severity": b.severity,
                "title": b.title,
                "description": b.description,
                "recommendation": b.recommendation,
                "confidence": b.confidence,
                "evidence": b.evidence,
            }
            for b in bottlenecks
        ]

    async def generate_report(
        self,
        organization_id: uuid.UUID,
        report_type: str,
        repository_id: uuid.UUID | None = None,
        time_range: str = "30d",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        title: str | None = None,
        generated_by: uuid.UUID | None = None,
        include_ai_insights: bool = True,
    ) -> Report:
        """
        Executes end-to-end report generation:
        1. Queries organization context and active repositories.
        2. Gathers current & previous analytics telemetry.
        3. Invokes AI/deterministic insights synthesis.
        4. Compiles structured report sections and persists records.
        5. Renders high-fidelity PDF document.
        """
        cur_start, cur_end, prev_start, prev_end, period_label = self.resolve_time_window(
            time_range, start_date, end_date
        )

        # Resolve Organization Name
        org_res = await self.db.execute(select(Organization).where(Organization.id == organization_id))
        org = org_res.scalars().first()
        org_name = org.name if org else "Engineering Organization"

        # Construct default title if not provided
        type_titles = {
            "ENGINEERING_HEALTH": "Engineering Health & Performance Report",
            "WEEKLY": "Weekly Software Delivery Cadence Report",
            "MONTHLY": "Monthly Engineering Flow & Stability Report",
            "REPOSITORY_HEALTH": "Repository Diagnostic & Code Review Report",
            "DORA": "DORA Software Delivery Metrics Report",
        }
        final_title = title or f"{org_name} — {type_titles.get(report_type.upper(), 'Engineering Report')}"

        # 1. Gather Current & Previous Analytics Telemetry
        team_current = await self.team_service.get_team_intelligence(
            organization_id=organization_id,
            repository_id=repository_id,
            start_date=cur_start,
            end_date=cur_end,
        )
        team_prev = await self.team_service.get_team_intelligence(
            organization_id=organization_id,
            repository_id=repository_id,
            start_date=prev_start,
            end_date=prev_end,
        )

        dora_current = await self.dora_service.get_dora_overview(
            organization_id=organization_id,
            repository_id=repository_id,
            start_date=cur_start,
            end_date=cur_end,
        )
        dora_prev = await self.dora_service.get_dora_overview(
            organization_id=organization_id,
            repository_id=repository_id,
            start_date=prev_start,
            end_date=prev_end,
        )

        bottlenecks = await self._fetch_active_bottlenecks(organization_id, repository_id)

        # 2. Compute Period-over-Period Deltas
        cur_payload = {
            "team": team_current.model_dump(),
            "dora": dora_current.model_dump(),
            "bottlenecks": bottlenecks,
            "period_label": period_label,
            "recommendations": team_current.systemic_recommendations,
        }
        prev_payload = {
            "team": team_prev.model_dump(),
            "dora": dora_prev.model_dump(),
        }
        comparison_deltas = calculate_period_comparison(cur_payload, prev_payload)

        # 3. AI Insights Synthesis
        if include_ai_insights:
            summary = await self.ai_provider.generate_executive_summary(
                cur_payload, org_name, period_label
            )
            raw_insights = await self.ai_provider.generate_insights(
                cur_payload, org_name, period_label
            )
        else:
            summary = (
                f"Standard engineering report for {org_name} across {period_label}. "
                f"Total PRs merged: {team_current.throughput.total_prs_merged}."
            )
            raw_insights = []

        # 4. Create Initial Report Entity
        report = Report(
            organization_id=organization_id,
            repository_id=repository_id,
            report_type=report_type.upper(),
            title=final_title,
            reporting_period_start=cur_start,
            reporting_period_end=cur_end,
            status="GENERATING",
            generated_by=generated_by,
            metadata_payload={
                "time_range": time_range,
                "comparison": comparison_deltas,
                "ai_provider": getattr(self.ai_provider, "model", "deterministic"),
            },
        )
        self.db.add(report)
        await self.db.flush()

        # 5. Build Report Sections
        section_dicts = ReportSectionBuilder.build_sections(
            report_type=report_type.upper(),
            metrics_data=cur_payload,
            executive_summary=summary,
            comparison_data=comparison_deltas,
        )
        for s_data in section_dicts:
            sec = ReportSection(
                report_id=report.id,
                section_type=s_data["section_type"],
                title=s_data["title"],
                content=s_data["content"],
                evidence=s_data["evidence"],
                order_index=s_data["order_index"],
            )
            self.db.add(sec)

        # 6. Render PDF Document
        try:
            pdf_path = self.pdf_generator.generate_pdf(
                report_id=report.id,
                report_type=report_type.upper(),
                title=final_title,
                organization_name=org_name,
                period_start=cur_start,
                period_end=cur_end,
                metrics_data=cur_payload,
                executive_summary=summary,
                sections_data=section_dicts,
                ai_provider_name=getattr(self.ai_provider, "model", "Deterministic Rules Engine"),
            )
            report.file_reference = pdf_path
            report.status = "COMPLETED"
            report.generated_at = datetime.now(UTC)
        except Exception as pdf_err:
            logger.error("Failed to render PDF for report %s: %s", report.id, pdf_err, exc_info=True)
            report.status = "FAILED"

        # 7. Persist AI Insight Entities
        for raw_ins in raw_insights:
            ai_entity = AIInsight(
                organization_id=organization_id,
                repository_id=repository_id,
                insight_type=raw_ins.get("insight_type", "HEALTH_DIAGNOSTIC"),
                title=raw_ins.get("title", "Delivery Insight"),
                explanation=raw_ins.get("explanation", ""),
                evidence=raw_ins.get("evidence", {}),
                recommendation=raw_ins.get("recommendation"),
                confidence=float(raw_ins.get("confidence", 1.0)),
                provider=getattr(self.ai_provider, "__class__", type).__name__,
                model=getattr(self.ai_provider, "model", "rules_engine"),
                generated_at=datetime.now(UTC),
                status="ACTIVE",
            )
            self.db.add(ai_entity)

        await self.db.commit()
        await self.db.refresh(report)
        return report
