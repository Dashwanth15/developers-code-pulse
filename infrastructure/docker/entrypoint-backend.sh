#!/bin/sh
set -e

# Default to 4 workers or CPU count
WORKERS=${GUNICORN_WORKERS:-4}
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "Starting Developers Code Pulse Backend (Environment: ${ENVIRONMENT:-development})..."

if [ "$ENVIRONMENT" = "production" ]; then
    echo "Starting production Gunicorn ASGI cluster with ${WORKERS} Uvicorn workers..."
    exec gunicorn app.main:app \
        --workers "$WORKERS" \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind "$HOST:$PORT" \
        --timeout 60 \
        --graceful-timeout 30 \
        --access-logfile - \
        --error-logfile -
else
    echo "Starting development/staging Uvicorn process..."
    exec uvicorn app.main:app --host "$HOST" --port "$PORT"
fi
