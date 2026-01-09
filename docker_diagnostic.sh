#!/bin/bash

# Docker 诊断和修复脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 诊断 Docker
diagnose_docker() {
    print_header "Docker 诊断"
    
    print_info "检查 Docker 安装..."
    if command -v docker &> /dev/null; then
        print_success "Docker 已安装"
        docker --version
    else
        print_error "Docker 未安装"
        return 1
    fi
    
    print_info "检查 Docker 运行状态..."
    if docker ps &> /dev/null; then
        print_success "Docker 正在运行"
    else
        print_error "Docker 未运行或权限不足"
        return 1
    fi
    
    print_info "检查 Docker Compose..."
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose 已安装"
        docker-compose --version
    else
        print_error "Docker Compose 未安装"
        return 1
    fi
    
    print_info "检查 Docker 磁盘空间..."
    docker system df
}

# 诊断容器
diagnose_containers() {
    print_header "容器诊断"
    
    print_info "运行中的容器："
    docker ps
    
    print_info ""
    print_info "所有容器（包括已停止）："
    docker ps -a
    
    print_info ""
    print_info "容器详细信息："
    docker-compose ps
}

# 诊断网络
diagnose_network() {
    print_header "网络诊断"
    
    print_info "Docker 网络列表："
    docker network ls
    
    print_info ""
    print_info "SuperInsight 网络详情："
    docker network inspect superinsight-network 2>/dev/null || print_warning "网络不存在"
}

# 诊断卷
diagnose_volumes() {
    print_header "卷诊断"
    
    print_info "Docker 卷列表："
    docker volume ls
    
    print_info ""
    print_info "卷详情："
    docker volume inspect superinsight-postgres 2>/dev/null || print_warning "卷不存在"
}

# 诊断服务连接
diagnose_services() {
    print_header "服务连接诊断"
    
    print_info "检查 PostgreSQL..."
    if docker-compose exec -T postgres pg_isready -U superinsight -d superinsight &> /dev/null; then
        print_success "PostgreSQL 连接正常"
    else
        print_error "PostgreSQL 连接失败"
    fi
    
    print_info "检查 Redis..."
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        print_success "Redis 连接正常"
    else
        print_error "Redis 连接失败"
    fi
    
    print_info "检查 Neo4j..."
    if curl -s http://localhost:7474 &> /dev/null; then
        print_success "Neo4j 连接正常"
    else
        print_error "Neo4j 连接失败"
    fi
    
    print_info "检查 Label Studio..."
    if curl -s http://localhost:8080/health &> /dev/null; then
        print_success "Label Studio 连接正常"
    else
        print_error "Label Studio 连接失败"
    fi
    
    print_info "检查 API..."
    if curl -s http://localhost:8000/health &> /dev/null; then
        print_success "API 连接正常"
    else
        print_error "API 连接失败"
    fi
}

# 诊断日志
diagnose_logs() {
    print_header "日志诊断"
    
    print_info "PostgreSQL 日志（最后 20 行）："
    docker-compose logs --tail=20 postgres 2>/dev/null || print_warning "无日志"
    
    print_info ""
    print_info "Redis 日志（最后 20 行）："
    docker-compose logs --tail=20 redis 2>/dev/null || print_warning "无日志"
    
    print_info ""
    print_info "Neo4j 日志（最后 20 行）："
    docker-compose logs --tail=20 neo4j 2>/dev/null || print_warning "无日志"
    
    print_info ""
    print_info "Label Studio 日志（最后 20 行）："
    docker-compose logs --tail=20 label-studio 2>/dev/null || print_warning "无日志"
    
    print_info ""
    print_info "API 日志（最后 20 行）："
    docker-compose logs --tail=20 superinsight-api 2>/dev/null || print_warning "无日志"
}

# 修复 PostgreSQL
fix_postgres() {
    print_header "修复 PostgreSQL"
    
    print_warning "停止 PostgreSQL 容器..."
    docker-compose stop postgres 2>/dev/null || true
    
    print_warning "删除 PostgreSQL 容器..."
    docker-compose rm -f postgres 2>/dev/null || true
    
    print_warning "删除 PostgreSQL 数据卷..."
    docker volume rm superinsight-postgres 2>/dev/null || true
    rm -rf data/postgres
    
    print_info "重新创建 PostgreSQL 数据目录..."
    mkdir -p data/postgres
    chmod 755 data/postgres
    
    print_info "启动 PostgreSQL..."
    docker-compose up -d postgres
    
    print_info "等待 PostgreSQL 就绪..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U superinsight -d superinsight &> /dev/null; then
            print_success "PostgreSQL 已修复"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    print_error "PostgreSQL 修复失败"
    return 1
}

# 修复所有服务
fix_all() {
    print_header "修复所有服务"
    
    print_warning "停止所有容器..."
    docker-compose down 2>/dev/null || true
    
    print_warning "删除所有卷..."
    docker-compose down -v 2>/dev/null || true
    
    print_info "清理数据目录..."
    rm -rf data/
    
    print_info "创建新的数据目录..."
    mkdir -p data/{postgres,redis,neo4j,label-studio,uploads}
    chmod -R 755 data/
    
    print_success "所有服务已修复"
    print_info "现在可以运行: bash start_fullstack.sh"
}

# 清理磁盘空间
cleanup_disk() {
    print_header "清理磁盘空间"
    
    print_info "删除未使用的镜像..."
    docker image prune -f
    
    print_info "删除未使用的容器..."
    docker container prune -f
    
    print_info "删除未使用的卷..."
    docker volume prune -f
    
    print_info "删除未使用的网络..."
    docker network prune -f
    
    print_success "磁盘清理完成"
    docker system df
}

# 显示帮助
show_help() {
    echo "Docker 诊断和修复脚本"
    echo ""
    echo "用法: bash docker_diagnostic.sh [命令]"
    echo ""
    echo "命令："
    echo "  diagnose    - 运行完整诊断"
    echo "  containers  - 诊断容器"
    echo "  network     - 诊断网络"
    echo "  volumes     - 诊断卷"
    echo "  services    - 诊断服务连接"
    echo "  logs        - 查看日志"
    echo "  fix-postgres - 修复 PostgreSQL"
    echo "  fix-all     - 修复所有服务"
    echo "  cleanup     - 清理磁盘空间"
    echo "  help        - 显示此帮助信息"
    echo ""
}

# 主函数
main() {
    case "${1:-diagnose}" in
        diagnose)
            diagnose_docker
            diagnose_containers
            diagnose_network
            diagnose_volumes
            diagnose_services
            ;;
        containers)
            diagnose_containers
            ;;
        network)
            diagnose_network
            ;;
        volumes)
            diagnose_volumes
            ;;
        services)
            diagnose_services
            ;;
        logs)
            diagnose_logs
            ;;
        fix-postgres)
            fix_postgres
            ;;
        fix-all)
            fix_all
            ;;
        cleanup)
            cleanup_disk
            ;;
        help)
            show_help
            ;;
        *)
            show_help
            exit 1
            ;;
    esac
}

main "$@"
