#!/bin/bash
# SuperInsight Sealos 镜像构建与推送脚本
# 用法: ./deploy/sealos/build-and-push.sh [tag]

set -e

TAG=${1:-sealos}
REGISTRY="angus888"

echo "=== 构建后端镜像 ==="
docker build -f deploy/sealos/Dockerfile.backend \
  -t ${REGISTRY}/superinsight-backend:${TAG} .

echo "=== 构建前端镜像 ==="
docker build -f deploy/sealos/Dockerfile.frontend \
  -t ${REGISTRY}/superinsight-frontend:${TAG} .

echo "=== 推送镜像 ==="
docker push ${REGISTRY}/superinsight-backend:${TAG}
docker push ${REGISTRY}/superinsight-frontend:${TAG}

echo "=== 完成 ==="
echo "后端: ${REGISTRY}/superinsight-backend:${TAG}"
echo "前端: ${REGISTRY}/superinsight-frontend:${TAG}"
