#!/bin/bash

# SuperInsight 一键启动脚本
# 用途：检查环境、初始化配置、启动所有服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
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

# 打印横幅
print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║           SuperInsight AI 数据治理与标注平台              ║"
    echo "║                                                           ║"
    echo "║                   一键部署启动脚本                        ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        return 1
    else
        print_success "$1 已安装"
        return 0
    fi
}

# 检查 Docker 环境
check_docker() {
    print_info "检查 Docker 环境..."
    
    if ! check_command docker; then
        print_error "请先安装 Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker 未运行，请启动 Docker"
        exit 1
    fi
    
    # 检查 Docker Compose
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
        print_success "Docker Compose (V2) 已安装"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
        print_success "Docker Compose (V1) 已安装"
    else
        print_error "Docker Compose 未安装"
        exit 1
    fi
}

# 初始化环境变量
init_env() {
    print_info "初始化环境变量..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            print_info "从 .env.example 创建 .env 文件..."
            cp .env.example .env
            print_success ".env 文件已创建"
            print_warning "请编辑 .env 文件，配置必要的环境变量（如数据库密码、API密钥等）"
        else
            print_warning ".env.example 不存在，创建默认 .env 文件..."
            cat > .env << 'EOF'
# SuperInsight 环境变量配置

# 数据库配置
POSTGRES_DB=superinsight
POSTGRES_USER=superinsight
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_PORT=5432

# Redis 配置
REDIS_PORT=6379

# Neo4j 配置
NEO4J_AUTH=neo4j/change_me_in_production

# Label Studio 配置
LABEL_STUDIO_PORT=8080
LABEL_STUDIO_HOST=http://localhost:8080
LABEL_STUDIO_USERNAME=admin@superinsight.com
LABEL_STUDIO_PASSWORD=change_me_in_production

# API 配置
API_PORT=8000
DEBUG=true

# Ollama 配置（可选）
OLLAMA_PORT=11434
OLLAMA_BASE_URL=http://localhost:11434

# LLM API 密钥（可选）
# OPENAI_API_KEY=your_openai_key
# AZURE_API_KEY=your_azure_key
# HUGGINGFACE_API_KEY=your_huggingface_key

# 日志级别
LOG_LEVEL=INFO
EOF
            print_success "默认 .env 文件已创建"
            print_warning "请编辑 .env 文件，修改默认密码和配置"
        fi
    else
        print_success ".env 文件已存在"
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    directories=(
        "data/postgres"
        "data/redis"
        "data/neo4j"
        "data/label-studio"
        "data/ollama"
        "logs/postgres"
        "logs/redis"
        "logs/neo4j"
        "logs/label-studio"
        "logs/api"
        "logs/ollama"
        "uploads"
        "exports"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "创建目录: $dir"
        fi
    done
}

# 停止现有服务
stop_services() {
    print_info "停止现有服务..."
    $DOCKER_COMPOSE_CMD down 2>/dev/null || true
    print_success "现有服务已停止"
}

# 拉取最新镜像
pull_images() {
    print_info "拉取最新 Docker 镜像..."
    $DOCKER_COMPOSE_CMD pull
    print_success "镜像拉取完成"
}

# 启动服务
start_services() {
    print_info "启动所有服务..."
    
    # 启动基础服务（数据库）
    print_info "启动数据库服务..."
    $DOCKER_COMPOSE_CMD up -d postgres redis neo4j
    
    # 等待数据库就绪
    print_info "等待数据库就绪..."
    sleep 10
    
    # 启动 Label Studio
    print_info "启动 Label Studio..."
    $DOCKER_COMPOSE_CMD up -d label-studio
    
    # 等待 Label Studio 就绪
    print_info "等待 Label Studio 就绪..."
    sleep 15
    
    # 启动 API 服务
    print_info "启动 API 服务..."
    $DOCKER_COMPOSE_CMD up -d superinsight-api
    
    print_success "所有服务已启动"
}

# 检查服务健康状态
check_health() {
    print_info "检查服务健康状态..."
    
    echo ""
    $DOCKER_COMPOSE_CMD ps
    echo ""
    
    # 等待服务完全启动
    print_info "等待服务完全启动（30秒）..."
    sleep 30
    
    # 检查各个服务
    services=(
        "postgres:5432"
        "redis:6379"
        "neo4j:7474"
        "label-studio:8080"
        "superinsight-api:8000"
    )
    
    all_healthy=true
    
    for service in "${services[@]}"; do
        name="${service%%:*}"
        port="${service##*:}"
        
        if $DOCKER_COMPOSE_CMD ps | grep -q "$name.*Up"; then
            print_success "$name 运行正常"
        else
            print_error "$name 未运行"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        print_success "所有服务健康检查通过"
    else
        print_warning "部分服务未正常运行，请检查日志"
    fi
}

# 显示访问信息
show_access_info() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║                  🎉 部署成功！                            ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}📍 访问地址：${NC}"
    echo ""
    echo -e "  ${YELLOW}API 文档：${NC}      http://localhost:8000/docs"
    echo -e "  ${YELLOW}API 健康检查：${NC}  http://localhost:8000/health"
    echo -e "  ${YELLOW}Label Studio：${NC} http://localhost:8080"
    echo -e "  ${YELLOW}Neo4j 浏览器：${NC} http://localhost:7474"
    echo ""
    echo -e "${BLUE}👤 默认登录信息：${NC}"
    echo ""
    echo -e "  ${YELLOW}Label Studio：${NC}"
    echo -e "    用户名: admin@superinsight.com"
    echo -e "    密码: 见 .env 文件中的 LABEL_STUDIO_PASSWORD"
    echo ""
    echo -e "  ${YELLOW}Neo4j：${NC}"
    echo -e "    用户名: neo4j"
    echo -e "    密码: 见 .env 文件中的 NEO4J_AUTH"
    echo ""
    echo -e "  ${YELLOW}API 测试用户：${NC}"
    echo -e "    admin / 任意密码"
    echo -e "    business_expert / 任意密码"
    echo -e "    tech_expert / 任意密码"
    echo -e "    annotator1 / 任意密码"
    echo ""
    echo -e "${BLUE}📝 常用命令：${NC}"
    echo ""
    echo -e "  查看日志:     ${YELLOW}$DOCKER_COMPOSE_CMD logs -f${NC}"
    echo -e "  停止服务:     ${YELLOW}$DOCKER_COMPOSE_CMD down${NC}"
    echo -e "  重启服务:     ${YELLOW}$DOCKER_COMPOSE_CMD restart${NC}"
    echo -e "  查看状态:     ${YELLOW}$DOCKER_COMPOSE_CMD ps${NC}"
    echo ""
}

# 主函数
main() {
    print_banner
    
    # 检查 Docker 环境
    check_docker
    
    # 初始化环境变量
    init_env
    
    # 创建必要的目录
    create_directories
    
    # 询问是否继续
    echo ""
    read -p "是否继续启动服务？(y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "已取消启动"
        exit 0
    fi
    
    # 停止现有服务
    stop_services
    
    # 拉取最新镜像
    pull_images
    
    # 启动服务
    start_services
    
    # 检查健康状态
    check_health
    
    # 显示访问信息
    show_access_info
}

# 运行主函数
main
