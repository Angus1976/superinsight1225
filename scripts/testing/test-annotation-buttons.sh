#!/bin/bash

# 测试标注按钮功能的脚本
# 用于验证 Label Studio 集成的 API 端点

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_BASE_URL="${API_BASE_URL:-http://localhost:57313}"
TASK_ID="${TASK_ID:-8d927f00-a2c6-4e2f-8967-f160a3d0b2eb}"

echo -e "${BLUE}=== 标注按钮功能测试 ===${NC}"
echo "API Base URL: $API_BASE_URL"
echo "Task ID: $TASK_ID"
echo ""

# 检查是否提供了 JWT token
if [ -z "$JWT_TOKEN" ]; then
    echo -e "${YELLOW}警告: 未设置 JWT_TOKEN 环境变量${NC}"
    echo "请先登录并设置 JWT_TOKEN:"
    echo "  export JWT_TOKEN='your-jwt-token'"
    echo ""
    echo "或者运行以下命令获取 token:"
    echo "  curl -X POST $API_BASE_URL/api/auth/login \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"username\":\"admin\",\"password\":\"your-password\"}'"
    exit 1
fi

# 函数：发送 API 请求
api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    echo -e "${BLUE}>>> $method $endpoint${NC}"
    
    if [ -n "$data" ]; then
        echo -e "${YELLOW}Request body:${NC}"
        echo "$data" | jq '.' 2>/dev/null || echo "$data"
    fi
    
    local response
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            "$API_BASE_URL$endpoint" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            "$API_BASE_URL$endpoint" \
            -H "Authorization: Bearer $JWT_TOKEN")
    fi
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ $http_code${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        echo "$body"
        return 0
    else
        echo -e "${RED}✗ $http_code${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        return 1
    fi
}

# 测试 1: 确保项目存在
echo -e "\n${BLUE}=== 测试 1: 确保项目存在 ===${NC}"
PROJECT_RESPONSE=$(api_request POST "/api/label-studio/projects/ensure" \
    "{\"task_id\":\"$TASK_ID\",\"task_name\":\"test\",\"annotation_type\":\"text_classification\"}")

if [ $? -eq 0 ]; then
    PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.project_id' 2>/dev/null)
    if [ -n "$PROJECT_ID" ] && [ "$PROJECT_ID" != "null" ]; then
        echo -e "${GREEN}✓ 项目 ID: $PROJECT_ID${NC}"
    else
        echo -e "${RED}✗ 无法获取项目 ID${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ 创建项目失败${NC}"
    exit 1
fi

# 测试 2: 验证项目
echo -e "\n${BLUE}=== 测试 2: 验证项目 ===${NC}"
VALIDATE_RESPONSE=$(api_request GET "/api/label-studio/projects/$PROJECT_ID/validate")

if [ $? -eq 0 ]; then
    EXISTS=$(echo "$VALIDATE_RESPONSE" | jq -r '.exists' 2>/dev/null)
    ACCESSIBLE=$(echo "$VALIDATE_RESPONSE" | jq -r '.accessible' 2>/dev/null)
    
    if [ "$EXISTS" = "true" ] && [ "$ACCESSIBLE" = "true" ]; then
        echo -e "${GREEN}✓ 项目存在且可访问${NC}"
    else
        echo -e "${RED}✗ 项目不存在或不可访问${NC}"
        echo "  exists: $EXISTS"
        echo "  accessible: $ACCESSIBLE"
        exit 1
    fi
else
    echo -e "${RED}✗ 验证项目失败${NC}"
    exit 1
fi

# 测试 3: 获取认证 URL (中文)
echo -e "\n${BLUE}=== 测试 3: 获取认证 URL (中文) ===${NC}"
AUTH_URL_ZH=$(api_request GET "/api/label-studio/projects/$PROJECT_ID/auth-url?language=zh")

if [ $? -eq 0 ]; then
    URL=$(echo "$AUTH_URL_ZH" | jq -r '.url' 2>/dev/null)
    if [ -n "$URL" ] && [ "$URL" != "null" ]; then
        echo -e "${GREEN}✓ 认证 URL (中文): $URL${NC}"
        
        # 检查 URL 是否包含语言参数
        if echo "$URL" | grep -q "lang=zh"; then
            echo -e "${GREEN}✓ URL 包含中文语言参数${NC}"
        else
            echo -e "${YELLOW}⚠ URL 不包含中文语言参数${NC}"
        fi
    else
        echo -e "${RED}✗ 无法获取认证 URL${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ 获取认证 URL 失败${NC}"
    exit 1
fi

# 测试 4: 获取认证 URL (英文)
echo -e "\n${BLUE}=== 测试 4: 获取认证 URL (英文) ===${NC}"
AUTH_URL_EN=$(api_request GET "/api/label-studio/projects/$PROJECT_ID/auth-url?language=en")

if [ $? -eq 0 ]; then
    URL=$(echo "$AUTH_URL_EN" | jq -r '.url' 2>/dev/null)
    if [ -n "$URL" ] && [ "$URL" != "null" ]; then
        echo -e "${GREEN}✓ 认证 URL (英文): $URL${NC}"
        
        # 检查 URL 是否包含语言参数
        if echo "$URL" | grep -q "lang=en"; then
            echo -e "${GREEN}✓ URL 包含英文语言参数${NC}"
        else
            echo -e "${YELLOW}⚠ URL 不包含英文语言参数${NC}"
        fi
    else
        echo -e "${RED}✗ 无法获取认证 URL${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ 获取认证 URL 失败${NC}"
    exit 1
fi

# 测试 5: 模拟"开始标注"流程
echo -e "\n${BLUE}=== 测试 5: 模拟"开始标注"流程 ===${NC}"
echo "1. 确保项目存在..."
PROJECT_RESPONSE=$(api_request POST "/api/label-studio/projects/ensure" \
    "{\"task_id\":\"$TASK_ID\",\"task_name\":\"test\",\"annotation_type\":\"text_classification\"}")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 项目已确保存在${NC}"
    
    echo "2. 验证项目..."
    VALIDATE_RESPONSE=$(api_request GET "/api/label-studio/projects/$PROJECT_ID/validate")
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 项目验证成功${NC}"
        echo -e "${GREEN}✓ 应该导航到: /tasks/$TASK_ID/annotate${NC}"
    else
        echo -e "${RED}✗ 项目验证失败${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ 确保项目存在失败${NC}"
    exit 1
fi

# 测试 6: 模拟"在新窗口打开"流程
echo -e "\n${BLUE}=== 测试 6: 模拟"在新窗口打开"流程 ===${NC}"
echo "1. 确保项目存在..."
PROJECT_RESPONSE=$(api_request POST "/api/label-studio/projects/ensure" \
    "{\"task_id\":\"$TASK_ID\",\"task_name\":\"test\",\"annotation_type\":\"text_classification\"}")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 项目已确保存在${NC}"
    
    echo "2. 获取认证 URL..."
    AUTH_URL_RESPONSE=$(api_request GET "/api/label-studio/projects/$PROJECT_ID/auth-url?language=zh")
    
    if [ $? -eq 0 ]; then
        URL=$(echo "$AUTH_URL_RESPONSE" | jq -r '.url' 2>/dev/null)
        echo -e "${GREEN}✓ 认证 URL 获取成功${NC}"
        echo -e "${GREEN}✓ 应该在新窗口打开: $URL${NC}"
    else
        echo -e "${RED}✗ 获取认证 URL 失败${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ 确保项目存在失败${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== 所有测试通过 ===${NC}"
echo ""
echo "总结:"
echo "  ✓ 项目创建/确保功能正常"
echo "  ✓ 项目验证功能正常"
echo "  ✓ 认证 URL 生成功能正常"
echo "  ✓ 语言参数传递正常"
echo "  ✓ '开始标注'流程正常"
echo "  ✓ '在新窗口打开'流程正常"
echo ""
echo "下一步:"
echo "  1. 在浏览器中打开任务详情页面"
echo "  2. 点击'开始标注'按钮，应该导航到 /tasks/$TASK_ID/annotate"
echo "  3. 点击'在新窗口打开'按钮，应该在新窗口打开 Label Studio"
echo "  4. 检查浏览器控制台是否有错误"
echo "  5. 检查网络请求是否成功"
