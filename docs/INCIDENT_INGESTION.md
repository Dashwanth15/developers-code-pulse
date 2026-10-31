# DEVELOPERS CODE PULSE (DCP)
## Incident Ingestion & Service Recovery Telemetry

---

### 1. Ingestion Architecture

The Incident Ingestion Engine captures service degradation events, outages, and critical bugs from external incident management systems (e.g., PagerDuty, Opsgenie, incident tracking tools, GitHub Issues labeled `incident`) and custom webhooks.

```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     Incident Webhooks / API     │   │   External Incident Monitors    │
└────────────────┬────────────────┘   └────────────────┬────────────────┘
                 │                                     │
                 └──────────────────┬──────────────────┘
                                    ▼
                     ┌──────────────────────────────┐
                     │    INCIDENT INGESTION        │
                     │  app/services/github/        │
                     │  deployment_service.py       │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │       incidents TABLE        │
                     │ (started_at, resolved_at,    │
                     │  recovery_duration_seconds)  │
                     └──────────────┬───────────────┘
                                    │
                     ┌──────────────┴───────────────┐
                     │   DEPLOYMENT CORRELATION     │
                     │ (Window: Deploy -> Incident) │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │   deployment_incidents TABLE │
                     │   (deployment_id, incident)  │
                     └──────────────────────────────┘
```

---

### 2. Database Entities

#### `incidents` Table
```sql
CREATE TABLE incidents (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    repository_id UUID NULL REFERENCES repositories(id),
    external_incident_id VARCHAR(255) NOT NULL,
    title VARCHAR(512) NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'MAJOR', -- CRITICAL, MAJOR, MINOR, LOW
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',     -- OPEN, INVESTIGATING, MITIGATED, RESOLVED
    started_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ NULL,
    recovery_duration_seconds INTEGER NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'manual',   -- pagerduty, opsgenie, github, manual
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `deployment_incidents` Table
Links an incident to the causative or mitigating deployment:
```sql
CREATE TABLE deployment_incidents (
    id UUID PRIMARY KEY,
    deployment_id UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    relationship_type VARCHAR(64) NOT NULL DEFAULT 'CAUSED_BY', -- CAUSED_BY, RESOLVED_BY, CORRELATED
    confidence FLOAT NOT NULL DEFAULT 1.0,
    provenance VARCHAR(128) NOT NULL DEFAULT 'heuristic_window',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 3. Automatic Deployment-Incident Correlation Heuristic

When an incident is ingested without an explicit deployment link, the system evaluates recent production rollouts for the affected repository (or across the organization if repo-agnostic):

1. **Temporal Proximity Window:**
   The engine searches for production deployments that completed within **3 hours prior** to `incident.started_at`:
   $$t_{\text{incident\_started}} - 3\text{h} \le t_{\text{deployed}} \le t_{\text{incident\_started}}$$
2. **Confidence Assignment:**
   - Deployments occurring within 30 minutes of incident onset receive a confidence score of `0.90`.
   - Deployments between 30 minutes and 3 hours receive a confidence score of `0.70`.
3. **Traceability Record:**
   A `DeploymentIncident` entry is created with `relationship_type = 'CAUSED_BY'` and `provenance = 'auto_heuristic_3h'`.

---

### 4. Mean Time to Recovery (MTTR) Engine

1. **Calculation:**
   When an incident is marked `RESOLVED` with a valid `resolved_at` timestamp:
   $$\text{recovery\_duration\_seconds} = \max(0, (T_{\text{resolved}} - T_{\text{started}}).\text{total\_seconds}())$$
2. **Aggregations:**
   - **Median Recovery Time ($\text{P50}$):** The central tendency of service restoration duration.
   - **75th Percentile ($\text{P75}$):** Measures recovery SLA adherence under complex outages.
3. **Absence of Incident Data:**
   If no incidents exist for the organization within the selected timeframe, the MTTR metric status is set to `INSUFFICIENT_DATA` with performance tier `UNKNOWN`.

---

### 5. API Reference

- `GET /api/v1/incidents`: Lists incidents with filters for repository, severity, status, and date range.
- `POST /api/v1/incidents`: Ingests an incident from an external system.
- `POST /api/v1/incidents/sync`: Triggers asynchronous synchronization of incident records via Celery.
