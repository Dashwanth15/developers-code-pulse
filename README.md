# Developers Code Pulse (DCP)

> **Official Tagline:** *"Understand your team's workflow. Build better software. Ship faster together."*  
> **Repository:** `developers-code-pulse` | **Backend Service:** `dcp-api` | **Database:** `dcp_db` | **Compose Project:** `developers-code-pulse`  
> **Status:** Phase 1 Complete (Project Foundation & Core Infrastructure)

---

## 1. Product Vision

**Developers Code Pulse (DCP)** is an enterprise-grade Developer Productivity and Team Engineering Intelligence platform. In modern engineering organizations, delays in code reviews, unclear handoffs, unbalanced workloads, and delivery friction reduce team velocity and developer experience.

DCP connects directly to GitHub to ingest, normalize, and analyze real-time development activity. It transforms raw Git events into actionable engineering workflow intelligence—without ever devolving into employee surveillance or simplistic individual ranking.

### What DCP Answers:
- How active is our development workflow across repositories?
- How many pull requests are created, merged, or stalling?
- How long does a PR wait for its first peer review?
- Where are the engineering bottlenecks and approval delays?
- Are review responsibilities distributed reasonably across team members?
- Is team delivery performance and cycle time improving?
- What are our true DORA metrics (Deployment Frequency, Lead Time for Changes, CFR, MTTR)?

---

## 2. Anti-Surveillance Manifesto

Developers Code Pulse enforces **team-level workflow optimization over individual developer surveillance**:
- **No Individual Productivity Scorecards:** DCP never ranks developers or grades performance based on commits, lines of code, or review volume.
- **Systemic Root Causes:** Bottlenecks are analyzed as workflow and process friction points, not personal failings.
- **Reviewer Burnout Protection:** Reviewer workload indexes highlight review concentration to prevent key maintainers from becoming bottlenecks.
- **Transparent & Traceable:** All recommendations and bottleneck alerts cite the exact underlying metrics and observation timeframe.

---

## 3. Technology Stack

### Frontend
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Styling:** Vanilla Tailwind CSS with custom HSL design tokens & dark/light theme support
- **Icons:** Lucide Icons
- **Routing:** React Router v6
- **Server State Management:** TanStack Query (React Query v5)

### Backend
- **Framework:** FastAPI (Python 3.12 compatible)
- **Validation:** Pydantic v2 & Pydantic Settings
- **ORM & Database:** SQLAlchemy 2.0 (asyncio) + `asyncpg` + PostgreSQL 16
- **Database Migrations:** Alembic (async support)
- **Background Workers:** Celery 5.3 + Redis 7.2
- **Logging:** Structured JSON logging via `structlog`
- **Code Quality:** Ruff linter & formatter

### DevOps & Infrastructure
- **Containerization:** Multi-stage Dockerfiles (non-root unprivileged runners)
- **Local Orchestration:** Docker Compose (PostgreSQL, Redis, FastAPI, Celery worker, Celery beat, Frontend)
- **CI/CD:** GitHub Actions (`.github/workflows/ci.yml`)
- **Observability:** Prometheus metrics (`/metrics`) and Grafana integration

---

## 4. Quickstart Guide

### Option A: Running with Docker Compose (Recommended)

1. Clone the repository and configure the environment:
   ```bash
   cp .env.example .env
   ```

2. Start the entire platform:
   ```bash
   docker compose up --build
   ```

3. Access the platform:
   - **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
   - **Backend API Gateway:** [http://localhost:8000](http://localhost:8000)
   - **Interactive API Documentation:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - **API Liveness Probe:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
   - **API Readiness Probe:** [http://localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready)

### Option B: Local Standalone Development

For detailed instructions on running Python and Node.js without Docker, see [docs/LOCAL_DEVELOPMENT_SETUP.md](docs/LOCAL_DEVELOPMENT_SETUP.md).

---

## 5. Project Directory Structure

```
developers-code-pulse/
├── backend/                  # FastAPI Application & Celery Workers
│   ├── app/
│   │   ├── api/v1/           # API Endpoints (Health, Auth, Analytics)
│   │   ├── core/             # Configuration, Logging, Exceptions
│   │   ├── database/         # Async SQLAlchemy Engine & Session
│   │   ├── models/           # Declarative Models & Base
│   │   ├── schemas/          # Pydantic Schemas
│   │   ├── services/         # Domain Business Logic
│   │   ├── workers/          # Celery App & Task Definitions
│   │   └── main.py           # Application Entrypoint
│   ├── migrations/           # Alembic Database Migrations
│   ├── tests/                # Pytest Test Suites
│   ├── requirements.txt      # Python Dependencies
│   └── Dockerfile            # Multi-stage Backend Container
├── frontend/                 # React 18 Single Page Application
│   ├── src/
│   │   ├── components/       # Layout, Navigation & Common Components
│   │   ├── contexts/         # ThemeProvider & Global State
│   │   ├── pages/            # 11 Dashboard & Feature Pages
│   │   ├── test/             # Vitest & Testing Library Suites
│   │   ├── utils/            # Styling & Utility Helpers
│   │   ├── App.tsx           # React Router & Query Client
│   │   └── index.css         # Design Tokens (Light/Dark)
│   ├── package.json          # Node Dependencies & Scripts
│   ├── vite.config.ts        # Vite & Vitest Configuration
│   └── Dockerfile            # Multi-stage Frontend Container
├── docs/                     # Specifications & Architectural Documentation
├── .github/workflows/        # CI/CD Workflows
├── docker-compose.yml        # Orchestration Configuration
└── README.md                 # Project Overview
```

---

## 6. Development Roadmap

- [x] **Phase 0 — Architecture & Technical Planning** (10 master documents, ER diagram, threat models)
- [x] **Phase 1 — Project Foundation** (FastAPI, React SPA, Postgres, Redis, Celery, Docker, CI)
- [ ] **Phase 2 — Authentication & GitHub Integration** (GitHub App, webhooks, HMAC verification)
- [ ] **Phase 3 — Commit Intelligence** (Commit cadence, active contributors, heatmaps)
- [ ] **Phase 4 — Pull Request Analytics** (PR lifecycle, cycle time, merge time)
- [ ] **Phase 5 — Review Intelligence** (Time to First Review, approval turnaround, workload Gini index)
- [ ] **Phase 6 — Bottleneck Detection Engine** (Deterministic friction rules BOT-01 to BOT-06)
- [ ] **Phase 7 — Team Intelligence & DORA** (Team throughput, cross-review matrix, 4 DORA metrics)
- [ ] **Phase 8 — Reports & Grounded AI Insights** (PDF/CSV exports, weekly summaries)
- [ ] **Phase 9 — Production DevOps & Hardening** (Full E2E Playwright, security audits, release)

---

## 7. Documentation Index

- [Project Overview & Charter](docs/PROJECT_OVERVIEW.md)
- [System Architecture](docs/SYSTEM_ARCHITECTURE.md)
- [Database Schema & ER Diagram](docs/DATABASE_SCHEMA.md)
- [REST API Specification](docs/API_SPECIFICATION.md)
- [GitHub Integration Architecture](docs/GITHUB_INTEGRATION.md)
- [Analytics & Bottleneck Engine](docs/ANALYTICS_ENGINE.md)
- [DevOps & Observability](docs/DEVOPS_ARCHITECTURE.md)
- [Security Model & Threat Analysis](docs/SECURITY_MODEL.md)
- [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Testing Strategy](docs/TESTING_STRATEGY.md)
- [Local Development Setup](docs/LOCAL_DEVELOPMENT_SETUP.md)
- [Phase 1 Implementation Report](docs/PHASE_1_IMPLEMENTATION.md)
