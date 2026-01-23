#!/bin/bash

# SuperInsight 部署到 cloud2 环境
# 使用 TCB 云端构建功能

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         SuperInsight 部署到 TCB Cloud2                    ║${NC}"
echo -e "${BLUE}╚C}"
echo ""

# 环境配置
ENV_ID="cloud2-3gegxdemf86cb89a"
SERVICE_NAME="superinsight-api"
REGION="ap-shanghai"

echo -eV_ID${NC}"
echo -e "${GREEN}✓ 服务名称: $SERVICE_NAME${NC}"
echo -e "${GREEN}✓ 地域: $REGION${NC}"
echo ""

# 检查 TCB CLI
if ! command -v tcb &> /dev/null; then
    echo -e "${RED}✗ TCB CLI 未安装${NC}"
    exit 1
fi

echo -e "${BLUE}[1/5] 准备部署文件...${NC}"

# 创建临时部署目录
DEPLOY_DIR="/tmp/superinsight-deploy-$(date +%s)"
mkdir -p "$DEPLOY_DIR"

# 复制必要文件
echo "复制源代码..."
cp -r src "$DEPLOY_DIR/"
cp main.py "$DEPLOY_DIR/"
cp requ_DIR/"
_DIR/" 2>/dev/null || true
cp alembic.ini "$DEPLOY_DIR/" 2>/dev/null || true
cp deploy/tcb/Dockerfile.api "$DEPLOY_DIR/Dockerfile"

echo -e "${GREEN}✓ 文件准备完成${NC}"
echo ""

echo -e "${BLUE}[2/5] 创建 cloudbaserc.json 配置...${NC}"

# 创建 TCB 配置文件
cat > "$DEPLOY_DIR/cloudbaserc.json" << EOF
{
  "envId": "$ENV_ID",
  "region": "$REGION",
  "functionRoot": "./functions",
  "functions": [],
  "framework": {
    "name": "superinsight-api",
    "plugins": {
      "container": {
        "use": "@cloudbase/framework-plugin-container",
        "inputs": {
          "serviceName": "$SERVICE_NAME",
          "servicePath": "/",
          "dockerfilePath": "./Dockerfile",
          "containerPort": 8000,
          "cpu": 2,
          "mem": 4,
          "minNum": 1,
          "maxNum": 5,
          "policyType": "cpu",
          "policyThreshold": 70,
          "envVariables": {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "INFO",
     "PYTHONUNBUFFERED": "1"
          },
          "customLogs": "stdout"
        }
      }
    }
  }
}
EOF

echo -e "${GREEN}✓ 配置文件创建完成${NC}"
echo ""

echo -e "${BLUE}[3/5] 使用 TCB Framework 部署...${NC}"
echo "这将使用云端构建，无需本地 Docker"
echo ""

cd "$DEPLOY_DIR"

# 使用 TCB Framework 部署
tcb framework:deploy --verbose

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ 部署成功！${NC}"
else
    echo ""
    echo -e "${RED}✗ 部署失败${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}[4/5] 查看服务状态...${NC}"
tcb cloudrun:service:describe --service-name "$SERVICE_NAME" --env-id "$ENV_ID"

echo ""
echo -e "${BLUE}[5/5] 获取访问地址...${NC}"

# 获取服务访问地址
SERVICE_INFO=$(tcb cloudrun:service:describe --service-name "$SERVICE_NAME" --env-id "$ENV_ID" 2>/dev/null)

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  🎉 部署完成！                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📍 部署信息：${NC}"
echo "  环境 ID: $ENV_ID"
echo "  服务名称: $SERVICE_NAME"
echo "  地域: $REGION"
echo ""
echo -e "${BLUE}🔧 常用命令：${NC}"
echo "  查看服务: tcb cloudrun:service:describe --service-name $SERVICE_NAME --env-id $ENV_ID"
echo "  查看日志: tcb cloudrun:service:log --service-name $SERVICE_NAME --env-id $ENV_ID --follow"
echo "  更新服务: cd $DEPLOY_DIR && tcb framework:deploy"
echo ""
echo -e "${BLUE}📝 访问地址：${NC}"
echo "  请在 TCB 控制台查看服务访问地址"
echo "  https://console.cloud.tencent.com/tcb/env/index?envId=$ENV_ID"
echo ""

# 清理临时文件（可选）
# rm -rf "$DEPLOY_DIR"
echo -e "${YELLOW}临时文件保存在: $DEPLOY_DIR${NC}"
echo ""
