#!/bin/bash

# SuperInsight TCB 部署脚本
# 用于通过本地推送方式部署到腾讯云 CloudBase

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

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║         SuperInsight 腾讯云 TCB 部署脚本                  ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查 TCB CLI
check_tcb_cli() {
    print_info "检查 TCB CLI..."
    
    if ! command -v tcb &> /dev/null; then
        print_error "TCB CLI 未安装"
        print_info "请运行以下命令安装："
        echo "  npm install -g @cloudbase/cli"
        exit 1
    fi
    
    print_success "TCB CLI 已安装: $(tcb --version | head -1)"
}

# 登录 TCB
login_tcb() {
    print_info "检查 TCB 登录状态..."
    
    # 尝试列出环境来检查登录状态
    if ! tcb env:list &> /dev/null; then
        print_warning "未登录或登录已过期"
        print_info "正在启动登录流程..."
        
        tcb login
        
        if [ $? -eq 0 ]; then
            print_success "登录成功"
        else
            print_error "登录失败"
            exit 1
        fi
    else
        print_success "已登录 TCB"
    fi
}

# 选择或创建环境
select_environment() {
    print_info "选择部署环境..."
    
    echo ""
    print_info "可用环境列表："
    tcb env:list
    echo ""
    
    read -p "请输入环境 ID（或按回车创建新环境）: " ENV_ID
    
    if [ -z "$ENV_ID" ]; then
        print_info "创建新环境..."
        read -p "请输入新环境名称: " ENV_NAME
        read -p "请选择地域 (ap-shanghai/ap-guangzhou/ap-beijing): " REGION
        
        tcb env:create --name "$ENV_NAME" --region "${REGION:-ap-shanghai}"
        
        # 获取新创建的环境 ID
        ENV_ID=$(tcb env:list | grep "$ENV_NAME" | awk '{print $1}')
        print_success "环境创建成功: $ENV_ID"
    fi
    
    export TCB_ENV_ID="$ENV_ID"
    print_success "使用环境: $TCB_ENV_ID"
}

# 配置环境变量
configure_env_vars() {
    print_info "配置环境变量..."
    
    if [ ! -f .env.tcb ]; then
        print_warning ".env.tcb 不存在，从 .env.example 创建..."
        
        cat > .env.tcb << 'EOF'
# TCB 部署环境变量

# TCB 配置
TCB_ENV_ID=your_env_id
TCB_REGION=ap-shanghai
DOMAIN_NAME=your-domain.com

# 数据库配置
POSTGRES_USER=superinsight
POSTGRES_PASSWORD=change_me_strong_password
POSTGRES_DB=superinsight

# 安全配置
SECRET_KEY=change_me_random_secret_key
JWT_SECRET_KEY=change_me_jwt_secret_key

# 腾讯云服务配置
HUNYUAN_API_KEY=your_hunyuan_api_key
HUNYUAN_SECRET_KEY=your_hunyuan_secret_key

# COS 对象存储配置
COS_REGION=ap-shanghai
COS_BUCKET=your-bucket-name
COS_SECRET_ID=your_cos_secret_id
COS_SECRET_KEY=your_cos_secret_key

# Label Studio 配置
LABEL_STUDIO_USERNAME=admin@superinsight.com
LABEL_STUDIO_PASSWORD=change_me_strong_password
EOF
        
        print_success ".env.tcb 已创建"
        print_warning "请编辑 .env.tcb 文件，配置必要的环境变量"
        
        read -p "是否现在编辑 .env.tcb？(y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env.tcb
        else
            print_warning "请手动编辑 .env.tcb 后重新运行此脚本"
            exit 0
        fi
    fi
    
    # 加载环境变量
    source .env.tcb
    print_success "环境变量已加载"
}

# 构建 Docker 镜像
build_docker_image() {
    print_info "构建 Docker 镜像..."
    
    # 选择构建类型
    echo ""
    echo "请选择构建类型："
    echo "  1) API 服务（仅后端）"
    echo "  2) 完整栈（包含数据库和 Label Studio）"
    echo "  3) Worker 服务（后台任务）"
    echo ""
    read -p "请选择 (1-3): " BUILD_TYPE
    
    case $BUILD_TYPE in
        1)
            DOCKERFILE="deploy/tcb/Dockerfile.api"
            IMAGE_NAME="superinsight-api"
            ;;
        2)
            DOCKERFILE="deploy/tcb/Dockerfile.fullstack"
            IMAGE_NAME="superinsight-fullstack"
            ;;
        3)
            DOCKERFILE="deploy/tcb/Dockerfile.worker"
            IMAGE_NAME="superinsight-worker"
            ;;
        *)
            print_error "无效选择"
            exit 1
            ;;
    esac
    
    print_info "使用 Dockerfile: $DOCKERFILE"
    print_info "构建镜像: $IMAGE_NAME"
    
    docker build -t "$IMAGE_NAME:latest" -f "$DOCKERFILE" .
    
    if [ $? -eq 0 ]; then
        print_success "镜像构建成功"
    else
        print_error "镜像构建失败"
        exit 1
    fi
    
    export IMAGE_NAME
}

# 推送镜像到 TCB
push_to_tcb() {
    print_info "推送镜像到 TCB 容器镜像服务..."
    
    # TCB 容器镜像仓库地址
    TCB_REGISTRY="ccr.ccs.tencentyun.com"
    TCB_NAMESPACE="tcb_${TCB_ENV_ID}"
    
    # 标记镜像
    REMOTE_IMAGE="${TCB_REGISTRY}/${TCB_NAMESPACE}/${IMAGE_NAME}:latest"
    
    print_info "标记镜像: $REMOTE_IMAGE"
    docker tag "${IMAGE_NAME}:latest" "$REMOTE_IMAGE"
    
    # 登录到 TCB 容器镜像仓库
    print_info "登录到容器镜像仓库..."
    tcb cloudrun:login
    
    # 推送镜像
    print_info "推送镜像（这可能需要几分钟）..."
    docker push "$REMOTE_IMAGE"
    
    if [ $? -eq 0 ]; then
        print_success "镜像推送成功"
    else
        print_error "镜像推送失败"
        exit 1
    fi
    
    export REMOTE_IMAGE
}

# 部署到 TCB CloudRun
deploy_to_cloudrun() {
    print_info "部署到 TCB CloudRun..."
    
    # 创建或更新服务
    SERVICE_NAME="superinsight-${IMAGE_NAME}"
    
    print_info "服务名称: $SERVICE_NAME"
    
    # 检查服务是否存在
    if tcb cloudrun:service:describe --service-name "$SERVICE_NAME" --env-id "$TCB_ENV_ID" &> /dev/null; then
        print_info "服务已存在，更新服务..."
        ACTION="update"
    else
        print_info "创建新服务..."
        ACTION="create"
    fi
    
    # 准备部署配置
    cat > /tmp/cloudrun-config.json << EOF
{
  "serviceName": "$SERVICE_NAME",
  "image": "$REMOTE_IMAGE",
  "cpu": 2,
  "mem": 4,
  "minNum": 1,
  "maxNum": 10,
  "containerPort": 8000,
  "envParams": {
    "TCB_ENV_ID": "$TCB_ENV_ID",
    "TCB_REGION": "$TCB_REGION",
    "POSTGRES_USER": "$POSTGRES_USER",
    "POSTGRES_PASSWORD": "$POSTGRES_PASSWORD",
    "POSTGRES_DB": "$POSTGRES_DB",
    "SECRET_KEY": "$SECRET_KEY",
    "JWT_SECRET_KEY": "$JWT_SECRET_KEY",
    "HUNYUAN_API_KEY": "$HUNYUAN_API_KEY",
    "HUNYUAN_SECRET_KEY": "$HUNYUAN_SECRET_KEY",
    "COS_REGION": "$COS_REGION",
    "COS_BUCKET": "$COS_BUCKET",
    "COS_SECRET_ID": "$COS_SECRET_ID",
    "COS_SECRET_KEY": "$COS_SECRET_KEY"
  },
  "customLogs": "stdout",
  "initialDelaySeconds": 60,
  "dataBaseName": "superinsight",
  "policyType": "cpu",
  "policyThreshold": 70
}
EOF
    
    # 部署服务
    if [ "$ACTION" = "create" ]; then
        tcb cloudrun:service:create \
            --env-id "$TCB_ENV_ID" \
            --config-file /tmp/cloudrun-config.json
    else
        tcb cloudrun:service:update \
            --env-id "$TCB_ENV_ID" \
            --service-name "$SERVICE_NAME" \
            --config-file /tmp/cloudrun-config.json
    fi
    
    if [ $? -eq 0 ]; then
        print_success "服务部署成功"
    else
        print_error "服务部署失败"
        exit 1
    fi
    
    # 清理临时文件
    rm -f /tmp/cloudrun-config.json
}

# 配置数据库
setup_database() {
    print_info "配置数据库..."
    
    # 检查是否已有 PostgreSQL 实例
    print_info "检查 PostgreSQL 数据库..."
    
    # 这里需要根据实际情况配置
    # TCB 可能需要使用腾讯云数据库 TencentDB for PostgreSQL
    
    print_warning "请确保已在腾讯云控制台创建 PostgreSQL 数据库实例"
    print_info "数据库配置信息应该已在 .env.tcb 中配置"
}

# 配置 COS 存储
setup_cos() {
    print_info "配置 COS 对象存储..."
    
    # 检查 COS 存储桶
    print_info "检查 COS 存储桶: $COS_BUCKET"
    
    # 创建存储桶（如果不存在）
    tcb storage:create-bucket \
        --env-id "$TCB_ENV_ID" \
        --bucket "$COS_BUCKET" \
        --region "$COS_REGION" 2>/dev/null || true
    
    print_success "COS 存储配置完成"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║                  🎉 部署成功！                            ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}📍 部署信息：${NC}"
    echo ""
    echo -e "  ${YELLOW}环境 ID：${NC}      $TCB_ENV_ID"
    echo -e "  ${YELLOW}地域：${NC}         $TCB_REGION"
    echo -e "  ${YELLOW}服务名称：${NC}     $SERVICE_NAME"
    echo -e "  ${YELLOW}镜像：${NC}         $REMOTE_IMAGE"
    echo ""
    echo -e "${BLUE}🔗 访问地址：${NC}"
    echo ""
    
    # 获取服务访问地址
    SERVICE_URL=$(tcb cloudrun:service:describe --service-name "$SERVICE_NAME" --env-id "$TCB_ENV_ID" 2>/dev/null | grep -o 'https://[^"]*' | head -1)
    
    if [ -n "$SERVICE_URL" ]; then
        echo -e "  ${YELLOW}API 文档：${NC}      ${SERVICE_URL}/docs"
        echo -e "  ${YELLOW}健康检查：${NC}     ${SERVICE_URL}/health"
        echo -e "  ${YELLOW}Label Studio：${NC} ${SERVICE_URL}:8080"
    else
        print_warning "无法获取服务地址，请在 TCB 控制台查看"
    fi
    
    echo ""
    echo -e "${BLUE}📝 后续步骤：${NC}"
    echo ""
    echo "  1. 访问 TCB 控制台查看服务状态"
    echo "  2. 配置自定义域名（可选）"
    echo "  3. 配置 SSL 证书（可选）"
    echo "  4. 查看服务日志"
    echo ""
    echo -e "${BLUE}🔧 常用命令：${NC}"
    echo ""
    echo -e "  查看服务列表:   ${YELLOW}tcb cloudrun:service:list --env-id $TCB_ENV_ID${NC}"
    echo -e "  查看服务详情:   ${YELLOW}tcb cloudrun:service:describe --service-name $SERVICE_NAME --env-id $TCB_ENV_ID${NC}"
    echo -e "  查看服务日志:   ${YELLOW}tcb cloudrun:service:log --service-name $SERVICE_NAME --env-id $TCB_ENV_ID${NC}"
    echo -e "  删除服务:       ${YELLOW}tcb cloudrun:service:delete --service-name $SERVICE_NAME --env-id $TCB_ENV_ID${NC}"
    echo ""
}

# 主函数
main() {
    print_banner
    
    # 检查 TCB CLI
    check_tcb_cli
    
    # 登录 TCB
    login_tcb
    
    # 选择环境
    select_environment
    
    # 配置环境变量
    configure_env_vars
    
    # 询问是否继续
    echo ""
    read -p "是否继续部署到 TCB？(y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "已取消部署"
        exit 0
    fi
    
    # 构建 Docker 镜像
    build_docker_image
    
    # 推送镜像到 TCB
    push_to_tcb
    
    # 配置数据库
    setup_database
    
    # 配置 COS 存储
    setup_cos
    
    # 部署到 CloudRun
    deploy_to_cloudrun
    
    # 显示部署信息
    show_deployment_info
}

# 运行主函数
main
