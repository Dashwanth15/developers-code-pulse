# Operations Runbook & Incident Response Guide — Developers Code Pulse (DCP)

## 1. Overview & Operational Responsibilities

This runbook provides Site Reliability Engineers (SREs), DevOps Engineers, and on-call responders with standard operating procedures (SOPs) for routine maintenance, incident triage, disaster recovery, and diagnostic commands for Developers Code Pulse (DCP).

---

## 2. Common Diagnostic Commands

### Container Health & Resource Inspection
```bash
# View active container status, ports, and healthcheck states
docker compose -f docker-compose.prod.yml ps

# View live CPU, Memory, and Network I/O metrics
docker stats --no-stream

# View real-time aggregated logs across all services
docker compose -f docker-compose.prod.yml logs -f --tail=100

# View specific service logs (e.g. backend API or Celery worker)
docker compose -f docker-compose.prod.yml logs -f --tail=200 dcp-api
docker compose -f docker-compose.prod.yml logs -f --tail=200 dcp-worker
```

### Database & Cache Diagnostics
```bash
# Execute query inside PostgreSQL container
docker compose -f docker-compose.prod.yml exec dcp-db psql -U dcp_user -d dcp_db -c "SELECT count(*) FROM reports;"

# Check active database connections and locks
docker compose -f docker-compose.prod.yml exec dcp-db psql -U dcp_user -d dcp_db -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Check Redis memory usage and connected clients
docker compose -f docker-compose.prod.yml exec dcp-redis redis-cli info memory
docker compose -f docker-compose.prod.yml exec dcp-redis redis-cli info clients
```

### Celery Worker & Queue Inspection
```bash
# Execute Celery health inspection script
docker compose -f docker-compose.prod.yml exec dcp-worker /app/infrastructure/scripts/celery_health.sh

# Query Celery active tasks
docker compose -f docker-compose.prod.yml exec dcp-worker celery -A app.workers.celery_app inspect active

# Query Celery registered queues
docker compose -f docker-compose.prod.yml exec dcp-worker celery -A app.workers.celery_app inspect active_queues
```

---

## 3. Incident Response Playbooks

### Playbook 1: Elevated HTTP 5xx Error Rate
- **Trigger**: Prometheus alert `ElevatedErrorRate` fires ($5\text{xx} > 5\%$).
- **Triage Steps**:
  1. Inspect API logs:
     ```bash
     docker compose -f docker-compose.prod.yml logs --tail=50 dcp-api | grep "unhandled_server_error"
     ```
  2. Verify database connection pool health:
     ```bash
     curl -s http://localhost/api/v1/ready | jq .
     ```
  3. If database pool is exhausted, restart API workers to refresh connections:
     ```bash
     docker compose -f docker-compose.prod.yml restart dcp-api
     ```

### Playbook 2: Celery Worker Stalled / Task Backlog
- **Trigger**: Tasks queue up without completion, or `RepeatedTaskFailures` alert fires.
- **Triage Steps**:
  1. Check Redis connectivity and memory capacity:
     ```bash
     docker compose -f docker-compose.prod.yml exec dcp-redis redis-cli ping
     ```
  2. Inspect worker process states:
     ```bash
     docker compose -f docker-compose.prod.yml exec dcp-worker celery -A app.workers.celery_app inspect ping
     ```
  3. Restart worker containers safely (graceful shutdown allows active tasks 30s to finish):
     ```bash
     docker compose -f docker-compose.prod.yml restart dcp-worker
     ```

### Playbook 3: Database Disk Space Saturation
- **Trigger**: Disk usage on `/var/lib/postgresql/data` exceeds 85%.
- **Triage Steps**:
  1. Inspect volume sizes:
     ```bash
     docker system df -v
     ```
  2. Prune old backup files:
     ```bash
     find /backups -type f -name "*.sql.gz*" -mtime +7 -delete
     ```
  3. Clean Docker build caches:
     ```bash
     docker builder prune -f
     ```

---

## 4. Routine Maintenance Procedures

### Weekly Maintenance
- Review Prometheus alert history and latency quantiles (ensure p95 $< 1.0\text{s}$).
- Verify database backup files exist and checksums validate cleanly.
- Review error logs for unhandled client exceptions.

### Monthly Maintenance
- Perform test database restoration on a staging instance using `infrastructure/scripts/restore_db.sh`.
- Review dependency security updates (`npm audit` and `pip audit`).
- Clean up unused container images (`docker image prune -a --filter "until=720h"`).

---

## 5. Known Production Limitations & Edge Cases

1. **Celery Beat Singleton**: Exactly one instance of `dcp-beat` must be running at any time. Running multiple beat instances concurrently will result in duplicate scheduled report generation.
2. **Ephemeral File Storage in Container Mode**: If running across multiple container hosts without a distributed volume (NFS/EFS), use an object store abstraction (e.g. AWS S3 / Cloud Storage) for persistent report storage.
3. **Database Concurrency Cap**: PostgreSQL 16 default `max_connections` is set to $100$. With 4 API workers and 4 Celery workers, connection pool settings must not exceed $80$ aggregate connections.
