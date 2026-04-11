#!/usr/bin/env bash
# 网络断续时自动重试 docker compose pull / build。
# - pull：已拉取的镜像层会保留，重试相当于续传。
# - build：BuildKit/缓存会保留已完成的步骤，重试从失败处继续。
#
# 用法（在项目根执行）：
#   ./scripts/docker-compose-resilient.sh pull
#   ./scripts/docker-compose-resilient.sh build
#   ./scripts/docker-compose-resilient.sh build --pull
#   ./scripts/docker-compose-resilient.sh build --pull --no-cache app celery-worker
#
# 兼容旧入口（仅 pull）：
#   ./scripts/docker-compose-pull-resilient.sh
#
# 环境变量：
#   COMPOSE_HTTP_TIMEOUT / DOCKER_CLIENT_TIMEOUT  默认 3600（秒）
#   COMPOSE_RETRY_SLEEP      pull/build 失败后休眠，默认 20（秒）
#   PULL_RETRY_SLEEP         仅覆盖 pull 的休眠（可选）
#   BUILD_RETRY_SLEEP        仅覆盖 build 的休眠（可选）

set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

export COMPOSE_HTTP_TIMEOUT="${COMPOSE_HTTP_TIMEOUT:-3600}"
export DOCKER_CLIENT_TIMEOUT="${DOCKER_CLIENT_TIMEOUT:-3600}"

RETRY_DEFAULT="${COMPOSE_RETRY_SLEEP:-20}"
SLEEP_PULL="${PULL_RETRY_SLEEP:-$RETRY_DEFAULT}"
SLEEP_BUILD="${BUILD_RETRY_SLEEP:-$RETRY_DEFAULT}"

usage() {
  echo "用法: $0 pull | build [docker compose build 的参数...]" >&2
  exit 1
}

ACTION="${1:-}"
if [[ -z "$ACTION" ]]; then
  usage
fi
shift

echo "==> COMPOSE_HTTP_TIMEOUT=${COMPOSE_HTTP_TIMEOUT}s DOCKER_CLIENT_TIMEOUT=${DOCKER_CLIENT_TIMEOUT}s"
echo ""

case "$ACTION" in
  pull)
    echo "==> 将反复执行: docker compose pull（失败后每 ${SLEEP_PULL}s 重试）"
    echo ""
    attempt=0
    until docker compose pull; do
      attempt=$((attempt + 1))
      echo ""
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] pull 失败或中断（第 ${attempt} 次），${SLEEP_PULL}s 后重试…"
      sleep "$SLEEP_PULL"
    done
    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] docker compose pull 已完成。"
    ;;
  build)
    echo "==> 将反复执行: docker compose build $*（失败后每 ${SLEEP_BUILD}s 重试）"
    echo ""
    attempt=0
    until docker compose build "$@"; do
      attempt=$((attempt + 1))
      echo ""
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] build 失败或中断（第 ${attempt} 次），${SLEEP_BUILD}s 后重试…"
      sleep "$SLEEP_BUILD"
    done
    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] docker compose build 已完成。"
    ;;
  *)
    usage
    ;;
esac
