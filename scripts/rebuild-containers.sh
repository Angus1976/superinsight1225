#!/bin/bash

# 重建和更新本地容器脚本
# 仅重建有代码变更的容器，基础容器保持不变

set -e

echo "=========================================="
echo "SuperInsight 容器重建脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装
DOCKER_PATH="/Applications/Docker.app/Contents/Resources/bin/docker"
if [ ! -f "$DOCKER_PATH" ]; then
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安装或不在 PATH 中${NC}"
        exit 1
    fi
    DOCKER="docker"
else
    DOCKER="$DOCKER_PATH"
fi

echo -e "${BLUE}📋 步骤 1: 检查当前容器状态${NC}"
echo "---"
$DOCKER compose ps || true
echo ""

echo -e "${BLUE}📋 步骤 2: 停止运行中的容器${NC}"
echo "---"
$DOCKER compose down || true
echo -e "${GREEN}✓ 容器已停止${NC}"
echo ""

echo -e "${BLUE}📋 步骤 3: 重建前端容器${NC}"
echo "---"
echo "检查前端代码变更..."
if git diff --name-only HEAD~1 | grep -q "^frontend/"; then
    echo "前端代码有变更，重建前端容器..."
    $DOCKER compose build --no-cache frontend
    echo -e "${GREEN}✓ 前端容器已重建${NC}"
else
    echo "前端代码无变更，使用缓存构建..."
    $DOCKER compose build frontend
    echo -e "${GREEN}✓ 前端容器已构建${NC}"
fi
echo ""

echo -e "${BLUE}📋 步骤 4: 重建后端容器${NC}"
echo "---"
echo "检查后端代码变更..."
if git diff --name-only HEAD~1 | grep -q "^src/"; then
    echo "后端代码有变更，重建后端容器..."
    $DOCKER compose build --no-cache app
    echo -e "${GREEN}✓ 后端容器已重建${NC}"
else
    echo "后端代码无变更，使用缓存构建..."
    $DOCKER compose build app
    echo -e "${GREEN}✓ 后端容器已构建${NC}"
fi
echo ""

echo -e "${BLUE}📋 步骤 5: 启动所有容器${NC}"
echo "---"
$DOCKER compose up -d
echo -e "${GREEN}✓ 所有容器已启动${NC}"
echo ""

echo -e "${BLUE}📋 步骤 6: 等待容器就绪${NC}"
echo "---"
echo "等待后端服务就绪..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health/live &> /dev/null; then
        echo -e "${GREEN}✓ 后端服务已就绪${NC}"
        break
    fi
    echo "等待中... ($i/30)"
    sleep 2
done

echo "等待前端服务就绪..."
for i in {1..30}; do
    if curl -f http://localhost:5173 &> /dev/null; then
        echo -e "${GREEN}✓ 前端服务已就绪${NC}"
        break
    fi
    echo "等待中... ($i/30)"
    sleep 2
done
echo ""

echo -e "${BLUE}📋 步骤 7: 显示容器状态${NC}"
echo "---"
$DOCKER compose ps
echo ""

echo -e "${GREEN}=========================================="
echo "✅ 容器重建完成！"
echo "=========================================="
echo ""
echo "服务地址:"
echo "  前端: http://localhost:5173"
echo "  后端 API: http://localhost:8000"
echo "  Label Studio: http://localhost:8080"
echo "  Argilla: http://localhost:6900"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana: http://localhost:3001"
echo ""
