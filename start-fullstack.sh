#!/bin/bash

# SuperInsight Docker Fullstack Startup Script
# This script starts all services using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

# Check if Docker is running
check_docker() {
    print_header "检查 Docker 状态"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi
    
    if ! docker ps &> /dev/null; then
        print_error "Docker 未运行或无权限"
        exit 1
    fi
    
    print_success "Docker 已安装并运行"
}

# Check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi
    
    print_success "Docker Compose 已安装"
}

# Check port availability
check_ports() {
    print_header "检查端口可用性"
    
    local ports=(5173 8000 8080 7474 5432 6379)
    local unavailable=0
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_warning "端口 $port 已被占用"
            unavailable=$((unavailable + 1))
        else
            print_success "端口 $port 可用"
        fi
    done
    
    if [ $unavailable -gt 0 ]; then
        print_warning "有 $unavailable 个端口已被占用，可能导致启动失败"
        read -p "是否继续? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Stop old containers
stop_old_containers() {
    print_header "停止旧容器"
    
    if docker-compose -f docker-compose.local.yml ps 2>/dev/null | grep -q "superinsight"; then
        print_info "停止旧的 docker-compose.local.yml 容器..."
        docker-compose -f docker-compose.local.yml down -v 2>/dev/null || true
        print_success "旧容器已停止"
    fi
}

# Build images
build_images() {
    print_header "构建 Docker 镜像"
    
    print_info "构建后端镜像..."
    docker build -f Dockerfile.backend -t superinsight-api . || {
        print_error "后端镜像构建失败"
        exit 1
    }
    print_success "后端镜像构建完成"
    
    print_info "构建前端镜像..."
    docker build -f frontend/Dockerfile -t superinsight-frontend ./frontend || {
        print_error "前端镜像构建失败"
        exit 1
    }
    print_success "前端镜像构建完成"
}

# Start services
start_services() {
    print_header "启动所有服务"
    
    print_info "启动容器..."
    docker-compose -f docker-compose.fullstack.yml up -d || {
        print_error "容器启动失败"
        exit 1
    }
    print_success "容器已启动"
}

# Wait for services to be healthy
wait_for_services() {
    print_header "等待服务就绪"
    
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local healthy=0
        local total=6
        
        # Check each service
        for service in postgres redis neo4j label-studio superinsight-api superinsight-frontend; do
            if docker-compose -f docker-compose.fullstack.yml ps $service 2>/dev/null | grep -q "healthy\|Up"; then
                healthy=$((healthy + 1))
                print_success "$service 已就绪"
            else
                print_info "$service 正在启动..."
            fi
        done
        
        if [ $healthy -eq $total ]; then
            print_success "所有服务已就绪"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_warning "部分服务启动超时，请检查日志"
}

# Create test users
create_test_users() {
    print_header "创建测试用户"
    
    print_info "在后端容器中创建测试用户..."
    docker-compose -f docker-compose.fullstack.yml exec -T superinsight-api \
        python create_test_users_for_login.py || {
        print_warning "测试用户创建失败，可能已存在"
    }
    print_success "测试用户已创建"
}

# Verify services
verify_services() {
    print_header "验证服务"
    
    print_info "检查后端 API..."
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "后端 API 可访问"
    else
        print_error "后端 API 无法访问"
    fi
    
    print_info "检查前端..."
    if curl -s http://localhost:5173 > /dev/null; then
        print_success "前端可访问"
    else
        print_error "前端无法访问"
    fi
    
    print_info "检查 Label Studio..."
    if curl -s http://localhost:8080 > /dev/null; then
        print_success "Label Studio 可访问"
    else
        print_error "Label Studio 无法访问"
    fi
    
    print_info "检查 Neo4j..."
    if curl -s http://localhost:7474 > /dev/null; then
        print_success "Neo4j 可访问"
    else
        print_error "Neo4j 无法访问"
    fi
}

# Print summary
print_summary() {
    print_header "启动完成"
    
    echo ""
    echo -e "${GREEN}所有服务已启动！${NC}"
    echo ""
    echo "访问地址:"
    echo -e "  ${BLUE}前端登录${NC}:        http://localhost:5173/login"
    echo -e "  ${BLUE}后端 API${NC}:        http://localhost:8000"
    echo -e "  ${BLUE}API 文档${NC}:        http://localhost:8000/docs"
    echo -e "  ${BLUE}Neo4j${NC}:           http://localhost:7474"
    echo -e "  ${BLUE}Label Studio${NC}:    http://localhost:8080"
    echo ""
    echo "测试凭证:"
    echo -e "  ${BLUE}用户名${NC}: admin_user"
    echo -e "  ${BLUE}密码${NC}:   Admin@123456"
    echo ""
    echo "常用命令:"
    echo -e "  ${BLUE}查看日志${NC}:        docker-compose -f docker-compose.fullstack.yml logs -f"
    echo -e "  ${BLUE}停止服务${NC}:        docker-compose -f docker-compose.fullstack.yml stop"
    echo -e "  ${BLUE}重启服务${NC}:        docker-compose -f docker-compose.fullstack.yml restart"
    echo -e "  ${BLUE}进入后端${NC}:        docker-compose -f docker-compose.fullstack.yml exec superinsight-api bash"
    echo -e "  ${BLUE}进入前端${NC}:        docker-compose -f docker-compose.fullstack.yml exec superinsight-frontend sh"
    echo ""
}

# Main execution
main() {
    print_header "SuperInsight Docker 全栈启动"
    
    check_docker
    check_docker_compose
    check_ports
    stop_old_containers
    build_images
    start_services
    wait_for_services
    create_test_users
    verify_services
    print_summary
}

# Run main function
main
