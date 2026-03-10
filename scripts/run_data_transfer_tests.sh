#!/bin/bash
#
# Data Transfer Integration - Regression Test Script
# Runs all backend and frontend tests related to the data transfer feature.
#
# Usage:
#   ./scripts/run_data_transfer_tests.sh
#
# Exit code:
#   0 - All tests passed
#   1 - One or more test suites failed
#

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
SKIPPED=0
SUITE_RESULTS=()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

run_suite() {
    local name="$1"
    shift
    local cmd=("$@")

    echo ""
    echo -e "${BLUE}━━━ Running: ${name} ━━━${NC}"

    if "${cmd[@]}"; then
        PASSED=$((PASSED + 1))
        SUITE_RESULTS+=("${GREEN}✓${NC} ${name}")
    else
        FAILED=$((FAILED + 1))
        SUITE_RESULTS+=("${RED}✗${NC} ${name}")
    fi
}

# ---------------------------------------------------------------------------
# Backend tests (pytest) — disable coverage & maxfail for regression run
# ---------------------------------------------------------------------------

PYTEST_OPTS=(-v --tb=short --no-header -p no:cacheprovider --override-ini="addopts=" )

run_suite "Unit: Permission Service" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/unit/test_permission_service.py

run_suite "Unit: Data Transfer Service" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/unit/test_data_transfer_service.py

run_suite "Unit: Transfer Messages (i18n)" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/unit/test_transfer_messages.py

run_suite "Unit: Permission Defaults" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/unit/test_permission_defaults.py

run_suite "Unit: Approval Defaults" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/unit/test_approval_defaults.py

run_suite "Integration: Transfer E2E" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/integration/test_transfer_e2e.py

run_suite "Integration: Approval E2E" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/integration/test_approval_e2e.py

run_suite "Integration: Legacy API Compat" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/integration/test_legacy_api_compat.py

run_suite "Integration: Permission Matrix" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/integration/test_permission_matrix.py

run_suite "Security: Data Transfer Security" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/security/test_data_transfer_security.py

run_suite "Security: Sensitive Data Validator" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/security/test_sensitive_data_validator.py

run_suite "Performance: Transfer Performance" \
    python -m pytest "${PYTEST_OPTS[@]}" tests/performance/test_transfer_performance.py

# ---------------------------------------------------------------------------
# Frontend tests (vitest)
# ---------------------------------------------------------------------------

FRONTEND_DIR="${PROJECT_ROOT}/frontend"

if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"

    run_suite "Frontend: TransferButton" \
        npx vitest run src/components/DataLifecycle/__tests__/TransferButton.test.tsx --reporter=verbose

    run_suite "Frontend: TransferModal" \
        npx vitest run src/components/DataLifecycle/__tests__/TransferModal.test.tsx --reporter=verbose

    cd "$PROJECT_ROOT"
else
    SKIPPED=$((SKIPPED + 2))
    SUITE_RESULTS+=("${YELLOW}⊘${NC} Frontend tests (directory not found)")
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

TOTAL=$((PASSED + FAILED + SKIPPED))

echo ""
echo "=========================================="
echo "  Data Transfer Regression Test Summary"
echo "=========================================="
echo ""

for result in "${SUITE_RESULTS[@]}"; do
    echo -e "  ${result}"
done

echo ""
echo -e "  Total: ${TOTAL}  ${GREEN}Passed: ${PASSED}${NC}  ${RED}Failed: ${FAILED}${NC}  ${YELLOW}Skipped: ${SKIPPED}${NC}"
echo ""

if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}REGRESSION TEST FAILED${NC}"
    exit 1
fi

echo -e "${GREEN}ALL REGRESSION TESTS PASSED${NC}"
exit 0
