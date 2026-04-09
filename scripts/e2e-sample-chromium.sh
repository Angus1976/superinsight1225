#!/usr/bin/env bash
# TC-H / 发布前 E2E 扩大抽样（Chromium），按依赖关系分阶段顺序执行。
# 每阶段内 Playwright 仍可并行用例；阶段之间严格先后，便于「先身份与租户、再配置、再数据链、再业务闭环、再安全与角色」排错。
# reviewer 含 --grep，单独最后阶段，避免过滤其它文件。
# 前置：frontend 依赖已安装；Playwright 按 playwright.config 启动/复用 dev server。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"
export PLAYWRIGHT_WORKERS="${PLAYWRIGHT_WORKERS:-2}"

run_phase() {
  local title="$1"
  shift
  local -a specs=("$@")
  if [[ ${#specs[@]} -eq 0 ]]; then
    return 0
  fi
  echo ""
  echo "================================================================================"
  echo "==> E2E sample phase: ${title} (${#specs[@]} files)"
  echo "================================================================================"
  npx playwright test "${specs[@]}" --project=chromium
}

# --- 1. 入口与壳层（无业务依赖）---
run_phase "1-foundation" \
  e2e/auth.spec.ts \
  e2e/dashboard.spec.ts

# --- 2. 多租户与权限基线（后续管理端/功能页常隐含租户与 RBAC）---
run_phase "2-tenant-and-permissions" \
  e2e/multi-tenant.spec.ts \
  e2e/permissions.spec.ts

# --- 3. 管理端：组织与配置先于数据库/同步/LLM/配额/账单 ---
run_phase "3-admin-organization" \
  e2e/admin-modules/admin-console.spec.ts \
  e2e/admin-modules/admin-users.spec.ts \
  e2e/admin-modules/admin-tenants.spec.ts \
  e2e/admin-modules/admin-permissions.spec.ts \
  e2e/admin-modules/admin-config.spec.ts

run_phase "4-admin-platform-config" \
  e2e/admin-db-config.spec.ts \
  e2e/admin-sync-strategy.spec.ts \
  e2e/admin-llm-config.spec.ts \
  e2e/admin-modules/admin-quotas.spec.ts \
  e2e/admin-modules/admin-billing.spec.ts

# --- 5. 数据同步：先集成总览，再源/湖/调度/导出子链路 ---
run_phase "5-datasync-pipeline" \
  e2e/data-sync-integration.spec.ts \
  e2e/datasync/sources-crud.spec.ts \
  e2e/datasync/datalake-browser.spec.ts \
  e2e/datasync/scheduler.spec.ts \
  e2e/datasync/export-flow.spec.ts

# --- 6. 标注与业务闭环（依赖任务/工作流语义）---
run_phase "6-annotation-and-business-flows" \
  e2e/annotation-workflow.spec.ts \
  e2e/business-workflow.spec.ts \
  e2e/complete-workflows.spec.ts

# --- 7. 质量与导出报表 ---
run_phase "7-quality-and-reporting" \
  e2e/quality.spec.ts \
  e2e/export-reporting-workflows.spec.ts

# --- 8. 安全、审计、合规（在主要模块之后做横切验证）---
run_phase "8-security-audit-compliance" \
  e2e/audit-security.spec.ts \
  e2e/compliance.spec.ts \
  e2e/security.spec.ts

# --- 9. 版本与持久化 ---
run_phase "9-versioning-and-persistence" \
  e2e/versioning.spec.ts \
  e2e/data-persistence.spec.ts

# --- 10. 角色工作流（在权限与模块冒烟之后再跑纵向旅程）---
run_phase "10-role-workflows" \
  e2e/role-workflows/data-manager-workflow.spec.ts \
  e2e/role-workflows/data-analyst-workflow.spec.ts \
  e2e/role-workflows/annotator-workflow.spec.ts \
  e2e/role-workflows/admin-workflow.spec.ts

# --- 11. Label Studio 工作区 reviewer（独立 grep）---
echo ""
echo "================================================================================"
echo "==> E2E sample phase: 11-ls-workspace-reviewer"
echo "================================================================================"
npx playwright test e2e/ls-workspace-permissions.spec.ts \
  --grep reviewer \
  --project=chromium

echo ""
echo "==> E2E sample (all phases) done"
