#!/bin/bash

# SuperInsight 部署到 cloud2 环境
# 自动化部署脚本

set -e

# 配置
ENV_ID="cloud2-3gegxdemf86cb89a"
IMAGE_NAME="superinsight-api"
SERVICE_NAME="superinsight-api"
DOCKERFILE="deploy/tcb/Dockerfile.api"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     SuperInsight 部署到 cloud2 环境                       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}✓ 目标环境: $ENV_ID${NC}"
echo -e "${GREEN}✓ 服务名称: $SERVICE_NAME${NC}"
echo -e "${GREEN}✓ 镜像名称: $IMAGE_NAME${NC}"
echo ""

# 确认部署
read -p "是否继续部署到 cloud2？(y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消部署"
    exit 0
fi

# 步骤 1: 构建镜像
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[1/4] 构建 Docker 镜像${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if docker build -t "$IMAGE_NAME:latest" -f "$DOCKERFILE" .; then
    echo -e "${GREEN}✓ 镜像构建成功${NC}"
else
    echo -e "${RED}✗ 镜像构建失败${NC}"
    exit 1
fi

# 步骤 2: 登录 TCB
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[2/4] 登录 TCB 容器镜像仓库${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if tcb cloudrun:login; then
    echo -e "${GREEN}✓ 登录成功${NC}"
else
    echo -e "${RED}✗ 登录失败${NC}"
    exit 1
fi

# 步骤 3: 推送镜像
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[3/4] 推送镜像到 TCB（这可能需要几分钟）${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

TCB_REGISTRY="ccr.ccs.tencentyun.com"
TCB_NAMESPACE="tcb_${ENV_ID}"
REMOTE_IMAGE="${TCB_REGISTRY}/${TCB_NAMESPACE}/${IMAGE_NAME}:latest"

echo "标记镜像: $REMOTE_IMAGE"
docker tag "${IMAGE_NAME}:latest" "$REMOTE_IMAGE"

echo "推送镜像..."
if docker push "$REMOTE_IMAGE"; then
    echo -e "${GREEN}✓ 镜像推送成功${NC}"
else
    echo -e "${RED}✗ 镜像推送失败${NC}"
    exit 1
fi

# 步骤 4: 部署服务
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[4/4] 部署服务到 CloudRun${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查服务是否存在
if tcb cloudrun:service:describe --service-name "$SERVICE_NAME" --env-id "$ENV_ID" &> /dev/null; then
    echo "服务已存在，更新服务..."
    if tcb cloudrun:service:update \
        --env-id "$ENV_ID" \
        --service-name "$SERVICE_NAME" \
        --image "$REMOTE_IMAGE"; then
        echo -e "${GREEN}✓ 服务更新成功${NC}"
    else
        echo -e "${RED}✗ 服务更新失败${NC}"
        exit 1
    fi
else
    echo "创建新服务..."
    if tcb cloudrun:service:create \
        --env-id "$ENV_ID" \
        --service-name "$SERVICE_NAME" \
        --image "$REMOTE_IMAGE" \
        --cpu 2 \
        --mem 4 \
        --min-num 1 \
        --max-num 5 \
        --container-port 8000; then
        echo -e "${GREEN}✓ 服务创建成功${NC}"
    else
        echo -e "${RED}✗ 服务创建失败${NC}"
        exit 1
    fi
fi

# 完成
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  🎉 部署成功！                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📍 部署信息：${NC}"
echo ""
echo "  环境 ID:    $ENV_ID"
echo "  服务名称:   $SERVICE_NAME"
echo "  镜像地址:   $REMOTE_IMAGE"
echo ""
echo -e "${BLUE}🔧 常用命令：${NC}"
echo ""
echo "  查看服务详情:"
echo "    tcb cloudrun:service:describe --service-name $SERVICE_NAME --env-id $ENV_ID"
echo ""
echo "  查看实时日志:"
echo "    tcb cloudrun:service:log --service-name $SERVICE_NAME --env-id $ENV_ID --follow"
echo ""
echo "  查看服务列表:"
echo "    tcb cloudrun:service:list --env-id $ENV_ID"
echo ""
echo -e "${BLUE}📝 下一步：${NC}"
echo ""
echo "  1. 等待服务启动（约 2-3 分钟）"
echo "  2. 查看服务日志确认启动成功"
echo "  3. 在 TCB 控制台配置自定义域名"
echo "  4. 配置环境变量（如需要）"
echo ""
