#!/bin/bash

# SuperInsight 本地部署脚本
# 用法: bash deploy_local.sh [start|stop|restart|status|logs|clean]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 检查 Docker
check_docker() {
    print_info "检查 Docker 安装..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi
    print_success "Docker 已安装"
    
    if ! docker ps &> /dev/null; then
        print_error "Docker 未运行或权限不足"
        exit 1
    fi
    print_success "Docker 正在运行"
}

# 检查 Docker Compose
check_docker_compose() {
    print_info "检查 Docker Compose 安装..."
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi
    print_success "Docker Compose 已安装"
}

# 检查 Python
check_python() {
    print_info "检查 Python 安装..."
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装"
        exit 1
    fi
    print_success "Python 3 已安装"
}

# 创建环境文件
setup_env() {
    print_info "设置环境变量..."
    if [ ! -f .env ]; then
        print_warning ".env 文件不存在，正在创建..."
        cp .env.example .env
        print_success ".env 文件已创建"
        print_warning "请编辑 .env 文件配置本地环境"
    else
        print_success ".env 文件已存在"
    fi
}

# 启动服务
start_services() {
    print_header "启动 SuperInsight 服务"
    
    check_docker
    check_docker_compose
    setup_env
    
    print_info "启动 Docker 容器..."
    docker-compose up -d
    
    print_info "等待服务启动..."
    sleep 10
    
    # 检查容器状态
    print_info "检查容器状态..."
    docker-compose ps
    
    # 等待数据库就绪
    print_info "等待 PostgreSQL 就绪..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U superinsight -d superinsight &> /dev/null; then
            print_success "PostgreSQL 已就绪"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "PostgreSQL 启动超时"
            exit 1
        fi
        echo -n "."
        sleep 1
    done
    
    # 等待 Redis 就绪
    print_info "等待 Redis 就绪..."
    for i in {1..30}; do
        if docker-compose exec -T redis redis-cli ping &> /dev/null; then
            print_success "Redis 已就绪"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Redis 启动超时"
            exit 1
        fi
        echo -n "."
        sleep 1
    done
    
    # 等待 Neo4j 就绪
    print_info "等待 Neo4j 就绪..."
    for i in {1..30}; do
        if docker-compose exec -T neo4j wget -q --spider http://localhost:7474 &> /dev/null; then
            print_success "Neo4j 已就绪"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Neo4j 启动超时（可能需要更多时间）"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    # 等待 Label Studio 就绪
    print_info "等待 Label Studio 就绪..."
    for i in {1..60}; do
        if curl -s http://localhost:8080/health &> /dev/null; then
            print_success "Label Studio 已就绪"
            break
        fi
        if [ $i -eq 60 ]; then
            print_warning "Label Studio 启动超时（可能需要更多时间）"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    print_success "所有服务已启动"
}

# 初始化数据库
init_database() {
    print_header "初始化数据库"
    
    check_python
    
    print_info "安装 Python 依赖..."
    pip3 install -q -r requirements.txt
    print_success "依赖已安装"
    
    print_info "运行数据库迁移..."
    python3 -m alembic upgrade head
    print_success "数据库迁移完成"
    
    print_info "创建初始数据..."
    python3 scripts/run_migrations.py
    print_success "初始数据已创建"
}

# 启动应用
start_app() {
    print_header "启动 SuperInsight 应用"
    
    print_info "启动应用容器..."
    docker-compose up -d superinsight-api
    
    print_info "等待应用启动..."
    sleep 5
    
    # 检查应用健康状态
    print_info "检查应用健康状态..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health &> /dev/null; then
            print_success "应用已启动"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "应用启动超时"
            exit 1
        fi
        echo -n "."
        sleep 1
    done
    
    print_success "应用已启动"
}

# 完整部署
full_deploy() {
    print_header "SuperInsight 完整本地部署"
    
    start_services
    init_database
    start_app
    
    print_header "部署完成"
    print_success "SuperInsight 已成功部署"
    print_info ""
    print_info "访问地址："
    print_info "  - API: http://localhost:8000"
    print_info "  - API 文档: http://localhost:8000/docs"
    print_info "  - 系统状态: http://localhost:8000/system/status"
    print_info "  - Label Studio: http://localhost:8080"
    print_info "  - Neo4j: http://localhost:7474"
    print_info ""
    print_info "默认凭证："
    print_info "  - Label Studio: admin@superinsight.com / admin123"
    print_info "  - PostgreSQL: superinsight / password"
    print_info "  - Neo4j: neo4j / password"
    print_info ""
}

# 停止服务
stop_services() {
    print_header "停止 SuperInsight 服务"
    
    print_info "停止所有容器..."
    docker-compose down
    
    print_success "所有服务已停止"
}

# 重启服务
restart_services() {
    print_header "重启 SuperInsight 服务"
    
    stop_services
    sleep 2
    start_services
    
    print_success "服务已重启"
}

# 查看服务状态
show_status() {
    print_header "SuperInsight 服务状态"
    
    docker-compose ps
    
    print_info ""
    print_info "检查应用健康状态..."
    if curl -s http://localhost:8000/health &> /dev/null; then
        print_success "应用正在运行"
        curl -s http://localhost:8000/health | python3 -m json.tool
    else
        print_warning "应用未响应"
    fi
}

# 查看日志
show_logs() {
    print_header "SuperInsight 日志"
    
    if [ -z "$2" ]; then
        print_info "显示所有服务日志（按 Ctrl+C 退出）..."
        docker-compose logs -f
    else
        print_info "显示 $2 服务日志（按 Ctrl+C 退出）..."
        docker-compose logs -f "$2"
    fi
}

# 清理
cleanup() {
    print_header "清理 SuperInsight"
    
    read -p "确定要删除所有容器和数据吗？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_warning "删除所有容器和数据卷..."
        docker-compose down -v
        print_success "清理完成"
    else
        print_info "已取消"
    fi
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            full_deploy
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$@"
            ;;
        clean)
            cleanup
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs|clean} [service]"
            echo ""
            echo "命令："
            echo "  start      - 启动所有服务并初始化数据库"
            echo "  stop       - 停止所有服务"
            echo "  restart    - 重启所有服务"
            echo "  status     - 显示服务状态"
            echo "  logs       - 显示日志（可选指定服务名）"
            echo "  clean      - 清理所有容器和数据"
            echo ""
            echo "示例："
            echo "  $0 start                    # 启动所有服务"
            echo "  $0 logs superinsight-api    # 查看应用日志"
            echo "  $0 logs postgres            # 查看数据库日志"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
