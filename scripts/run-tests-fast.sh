#!/usr/bin/env bash
# Local quick regression: low Hypothesis sample count + no coverage overhead.
# 仅跑 tests/unit 且更省内存：./scripts/run-unit-lowmem.sh
# 打印本次运行峰值常驻内存：./scripts/run-unit-lowmem.sh --mem
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
