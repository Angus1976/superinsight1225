#!/usr/bin/env bash
# Local quick regression: low Hypothesis sample count + no coverage overhead.
# Usage:
#   ./scripts/run-tests-fast.sh
#   ./scripts/run-tests-fast.sh tests/unit/test_foo.py -v
#
# Override profile:
#   HYPOTHESIS_PROFILE=dev ./scripts/run-tests-fast.sh   # 25 examples (see tests/conftest.py)

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export HYPOTHESIS_PROFILE="${HYPOTHESIS_PROFILE:-fast}"

exec python3 -m pytest tests/unit tests/api \
  --no-cov \
  -q \
  "$@"
