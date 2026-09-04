#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "The virtual environment is missing. Run: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt" >&2
  exit 1
fi

export ORANGEFLOW_DATABASE_URL="postgresql+psycopg://orangeflow:orangeflow@127.0.0.1:55432/orangeflow"

./scripts/local-postgres.sh start
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed

echo "OrangeFlow is available at http://127.0.0.1:8000"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
