#!/bin/bash

# Docker 环境设置脚本
# 配置 Docker 路径并提供便捷命令

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Docker 路径
DOCKER_PATH="/Applications/Docker.app/Contents/Resources/bin/docker"

echo -e "${BLUE}=========================================="
echo "Docker 环境设置"
echo "=========================================="
echo ""

# 检查 Docker 是否存在
if [ -f "$DOCKER_PATH" ]; then
    echo -e "${GREEN}✓ Docker 已找到: $DOCKER_PATH${NC}"
else
    echo "❌ Docker 未找到，请确保已安装"
    exit 1
fi

# 创建别名
echo ""
echo "创建 Docker 别名..."
echo ""

# 添加到 ~/.zshrc
if [ -f ~/.zshrc ]; then
    if ! grep -q "alias docker=" ~/.zshrc; then
        echo "alias docker='$DOCKER_PATH'" >> ~/.zshrc
        echo -e "${GREEN}✓ 已添加 docker 别名到 ~/.zshrc${NC}"
    else
        echo "✓ docker 别名已存在"
    fi
fi

# 添加到 ~/.bash_profile
if [ -f ~/.bash_profile ]; then
    if ! grep -q "alias docker=" ~/.bash_profile; then
        echo "alias docker='$DOCKER_PATH'" >> ~/.bash_profile
        echo -e "${GREEN}✓ 已添加 docker 别名到 ~/.bash_profile${NC}"
    else
        echo "✓ docker 别名已存在"
    fi
fi

echo ""
echo -e "${BLUE}=========================================="
echo "设置完成！"
echo "=========================================="
echo ""
echo "现在可以使用以下命令："
echo "  docker compose ps"
echo "  docker compose up -d"
echo "  docker compose down"
echo "  docker compose logs -f"
echo ""
echo "或者在新终端中运行："
echo "  source ~/.zshrc"
echo ""
