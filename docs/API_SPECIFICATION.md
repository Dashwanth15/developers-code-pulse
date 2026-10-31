# DEVELOPERS CODE PULSE (DCP)
## REST API Specification & Contract

---

## 1. Global API Conventions & Standards

Developers Code Pulse exposes a uniform RESTful API rooted at:
```
https://api.developerscodepulse.com/api/v1
```

### 1.1 Content Types & Encoding
- All request bodies must have `Content-Type: application/json` (except multipart file uploads).
- All response bodies use `Content-Type: application/json; charset=utf-8`.
- Timestamps in requests and responses use strict ISO 8601 UTC format: `YYYY-MM-DDTHH:MM:SS.sssZ`.

### 1.2 Authentication & Authorization Headers
Protected endpoints require an `Authorization` header containing a valid Bearer JWT:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
Multi-tenant requests can optionally include an explicit organization context header:
```http
X-Organization-ID: 7a82ec90-21a4-4a41-8eb1-744018285df6
```
If omitted, the user's default/primary organization is resolved by backend middleware.

### 1.3 Uniform Error Envelope (RFC 7807 Compatible)
All non-2xx responses return a standardized structured JSON error object:
```json
{
  "type": "https://developerscodepulse.com/errors/RESOURCE_NOT_FOUND",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Repository with ID '9b43e8a5-d05b-4322-a720-3da7d7211a7a' does not exist in this organization.",
  "instance": "/api/v1/repositories/9b43e8a5-d05b-4322-a720-3da7d7211a7a",
  "code": "REPOSITORY_NOT_FOUND",
  "errors": [],
  "timestamp": "2026-10-31T14:45:00.000Z",
  "trace_id": "req_88a4e321bf"
}
```

### 1.4 Uniform Pagination Envelope
Endpoints returning collections support cursor-based or limit-offset pagination:
```json
{
  "data": [ ... ],
  "pagination": {
    "total_items": 154,
    "limit": 20,
    "offset": 0,
    "has_next": true,
    "has_prev": false,
    "next_cursor": "eyJpZCI6IC..."
  }
}
```

### 1.5 Asynchronous Long-Running Operations (202 Accepted)
Operations taking >1 second (such as historical repository backfill or PDF generation) return `202 Accepted` with a job tracker envelope:
```json
{
  "job_id": "job_c031d457-3932-4467-b50a-f0fbfdfa04c1",
  "status": "QUEUED",
  "poll_url": "/api/v1/jobs/job_c031d457-3932-4467-b50a-f0fbfdfa04c1",
  "estimated_duration_seconds": 45,
  "created_at": "2026-10-31T14:45:00.000Z"
}
```

---

## 2. Complete API Endpoint Inventory

| Category | HTTP Verb | Endpoint Path | Description | Access Role |
| :--- | :--- | :--- | :--- | :--- |
| **System** | `GET` | `/health` | Liveness probe (container health) | Public |
| **System** | `GET` | `/ready` | Readiness probe (DB & Redis connection check) | Public |
| **System** | `GET` | `/metrics` | Prometheus metrics scrape endpoint | Internal / Admin |
| **Auth** | `POST` | `/auth/register` | Register new user & bootstrap organization | Public |
| **Auth** | `POST` | `/auth/login` | Email/password login -> returns Access + Refresh token | Public |
| **Auth** | `POST` | `/auth/refresh` | Refresh expired access token | Public |
| **Auth** | `POST` | `/auth/logout` | Revoke current refresh token | Authenticated |
| **Auth** | `GET` | `/auth/me` | Fetch authenticated user profile & memberships | Authenticated |
| **Auth** | `POST` | `/auth/password-reset/request` | Initiate password reset email | Public |
| **Auth** | `POST` | `/auth/password-reset/confirm` | Reset password using reset token | Public |
| **Organizations** | `GET` | `/organizations` | List organizations user belongs to | Authenticated |
| **Organizations** | `POST` | `/organizations` | Create a new organization | Authenticated |
| **Organizations** | `GET` | `/organizations/{id}` | Get organization details | Member |
| **Organizations** | `PATCH` | `/organizations/{id}` | Update organization details | Admin |
| **Organizations** | `GET` | `/organizations/{id}/members` | List members & roles | Member |
| **Organizations** | `POST` | `/organizations/{id}/members` | Invite new member to organization | Admin |
| **Organizations** | `PATCH` | `/organizations/{id}/members/{user_id}` | Change member role | Owner |
| **Organizations** | `DELETE` | `/organizations/{id}/members/{user_id}` | Remove member from organization | Owner |
| **GitHub** | `GET` | `/integrations/github/install` | Get GitHub App installation redirect URL | Admin |
| **GitHub** | `GET` | `/integrations/github/callback` | OAuth / installation callback handler | Public |
| **GitHub** | `POST` | `/integrations/github/webhooks` | Webhook ingestion from GitHub (HMAC verified) | Public (Signed) |
| **GitHub** | `GET` | `/integrations/github/installations`| List active GitHub installations | Member |
| **GitHub** | `DELETE` | `/integrations/github/installations/{id}` | Disconnect GitHub installation | Admin |
| **GitHub** | `GET` | `/integrations/github/repositories` | Discover repos authorized via GitHub App | Member |
| **Repositories** | `GET` | `/repositories` | List monitored repositories in organization | Member |
| **Repositories** | `POST` | `/repositories` | Connect/enable monitoring for a repository | Admin |
| **Repositories** | `GET` | `/repositories/{id}` | Get repository metadata & sync status | Member |
| **Repositories** | `PATCH` | `/repositories/{id}` | Toggle monitoring or change default branch | Admin |
| **Repositories** | `GET` | `/repositories/{id}/activity` | Fetch recent raw activity timeline | Member |
| **Repositories** | `POST` | `/repositories/{id}/sync` | Trigger asynchronous backfill / sync | Admin |
| **Commits** | `GET` | `/repositories/{id}/commits` | List commits for a repository (paginated) | Member |
| **Commits** | `GET` | `/analytics/commits` | Aggregate commit cadence, frequency, trends | Member |
| **Pull Requests** | `GET` | `/pull-requests` | List pull requests with lifecycle metrics | Member |
| **Pull Requests** | `GET` | `/pull-requests/{id}` | Detailed PR view with review timeline | Member |
| **Pull Requests** | `GET` | `/analytics/pull-requests` | PR volume, merge rate, cycle time distribution | Member |
| **Reviews** | `GET` | `/analytics/reviews` | Review turnaround, TTFR percentiles | Member |
| **Reviews** | `GET` | `/analytics/reviews/workload` | Review distribution & reviewer workload index | Member |
| **Reviews** | `GET` | `/analytics/reviews/pending` | Real-time queue of PRs awaiting review | Member |
| **Bottlenecks** | `GET` | `/bottlenecks` | List active & historical workflow bottlenecks | Member |
| **Bottlenecks** | `GET` | `/bottlenecks/{id}` | Get bottleneck details with metric evidence | Member |
| **Bottlenecks** | `PATCH` | `/bottlenecks/{id}` | Acknowledge or manually resolve bottleneck | Admin |
| **Team Analytics**| `GET` | `/analytics/team` | Team-level collaboration and throughput trends | Member |
| **Team Analytics**| `GET` | `/analytics/repositories` | Cross-repository comparative analytics | Member |
| **DORA** | `GET` | `/analytics/dora` | 4 DORA metrics summary (with data completeness flags) | Member |
| **DORA** | `POST` | `/analytics/dora/deployments`| Record external deployment event | Admin |
| **DORA** | `POST` | `/analytics/dora/incidents` | Record production incident / outage | Admin |
| **Reports** | `GET` | `/reports` | List generated engineering reports | Member |
| **Reports** | `POST` | `/reports` | Request new report generation (PDF/CSV/JSON) | Member |
| **Reports** | `GET` | `/reports/{id}` | Check report generation status | Member |
| **Reports** | `GET` | `/reports/{id}/download` | Download compiled report file | Member |
| **Insights (AI)** | `GET` | `/insights` | Fetch latest AI engineering workflow summaries | Member |
| **Insights (AI)** | `POST` | `/insights/generate` | Trigger on-demand grounded AI analysis | Member |
| **Notifications** | `GET` | `/notifications` | List user in-app notifications | Authenticated |
| **Notifications** | `PATCH` | `/notifications/{id}/read` | Mark notification as read | Authenticated |
| **Audit Logs** | `GET` | `/audit-logs` | Organization audit trail of sensitive actions | Admin |

---

## 3. Detailed Request / Response Contracts (Key Endpoints)

### 3.1 Webhook Ingestion (`POST /integrations/github/webhooks`)
- **Headers Required:**
  - `X-GitHub-Event`: e.g., `pull_request`
  - `X-GitHub-Delivery`: UUID string (e.g., `72d31630-f38b-11ea-94e8-8a8f10842e47`)
  - `X-Hub-Signature-256`: `sha256=...` (HMAC SHA-256 using configured secret)
- **Status Codes:**
  - `202 Accepted`: Payload verified and queued for async processing.
  - `200 OK`: Payload recognized as duplicate `X-GitHub-Delivery` and skipped.
  - `401 Unauthorized`: Missing or invalid `X-Hub-Signature-256`.
  - `400 Bad Request`: Malformed JSON or unparseable event.

### 3.2 Pull Request Analytics (`GET /analytics/pull-requests`)
- **Query Parameters:**
  - `organization_id` (UUID, optional if header provided)
  - `repository_ids` (comma-separated UUIDs, optional)
  - `time_window` (Enum: `7d`, `14d`, `30d`, `90d`, default `30d`)
  - `start_date` / `end_date` (ISO dates, optional custom window)
- **Response `200 OK`:**
```json
{
  "time_window": "30d",
  "start_date": "2026-10-01",
  "end_date": "2026-10-31",
  "summary": {
    "total_prs_opened": 84,
    "total_prs_merged": 76,
    "total_prs_closed_unmerged": 5,
    "currently_open_prs": 12,
    "merge_rate_percentage": 93.8,
    "median_merge_time_hours": 18.5,
    "p75_merge_time_hours": 36.2,
    "median_cycle_time_hours": 24.1
  },
  "cadence_trend": [
    {
      "date": "2026-10-01",
      "opened": 4,
      "merged": 3,
      "closed": 0
    }
  ],
  "size_distribution": {
    "small_under_100_lines": { "count": 45, "avg_merge_hours": 8.2 },
    "medium_100_to_500_lines": { "count": 28, "avg_merge_hours": 22.4 },
    "large_over_500_lines": { "count": 11, "avg_merge_hours": 64.8 }
  }
}
```

### 3.3 Review Intelligence (`GET /analytics/reviews`)
- **Query Parameters:**
  - `repository_ids` (optional)
  - `time_window` (default `30d`)
- **Response `200 OK`:**
```json
{
  "time_window": "30d",
  "metrics": {
    "time_to_first_review": {
      "median_hours": 3.8,
      "p75_hours": 12.1,
      "p90_hours": 28.5,
      "benchmark_comparison": "HEALTHY"
    },
    "approval_turnaround": {
      "median_hours": 14.2,
      "p75_hours": 31.0
    },
    "average_review_rounds": 1.4,
    "review_coverage_rate": 96.4
  },
  "turnaround_histogram": [
    { "range": "< 2h", "count": 32 },
    { "range": "2h - 6h", "count": 25 },
    { "range": "6h - 24h", "count": 18 },
    { "range": "24h - 48h", "count": 6 },
    { "range": "> 48h", "count": 3 }
  ],
  "pending_queue_count": 7
}
```

### 3.4 Bottleneck Detection (`GET /bottlenecks`)
- **Query Parameters:**
  - `status` (Enum: `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`, default `ACTIVE`)
  - `severity` (Enum: `INFO`, `WARNING`, `CRITICAL`, optional)
- **Response `200 OK`:**
```json
{
  "bottlenecks": [
    {
      "id": "e4f8a3d1-447a-4286-9a28-1f63bb472ad3",
      "repository": {
        "id": "9b43e8a5-d05b-4322-a720-3da7d7211a7a",
        "name": "dcp-api"
      },
      "pull_request": {
        "id": "fa2b39c0-9981-4da6-953e-e67d26bb4377",
        "number": 142,
        "title": "feat: async PDF export pipeline"
      },
      "bottleneck_type": "DELAYED_FIRST_REVIEW",
      "severity": "WARNING",
      "status": "ACTIVE",
      "metric_evidence": {
        "hours_waiting": 54.5,
        "threshold_hours": 24.0,
        "requested_reviewers": ["sarah-dev"]
      },
      "explanation": "PR #142 has been awaiting its first review for 54.5 hours, exceeding the team threshold of 24 hours.",
      "recommended_action": "Reassign review or request a secondary reviewer from the backend group to unblock progress.",
      "detected_at": "2026-10-31T09:15:00.000Z",
      "resolved_at": null
    }
  ]
}
```

### 3.5 DORA Metrics (`GET /analytics/dora`)
- **Query Parameters:**
  - `time_window` (Enum: `30d`, `90d`)
- **Response `200 OK`:**
```json
{
  "time_window": "30d",
  "deployment_frequency": {
    "status": "AVAILABLE",
    "value_per_day": 1.4,
    "total_deployments": 42,
    "performance_tier": "HIGH"
  },
  "lead_time_for_changes": {
    "status": "AVAILABLE",
    "median_hours": 28.5,
    "performance_tier": "MEDIUM"
  },
  "change_failure_rate": {
    "status": "AVAILABLE",
    "percentage": 4.8,
    "failed_deployments": 2,
    "total_deployments": 42,
    "performance_tier": "ELITE"
  },
  "mean_time_to_restore": {
    "status": "INSUFFICIENT_DATA",
    "reason": "No production incident records linked to deployments in this reporting window.",
    "median_hours": null,
    "performance_tier": "UNKNOWN"
  }
}
```
*(Notice: DORA returns `INSUFFICIENT_DATA` honestly when incident tracking is absent, never fabricating fake MTTR).*

### 3.6 AI Engineering Insights (`POST /insights/generate`)
- **Request Body:**
```json
{
  "organization_id": "7a82ec90-21a4-4a41-8eb1-744018285df6",
  "repository_ids": ["9b43e8a5-d05b-4322-a720-3da7d7211a7a"],
  "time_window": "7d"
}
```
- **Response `200 OK`:**
```json
{
  "insight_id": "ins_5510f2b3-57a9-4a0b-bc17-1049fa982bd0",
  "category": "WEEKLY_SUMMARY",
  "reporting_period": {
    "start_date": "2026-10-24",
    "end_date": "2026-10-31"
  },
  "summary": "Engineering activity remained high with 22 PRs merged this week. However, Time to First Review in 'dcp-api' jumped from 3.2 hours to 9.8 hours. Two large PRs (>800 lines) accounted for 60% of the review turnaround delay.",
  "grounded_metrics": {
    "prs_merged": 22,
    "prior_ttfr_median_hours": 3.2,
    "current_ttfr_median_hours": 9.8,
    "oversized_prs_count": 2
  },
  "actionable_recommendations": [
    "Decompose PRs exceeding 500 lines into incremental sub-tasks before requesting team reviews.",
    "Review the 3 PRs currently in the pending review queue to restore turnaround under 4 hours."
  ],
  "created_at": "2026-10-31T14:45:00.000Z"
}
```
