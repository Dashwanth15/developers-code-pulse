#!/usr/bin/env bash
# ==============================================================================
# Developers Code Pulse (DCP) — Database Restore Utility
# Validates checksums and restores PostgreSQL backups safely.
# ==============================================================================
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
POSTGRES_HOST="${POSTGRES_HOST:-dcp-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-dcp_user}"
POSTGRES_DB="${POSTGRES_DB:-dcp_db}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file does not exist: $BACKUP_FILE"
    exit 1
fi

CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [ -f "$CHECKSUM_FILE" ]; then
    echo "Verifying SHA256 integrity checksum..."
    sha256sum -c "$CHECKSUM_FILE"
    echo "Checksum verified successfully."
else
    echo "Warning: Checksum file not found. Proceeding with caution."
fi

echo "=========================================================="
echo "WARNING: Restoring will overwrite existing data in ${POSTGRES_DB}!"
echo "Target: ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "=========================================================="

if [ "${FORCE_RESTORE:-0}" -ne 1 ]; then
    read -p "Type 'RESTORE' to confirm: " CONFIRMATION
    if [ "$CONFIRMATION" != "RESTORE" ]; then
        echo "Restore aborted by user."
        exit 0
    fi
fi

echo "Terminating existing database connections..."
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" || true

echo "Restoring database from ${BACKUP_FILE}..."
gunzip -c "$BACKUP_FILE" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" --single-transaction

echo "=========================================================="
echo "Database restore completed successfully!"
echo "=========================================================="
