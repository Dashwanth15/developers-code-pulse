# DEVELOPERS CODE PULSE (DCP)
## Bottleneck Detection Engine — Architecture & Specification

---

### 1. Architectural Overview

The **Bottleneck Detection Engine** in Developers Code Pulse (DCP) identifies systemic workflow delivery friction, review starvation, approval churn, merge delays, and reviewer capacity congestion across engineering teams.

Adhering strictly to DCP's **Modular Monolith** architecture and **Anti-Surveillance Manifesto**, this engine models macro process dynamics and operational baselines. It analyzes team queues, cycle delays, and load dispersion without generating individual developer speed scores or employee rankings.

```
                      ┌────────────────────────────────────────┐
                      │          GitHub Ingestion              │
                      │  (Webhooks, Commits, PRs, Reviews)     │
                      └──────────────────┬─────────────────────┘
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │    Normalized Operational Datastore    │
                      │   (pull_requests, pr_reviews, commits) │
                      └──────────────────┬─────────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
              ┌─────────────────────┐         ┌─────────────────────┐
              │ PR Flow Metrics     │         │ Review Intelligence │
              │ (T_merge, T_cycle)  │         │ (TTFR, Gini, Queue) │
              └──────────┬──────────┘         └──────────┬──────────┘
                         │                               │
                         └───────────────┬───────────────┘
                                         ▼
                      ┌────────────────────────────────────────┐
                      │       Bottleneck Detection Engine      │
                      │  (Orchestrator: BottleneckEngine)      │
                      ├────────────────────────────────────────┤
                      │ • ReviewDelayDetector                  │
                      │ • ApprovalDelayDetector                │
                      │ • MergeDelayDetector                   │
                      │ • ReviewerCapacityDetector             │
                      │ • PRSizeBottleneckDetector             │
                      │ • RepositoryWorkflowDetector           │
                      └──────────────────┬─────────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
              ┌─────────────────────┐         ┌─────────────────────┐
              │ Severity & Baseline │         │ Evidence-Backed     │
              │ Classifier          │         │ Recommendations     │
              │ (CRITICAL, HIGH...) │         │ Generator           │
              └──────────┬──────────┘         └──────────┬──────────┘
                         │                               │
                         └───────────────┬───────────────┘
                                         ▼
                      ┌────────────────────────────────────────┐
                      │      Tenant-Isolated Persistence       │
                      │  (bottlenecks, bottleneck_history,     │
                      │            detection_runs)             │
                      └────────────────────────────────────────┘
```

---

### 2. Detection Flow & Lifecycle

1. **Triggering**: Detection can run synchronously via `POST /api/v1/bottlenecks/detect` or asynchronously via Celery background tasks (`run_bottleneck_detection`).
2. **Data Scope**: Scoped strictly by `organization_id` (enforced by multi-tenant foreign keys and role-based access control).
3. **Execution**: The `BottleneckEngine` iterates through the 6 specialized detectors at both organization-wide and per-repository scopes.
4. **Fingerprinting & Deduplication**:
   - Every detected friction condition computes a deterministic SHA-256 fingerprint:
     $$\text{Fingerprint} = \text{SHA256}(\text{org\_id} : \text{repo\_id} : \text{bottleneck\_type} : \text{target\_key})$$
   - If an active or acknowledged bottleneck already exists with the same fingerprint, the engine updates `last_observed_at`, `evidence`, and `severity`, and appends an observation point to `bottleneck_history`.
   - If no active match exists, a new `Bottleneck` record is created.
5. **Historical Telemetry**: Every evaluation records an observation value against its baseline in `bottleneck_history` to power time-series trend analysis.

---

### 3. Database Schema

#### `bottlenecks`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique identifier |
| `organization_id` | UUID (FK) | Tenant organization (CASCADE) |
| `repository_id` | UUID (FK) | Affected repository (SET NULL, nullable) |
| `bottleneck_type` | VARCHAR(64) | Detection category |
| `severity` | VARCHAR(16) | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `confidence` | VARCHAR(16) | `LOW`, `MEDIUM`, `HIGH` |
| `title` | VARCHAR(255) | User-facing descriptive summary |
| `description` | TEXT | Narrative explaining the friction condition |
| `evidence` | JSONB | Telemetry payload (observed, baseline, affected items) |
| `recommendation` | TEXT | Actionable process guidance |
| `detected_at` | TIMESTAMPTZ | Initial identification timestamp |
| `first_observed_at` | TIMESTAMPTZ | Chronological first observed timestamp |
| `last_observed_at` | TIMESTAMPTZ | Most recent evaluation timestamp |
| `status` | VARCHAR(32) | `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`, `IGNORED` |
| `fingerprint` | VARCHAR(128) | Unique deduplication hash |
| `resolved_at` | TIMESTAMPTZ | Resolution timestamp (nullable) |

#### `bottleneck_history`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Observation identifier |
| `bottleneck_id` | UUID (FK) | Reference to `bottlenecks.id` (CASCADE) |
| `observed_value` | FLOAT | Telemetry value at evaluation time |
| `baseline_value` | FLOAT | Target baseline or team SLA value |
| `observation_window_start` | TIMESTAMPTZ | Window start timestamp |
| `observation_window_end` | TIMESTAMPTZ | Window end timestamp |
| `recorded_at` | TIMESTAMPTZ | Timestamp of evaluation |

#### `detection_runs`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Execution run identifier |
| `organization_id` | UUID (FK) | Tenant organization (CASCADE) |
| `repository_id` | UUID (FK) | Target repository filter (nullable) |
| `status` | VARCHAR(32) | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED` |
| `started_at` | TIMESTAMPTZ | Run start timestamp |
| `completed_at` | TIMESTAMPTZ | Run completion timestamp |
| `total_bottlenecks` | INTEGER | Number of bottlenecks evaluated |
| `error_message` | TEXT | Failure details (nullable) |

---

### 4. Security & Tenant Isolation

- **Tenant Isolation**: Every database query joins directly on `organization_id`. Cross-tenant data leakage is mathematically impossible at the query level.
- **Authorization**: Endpoints require JWT authentication and verify membership role in the target organization:
  - Viewer: Read-only access (`GET /bottlenecks`, `GET /bottlenecks/summary`, `GET /bottlenecks/trends`, `GET /bottlenecks/recommendations`)
  - Member: Status transitions (`PATCH /bottlenecks/{id}/status`)
  - Admin: Detection execution (`POST /bottlenecks/detect`)
