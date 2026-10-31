# Database Backup, Disaster Recovery & Migration Reliability — Developers Code Pulse (DCP)

## 1. Overview & Recovery Objectives

Data integrity and disaster recovery are foundational to Developers Code Pulse (DCP). This document specifies backup schedules, retention policies, verification mechanisms, restore drills, and safe schema migration procedures.

### Key Operational Targets
- **Recovery Point Objective (RPO)**: $< 1 \text{ hour}$ (loss of at most 1 hour of telemetry data).
- **Recovery Time Objective (RTO)**: $< 15 \text{ minutes}$ (full service recovery from cold storage).

---

## 2. Automated Backup Strategy

### Daily Full Backups
Backups are orchestrated via `infrastructure/scripts/backup_db.sh`:
1. Executes `pg_dump` with high-compression gzip format (`gzip -9`).
2. Excludes ownership and privilege grants for portable multi-environment restoration.
3. Calculates a cryptographic SHA256 checksum stored in `.sql.gz.sha256`.
4. Enforces a 14-day rolling retention policy, automatically pruning stale archives.

### Recommended Cron Configuration
Add to the host's crontab (`crontab -e`):
```cron
# Execute daily full backup at 02:00 UTC
0 2 * * * /opt/dcp/infrastructure/scripts/backup_db.sh >> /var/log/dcp_backup.log 2>&1
```

---

## 3. Disaster Recovery & Restoration Procedure

To restore the database from a backup file:

```bash
# 1. Place backup archive on target host
scp user@backup-server:/backups/dcp_backup_dcp_db_20261031_020000Z.sql.gz /tmp/

# 2. Run the restore utility with verified checksum
chmod +x /opt/dcp/infrastructure/scripts/restore_db.sh
/opt/dcp/infrastructure/scripts/restore_db.sh /tmp/dcp_backup_dcp_db_20261031_020000Z.sql.gz
```

The script automatically:
1. Validates the SHA256 checksum to prevent restoring corrupted or truncated files.
2. Terminates active connection pools holding locks on the target database.
3. Streams decompressed SQL directly into PostgreSQL within a single atomic transaction (`--single-transaction`).
4. Aborts cleanly if any statement fails, leaving the existing database untouched.

---

## 4. Connection Pooling & Query Reliability

PostgreSQL connections are pooled asynchronously via SQLAlchemy and `asyncpg`:
- `DB_POOL_SIZE`: $15$ active connections per API worker.
- `DB_MAX_OVERFLOW`: $25$ surge connections during traffic bursts.
- `DB_POOL_TIMEOUT`: $30$ seconds checkout timeout before raising a connection pool error.
- `pool_pre_ping=True`: Executes `SELECT 1` heartbeat check on connection checkout, discarding dead connections.
- `pool_recycle=1800`: Recycles connections older than 30 minutes, preventing silent drops by stateful firewalls or cloud NAT gateways.

---

## 5. Safe Schema Migrations & Zero-Downtime Deployment Sequencing

DCP uses **Alembic** for schema migrations. Destructive schema migrations are **never** executed automatically on container startup.

### Safe 4-Phase Deployment Sequencing for Schema Changes:
1. **Expand (Add Phase)**:
   - Add new nullable columns or tables via forward migrations.
   - Deploy code that writes to both old and new schema elements if necessary.
2. **Backfill**:
   - Run asynchronous background Celery tasks to populate new columns from legacy data.
3. **Contract (Update Phase)**:
   - Deploy code that reads exclusively from the new schema elements.
4. **Prune (Cleanup Phase)**:
   - Run a subsequent migration to remove deprecated columns or indexes after verifying stability.

### Executing Migrations in Production:
```bash
# 1. Inspect pending migration SQL without executing
docker compose -f docker-compose.prod.yml run --rm dcp-api alembic upgrade head --sql

# 2. Execute migration
docker compose -f docker-compose.prod.yml run --rm dcp-api alembic upgrade head

# 3. Verify current schema revision matches head
docker compose -f docker-compose.prod.yml run --rm dcp-api alembic current
```
