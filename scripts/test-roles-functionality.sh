#!/bin/bash

# 各角色功能测试脚本
# 测试管理员、标注员、专家等不同角色的功能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Docker 路径
DOCKER_PATH="/Applications/Docker.app/Contents/Resources/bin/docker"
if [ ! -f "$DOCKER_PATH" ]; then
    DOCKER="docker"
else
    DOCKER="$DOCKER_PATH"
fi

# API 基础 URL
API_BASE_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:5173"

# 测试计数
TESTS_PASSED=0
TESTS_FAILED=0

# 测试函数
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local expected_status=$4
    local data=$5
    
    echo -n "测试: $name ... "
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_BASE_URL$endpoint" \
            -H "Content-Type: application/json")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ 通过 (HTTP $http_code)${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ 失败 (期望 $expected_status, 实际 $http_code)${NC}"
        echo "  响应: $body"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "=========================================="
echo "SuperInsight 角色功能测试"
echo "=========================================="
echo ""

# 检查服务是否就绪
echo -e "${BLUE}📋 检查服务状态${NC}"
echo "---"

echo -n "检查后端服务... "
if curl -f http://localhost:8000/health/live &> /dev/null; then
    echo -e "${GREEN}✓ 后端服务就绪${NC}"
else
    echo -e "${RED}✗ 后端服务未就绪${NC}"
    exit 1
fi

echo -n "检查前端服务... "
if curl -f http://localhost:5173 &> /dev/null; then
    echo -e "${GREEN}✓ 前端服务就绪${NC}"
else
    echo -e "${RED}✗ 前端服务未就绪${NC}"
    exit 1
fi
echo ""

# ============================================================================
# 1. 系统健康检查
# ============================================================================
echo -e "${BLUE}📋 1. 系统健康检查${NC}"
echo "---"
test_endpoint "系统健康检查" "GET" "/health/live" "200"
test_endpoint "系统状态检查" "GET" "/system/status" "200"
echo ""

# ============================================================================
# 2. 管理员功能测试
# ============================================================================
echo -e "${BLUE}📋 2. 管理员功能测试${NC}"
echo "---"

# 测试管理员登录
test_endpoint "管理员登录" "POST" "/api/v1/auth/login" "200" \
    '{"username":"admin","password":"admin"}'

# 测试获取用户列表
test_endpoint "获取用户列表" "GET" "/api/v1/admin/users" "200"

# 测试获取系统配置
test_endpoint "获取系统配置" "GET" "/api/v1/admin/config" "200"

# 测试获取审计日志
test_endpoint "获取审计日志" "GET" "/api/v1/admin/audit-logs" "200"

echo ""

# ============================================================================
# 3. 标注员功能测试
# ============================================================================
echo -e "${BLUE}📋 3. 标注员功能测试${NC}"
echo "---"

# 测试标注员登录
test_endpoint "标注员登录" "POST" "/api/v1/auth/login" "200" \
    '{"username":"annotator","password":"password"}'

# 测试获取标注任务列表
test_endpoint "获取标注任务列表" "GET" "/api/v1/annotation/tasks" "200"

# 测试获取标注项目
test_endpoint "获取标注项目" "GET" "/api/v1/annotation/projects" "200"

# 测试获取质量指标
test_endpoint "获取质量指标" "GET" "/api/v1/annotation/quality-metrics" "200"

echo ""

# ============================================================================
# 4. 专家功能测试
# ============================================================================
echo -e "${BLUE}📋 4. 专家功能测试${NC}"
echo "---"

# 测试专家登录
test_endpoint "专家登录" "POST" "/api/v1/auth/login" "200" \
    '{"username":"expert","password":"password"}'

# 测试获取本体信息
test_endpoint "获取本体信息" "GET" "/api/v1/ontology/info" "200"

# 测试获取协作请求
test_endpoint "获取协作请求" "GET" "/api/v1/ontology/collaboration/requests" "200"

# 测试获取变更历史
test_endpoint "获取变更历史" "GET" "/api/v1/ontology/change-history" "200"

echo ""

# ============================================================================
# 5. 品牌系统功能测试
# ============================================================================
echo -e "${BLUE}📋 5. 品牌系统功能测试${NC}"
echo "---"

# 测试获取品牌主题
test_endpoint "获取品牌主题" "GET" "/api/v1/brand/themes" "200"

# 测试获取品牌配置
test_endpoint "获取品牌配置" "GET" "/api/v1/brand/config" "200"

# 测试获取 A/B 测试配置
test_endpoint "获取 A/B 测试配置" "GET" "/api/v1/brand/ab-tests" "200"

echo ""

# ============================================================================
# 6. 管理配置功能测试
# ============================================================================
echo -e "${BLUE}📋 6. 管理配置功能测试${NC}"
echo "---"

# 测试获取数据库配置
test_endpoint "获取数据库配置" "GET" "/api/v1/admin/config/database" "200"

# 测试获取 LLM 配置
test_endpoint "获取 LLM 配置" "GET" "/api/v1/admin/config/llm" "200"

# 测试获取同步策略
test_endpoint "获取同步策略" "GET" "/api/v1/admin/config/sync-strategy" "200"

echo ""

# ============================================================================
# 7. AI 标注功能测试
# ============================================================================
echo -e "${BLUE}📋 7. AI 标注功能测试${NC}"
echo "---"

# 测试获取 AI 标注方法
test_endpoint "获取 AI 标注方法" "GET" "/api/v1/ai/annotation-methods" "200"

# 测试获取标注缓存
test_endpoint "获取标注缓存" "GET" "/api/v1/ai/annotation-cache" "200"

# 测试获取标注指标
test_endpoint "获取标注指标" "GET" "/api/v1/ai/annotation-metrics" "200"

echo ""

# ============================================================================
# 8. 文本转 SQL 功能测试
# ============================================================================
echo -e "${BLUE}📋 8. 文本转 SQL 功能测试${NC}"
echo "---"

# 测试获取 SQL 方法
test_endpoint "获取 SQL 方法" "GET" "/api/v1/text-to-sql/methods" "200"

# 测试获取数据库架构
test_endpoint "获取数据库架构" "GET" "/api/v1/text-to-sql/schema" "200"

echo ""

# ============================================================================
# 9. 本体协作功能测试
# ============================================================================
echo -e "${BLUE}📋 9. 本体协作功能测试${NC}"
echo "---"

# 测试获取协作专家
test_endpoint "获取协作专家" "GET" "/api/v1/ontology/collaboration/experts" "200"

# 测试获取协作历史
test_endpoint "获取协作历史" "GET" "/api/v1/ontology/collaboration/history" "200"

echo ""

# ============================================================================
# 10. 前端功能测试
# ============================================================================
echo -e "${BLUE}📋 10. 前端功能测试${NC}"
echo "---"

echo -n "测试: 前端主页加载 ... "
if curl -f http://localhost:5173 &> /dev/null; then
    echo -e "${GREEN}✓ 通过${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ 失败${NC}"
    ((TESTS_FAILED++))
fi

echo ""

# ============================================================================
# 测试总结
# ============================================================================
echo -e "${BLUE}=========================================="
echo "测试总结"
echo "=========================================="
echo -e "通过: ${GREEN}$TESTS_PASSED${NC}"
echo -e "失败: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}❌ 有 $TESTS_FAILED 个测试失败${NC}"
    exit 1
fi
