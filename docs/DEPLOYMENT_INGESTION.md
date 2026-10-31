# DEVELOPERS CODE PULSE (DCP)
## Deployment Ingestion Pipeline & Architecture

---

### 1. Ingestion Overview

The Deployment Ingestion Pipeline receives, normalizes, and correlates deployment telemetry from GitHub Actions workflow runs, GitHub Deployments API, and external deployment systems.

```
┌─────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│  GitHub Actions Runs    │   │  GitHub Deployments API  │   │ External CI/CD Pipelines │
└────────────┬────────────┘   └────────────┬─────────────┘   └────────────┬─────────────┘
             │                             │                              │
             └───────────────────────┬─────┴──────────────────────────────┘
                                     ▼
                      ┌──────────────────────────────┐
                      │    DEPLOYMENT SERVICE        │
                      │  app/services/github/        │
                      │  deployment_service.py       │
                      └──────────────┬───────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
│    Environment     │    │     Commit Lead    │    │      Incident      │
│   Classification   │    │  Time Traceability │    │  Auto-Correlation  │
│ (Prod vs Staging)  │    │  (Commit -> Prod)  │    │ (Proximity Window) │
└────────────────────┘    └────────────────────┘    └────────────────────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     ▼
                      ┌──────────────────────────────┐
                      │      deployments TABLE       │
                      │   (Multi-tenant, Idempotent) │
                      └──────────────────────────────┘
```

---

### 2. Environment Classification & Filtering

**Critical Rule:** A successful continuous integration (CI) run or unit test build is **not** a production deployment.

The pipeline applies deterministic classification rules to map raw environment strings:

```python
def classify_environment(raw_env: str | None) -> str:
    """Normalize and classify environment strings."""
    if not raw_env:
        return "development"

    env = raw_env.lower().strip()
    if any(k in env for k in ["prod", "live", "release"]):
        return "production"
    if any(k in env for k in ["stage", "staging", "uat", "preprod"]):
        return "staging"
    if any(k in env for k in ["test", "ci", "build", "dev", "preview"]):
        return "development"
    return "development"
```

Only deployments classified as `"production"` are factored into DORA metrics.

---

### 3. Workflow Run vs. Deployment Run Disambiguation

When ingesting GitHub Actions workflow runs (`workflow_run` webhooks or `/actions/runs` API queries):
1. **Target Branch & Name Inspection:** The workflow name and head branch are evaluated. Workflows named `deploy*`, `release*`, or running on `production`/`release` branches with production deployment jobs are ingested.
2. **Execution Status Mapping:**
   - GitHub `conclusion == "success"` $\rightarrow$ `status = "SUCCESS"`
   - GitHub `conclusion in ("failure", "timed_out")` $\rightarrow$ `status = "FAILED"`
   - GitHub `conclusion in ("cancelled", "skipped")` $\rightarrow$ `status = "CANCELLED"`
3. **External Deployment ID Idempotency:** The external GitHub workflow run ID or deployment ID is stored in `external_deployment_id`. If an event with the same `external_deployment_id` is re-received, the existing record is updated in place, preventing duplicate count inflation.

---

### 4. Lead Time Traceability

Upon recording a deployment:
1. The pipeline extracts `commit_sha`.
2. It queries `commits` matching the SHA and repository ID:
   ```python
   commit = await db.scalar(
       select(Commit).where(
           Commit.repository_id == repository_id,
           Commit.sha == commit_sha
       )
   )
   ```
3. If found, lead time is computed:
   $$\text{lead\_time\_seconds} = \max(0, (T_{\text{deployed}} - T_{\text{authored}}).\text{total\_seconds}())$$
4. The resolved duration is saved directly to `deployments.lead_time_seconds` for immediate indexable access.

---

### 5. Multi-Tenant Isolation

All deployment ingestion enforces tenant boundaries:
- The `organization_id` is validated against the authenticated user's organization.
- Repositories are queried with `Repository.organization_id == organization_id`.
- Foreign key constraints ensure deployments cannot be orphaned or cross-pollinated between tenants.

---

### 6. Background Synchronization (Celery)

Asynchronous bulk synchronization of historical deployments is handled via Celery:

```python
@shared_task(bind=True, max_retries=3)
def sync_deployments_task(self, organization_id_str: str, repository_id_str: str | None = None):
    """Asynchronously sync deployments from GitHub API for an organization."""
    # Executes deployment_service.sync_repository_deployments()
    # Captures missing deployment history and calculates lead times
```

---

### 7. Ingestion API Endpoints

- `GET /api/v1/deployments`: Lists recorded deployments with filters for repository, environment, status, and pagination.
- `POST /api/v1/deployments`: Ingests an ad-hoc deployment record from custom internal deployment tooling.
- `POST /api/v1/deployments/sync`: Triggers asynchronous Celery synchronization for all connected repositories.
