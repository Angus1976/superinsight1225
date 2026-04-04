#!/usr/bin/env bash
# 按依赖顺序执行测试：后端 unit → property → 前端 Vitest →（可选）集成 →（可选）E2E
# 与 CI 分层一致：先快后慢，失败即停（set -e）。
#
# Usage:
#   ./scripts/run-tests-by-deps.sh
#   RUN_INTEGRATION=1 ./scripts/run-tests-by-deps.sh    # 需可用的 Postgres/Redis 与 .env.test
#   RUN_E2E=1 ./scripts/run-tests-by-deps.sh             # 需先启动后端与本机 frontend dev（见 frontend/playwright.config.ts）
#
# Hypothesis 采样：
#   HYPOTHESIS_PROFILE=dev ./scripts/run-tests-by-deps.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export HYPOTHESIS_PROFILE="${HYPOTHESIS_PROFILE:-dev}"

echo "=== [1/5] Backend unit (pytest -m unit) ==="
python3 -m pytest tests/ -m unit --tb=short -v --no-cov --maxfail=10

echo "=== [2/5] Backend property (pytest -m property) ==="
python3 -m pytest tests/ -m property --tb=short -v --no-cov --hypothesis-seed=0 --maxfail=5

echo "=== [3/5] Frontend unit (Vitest) ==="
(
  cd frontend
  npm run test:run
)

if [[ "${RUN_INTEGRATION:-0}" == "1" ]]; then
  echo "=== [4/5] Integration (pytest -m integration) ==="
  python3 -m pytest tests/ -m integration --tb=short -v --no-cov --maxfail=10
else
  echo "=== [4/5] Integration: skipped (set RUN_INTEGRATION=1; configure DATABASE_URL / Redis) ==="
fi

if [[ "${RUN_E2E:-0}" == "1" ]]; then
  echo "=== [5/5] Playwright E2E ==="
  (
    cd frontend
    npm run test:e2e -- --project=chromium
  )
else
  echo "=== [5/5] E2E: skipped (set RUN_E2E=1; start backend + npm run dev in frontend) ==="
fi

echo "=== Done (order: unit → property → frontend → [integration] → [e2e]) ==="
