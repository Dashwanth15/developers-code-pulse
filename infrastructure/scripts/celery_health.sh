#!/usr/bin/env bash
# ==============================================================================
# Developers Code Pulse (DCP) — Celery Worker Health & Queue Inspector
# Inspects worker status, active queues, and task throughput.
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo "Inspecting DCP Celery Worker Cluster"
echo "=========================================================="

echo "1. Pinging active Celery worker processes..."
celery -A app.workers.celery_app inspect ping || {
    echo "ERROR: Celery worker processes failed to respond to ping!"
    exit 1
}

echo "2. Querying active worker queues..."
celery -A app.workers.celery_app inspect active_queues

echo "3. Querying currently executing tasks..."
celery -A app.workers.celery_app inspect active

echo "4. Checking task queue statistics..."
celery -A app.workers.celery_app inspect stats

echo "=========================================================="
echo "Celery cluster health verification complete: ALL HEALTHY"
echo "=========================================================="
