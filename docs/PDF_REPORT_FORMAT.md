# PDF Report Format & Enterprise Document Design — Developers Code Pulse (DCP)

## 1. Overview & Objectives

Developers Code Pulse (DCP) generates enterprise-grade PDF reports suitable for executive briefings, engineering retrospectives, and board-level presentations.

The PDF generation engine is built using **ReportLab** (`reportlab>=4.1.0`), utilizing a clean, modern design system that reflects high-performance engineering standards.

---

## 2. Document Layout & Design System

### A. Color Palette
- **Primary / Brand Slate**: `#0f172a` (Deep Slate Navy)
- **Primary Accent**: `#2563eb` (Royal Blue)
- **Secondary Slate**: `#334155` (Muted Steel)
- **Positive Trend / Success**: `#16a34a` (Emerald Green)
- **Warning / Degraded**: `#d97706` (Amber)
- **Critical / Danger**: `#dc2626` (Ruby Red)
- **Card Background**: `#f8fafc` (Ultra-light Slate)
- **Table Border**: `#e2e8f0` (Subtle Slate Border)
- **Body Text**: `#1e293b` (High-contrast Charcoal)

### B. Typography & Hierarchy
- **Document Title**: Helvetica-Bold, 22pt, Dark Slate Navy
- **Section Headers (H1)**: Helvetica-Bold, 14pt with bottom accent underline
- **Sub-headers (H2)**: Helvetica-Bold, 11pt, Slate Navy
- **Body Text**: Helvetica, 9.5pt, line spacing 13pt
- **Table Cells**: Helvetica, 8.5pt, compact vertical padding (4pt)
- **Footnotes & Metadata**: Helvetica-Oblique, 7.5pt, muted slate

### C. Header & Footer Running Canvas
- Implemented via a custom two-pass ReportLab canvas (`NumberedCanvas`):
  - **Running Header**: Brand mark ("DEVELOPERS CODE PULSE — ENGINEERING INTELLIGENCE"), organization name, and reporting period.
  - **Running Footer**: Confidentiality notice, generation timestamp in UTC, and dynamic page numbering ("Page X of Y").

---

## 3. Structural Sections

Every compiled report contains structured modular sections:

```
+-------------------------------------------------------+
|  1. HEADER & EXECUTIVE SUMMARY                        |
|     - Organization Name & Scope Badge                 |
|     - Reporting Period & Timezone (UTC)               |
|     - Grounded AI / Deterministic Executive Narrative |
+-------------------------------------------------------+
|  2. KEY PERFORMANCE INDICATORS (KPI) SUMMARY           |
|     - Metric Cards Grid (Throughput, Cadence, Flow)   |
|     - Baseline Period Comparison & Delta Indicators   |
+-------------------------------------------------------+
|  3. DELIVERY LATENCY & WORKLOAD DISTRIBUTION          |
|     - PR Cycle Time, Merge Latency, TTFR Breakdown    |
|     - Reviewer Workload Equity (Gini Coefficient)     |
+-------------------------------------------------------+
|  4. BOTTLENECK RADAR & WORKFLOW FRICTION               |
|     - Active Bottlenecks Table (Type, Severity, Title)|
|     - Resolution Status vs Detected Ratio             |
+-------------------------------------------------------+
|  5. DORA METRICS DELIVERY MATRIX                       |
|     - 4 Pillars: Deployment Frequency, Lead Time,     |
|       Change Failure Rate, Time to Restore Service    |
|     - Elite/High/Medium/Low Performance Tiers         |
|     - Explicit Insufficient-Data Notices (if any)     |
+-------------------------------------------------------+
|  6. SYSTEMIC ENGINEERING RECOMMENDATIONS              |
|     - High-impact Process & Pipeline Interventions    |
|     - Root Cause Observations & Target Outcomes       |
+-------------------------------------------------------+
|  7. METHODOLOGY, PROVENANCE & ETHICAL CHARTER         |
|     - Metric Calculation Formulas & Data Sources      |
|     - Strict Anti-Surveillance Ethics Notice          |
+-------------------------------------------------------+
```

---

## 4. Report Type Specializations

### 1. `ENGINEERING_HEALTH` (Comprehensive Organization Overview)
- Comprehensive 3–5 page document.
- Combines organization-wide throughput, code review distribution, bottleneck radar, full DORA 4-pillar analysis, and AI-synthesized systemic recommendations.

### 2. `WEEKLY` (Operational Sprint Retrospective)
- Streamlined 2-page document.
- Focuses on operational velocity: PRs opened vs merged, merge rate, median time-to-first-review, review workload balance, active bottlenecks, and weekly rollouts.

### 3. `MONTHLY` (Strategic Engineering Review)
- Strategic 3-page document.
- Highlights macro throughput changes, month-over-month cycle time deltas, resolved vs lingering bottlenecks, and strategic continuous delivery trends.

### 4. `REPOSITORY_HEALTH` (Single Codebase Diagnostic)
- Focused 2-page document scoped to a specific repository.
- Detailed commit cadence, pull request size distribution, review latency, and repository-specific DORA metrics.

### 5. `DORA` (Delivery Velocity & Stability Audit)
- Dedicated 2-page SRE & DevOps document.
- In-depth breakdown of Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Mean Time to Recovery, complete with benchmark classifications, missing data warnings, and provenance details.

---

## 5. Technical Implementation Details

### File Generation & Storage
- **Generator**: `backend/app/services/reports/pdf_generator.py`
- **Output Path**: `data/reports/{organization_id}/{report_id}.pdf`
- **Streaming**: Handled via FastAPI `FileResponse` with content-disposition header `attachment; filename="{sanitized_title}.pdf"`.
- **MIME Type**: `application/pdf`

### Insufficient Data Handling
DCP never guesses or fabricates missing values in PDF reports:
- Missing DORA data renders an amber warning box: `INSUFFICIENT DATA — Requires additional deployment correlation or incident integration`.
- Missing cycle times render as `—` (Not Recorded) with an explicit explanatory note in the methodology section.
