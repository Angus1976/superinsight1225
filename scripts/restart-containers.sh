#!/bin/bash

# 重启前后端容器脚本

set -e

# Docker 路径
DOCKER_PATH="/Applications/Docker.app/Contents/Resources/bin/docker"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "重启前后端容器"
echo "=========================================="
echo ""

# 步骤 1: 停止容器
echo -e "${BLUE}📋 步骤 1: 停止现有容器${NC}"
echo "---"
$DOCKER_PATH compose down || true
echo -e "${GREEN}✓ 容器已停止${NC}"
echo ""

# 步骤 2: 启动前后端容器
echo -e "${BLUE}📋 步骤 2: 启动前后端容器${NC}"
echo "---"
$DOCKER_PATH compose up -d frontend app postgres redis
echo -e "${GREEN}✓ 容器已启动${NC}"
echo ""

# 步骤 3: 等待服务就绪
echo -e "${BLUE}📋 步骤 3: 等待服务就绪${NC}"
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

# 步骤 4: 显示容器状态
echo -e "${BLUE}📋 步骤 4: 显示容器状态${NC}"
echo "---"
$DOCKER_PATH compose ps
echo ""

echo -e "${GREEN}=========================================="
echo "✅ 容器重启完成！"
echo "=========================================="
echo ""
echo "服务地址:"
echo "  前端: http://localhost:5173"
echo "  后端 API: http://localhost:8000"
echo ""
