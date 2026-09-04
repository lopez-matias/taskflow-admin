#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${PROJECT_DIR}/.postgres-data"
SOCKET_DIR="${PROJECT_DIR}/.postgres-socket"
PORT="${ORANGEFLOW_LOCAL_POSTGRES_PORT:-55432}"
ACTION="${1:-start}"

if ! command -v pg_config >/dev/null 2>&1; then
  echo "PostgreSQL was not found. Install it or use Docker Compose." >&2
  exit 1
fi

POSTGRES_BIN="$(pg_config --bindir)"

case "${ACTION}" in
  start)
    mkdir -p "${DATA_DIR}" "${SOCKET_DIR}"
    if [[ ! -f "${DATA_DIR}/PG_VERSION" ]]; then
      "${POSTGRES_BIN}/initdb" \
        -D "${DATA_DIR}" \
        --auth-local=trust \
        --auth-host=trust \
        --username=orangeflow \
        --no-instructions
    fi

    if ! "${POSTGRES_BIN}/pg_ctl" -D "${DATA_DIR}" status >/dev/null 2>&1; then
      "${POSTGRES_BIN}/pg_ctl" \
        -D "${DATA_DIR}" \
        -l "${DATA_DIR}/server.log" \
        -o "-h 127.0.0.1 -p ${PORT} -k ${SOCKET_DIR}" \
        start
    fi

    if [[ "$("${POSTGRES_BIN}/psql" -h 127.0.0.1 -p "${PORT}" -U orangeflow -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = 'orangeflow'")" != "1" ]]; then
      "${POSTGRES_BIN}/createdb" -h 127.0.0.1 -p "${PORT}" -U orangeflow orangeflow
    fi

    echo "Local PostgreSQL is ready at 127.0.0.1:${PORT}."
    ;;
  stop)
    if [[ -f "${DATA_DIR}/PG_VERSION" ]]; then
      "${POSTGRES_BIN}/pg_ctl" -D "${DATA_DIR}" stop
    fi
    ;;
  status)
    "${POSTGRES_BIN}/pg_ctl" -D "${DATA_DIR}" status
    ;;
  *)
    echo "Usage: $0 [start|stop|status]" >&2
    exit 2
    ;;
esac
