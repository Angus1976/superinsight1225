#!/bin/bash

# Quick Label Studio Connection Test
# 快速测试 Label Studio 连接

echo "=========================================="
echo "Label Studio 连接测试"
echo "=========================================="
echo ""

# Configuration
LABEL_STUDIO_URL="http://localhost:8080"
API_TOKEN="YOUR_LABEL_STUDIO_API_TOKEN_HERE"  # Get from Label Studio: Account & Settings > Legacy Tokens

# Test 1: Label Studio Health Check
echo "1️⃣  测试 Label Studio 服务..."
if curl -s -f "${LABEL_STUDIO_URL}/health" > /dev/null 2>&1; then
    echo "   ✅ Label Studio 服务正常运行"
else
    echo "   ❌ Label Studio 服务无法访问"
    echo "   请检查: docker ps | grep label-studio"
    exit 1
fi
echo ""

# Test 2: API Authentication
echo "2️⃣  测试 API Token 认证..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Token ${API_TOKEN}" \
    "${LABEL_STUDIO_URL}/api/current-user/whoami/")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ API Token 认证成功"
    echo "   用户信息:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo "   ❌ API Token 认证失败 (HTTP $HTTP_CODE)"
    echo "   响应: $BODY"
    echo ""
    echo "   解决方案:"
    echo "   1. 访问 http://localhost:8080"
    echo "   2. 登录后进入 Account & Settings"
    echo "   3. 在 Legacy Tokens 部分生成新 Token"
    echo "   4. 更新 .env 文件中的 LABEL_STUDIO_API_TOKEN"
    exit 1
fi
echo ""

# Test 3: List Projects
echo "3️⃣  测试项目列表 API..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Token ${API_TOKEN}" \
    "${LABEL_STUDIO_URL}/api/projects/")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ 项目列表 API 正常"
    PROJECT_COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('results', [])))" 2>/dev/null || echo "0")
    echo "   当前项目数: $PROJECT_COUNT"
else
    echo "   ❌ 项目列表 API 失败 (HTTP $HTTP_CODE)"
    echo "   响应: $BODY"
fi
echo ""

# Test 4: Check .env Configuration
echo "4️⃣  检查 .env 配置..."
if [ -f ".env" ]; then
    echo "   ✅ .env 文件存在"
    
    if grep -q "LABEL_STUDIO_API_TOKEN=" .env; then
        echo "   ✅ LABEL_STUDIO_API_TOKEN 已配置"
    else
        echo "   ❌ LABEL_STUDIO_API_TOKEN 未配置"
    fi
    
    if grep -q "LABEL_STUDIO_URL=" .env; then
        CONFIGURED_URL=$(grep "LABEL_STUDIO_URL=" .env | cut -d'=' -f2)
        echo "   ✅ LABEL_STUDIO_URL = $CONFIGURED_URL"
    else
        echo "   ❌ LABEL_STUDIO_URL 未配置"
    fi
else
    echo "   ❌ .env 文件不存在"
    echo "   请从 .env.example 复制并配置"
fi
echo ""

# Summary
echo "=========================================="
echo "测试总结"
echo "=========================================="
echo ""
echo "如果所有测试都通过，可以继续："
echo ""
echo "1. 重启后端容器:"
echo "   docker compose restart app"
echo ""
echo "2. 运行完整测试:"
echo "   python test_label_studio_sync.py"
echo ""
echo "3. 或手动测试 API:"
echo "   curl http://localhost:8000/api/tasks/label-studio/test-connection \\"
echo "     -H \"Authorization: Bearer YOUR_JWT_TOKEN\""
echo ""
