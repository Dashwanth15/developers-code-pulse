#!/usr/bin/env bash
# ==============================================================================
# Developers Code Pulse (DCP) — Database Backup Utility
# Performs compressed, verified PostgreSQL backups with retention management.
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
POSTGRES_HOST="${POSTGRES_HOST:-dcp-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-dcp_user}"
POSTGRES_DB="${POSTGRES_DB:-dcp_db}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="${BACKUP_DIR}/dcp_backup_${POSTGRES_DB}_${TIMESTAMP}.sql.gz"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

echo "=========================================================="
echo "Starting PostgreSQL backup: ${POSTGRES_DB} at ${TIMESTAMP}"
echo "=========================================================="

# Execute pg_dump with custom directory/compression format
pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --format=plain \
    --no-owner \
    --no-privileges \
    | gzip -9 > "$BACKUP_FILE"

# Calculate SHA256 checksum
sha256sum "$BACKUP_FILE" > "$CHECKSUM_FILE"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup successfully completed: ${BACKUP_FILE} (${BACKUP_SIZE})"
echo "SHA256 Checksum: $(cat "$CHECKSUM_FILE")"

# Enforce retention policy: delete backups older than RETENTION_DAYS
echo "Pruning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -type f -name "dcp_backup_*.sql.gz*" -mtime "+${RETENTION_DAYS}" -delete
echo "Retention pruning completed."
