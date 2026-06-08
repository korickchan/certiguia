#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"
WORKERS="${WEB_CONCURRENCY:-1}"
TIMEOUT="${GUNICORN_TIMEOUT:-300}"

echo "Iniciando CertiGuia na porta ${PORT}..."
exec gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --threads 4 \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile - \
  app:app
