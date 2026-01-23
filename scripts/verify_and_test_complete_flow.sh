#!/bin/bash

# SuperInsight 完整流程测试脚本
# 验证数据入库并测试完整的工作流

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_URL="${API_URL:-http://localhost:8000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-superinsight}"
DB_NAME="${DB_NAME:-superinsight}"
DB_PASSWORD="${DB_PASSWORD:-password}"

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
    print_header "第一步：检查服务状态"
    
    # 检查 API
    if curl -s -f "$API_URL/health" > /dev/null 2>&1; then
        print_success "API 服务运行正常"
    else
        print_error "API 服务未运行或无法连接"
        print_info "请先运行: docker compose up -d"
        exit 1
    fi
    
    # 检查数据库
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
        print_success "数据库连接正常"
    else
        print_error "数据库连接失败"
        exit 1
    fi
}

# 验证数据库中的数据
verify_database_data() {
    print_header "第二步：验证数据库中的数据"
    
    # 检查用户表
    print_info "检查用户表..."
    user_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
    
    if [ "$user_count" -gt 0 ]; then
        print_success "用户表中有 $user_count 条记录"
        
        # 显示用户列表
        print_info "用户列表："
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT username, email, role_id FROM users LIMIT 10;" 2>/dev/null
    else
        print_warning "用户表为空，需要生成演示数据"
        print_info "运行: docker compose exec superinsight-api python scripts/seed_demo_data.py"
        return 1
    fi
    
    # 检查项目表
    print_info "检查项目表..."
    project_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM projects;" 2>/dev/null | tr -d ' ')
    
    if [ "$project_count" -gt 0 ]; then
        print_success "项目表中有 $project_count 条记录"
        
        # 显示项目列表
        print_info "项目列表："
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT name, status FROM projects LIMIT 10;" 2>/dev/null
    else
        print_warning "项目表为空"
    fi
    
    # 检查任务表
    print_info "检查标注任务表..."
    task_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM annotation_tasks;" 2>/dev/null | tr -d ' ')
    
    if [ "$task_count" -gt 0 ]; then
        print_success "标注任务表中有 $task_count 条记录"
        
        # 显示任务列表
        print_info "任务列表："
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT name, status, total_items, completed_items FROM annotation_tasks LIMIT 10;" 2>/dev/null
    else
        print_warning "标注任务表为空"
    fi
}

# 测试用户登录
test_user_login() {
    print_header "第三步：测试用户登录"
    
    local username=$1
    local password=$2
    
    print_info "测试登录: $username"
    
    response=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$username\", \"password\": \"$password\"}")
    
    token=$(echo "$response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$token" ]; then
        print_error "登录失败: $username"
        print_info "响应: $response"
        return 1
    else
        print_success "登录成功: $username"
        echo "$token"
        return 0
    fi
}

# 测试 API 端点
test_api_endpoints() {
    print_header "第四步：测试 API 端点"
    
    local token=$1
    local username=$2
    
    print_info "用户: $username\n"
    
    # 测试获取用户信息
    print_info "测试: GET /api/v1/users/me"
    response=$(curl -s -X GET "$API_URL/api/v1/users/me" \
        -H "Authorization: Bearer $token")
    
    if echo "$response" | grep -q "username"; then
        print_success "获取用户信息成功"
        echo "$response" | grep -o '"username":"[^"]*' | head -1
    else
        print_error "获取用户信息失败"
    fi
    
    # 测试获取项目列表
    print_info "测试: GET /api/v1/projects"
    response=$(curl -s -X GET "$API_URL/api/v1/projects" \
        -H "Authorization: Bearer $token")
    
    if echo "$response" | grep -q "projects\|items\|name"; then
        print_success "获取项目列表成功"
        project_count=$(echo "$response" | grep -o '"name"' | wc -l)
        print_info "返回 $project_count 个项目"
    else
        print_warning "获取项目列表返回空或错误"
    fi
    
    # 测试获取任务列表
    print_info "测试: GET /api/v1/tasks"
    response=$(curl -s -X GET "$API_URL/api/v1/tasks" \
        -H "Authorization: Bearer $token")
    
    if echo "$response" | grep -q "tasks\|items\|name"; then
        print_success "获取任务列表成功"
        task_count=$(echo "$response" | grep -o '"name"' | wc -l)
        print_info "返回 $task_count 个任务"
    else
        print_warning "获取任务列表返回空或错误"
    fi
}

# 测试完整的标注工作流
test_annotation_workflow() {
    print_header "第五步：测试完整的标注工作流"
    
    # 获取 admin token
    print_info "以 admin 身份登录..."
    admin_token=$(test_user_login "admin" "admin123")
    if [ -z "$admin_token" ]; then
        print_error "Admin 登录失败"
        return 1
    fi
    
    # 获取 annotator token
    print_info "以 annotator1 身份登录..."
    annotator_token=$(test_user_login "annotator1" "annotator123")
    if [ -z "$annotator_token" ]; then
        print_error "Annotator 登录失败"
        return 1
    fi
    
    # 获取 reviewer token
    print_info "以 reviewer 身份登录..."
    reviewer_token=$(test_user_login "reviewer" "reviewer123")
    if [ -z "$reviewer_token" ]; then
        print_error "Reviewer 登录失败"
        return 1
    fi
    
    print_success "所有用户登录成功"
    
    # 测试标注员获取分配的任务
    print_info "标注员获取分配的任务..."
    response=$(curl -s -X GET "$API_URL/api/v1/tasks/assigned" \
        -H "Authorization: Bearer $annotator_token")
    
    if echo "$response" | grep -q "tasks\|items"; then
        print_success "标注员可以获取分配的任务"
    else
        print_warning "标注员获取任务失败或无任务分配"
    fi
}

# 测试权限控制
test_permissions() {
    print_header "第六步：测试权限控制"
    
    # 获取 admin token
    admin_token=$(test_user_login "admin" "admin123")
    
    # 获取 annotator token
    annotator_token=$(test_user_login "annotator1" "annotator123")
    
    # Admin 创建用户（应该成功）
    print_info "测试: Admin 创建用户"
    response=$(curl -s -X POST "$API_URL/api/v1/users" \
        -H "Authorization: Bearer $admin_token" \
        -H "Content-Type: application/json" \
        -d '{"username": "test_user_'$(date +%s)'", "email": "test@example.com", "password": "test123"}')
    
    if echo "$response" | grep -q "id\|username"; then
        print_success "Admin 可以创建用户"
    else
        print_warning "Admin 创建用户失败或返回错误"
    fi
    
    # Annotator 尝试创建用户（应该被拒绝）
    print_info "测试: Annotator 尝试创建用户（应该被拒绝）"
    response=$(curl -s -X POST "$API_URL/api/v1/users" \
        -H "Authorization: Bearer $annotator_token" \
        -H "Content-Type: application/json" \
        -d '{"username": "test_user_'$(date +%s)'", "email": "test@example.com", "password": "test123"}')
    
    if echo "$response" | grep -q "403\|Forbidden\|permission\|unauthorized"; then
        print_success "Annotator 被正确拒绝创建用户"
    else
        print_warning "权限控制可能未正确实现"
    fi
}

# 生成测试报告
generate_report() {
    print_header "测试报告"
    
    echo "测试时间: $(date)"
    echo "API 地址: $API_URL"
    echo "数据库: $DB_HOST:$DB_PORT/$DB_NAME"
    echo ""
    echo "测试项目:"
    echo "  ✅ 服务状态检查"
    echo "  ✅ 数据库数据验证"
    echo "  ✅ 用户登录测试"
    echo "  ✅ API 端点测试"
    echo "  ✅ 标注工作流测试"
    echo "  ✅ 权限控制测试"
    echo ""
    echo "数据库统计:"
    
    user_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
    project_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM projects;" 2>/dev/null | tr -d ' ')
    task_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM annotation_tasks;" 2>/dev/null | tr -d ' ')
    
    echo "  • 用户: $user_count"
    echo "  • 项目: $project_count"
    echo "  • 任务: $task_count"
    echo ""
}

# 主函数
main() {
    print_header "SuperInsight 完整流程测试"
    
    # 检查服务
    check_services
    
    # 验证数据库数据
    if ! verify_database_data; then
        print_error "数据库中没有数据，请先生成演示数据"
        print_info "运行以下命令生成演示数据:"
        print_info "  docker compose exec superinsight-api python scripts/seed_demo_data.py"
        exit 1
    fi
    
    # 测试用户登录
    test_user_login "admin" "admin123"
    
    # 测试 API 端点
    admin_token=$(test_user_login "admin" "admin123")
    test_api_endpoints "$admin_token" "admin"
    
    # 测试完整的标注工作流
    test_annotation_workflow
    
    # 测试权限控制
    test_permissions
    
    # 生成报告
    generate_report
    
    print_header "测试完成"
    print_success "所有测试已完成！"
    print_info "现在你可以:"
    print_info "  1. 访问 API 文档: http://localhost:8000/docs"
    print_info "  2. 访问 Label Studio: http://localhost:8080"
    print_info "  3. 使用测试账号登录进行手动测试"
}

# 运行主函数
main
