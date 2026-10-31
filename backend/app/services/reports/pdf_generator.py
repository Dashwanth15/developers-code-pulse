import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import get_settings


class PDFReportGenerator:
    """
    High-fidelity enterprise PDF report generator for Developers Code Pulse.
    Renders executive summaries, macro KPI cards, DORA stability pillars,
    bottleneck constraints, and methodology notes.
    """

    def __init__(self, storage_dir: str | None = None) -> None:
        settings = get_settings()
        self.storage_dir = Path(storage_dir or settings.REPORTS_STORAGE_PATH)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._init_styles()

    def _init_styles(self) -> None:
        self.base_styles = getSampleStyleSheet()

        self.primary_color = colors.HexColor("#0f172a")  # Slate 900
        self.accent_color = colors.HexColor("#2563eb")   # Blue 600
        self.text_muted = colors.HexColor("#64748b")     # Slate 500
        self.card_bg = colors.HexColor("#f8fafc")        # Slate 50
        self.border_color = colors.HexColor("#e2e8f0")   # Slate 200
        self.emerald = colors.HexColor("#059669")
        self.rose = colors.HexColor("#e11d48")
        self.amber = colors.HexColor("#d97706")

        self.title_style = ParagraphStyle(
            "ReportTitle",
            parent=self.base_styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=self.primary_color,
            fontName="Helvetica-Bold",
        )
        self.subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=self.base_styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=self.text_muted,
            fontName="Helvetica",
        )
        self.section_header_style = ParagraphStyle(
            "ReportSectionHeader",
            parent=self.base_styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=self.primary_color,
            fontName="Helvetica-Bold",
            spaceBefore=12,
            spaceAfter=6,
        )
        self.body_style = ParagraphStyle(
            "ReportBody",
            parent=self.base_styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
            fontName="Helvetica",
        )
        self.kpi_val_style = ParagraphStyle(
            "KPIValue",
            parent=self.base_styles["Normal"],
            fontSize=14,
            leading=18,
            textColor=self.primary_color,
            fontName="Helvetica-Bold",
            alignment=1,
        )
        self.kpi_lbl_style = ParagraphStyle(
            "KPILabel",
            parent=self.base_styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=self.text_muted,
            fontName="Helvetica",
            alignment=1,
        )
        self.badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=self.base_styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=1,
        )

    def generate_pdf(
        self,
        report_id: uuid.UUID,
        report_type: str,
        title: str,
        organization_name: str,
        period_start: datetime,
        period_end: datetime,
        metrics_data: dict[str, Any],
        executive_summary: str,
        sections_data: list[dict[str, Any]],
        ai_provider_name: str = "Deterministic Rules Engine",
    ) -> str:
        """
        Compiles and renders the complete multi-page PDF document to storage.
        Returns the relative file reference path.
        """
        filename = f"report_{report_id}.pdf"
        file_path = self.storage_dir / filename
        _ = (report_type, sections_data)

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        elements: list[Any] = []

        # 1. Header Banner
        elements.append(Paragraph("DEVELOPERS CODE PULSE", self.subtitle_style))
        elements.append(Paragraph(title, self.title_style))
        period_str = (
            f"Organization: <b>{organization_name}</b> | "
            f"Reporting Window: <b>{period_start.strftime('%Y-%m-%d')}</b> to "
            f"<b>{period_end.strftime('%Y-%m-%d')}</b> (UTC)"
        )
        elements.append(Paragraph(period_str, self.subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=self.accent_color, spaceBefore=4, spaceAfter=12))

        # 2. Executive Summary Card
        elements.append(Paragraph("Executive Summary & Delivery Diagnostic", self.section_header_style))
        exec_table_data = [[
            Paragraph(executive_summary, self.body_style)
        ]]
        exec_table = Table(exec_table_data, colWidths=[540])
        exec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.card_bg),
            ("BOX", (0, 0), (-1, -1), 1, self.border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        elements.append(exec_table)
        elements.append(Spacer(1, 12))

        # 3. Macro KPI Grid
        team = metrics_data.get("team", {})
        throughput = team.get("throughput", {})
        cadence = team.get("cadence", {})

        prs_merged = throughput.get("total_prs_merged", 0)
        merge_rate = throughput.get("merge_rate", 0.0)
        median_cycle = cadence.get("median_pr_cycle_time_hours")
        median_cycle_str = f"{median_cycle:.1f}h" if median_cycle is not None else "N/A"
        median_ttfr = cadence.get("median_time_to_first_review_hours")
        median_ttfr_str = f"{median_ttfr:.1f}h" if median_ttfr is not None else "N/A"
        prod_deploys = throughput.get("total_production_deployments", 0)

        kpi_table_data = [
            [
                Paragraph(str(prs_merged), self.kpi_val_style),
                Paragraph(f"{merge_rate:.1f}%", self.kpi_val_style),
                Paragraph(median_cycle_str, self.kpi_val_style),
                Paragraph(median_ttfr_str, self.kpi_val_style),
                Paragraph(str(prod_deploys), self.kpi_val_style),
            ],
            [
                Paragraph("PRs Merged", self.kpi_lbl_style),
                Paragraph("Merge Rate", self.kpi_lbl_style),
                Paragraph("Median Cycle Time", self.kpi_lbl_style),
                Paragraph("Median TTFR", self.kpi_lbl_style),
                Paragraph("Prod Deployments", self.kpi_lbl_style),
            ]
        ]
        kpi_table = Table(kpi_table_data, colWidths=[108, 108, 108, 108, 108])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.card_bg),
            ("BOX", (0, 0), (-1, -1), 1, self.border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, self.border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(Paragraph("Software Delivery Throughput & Cadence", self.section_header_style))
        elements.append(kpi_table)
        elements.append(Spacer(1, 14))

        # 4. DORA Metrics Table
        dora = metrics_data.get("dora", {})
        df = dora.get("deployment_frequency", {})
        lt = dora.get("lead_time_for_changes", {})
        cfr = dora.get("change_failure_rate", {})
        mttr = dora.get("mean_time_to_recovery", {})

        elements.append(Paragraph("DORA Delivery Performance Pillars", self.section_header_style))
        dora_table_data = [
            [
                Paragraph("<b>DORA Metric</b>", self.body_style),
                Paragraph("<b>Calculated Value</b>", self.body_style),
                Paragraph("<b>Industry Tier</b>", self.body_style),
                Paragraph("<b>Sample Size / Status</b>", self.body_style),
            ],
            [
                Paragraph("Deployment Frequency (DF)", self.body_style),
                Paragraph(df.get("formatted_value", "INSUFFICIENT_DATA"), self.body_style),
                Paragraph(df.get("performance_level", "UNKNOWN"), self.body_style),
                Paragraph(f"{df.get('sample_size', 0)} production deployments", self.body_style),
            ],
            [
                Paragraph("Lead Time for Changes (LT)", self.body_style),
                Paragraph(lt.get("formatted_value", "INSUFFICIENT_DATA"), self.body_style),
                Paragraph(lt.get("performance_level", "UNKNOWN"), self.body_style),
                Paragraph(f"{lt.get('sample_size', 0)} traced deployments", self.body_style),
            ],
            [
                Paragraph("Change Failure Rate (CFR)", self.body_style),
                Paragraph(cfr.get("formatted_value", "INSUFFICIENT_DATA"), self.body_style),
                Paragraph(cfr.get("performance_level", "UNKNOWN"), self.body_style),
                Paragraph(f"{cfr.get('sample_size', 0)} evaluated rollouts", self.body_style),
            ],
            [
                Paragraph("Time to Restore Service (MTTR)", self.body_style),
                Paragraph(mttr.get("formatted_value", "INSUFFICIENT_DATA"), self.body_style),
                Paragraph(mttr.get("performance_level", "UNKNOWN"), self.body_style),
                Paragraph(
                    "Requires incident tracking source"
                    if mttr.get("status") == "INSUFFICIENT_DATA"
                    else f"{mttr.get('sample_size', 0)} incidents",
                    self.body_style,
                ),
            ],
        ]
        dora_table = Table(dora_table_data, colWidths=[160, 120, 110, 150])
        dora_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, self.border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, self.border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(dora_table)
        elements.append(Spacer(1, 14))

        # 5. Bottleneck Analysis & Friction Points
        bottlenecks = metrics_data.get("bottlenecks", [])
        elements.append(Paragraph("Workflow Bottlenecks & Friction Points", self.section_header_style))

        if bottlenecks:
            b_rows = [
                [
                    Paragraph("<b>Rule / Category</b>", self.body_style),
                    Paragraph("<b>Severity</b>", self.body_style),
                    Paragraph("<b>Observation & Evidence</b>", self.body_style),
                    Paragraph("<b>Recommendation</b>", self.body_style),
                ]
            ]
            for b in bottlenecks[:6]:
                b_rows.append([
                    Paragraph(b.get("category", "Friction").replace("_", " ").title(), self.body_style),
                    Paragraph(b.get("severity", "MEDIUM"), self.body_style),
                    Paragraph(b.get("description", ""), self.body_style),
                    Paragraph(b.get("recommendation", ""), self.body_style),
                ])
            b_table = Table(b_rows, colWidths=[120, 70, 180, 170])
            b_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, self.border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, self.border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(b_table)
        else:
            no_b_text = (
                "Zero active workflow bottlenecks were detected in this reporting period. "
                "Review turnaround, approval dynamics, and merge latency are operating within benchmark thresholds."
            )
            elements.append(Paragraph(no_b_text, self.body_style))

        elements.append(Spacer(1, 14))

        # 6. Actionable Systemic Recommendations (Anti-Surveillance Manifesto)
        elements.append(
            Paragraph("Systemic Engineering Recommendations & Process Priorities", self.section_header_style)
        )
        recommendations = metrics_data.get("recommendations", [])
        if not recommendations and bottlenecks:
            recommendations = [b.get("recommendation") for b in bottlenecks if b.get("recommendation")]

        if recommendations:
            rec_text = "<br/>".join([f"• <b>{r}</b>" for r in recommendations[:4]])
        else:
            rec_text = "• Continue maintaining automated CI pipelines and small, incremental pull request scopes."

        rec_table = Table([[Paragraph(rec_text, self.body_style)]], colWidths=[540])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),  # Emerald 50
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bbf7d0")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(rec_table)
        elements.append(Spacer(1, 14))

        # 7. Methodology, Provenance & Anti-Surveillance Ethics Notice
        footer_elements = [
            Paragraph("Methodology, Data Integrity & Anti-Surveillance Ethics Guarantee", self.section_header_style),
            Paragraph(
                "<b>Anti-Surveillance Guarantee:</b> Developers Code Pulse analyzes macro system cadence, peer review loops, "
                "and deployment stability across engineering organizations and repositories. It strictly prohibits individual developer rankings, "
                "personal productivity scoring, and developer velocity quotas.<br/>"
                "<b>Provenance:</b> All throughput, cycle times, and DORA statistics are derived directly from verified GitHub pull requests, "
                "peer review submissions, and production release workflows. Unobserved pillars explicitly output INSUFFICIENT_DATA.<br/>"
                f"<i>Generated on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')} | "
                f"Synthesis Provider: {ai_provider_name}</i>",
                self.subtitle_style,
            ),
        ]
        elements.append(KeepTogether(footer_elements))

        # Render document to storage
        doc.build(elements)
        return str(file_path)
