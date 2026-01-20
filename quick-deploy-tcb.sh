#!/bin/bash

# SuperInsight TCB 快速部署脚本
# 简化版本，用于快速部署到现有环境

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         SuperInsight TCB 快速部署                         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 显示可用环境
echo -e "${BLUE}可用的 TCB 环境：${NC}"
tcb env:list
echo ""

# 选择环境
read -p "请输入环境 ID (cloud1-7galmfiu70af91a6 或 cloud2-3gegxdemf86cb89a): " ENV_ID

if [ -z "$ENV_ID" ]; then
    echo -e "${YELLOW}未输入环境 ID，使用默认环境: cloud2-3gegxdemf86cb89a${NC}"
    ENV_ID="cloud2-3gegxdemf86cb89a"
fi

echo ""
echo -e "${GREEN}✓ 使用环境: $ENV_ID${NC}"
echo ""

# 选择部署类型
echo "请选择部署类型："
echo "  1) API 服务（推荐，仅后端）"
echo "  2) 完整栈（包含数据库，较大）"
echo ""
read -p "请选择 (1-2): " DEPLOY_TYPE

case $DEPLOY_TYPE in
    1)
        DOCKERFILE="deploy/tcb/Dockerfile.api"
        IMAGE_NAME="superinsight-api"
        SERVICE_NAME="superinsight-api"
        ;;
    2)
        DOCKERFILE="deploy/tcb/Dockerfile.fullstack"
        IMAGE_NAME="superinsight-fullstack"
        SERVICE_NAME="superinsight-fullstack"
        ;;
    *)
        echo "使用默认: API 服务"
        DOCKERFILE="deploy/tcb/Dockerfile.api"
        IMAGE_NAME="superinsight-api"
        SERVICE_NAME="superinsight-api"
        ;;
esac

echo ""
echo -e "${GREEN}✓ 部署类型: $IMAGE_NAME${NC}"
echo ""

# 确认部署
read -p "是否继续部署？(y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消部署"
    exit 0
fi

echo ""
echo -e "${BLUE}[1/4] 构建 Docker 镜像...${NC}"
docker build -t "$IMAGE_NAME:latest" -f "$DOCKERFILE" .

echo ""
echo -e "${BLUE}[2/4] 登录 TCB 容器镜像仓库...${NC}"
tcb cloudrun:login

echo ""
echo -e "${BLUE}[3/4] 推送镜像到 TCB...${NC}"
TCB_REGISTRY="ccr.ccs.tencentyun.com"
TCB_NAMESPACE="tcb_${ENV_ID}"
REMOTE_IMAGE="${TCB_REGISTRY}/${TCB_NAMESPACE}/${IMAGE_NAME}:latest"

docker tag "${IMAGE_NAME}:latest" "$REMOTE_IMAGE"
docker push "$REMOTE_IMAGE"

echo ""
echo -e "${BLUE}[4/4] 部署服务到 CloudRun...${NC}"

# 检查服务是否存在
if tcb cloudrun:service:describe --service-name "$SERVICE_NAME" --env-id "$ENV_ID" &> /dev/null; then
    echo "服务已存在，更新服务..."
    tcb cloudrun:service:update \
        --env-id "$ENV_ID" \
        --service-name "$SERVICE_NAME" \
        --image "$REMOTE_IMAGE"
else
    echo "创建新服务..."
    tcb cloudrun:service:create \
        --env-id "$ENV_ID" \
        --service-name "$SERVICE_NAME" \
        --image "$REMOTE_IMAGE" \
        --cpu 2 \
        --mem 4 \
        --min-num 1 \
        --max-num 5 \
        --container-port 8000
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  🎉 部署成功！                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📍 部署信息：${NC}"
echo "  环境 ID: $ENV_ID"
echo "  服务名称: $SERVICE_NAME"
echo "  镜像: $REMOTE_IMAGE"
echo ""
echo -e "${BLUE}🔧 查看服务：${NC}"
echo "  tcb cloudrun:service:describe --service-name $SERVICE_NAME --env-id $ENV_ID"
echo ""
echo -e "${BLUE}📝 查看日志：${NC}"
echo "  tcb cloudrun:service:log --service-name $SERVICE_NAME --env-id $ENV_ID --follow"
echo ""
