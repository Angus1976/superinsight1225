#!/bin/bash

# SuperInsight 停止脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测 Docker Compose 命令
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    print_error "Docker Compose 未安装"
    exit 1
fi

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║           SuperInsight 服务停止脚本                       ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 询问是否保留数据
echo ""
echo -e "${YELLOW}请选择停止方式：${NC}"
echo ""
echo "  1) 停止服务（保留数据）"
echo "  2) 停止服务并删除所有数据（⚠️  不可恢复）"
echo "  3) 仅停止特定服务"
echo "  4) 取消"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        print_info "停止所有服务（保留数据）..."
        $DOCKER_COMPOSE_CMD down
        print_success "服务已停止，数据已保留"
        ;;
    2)
        print_warning "⚠️  这将删除所有数据，包括数据库、上传文件等"
        read -p "确认删除所有数据？(yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            print_info "停止服务并删除所有数据..."
            $DOCKER_COMPOSE_CMD down -v
            print_success "服务已停止，所有数据已删除"
        else
            print_info "已取消"
        fi
        ;;
    3)
        echo ""
        echo "可用服务："
        $DOCKER_COMPOSE_CMD ps --services
        echo ""
        read -p "请输入要停止的服务名称（空格分隔）: " services
        if [ -n "$services" ]; then
            print_info "停止服务: $services"
            $DOCKER_COMPOSE_CMD stop $services
            print_success "服务已停止: $services"
        else
            print_info "未输入服务名称，已取消"
        fi
        ;;
    4)
        print_info "已取消"
        exit 0
        ;;
    *)
        print_error "无效选项"
        exit 1
        ;;
esac

echo ""
print_info "当前服务状态："
$DOCKER_COMPOSE_CMD ps
echo ""
