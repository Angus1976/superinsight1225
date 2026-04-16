#!/usr/bin/env bash
# Unified release gate for local/staging validation.
# Profiles:
#   smoke   - fast local regression
#   pr      - align with PR-level verification
#   release - pr + staged Chromium E2E sample
#   full    - release + security/performance/deployment checks

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROFILE="${1:-${PROFILE:-release}}"

timestamp() {
  date '+%H:%M:%S'
}

log() {
  echo "[$(timestamp)] $*"
}

section() {
  echo ""
  echo "=============================================================================="
  echo "==> $*"
  echo "=============================================================================="
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

run_backend_fast() {
  ./scripts/run-tests-fast.sh
}

run_backend_property() {
  export HYPOTHESIS_PROFILE="${HYPOTHESIS_PROFILE:-dev}"
  ./scripts/run-property-tests.sh --ci-marker
}

run_frontend_gate() {
  (
    cd frontend
    npm run lint
    npm run typecheck
    npm run build
    npm run test:run
  )
}

run_integration_gate() {
  local marker="integration and not docker"
  if [[ "${RUN_INTEGRATION_DOCKER:-0}" == "1" ]]; then
    marker="integration"
  fi

  python3 -m pytest tests/ \
    -m "$marker" \
    --tb=short \
    -v \
    --no-cov \
    --maxfail=10
}

run_e2e_sample_gate() {
  ./scripts/e2e-sample-chromium.sh
}

run_e2e_full_gate() {
  (
    cd frontend
    npm run test:e2e -- --project=chromium
  )
}

run_security_gate() {
  python3 -m pytest tests/security/ \
    --tb=short \
    -v \
    --no-cov \
    --maxfail=10
}

run_performance_gate() {
  python3 -m pytest tests/performance/ tests/high_availability/ \
    --tb=short \
    -v \
    --no-cov \
    --maxfail=10

  (
    cd frontend
    npx playwright test e2e/performance.spec.ts --project=chromium
  )
}

run_deployment_gate() {
  require_cmd docker

  docker build -t superinsight-backend:release-check -f Dockerfile .
  docker build -t superinsight-frontend:release-check -f frontend/Dockerfile frontend
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/run-release-gate.sh [smoke|pr|release|full]

Profiles:
  smoke   Fast local regression: backend fast tests + frontend lint/type/build/test
  pr      smoke + backend property tests + integration (non-docker by default)
  release pr + staged Chromium E2E sample
  full    release + security + performance + docker/deployment build checks

Common overrides:
  HYPOTHESIS_PROFILE=fast ./scripts/run-release-gate.sh pr
  RUN_INTEGRATION=0 ./scripts/run-release-gate.sh pr
  RUN_E2E_SAMPLE=0 ./scripts/run-release-gate.sh release
  RUN_INTEGRATION_DOCKER=1 ./scripts/run-release-gate.sh full
  RUN_E2E_FULL=1 ./scripts/run-release-gate.sh full

Notes:
  - Integration tests expect .env.test plus test Postgres/Redis.
  - Playwright expects frontend dependencies and browsers installed.
  - The script defaults to no coverage locally; CI remains the source of truth for coverage gates.
EOF
}

if [[ "$PROFILE" == "-h" || "$PROFILE" == "--help" ]]; then
  usage
  exit 0
fi

case "$PROFILE" in
  smoke)
    : "${RUN_INTEGRATION:=0}"
    : "${RUN_E2E_SAMPLE:=0}"
    : "${RUN_E2E_FULL:=0}"
    : "${RUN_SECURITY:=0}"
    : "${RUN_PERFORMANCE:=0}"
    : "${RUN_DEPLOYMENT:=0}"
    ;;
  pr)
    : "${RUN_INTEGRATION:=1}"
    : "${RUN_E2E_SAMPLE:=0}"
    : "${RUN_E2E_FULL:=0}"
    : "${RUN_SECURITY:=0}"
    : "${RUN_PERFORMANCE:=0}"
    : "${RUN_DEPLOYMENT:=0}"
    ;;
  release)
    : "${RUN_INTEGRATION:=1}"
    : "${RUN_E2E_SAMPLE:=1}"
    : "${RUN_E2E_FULL:=0}"
    : "${RUN_SECURITY:=0}"
    : "${RUN_PERFORMANCE:=0}"
    : "${RUN_DEPLOYMENT:=0}"
    ;;
  full)
    : "${RUN_INTEGRATION:=1}"
    : "${RUN_E2E_SAMPLE:=0}"
    : "${RUN_E2E_FULL:=1}"
    : "${RUN_SECURITY:=1}"
    : "${RUN_PERFORMANCE:=1}"
    : "${RUN_DEPLOYMENT:=1}"
    : "${RUN_INTEGRATION_DOCKER:=1}"
    ;;
  *)
    echo "Unknown profile: $PROFILE" >&2
    usage
    exit 1
    ;;
esac

require_cmd python3
require_cmd npm

log "Release gate profile: $PROFILE"
log "Root: $ROOT"

section "1. Backend fast regression"
run_backend_fast

section "2. Frontend lint, typecheck, build, unit tests"
run_frontend_gate

if [[ "$PROFILE" != "smoke" ]]; then
  section "3. Backend property tests"
  run_backend_property
fi

if [[ "${RUN_INTEGRATION}" == "1" ]]; then
  section "4. Integration tests"
  run_integration_gate
else
  log "Skipping integration tests (RUN_INTEGRATION=0)"
fi

if [[ "${RUN_E2E_SAMPLE}" == "1" ]]; then
  section "5. Chromium E2E staged sample"
  run_e2e_sample_gate
fi

if [[ "${RUN_E2E_FULL}" == "1" ]]; then
  section "6. Chromium E2E full run"
  run_e2e_full_gate
fi

if [[ "${RUN_SECURITY}" == "1" ]]; then
  section "7. Security regression bucket"
  run_security_gate
fi

if [[ "${RUN_PERFORMANCE}" == "1" ]]; then
  section "8. Performance and HA regression"
  run_performance_gate
fi

if [[ "${RUN_DEPLOYMENT}" == "1" ]]; then
  section "9. Deployment build verification"
  run_deployment_gate
fi

log "Release gate completed successfully for profile: $PROFILE"
