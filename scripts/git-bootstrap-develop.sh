#!/usr/bin/env bash
# 从 origin/main 创建并推送 develop（与《生产上线综合测试计划表》分支策略一致）。
# 若远程已有 develop，仅提示，不覆盖。
set -euo pipefail

REMOTE="${1:-origin}"

git fetch "$REMOTE" main

if git rev-parse --verify develop >/dev/null 2>&1; then
  echo "本地已存在分支 develop，跳过创建。"
else
  git branch develop "$REMOTE/main"
  echo "已创建本地分支 develop（指向 $REMOTE/main）。"
fi

if git ls-remote --heads "$REMOTE" develop | grep -q .; then
  echo "远程 $REMOTE 已存在 develop，无需 push。"
  exit 0
fi

echo "即将执行: git push -u $REMOTE develop"
git push -u "$REMOTE" develop
