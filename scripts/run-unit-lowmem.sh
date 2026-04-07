#!/usr/bin/env bash
# 本地/笔记本友好：不启用 coverage，降低内存与磁盘 I/O（避免与 IDE 同时占满内存）。
# CI 仍应使用带 coverage 的完整命令（如 .github workflows）。
#
# Usage:
#   ./scripts/run-unit-lowmem.sh
#   ./scripts/run-unit-lowmem.sh tests/unit/test_foo.py
#   ./scripts/run-unit-lowmem.sh tests/unit/ -k "not slow"
#
# 分批跑 tests/unit（按文件名首字母，降低单次峰值内存）:
#   ./scripts/run-unit-lowmem.sh --chunk 1   # test_[a-h]*
#   ./scripts/run-unit-lowmem.sh --chunk 2   # test_[i-p]*
#   ./scripts/run-unit-lowmem.sh --chunk 3   # test_[q-z]*
#
# 结束时打印本次 pytest 进程的峰值常驻内存（ru_maxrss，约等于 Max RSS）:
#   ./scripts/run-unit-lowmem.sh --mem
#   等价于: PYTEST_REPORT_MAXRSS=1 python3 -m pytest …
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export HYPOTHESIS_PROFILE="${HYPOTHESIS_PROFILE:-fast}"

CHUNK=""
POS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --chunk)
      CHUNK="${2:-}"
      shift 2
      ;;
    --mem)
      export PYTEST_REPORT_MAXRSS=1
      shift
      ;;
    *)
      POS+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$CHUNK" ]]; then
  case "$CHUNK" in
    1) PAT='test_[a-h]*.py' ;;
    2) PAT='test_[i-p]*.py' ;;
    3) PAT='test_[q-z]*.py' ;;
    *)
      echo "Unknown --chunk value: $CHUNK (use 1, 2, or 3)" >&2
      exit 1
      ;;
  esac
  mapfile -t POS < <(find tests/unit -maxdepth 1 -name "$PAT" | sort)
  if [[ ${#POS[@]} -eq 0 ]]; then
    echo "No files matched chunk $CHUNK" >&2
    exit 1
  fi
elif [[ ${#POS[@]} -eq 0 ]]; then
  POS=(tests/unit/)
fi

exec python3 -m pytest "${POS[@]}" \
  --no-cov \
  -q \
  --tb=line \
  -o addopts='--strict-markers -ra --maxfail=10'
