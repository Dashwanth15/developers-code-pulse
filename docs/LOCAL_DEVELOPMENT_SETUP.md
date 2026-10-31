# DEVELOPERS CODE PULSE (DCP)
## Local Development Setup & Operations Guide

---

## 1. Prerequisites

Before setting up Developers Code Pulse locally, ensure you have installed:
- **Python 3.12+** (with `pip` and `venv`)
- **Node.js 20+** and **npm 10+**
- **Docker Engine 24+** and **Docker Compose v2.20+**
- **Git**

---

## 2. Environment Configuration

1. Clone the repository and navigate to the project root:
   ```bash
   cd developers-code-pulse
   ```

2. Copy the template environment configuration file:
   ```bash
   cp .env.example .env
   ```

3. Review the defaults in `.env`:
   - `ENVIRONMENT=development`
   - `DEBUG=true`
   - `DATABASE_URL=postgresql+asyncpg://dcp_user:dcp_password@localhost:5432/dcp_db`
   - `REDIS_URL=redis://localhost:6379/0`
   - `CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]`

---

## 3. Starting the Full Stack with Docker Compose

The recommended and simplest way to run the entire Developers Code Pulse stack locally is with Docker Compose:

```bash
docker compose up --build
```

### Services Launched:
| Container Name | Service | Internal Port | Exposed Port | Role |
| :--- | :--- | :--- | :--- | :--- |
| `dcp-frontend` | React SPA + Nginx | 8080 | 3000 | Web UI Dashboard |
| `dcp-api` | FastAPI Backend | 8000 | 8000 | REST API Gateway |
| `dcp-db` | PostgreSQL 16 | 5432 | 5432 | Primary Relational DB |
| `dcp-redis` | Redis 7.2 | 6379 | 6379 | Broker & Cache |
| `dcp-worker` | Celery Worker | N/A | N/A | Background Task Processor |
| `dcp-beat` | Celery Beat | N/A | N/A | Periodic Scheduler |

### Stopping Services:
```bash
docker compose down
# To also remove persistent volumes:
docker compose down -v
```

---

## 4. Running Backend Standalone (Without Docker)

If you prefer developing the FastAPI backend locally:

1. Create and activate a Python virtual environment:
   ```bash
   # On macOS / Linux
   python3 -m venv backend/.venv
   source backend/.venv/bin/activate

   # On Windows (PowerShell)
   py -m venv backend/.venv
   .\backend\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

3. Start PostgreSQL and Redis (e.g., via Docker):
   ```bash
   docker compose up -d dcp-db dcp-redis
   ```

4. Run the FastAPI development server:
   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Run Celery background worker (separate terminal):
   ```bash
   cd backend
   celery -A app.workers.celery_app worker --loglevel=info -Q webhooks,repo_sync,analytics_calc,report_gen
   ```

---

## 5. Running Frontend Standalone (Without Docker)

1. Navigate to `frontend/`:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start Vite development server:
   ```bash
   npm run dev
   ```
   The dashboard will be available at `http://localhost:3000`.

---

## 6. Running Test Suites

### Backend Tests (Pytest)
```bash
# From repository root or backend/
cd backend
pytest tests/ -v
# With code coverage report:
pytest tests/ --cov=app --cov-report=term-missing
```

### Backend Linting (Ruff)
```bash
# Check formatting and style
ruff check app/ tests/
# Check format without modifying
ruff format --check app/ tests/
```

### Frontend Tests (Vitest)
```bash
cd frontend
npm run test
```

### Frontend Typecheck & Linting
```bash
cd frontend
npx tsc --noEmit
npm run lint
```

### Frontend Production Build Validation
```bash
cd frontend
npm run build
```

---

## 7. Verifying API Health Endpoints

Once `dcp-api` is running, verify:

1. **Liveness Probe:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
   Expected response (`200 OK`):
   ```json
   {
     "status": "healthy",
     "app_name": "Developers Code Pulse",
     "version": "0.1.0",
     "timestamp": "2026-10-31T15:00:00.000Z"
   }
   ```

2. **Readiness Probe:**
   ```bash
   curl http://localhost:8000/api/v1/ready
   ```
   Expected response (`200 OK` when Postgres and Redis are up):
   ```json
   {
     "status": "ready",
     "dependencies": {
       "postgres": { "status": "healthy", "error": null },
       "redis": { "status": "healthy", "error": null }
     },
     "timestamp": "2026-10-31T15:00:00.000Z"
   }
   ```

3. **Interactive OpenAPI Documentation:**
   Open `http://localhost:8000/api/v1/docs` in your browser.
