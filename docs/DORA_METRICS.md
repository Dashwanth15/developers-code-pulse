# DEVELOPERS CODE PULSE (DCP)
## DORA Metrics Engine Specification & Calculation Methodology

---

### 1. Architectural Philosophy & Integrity Guarantees

The DevOps Research and Assessment (DORA) metrics represent the industry standard for evaluating software delivery performance and operational stability.

DCP adheres to three immutable operational principles:
1. **Never Fabricate Data:** DCP never manufactures dummy deployment frequencies, estimated recovery times, or hypothetical failure rates.
2. **Explicit Insufficient Data State:** If an organization lacks connected deployment pipelines or incident management tools, the engine outputs `INSUFFICIENT_DATA` with performance tier `UNKNOWN`.
3. **Strict Production Environment Isolation:** Only rollouts targeting verified `production` environments are counted. Development builds, CI checks, staging runs, and preview deployments are strictly isolated.

---

### 2. The Four Core DORA Metrics

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                DORA METRICS ENGINE                              │
│                                                                                 │
│   ┌───────────────────────────┐             ┌───────────────────────────────┐   │
│   │   Deployment Frequency    │             │    Lead Time for Changes      │   │
│   │   · Daily / Weekly Cadence│             │    · Commit -> PR -> Merge    │   │
│   │   · Successful Prod Only  │             │    · Merge -> Production      │   │
│   │   · Elite: Multiple / Day │             │    · Elite: < 1 Hour          │   │
│   └───────────────────────────┘             └───────────────────────────────┘   │
│                                                                                 │
│   ┌───────────────────────────┐             ┌───────────────────────────────┐   │
│   │   Change Failure Rate     │             │    Time to Restore Service    │   │
│   │   · Failed Deployments    │             │    · Incident Start -> Resolve│   │
│   │   · Post-Deploy Incidents │             │    · Median & P75 Latencies   │   │
│   │   · Elite: 0% - 5%        │             │    · Elite: < 1 Hour          │   │
│   └───────────────────────────┘             └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### 3. Detailed Metric Methodology

#### A. Deployment Frequency (DF)
- **Definition:** The rate of successful production deployments over a specific timeframe ($T$).
- **Filtering Rules:**
  - `environment = 'production'` (case-insensitive normalized).
  - `status = 'SUCCESS'`.
  - Staging, preview, and failed deployments are excluded.
- **Cadence Calculations:**
  - $\text{Daily Frequency} = \frac{\text{Successful Production Deployments}}{\text{Days in Period}}$
  - $\text{Weekly Frequency} = \text{Daily Frequency} \times 7$
  - $\text{Monthly Frequency} = \text{Daily Frequency} \times 30$
- **Performance Tiers (Industry Standard):**
  - **Elite:** Multiple deployments per day ($\text{Daily} \ge 1.0$)
  - **High:** Between once per day and once per week ($0.14 \le \text{Daily} < 1.0$)
  - **Medium:** Between once per week and once per month ($0.033 \le \text{Daily} < 0.14$)
  - **Low:** Fewer than once per month ($\text{Daily} < 0.033$)

---

#### B. Lead Time for Changes (LT)
- **Definition:** The elapsed time from code commit to verified production deployment.
- **Traceability Methodology:**
  1. A deployment records `commit_sha` and `deployed_at`.
  2. The system queries the corresponding `Commit` record by `sha` to retrieve `authored_at` or `committed_at`.
  3. Lead time is computed as:
     $$\Delta T_{\text{lead}} = T_{\text{deployed}} - T_{\text{commit\_authored}}$$
  4. If a commit cannot be resolved, the deployment is marked as untraced. The system reports `traceability_rate` ($\frac{\text{Traced Deployments}}{\text{Total Deployments}}$) without guessing timestamps.
- **Statistical Metric:**
  - Nonparametric **Median** ($\text{P50}$) to eliminate pipeline freeze skew.
  - **75th Percentile** ($\text{P75}$) to capture tail latency.
- **Performance Tiers:**
  - **Elite:** Less than 1 hour ($\le 1\text{h}$)
  - **High:** Between 1 hour and 1 day ($> 1\text{h}$ and $\le 24\text{h}$)
  - **Medium:** Between 1 day and 1 week ($> 24\text{h}$ and $\le 168\text{h}$)
  - **Low:** More than 1 week ($> 168\text{h}$)

---

#### C. Change Failure Rate (CFR)
- **Definition:** The percentage of production deployments that result in an outage, service degradation, or immediate hotfix.
- **Failure Classification:**
  A deployment is classified as degraded if:
  1. The deployment itself terminated in `FAILED`, `CANCELLED`, or `ERROR` status, **OR**
  2. A verified `Incident` is correlated to the deployment via `DeploymentIncident` mapping within the proximity window.
- **Calculation Formula:**
  $$\text{CFR} = \frac{\text{Degraded Deployments} + \text{Incident-Linked Deployments}}{\text{Total Production Deployments Attempted}} \times 100\%$$
- **Performance Tiers:**
  - **Elite:** 0% – 5%
  - **High:** 6% – 15%
  - **Medium:** 16% – 30%
  - **Low:** $> 30\%$

---

#### D. Time to Restore Service / Mean Time to Recovery (MTTR)
- **Definition:** The elapsed duration between a production incident start and verified resolution.
- **Data Source Requirements:**
  - Requires integration with incident tracking systems (PagerDuty, Opsgenie, GitHub Incident Issues, or DCP Incident API).
  - If zero incident data exists, the metric status is explicitly flagged as `INSUFFICIENT_DATA`.
- **Calculations:**
  $$\Delta T_{\text{recovery}} = T_{\text{resolved}} - T_{\text{started}}$$
  - **Median Recovery Time** ($\text{P50}$) in hours.
  - **P75 Recovery Time** ($\text{P75}$) in hours.
- **Performance Tiers:**
  - **Elite:** Less than 1 hour ($\le 1\text{h}$)
  - **High:** Less than 1 day ($\le 24\text{h}$)
  - **Medium:** Less than 1 week ($\le 168\text{h}$)
  - **Low:** More than 1 week ($> 168\text{h}$)

---

### 4. DORA Snapshot Aggregations

To prevent expensive real-time database queries on high-traffic dashboards, Celery periodic workers calculate and store metric snapshots in `dora_metric_snapshots`:

```sql
CREATE TABLE dora_metric_snapshots (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    repository_id UUID NULL,
    metric_type VARCHAR(64) NOT NULL,
    metric_value FLOAT NULL,
    status VARCHAR(32) NOT NULL,
    performance_level VARCHAR(32) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    sample_size INTEGER NOT NULL,
    data_completeness BOOLEAN NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL,
    methodology_version VARCHAR(32) NOT NULL,
    details JSONB NULL
);
```

---

### 5. API Reference

- `GET /api/v1/analytics/dora?time_range=30d&repository_id=<id>`: Comprehensive DORA overview including all four metrics, industry tiers, and cross-repo comparisons.
- `GET /api/v1/analytics/dora/deployment-frequency`: Dedicated frequency trends and cadences.
- `GET /api/v1/analytics/dora/lead-time`: Traceability rates and commit-to-deploy latency distribution.
- `GET /api/v1/analytics/dora/change-failure-rate`: Failure attribution and incident correlation.
- `GET /api/v1/analytics/dora/mean-time-to-recovery`: Outage duration percentiles and resolution telemetry.
