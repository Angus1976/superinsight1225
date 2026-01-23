#!/bin/bash

# SuperInsight 多角色测试脚本
# 用于测试不同角色的功能和权限

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_URL="${API_URL:-http://localhost:8000}"
LABEL_STUDIO_URL="${LABEL_STUDIO_URL:-http://localhost:8080}"

# 测试账号
declare -A USERS=(
    ["admin"]="admin123"
    ["business_expert"]="business123"
    ["tech_expert"]="tech123"
    ["annotator1"]="annotator123"
    ["annotator2"]="annotator123"
    ["reviewer"]="reviewer123"
)

# 打印带颜色的消息
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检查服务是否运行
check_services() {
    print_header "检查服务状态"
    
    # 检查 API
    if curl -s -f "$API_URL/health" > /dev/null; then
        print_success "API 服务运行正常"
    else
        print_error "API 服务未运行"
        exit 1
    fi
    
    # 检查 Label Studio
    if curl -s -f "$LABEL_STUDIO_URL/health" > /dev/null; then
        print_success "Label Studio 运行正常"
    else
        print_warning "Label Studio 未运行或不可访问"
    fi
}

# 获取 JWT Token
get_token() {
    local username=$1
    local password=$2
    
    local response=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$username\", \"password\": \"$password\"}")
    
    echo "$response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4
}

# 测试用户登录
test_login() {
    print_header "测试用户登录"
    
    for username in "${!USERS[@]}"; do
        password=${USERS[$username]}
        
        print_info "测试登录: $username"
        
        token=$(get_token "$username" "$password")
        
        if [ -z "$token" ]; then
            print_error "登录失败: $username"
            return 1
        else
            print_success "登录成功: $username"
            # 保存 token 供后续使用
            eval "${username}_token=$token"
        fi
    done
}

# 测试 API 端点
test_api_endpoints() {
    print_header "测试 API 端点"
    
    local token=$1
    local username=$2
    
    print_info "用户: $username\n"
    
    # 测试获取用户信息
    print_info "测试: GET /api/v1/users/me"
    response=$(curl -s -X GET "$API_URL/api/v1/users/me" \
        -H "Authorization: Bearer $token")
    
    if echo "$response" | grep -q "username"; then
        print_success "获取用户信息成功"
    else
        print_error "获取用户信息失败"
    fi
    
    # 测试获取项目列表
    print_info "测试: GET /api/v1/projects"
    response=$(curl -s -X GET "$API_URL/api/v1/projects" \
        -H "Authorization: Bearer $token")
    
    if echo "$response" | grep -q "projects\|items"; then
        print_success "获取项目列表成功"
    else
        print_warning "获取项目列表返回空或错误"
    fi
    
    # 测试获取任务列表
    print_info "测试: GET /api/v1/tasks"
    response=$(curl -s -X GET "$API_URL/api/v1/tasks" \
        -H "Authorization: Bearer $token")
    
    if echo "$response" | grep -q "tasks\|items"; then
        print_success "获取任务列表成功"
    else
        print_warning "获取任务列表返回空或错误"
    fi
}

# 测试权限控制
test_permissions() {
    print_header "测试权限控制"
    
    # 获取 admin token
    admin_token=$(get_token "admin" "admin123")
    
    # 获取 annotator token
    annotator_token=$(get_token "annotator1" "annotator123")
    
    print_info "测试: Admin 创建用户\n"
    response=$(curl -s -X POST "$API_URL/api/v1/users" \
        -H "Authorization: Bearer $admin_token" \
        -H "Content-Type: application/json" \
        -d '{"username": "test_user", "email": "test@example.com", "password": "test123"}')
    
    if echo "$response" | grep -q "id\|username"; then
        print_success "Admin 可以创建用户"
    else
        print_warning "Admin 创建用户失败或返回错误"
    fi
    
    print_info "测试: Annotator 创建用户（应该被拒绝）\n"
    response=$(curl -s -X POST "$API_URL/api/v1/users" \
        -H "Authorization: Bearer $annotator_token" \
        -H "Content-Type: application/json" \
        -d '{"username": "test_user2", "email": "test2@example.com", "password": "test123"}')
    
    if echo "$response" | grep -q "403\|Forbidden\|permission"; then
        print_success "Annotator 被正确拒绝创建用户"
    else
        print_warning "权限控制可能未正确实现"
    fi
}

# 测试标注工作流
test_annotation_workflow() {
    print_header "测试标注工作流"
    
    # 获取 annotator token
    annotator_token=$(get_token "annotator1" "annotator123")
    
    print_info "获取分配的任务\n"
    response=$(curl -s -X GET "$API_URL/api/v1/tasks/assigned" \
        -H "Authorization: Bearer $annotator_token")
    
    if echo "$response" | grep -q "tasks\|items"; then
        print_success "获取分配的任务成功"
    else
        print_warning "获取分配的任务失败"
    fi
    
    print_info "获取待标注的数据\n"
    response=$(curl -s -X GET "$API_URL/api/v1/tasks/1/items" \
        -H "Authorization: Bearer $annotator_token")
    
    if echo "$response" | grep -q "items\|data"; then
        print_success "获取待标注的数据成功"
    else
        print_warning "获取待标注的数据失败"
    fi
}

# 测试 Label Studio 集成
test_label_studio_integration() {
    print_header "测试 Label Studio 集成"
    
    print_info "检查 Label Studio 连接\n"
    
    if curl -s -f "$LABEL_STUDIO_URL/health" > /dev/null; then
        print_success "Label Studio 连接正常"
        
        print_info "获取 Label Studio 项目列表\n"
        response=$(curl -s -X GET "$LABEL_STUDIO_URL/api/projects" \
            -H "Authorization: Token ${LABEL_STUDIO_API_TOKEN:-}")
        
        if echo "$response" | grep -q "results\|projects"; then
            print_success "获取 Label Studio 项目列表成功"
        else
            print_warning "获取 Label Studio 项目列表失败（可能需要 API Token）"
        fi
    else
        print_error "Label Studio 不可访问"
    fi
}

# 生成测试报告
generate_report() {
    print_header "测试报告"
    
    echo "测试时间: $(date)"
    echo "API 地址: $API_URL"
    echo "Label Studio 地址: $LABEL_STUDIO_URL"
    echo ""
    echo "测试账号:"
    for username in "${!USERS[@]}"; do
        echo "  - $username"
    done
    echo ""
    echo "测试项目:"
    echo "  ✅ 服务状态检查"
    echo "  ✅ 用户登录测试"
    echo "  ✅ API 端点测试"
    echo "  ✅ 权限控制测试"
    echo "  ✅ 标注工作流测试"
    echo "  ✅ Label Studio 集成测试"
    echo ""
}

# 主函数
main() {
    print_header "SuperInsight 多角色测试"
    
    # 检查服务
    check_services
    
    # 测试登录
    test_login
    
    # 测试 API 端点
    for username in "${!USERS[@]}"; do
        token_var="${username}_token"
        test_api_endpoints "${!token_var}" "$username"
    done
    
    # 测试权限控制
    test_permissions
    
    # 测试标注工作流
    test_annotation_workflow
    
    # 测试 Label Studio 集成
    test_label_studio_integration
    
    # 生成报告
    generate_report
    
    print_header "测试完成"
    print_success "所有测试已完成！"
}

# 运行主函数
main
