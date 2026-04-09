#!/usr/bin/env bash
# Property-based tests (Hypothesis). Local default: fast profile, no coverage overhead.
#
# Anti-pattern: do **not** pipe pytest to `tail` / `head` — you will see no progress until the
# process exits (pipe buffering). Use this script directly, or tee to a **file** if you need a log:
#   ./scripts/run-property-tests.sh 2>&1 | tee property-run.log
#
# Usage:
#   ./scripts/run-property-tests.sh
#   ./scripts/run-property-tests.sh tests/property/test_foo.py -v
#
# Same gate as commit-tests "backend property" step (only @pytest.mark.property cases):
#   ./scripts/run-property-tests.sh --ci-marker
#
# Override Hypothesis profile (see tests/conftest.py):
#   HYPOTHESIS_PROFILE=dev ./scripts/run-property-tests.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export HYPOTHESIS_PROFILE="${HYPOTHESIS_PROFILE:-fast}"

# Override pytest.ini --maxfail=5 for full property runs (set PYTEST_MAXFAIL=5 to restore early stop).
: "${PYTEST_MAXFAIL:=0}"

if [[ "${1:-}" == "--ci-marker" ]]; then
  shift
  exec python3 -u -m pytest tests/ \
    -m property \
    --no-cov \
    -q \
    --tb=line \
    --hypothesis-seed=0 \
    --maxfail="${PYTEST_MAXFAIL}" \
    "$@"
else
  exec python3 -u -m pytest tests/property \
    --no-cov \
    -q \
    --tb=line \
    --maxfail="${PYTEST_MAXFAIL}" \
    "$@"
fi
