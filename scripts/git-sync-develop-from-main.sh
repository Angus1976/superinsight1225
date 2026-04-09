#!/usr/bin/env bash
# 将 origin/main 合并进 develop 并推送（发版合入 main 后，把稳定线同步回集成线）。
# 要求工作区干净（无未提交变更）；冲突时解决后执行 git commit 再 push。
set -euo pipefail

REMOTE="${1:-origin}"

if [ -n "$(git status --porcelain)" ]; then
  echo "工作区有未提交或未跟踪变更，请先提交或 stash 后再运行。" >&2
  exit 1
fi

git fetch "$REMOTE" main develop

if git show-ref --verify --quiet refs/heads/develop; then
  git checkout develop
else
  git checkout -b develop "$REMOTE/develop"
fi

git merge "$REMOTE/main" -m "chore: sync develop from main after release"

echo "即将推送 develop → $REMOTE"
git push "$REMOTE" develop
