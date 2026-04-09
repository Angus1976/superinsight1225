#!/usr/bin/env bash
#
# TC-P1-04 等价演练：PostgreSQL 备份 → 删表 → 从备份恢复 → 行数校验。
# 默认连接 docker-compose.integration-test.yml 中的 postgres-test（主机 5433）。
# 仅创建/使用表 public.p1_drill_checkpoint，不修改业务表；禁止在生产主库执行。
#
# 前置：docker compose -f docker-compose.integration-test.yml up -d
# 用法：bash scripts/pg-backup-restore-drill.sh
#
# 若本机无 psql/pg_dump，可设 USE_DOCKER_EXEC=1（默认自动检测）在容器内执行。
# CI：`commit-tests.yml` 中安装 postgresql-client 并设置 PGHOST/PGPORT/PGUSER/PGDATABASE（与 job 内 postgres service 一致）。
#
set -euo pipefail

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5433}"
PGUSER="${PGUSER:-superinsight_test}"
PGPASSWORD="${PGPASSWORD:-test_password}"
PGDATABASE="${PGDATABASE:-superinsight_test}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-superinsight-postgres-test}"
export PGPASSWORD

# 未显式设置时：本机无 psql/pg_dump 则走 Docker 容器内客户端
if [[ -z "${USE_DOCKER_EXEC:-}" ]]; then
  if command -v psql >/dev/null 2>&1 && command -v pg_dump >/dev/null 2>&1; then
    USE_DOCKER_EXEC=0
  else
    USE_DOCKER_EXEC=1
  fi
fi

run_psql() {
  if [[ "$USE_DOCKER_EXEC" == "1" ]]; then
    docker exec -i -e PGPASSWORD="$PGPASSWORD" "$POSTGRES_CONTAINER" \
      psql -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 "$@"
  else
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 "$@"
  fi
}

run_psql_q() {
  if [[ "$USE_DOCKER_EXEC" == "1" ]]; then
    docker exec -i -e PGPASSWORD="$PGPASSWORD" "$POSTGRES_CONTAINER" \
      psql -U "$PGUSER" -d "$PGDATABASE" "$@"
  else
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" "$@"
  fi
}

run_pg_dump() {
  if [[ "$USE_DOCKER_EXEC" == "1" ]]; then
    docker exec -e PGPASSWORD="$PGPASSWORD" "$POSTGRES_CONTAINER" \
      pg_dump -U "$PGUSER" -d "$PGDATABASE" "$@"
  else
    pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" "$@"
  fi
}

if [[ "$USE_DOCKER_EXEC" == "1" ]]; then
  if ! docker exec "$POSTGRES_CONTAINER" true 2>/dev/null; then
    echo "Docker container ${POSTGRES_CONTAINER} not running. Start with:" >&2
    echo "  docker compose -f docker-compose.integration-test.yml up -d" >&2
    exit 1
  fi
  echo "==> P1-04 drill: using docker exec into ${POSTGRES_CONTAINER}"
else
  echo "==> P1-04 drill: connecting ${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE}"
fi

DUMP="$(mktemp /tmp/p1-drill-XXXXXX.sql)"
cleanup() { rm -f "$DUMP"; }
trap cleanup EXIT

run_psql <<'SQL'
DROP TABLE IF EXISTS p1_drill_checkpoint;
CREATE TABLE p1_drill_checkpoint (
  id serial PRIMARY KEY,
  checkpoint_at timestamptz NOT NULL DEFAULT now(),
  note text NOT NULL DEFAULT 'p1-drill'
);
INSERT INTO p1_drill_checkpoint (note) VALUES ('before-backup');
SQL

ROWS_BEFORE=$(run_psql_q -t -A -c "SELECT count(*) FROM p1_drill_checkpoint;")
if [[ "${ROWS_BEFORE// /}" != "1" ]]; then
  echo "unexpected row count before dump: ${ROWS_BEFORE}" >&2
  exit 1
fi

if [[ "$USE_DOCKER_EXEC" == "1" ]]; then
  run_pg_dump --no-owner --no-privileges -F p -t public.p1_drill_checkpoint >"$DUMP"
else
  run_pg_dump --no-owner --no-privileges -F p -f "$DUMP" -t public.p1_drill_checkpoint
fi

run_psql -c "DROP TABLE IF EXISTS p1_drill_checkpoint CASCADE;"

ROWS_GONE=$(run_psql_q -t -A -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='p1_drill_checkpoint';")
if [[ "${ROWS_GONE// /}" != "0" ]]; then
  echo "table still present after DROP" >&2
  exit 1
fi

if [[ "$USE_DOCKER_EXEC" == "1" ]]; then
  docker exec -i -e PGPASSWORD="$PGPASSWORD" "$POSTGRES_CONTAINER" \
    psql -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 <"$DUMP"
else
  psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f "$DUMP"
fi

ROWS_AFTER=$(run_psql_q -t -A -c "SELECT count(*) FROM p1_drill_checkpoint;")
NOTE_AFTER="$(run_psql_q -t -A -c "SELECT note FROM p1_drill_checkpoint LIMIT 1;" | tr -d '\r\n' )"

if [[ "${ROWS_AFTER// /}" != "1" ]] || [[ "$NOTE_AFTER" != "before-backup" ]]; then
  echo "P1 drill FAILED: rows=${ROWS_AFTER} note=${NOTE_AFTER}" >&2
  exit 1
fi

echo "==> P1-04 drill OK: pg_dump → DROP → psql restore; checkpoint rows=1 note=before-backup"
