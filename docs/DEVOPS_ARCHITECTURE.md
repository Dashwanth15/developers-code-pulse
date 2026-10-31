# DEVELOPERS CODE PULSE (DCP)
## DevOps, CI/CD, and Observability Architecture

---

## 1. Containerization & Docker Architecture

Developers Code Pulse enforces container parity between local development and production environments. All containers run as unprivileged non-root users and utilize multi-stage builds to minimize image surface area.

### 1.1 Frontend Container Design (`frontend/Dockerfile`)
```dockerfile
# Stage 1: Build static assets
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production Nginx runner
FROM nginxinc/nginx-unprivileged:alpine-slim
COPY --from=builder /app/dist /usr/share/nginx/html
COPY infrastructure/docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8080/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
```

### 1.2 Backend API & Worker Container Design (`backend/Dockerfile`)
```dockerfile
# Stage 1: Dependency builder
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Minimal runtime image
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 10001 dcpuser
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY . .
USER dcpuser
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 2. Local Docker Compose Architecture

The `docker-compose.yml` orchestrates the local development and testing environment:

```yaml
version: "3.9"

services:
  dcp-db:
    image: postgres:16-alpine
    container_name: dcp-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-dcp_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dcp_password}
      POSTGRES_DB: ${POSTGRES_DB:-dcp_db}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dcp_user -d dcp_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  dcp-redis:
    image: redis:7.2-alpine
    container_name: dcp-redis
    command: ["redis-server", "--appendonly", "yes"]
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  dcp-api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: dcp-api
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://dcp_user:dcp_password@dcp-db:5432/dcp_db
      - REDIS_URL=redis://dcp-redis:6379/0
      - ENVIRONMENT=development
    ports:
      - "8000:8000"
    depends_on:
      dcp-db:
        condition: service_healthy
      dcp-redis:
        condition: service_healthy

  dcp-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: dcp-worker
    command: ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "-Q", "webhooks,repo_sync,analytics_calc,report_gen"]
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://dcp_user:dcp_password@dcp-db:5432/dcp_db
      - REDIS_URL=redis://dcp-redis:6379/0
    depends_on:
      dcp-db:
        condition: service_healthy
      dcp-redis:
        condition: service_healthy

  dcp-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: dcp-beat
    command: ["celery", "-A", "app.workers.celery_app", "beat", "--loglevel=info"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://dcp_user:dcp_password@dcp-db:5432/dcp_db
      - REDIS_URL=redis://dcp-redis:6379/0
    depends_on:
      dcp-redis:
        condition: service_healthy

  dcp-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: dcp-frontend
    ports:
      - "3000:8080"
    depends_on:
      - dcp-api

  dcp-prometheus:
    image: prom/prometheus:v2.51.0
    container_name: dcp-prometheus
    volumes:
      - ./infrastructure/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  dcp-grafana:
    image: grafana/grafana:10.4.0
    container_name: dcp-grafana
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - dcp-prometheus

volumes:
  postgres_data:
  redis_data:
  grafana_data:
```

---

## 3. GitHub Actions CI/CD Pipeline Architecture

```mermaid
graph TD
    Trigger[Code Push or Pull Request] --> CI_Workflow[Workflow: ci.yml]
    
    subgraph CI_Pipeline["CI Verification Pipeline"]
        BE_Lint[Backend Lint: Ruff]
        BE_Type[Backend Type Check: Mypy]
        BE_Test[Backend Unit & Integration Tests: Pytest]
        FE_Lint[Frontend Lint: ESLint & Prettier]
        FE_Type[Frontend Type Check: tsc]
        FE_Test[Frontend Tests: Vitest]
        FE_Build[Frontend Build Check: Vite]
    end
    
    CI_Workflow --> BE_Lint & BE_Type & BE_Test & FE_Lint & FE_Type & FE_Test & FE_Build

    subgraph Security_Pipeline["Workflow: security.yml"]
        Gitleaks[Secret Scanning: Gitleaks]
        Trivy_FS[Static Vuln Scan: Trivy]
        Pip_Audit[Python Dependency Audit: pip-audit]
        Npm_Audit[Node Dependency Audit: npm audit]
    end
    
    Trigger --> Security_Pipeline

    BE_Test & FE_Build --> Release_Check{Merged to 'main'?}
    
    subgraph CD_Pipeline["Workflow: docker-build.yml & deploy.yml"]
        Docker_Build[Build Multi-arch Images]
        Trivy_Image[Container Vulnerability Scan]
        Deploy_Staging[Deploy to Staging Environment]
        E2E_Test[Run Smoke Tests & Playwright E2E]
        Deploy_Prod[Zero-downtime Rolling Deploy to Production]
        Post_Health[Verify /ready and /health Probes]
    end

    Release_Check -->|Yes| Docker_Build
    Docker_Build --> Trivy_Image --> Deploy_Staging --> E2E_Test --> Deploy_Prod --> Post_Health
```

---

## 4. GitHub Actions Workflows Inventory

All workflows pin external actions by **full commit SHA** rather than mutable tags for supply chain security.

### 4.1 `.github/workflows/ci.yml`
- **Triggers:** `push: [main, develop]`, `pull_request: [main, develop]`.
- **Jobs:**
  - `backend-ci`: Ruff lint/format check, mypy type verification, pytest with code coverage tracking.
  - `frontend-ci`: ESLint, Prettier, TypeScript strict check, Vitest suite, Vite production build validation.

### 4.2 `.github/workflows/docker-build.yml`
- **Triggers:** `push: tags: ['v*']` or manual workflow dispatch.
- **Jobs:** Builds production container images for `dcp-api` and `dcp-frontend`, runs Trivy image vulnerability scanners, and securely pushes images to the GitHub Container Registry (`ghcr.io`).

### 4.3 `.github/workflows/deploy.yml`
- **Triggers:** Successful completion of `docker-build.yml` on release branches.
- **Jobs:** Executes blue/green or rolling zero-downtime updates, runs database migrations (`alembic upgrade head`), verifies `/ready` and `/health` endpoints, and rolls back automatically if health checks fail.

### 4.4 `.github/workflows/security.yml`
- **Triggers:** Scheduled weekly cron + PRs targeting `main`.
- **Jobs:**
  - `gitleaks`: Scans codebase for committed credentials or private keys.
  - `pip-audit`: Audits Python dependencies against known CVEs.
  - `npm-audit`: Audits Node.js packages.
  - `codeql`: Deep semantic code analysis.

### 4.5 `.github/workflows/metric-sync.yml`
- **Triggers:** Scheduled cron (`0 */6 * * *`) or workflow dispatch.
- **Jobs:** Invokes the secure DCP reconciliation endpoint (`POST /api/v1/repositories/{id}/sync`) using an authorized service token to reconcile any missed webhook deliveries.

### 4.6 `.github/workflows/weekly-report.yml`
- **Triggers:** Scheduled cron (`0 6 * * 1` - Every Monday at 06:00 UTC).
- **Jobs:** Calls DCP report trigger API to compile weekly PDF/CSV retrospectives and dispatches notification summaries to engineering managers.

### 4.7 `.github/workflows/deployment-tracking.yml`
- **Triggers:** `workflow_call` or `deployment_status`.
- **Jobs:** Emits standardized deployment events to the DCP API (`POST /api/v1/analytics/dora/deployments`) with commit SHA, environment, and deployment duration to feed DORA metrics.

---

## 5. Monitoring, Observability, and Metrics

### 5.1 Prometheus Metrics Scraped via `/api/v1/metrics`
- `dcp_http_requests_total{method, endpoint, status_code}`: Request counter.
- `dcp_http_request_duration_seconds{endpoint}`: Request latency histogram.
- `dcp_webhook_events_received_total{event_type, status}`: Ingestion throughput.
- `dcp_celery_queue_depth{queue_name}`: Pending background task backlog.
- `dcp_db_connection_pool_status{status}`: Active/idle database connections.

### 5.2 Pre-Configured Grafana Dashboards
1. **API Gateway & HTTP Health:** Request rate (RPS), error rates (4xx/5xx), P95/P99 latency.
2. **Webhook & Event Ingestion Pipeline:** Webhook arrival velocity, delivery verification failures, queue wait times.
3. **Celery Worker Fleet:** Task execution durations, worker memory utilization, retry frequencies.
4. **PostgreSQL & Redis Health:** Connection pool saturation, slow query logs (>250ms), cache hit ratios.
