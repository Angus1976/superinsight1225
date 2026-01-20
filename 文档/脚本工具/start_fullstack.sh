#!/bin/bash

# SuperInsight 本地 Docker 全栈启动脚本
# 用法: bash start_fullstack.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    print_info "检查 Docker..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi
    if ! docker ps &> /dev/null; then
        print_error "Docker 未运行"
        exit 1
    fi
    print_success "Docker 已就绪"
}

# 检查 Docker Compose
check_docker_compose() {
    print_info "检查 Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi
    print_success "Docker Compose 已就绪"
}

# 清理旧容器
cleanup_old() {
    print_info "清理旧容器..."
    docker-compose down -v 2>/dev/null || true
    print_success "旧容器已清理"
}

# 创建目录
create_directories() {
    print_info "创建数据目录..."
    mkdir -p data/{postgres,redis,neo4j,label-studio,uploads}
    mkdir -p logs/{postgres,redis,neo4j,label-studio,api}
    chmod -R 755 data/ logs/
    print_success "目录已创建"
}

# 配置环境
setup_env() {
    print_info "配置环境变量..."
    if [ ! -f .env ]; then
        cp .env.example .env
        print_warning "已创建 .env 文件，请检查配置"
    fi
    print_success "环境已配置"
}

# 启动 PostgreSQL
start_postgres() {
    print_header "启动 PostgreSQL"
    
    docker-compose up -d postgres
    
    print_info "等待 PostgreSQL 就绪..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U superinsight -d superinsight &> /dev/null; then
            print_success "PostgreSQL 已就绪"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    print_error "PostgreSQL 启动超时"
    docker-compose logs postgres
    exit 1
}

# 启动 Redis
start_redis() {
    print_header "启动 Redis"
    
    docker-compose up -d redis
    
    print_info "等待 Redis 就绪..."
    for i in {1..30}; do
        if docker-compose exec -T redis redis-cli ping &> /dev/null; then
            print_success "Redis 已就绪"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    print_error "Redis 启动超时"
    docker-compose logs redis
    exit 1
}

# 启动 Neo4j
start_neo4j() {
    print_header "启动 Neo4j"
    
    docker-compose up -d neo4j
    
    print_info "等待 Neo4j 就绪（可能需要 30-60 秒）..."
    for i in {1..60}; do
        if curl -s http://localhost:7474 &> /dev/null; then
            print_success "Neo4j 已就绪"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    print_warning "Neo4j 启动可能需要更多时间，继续..."
}

# 启动 Label Studio
start_label_studio() {
    print_header "启动 Label Studio"
    
    docker-compose up -d label-studio
    
    print_info "等待 Label Studio 就绪（可能需要 30-60 秒）..."
    for i in {1..60}; do
        if curl -s http://localhost:8080/health &> /dev/null; then
            print_success "Label Studio 已就绪"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    print_warning "Label Studio 启动可能需要更多时间，继续..."
}

# 初始化数据库
init_database() {
    print_header "初始化数据库"
    
    print_info "安装 Python 依赖..."
    pip install -q -r requirements.txt 2>/dev/null || print_warning "依赖安装可能失败，继续..."
    
    print_info "运行数据库迁移..."
    if python -m alembic upgrade head 2>/dev/null; then
        print_success "数据库迁移完成"
    else
        print_warning "数据库迁移可能失败，继续..."
    fi
}

# 启动 API
start_api() {
    print_header "启动 SuperInsight API"
    
    docker-compose up -d superinsight-api
    
    print_info "等待 API 就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health &> /dev/null; then
            print_success "API 已就绪"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    print_warning "API 启动可能需要更多时间"
    print_info "查看日志: docker-compose logs -f superinsight-api"
}

# 验证所有服务
verify_services() {
    print_header "验证服务状态"
    
    docker-compose ps
    
    print_info ""
    print_info "服务验证结果："
    
    # 验证 PostgreSQL
    if docker-compose exec -T postgres pg_isready -U superinsight -d superinsight &> /dev/null; then
        print_success "PostgreSQL ✓"
    else
        print_error "PostgreSQL ✗"
    fi
    
    # 验证 Redis
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        print_success "Redis ✓"
    else
        print_error "Redis ✗"
    fi
    
    # 验证 Neo4j
    if curl -s http://localhost:7474 &> /dev/null; then
        print_success "Neo4j ✓"
    else
        print_error "Neo4j ✗"
    fi
    
    # 验证 Label Studio
    if curl -s http://localhost:8080/health &> /dev/null; then
        print_success "Label Studio ✓"
    else
        print_error "Label Studio ✗"
    fi
    
    # 验证 API
    if curl -s http://localhost:8000/health &> /dev/null; then
        print_success "SuperInsight API ✓"
    else
        print_warning "SuperInsight API ⏳ (可能仍在启动)"
    fi
}

# 显示访问信息
show_access_info() {
    print_header "访问信息"
    
    echo ""
    echo -e "${GREEN}服务已启动，访问地址：${NC}"
    echo ""
    echo -e "${BLUE}API 服务：${NC}"
    echo "  - API: http://localhost:8000"
    echo "  - API 文档: http://localhost:8000/docs"
    echo "  - 系统状态: http://localhost:8000/system/status"
    echo ""
    echo -e "${BLUE}标注工具：${NC}"
    echo "  - Label Studio: http://localhost:8080"
    echo "  - 用户名: admin@superinsight.com"
    echo "  - 密码: admin123"
    echo ""
    echo -e "${BLUE}数据库：${NC}"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - 用户名: superinsight"
    echo "  - 密码: password"
    echo ""
    echo -e "${BLUE}缓存：${NC}"
    echo "  - Redis: localhost:6379"
    echo ""
    echo -e "${BLUE}知识图谱：${NC}"
    echo "  - Neo4j: http://localhost:7474"
    echo "  - 用户名: neo4j"
    echo "  - 密码: password"
    echo ""
    echo -e "${BLUE}常用命令：${NC}"
    echo "  - 查看日志: docker-compose logs -f"
    echo "  - 查看特定服务日志: docker-compose logs -f superinsight-api"
    echo "  - 停止服务: docker-compose down"
    echo "  - 重启服务: docker-compose restart"
    echo ""
}

# 主函数
main() {
    print_header "SuperInsight 本地 Docker 全栈启动"
    
    check_docker
    check_docker_compose
    cleanup_old
    create_directories
    setup_env
    
    start_postgres
    start_redis
    start_neo4j
    start_label_studio
    
    init_database
    
    start_api
    
    verify_services
    show_access_info
    
    print_header "启动完成"
    print_success "SuperInsight 已成功启动！"
}

# 运行主函数
main "$@"
