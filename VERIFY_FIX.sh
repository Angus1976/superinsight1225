#!/bin/bash
# 验证标注按钮修复 - 自动化测试脚本
# Verify Annotation Buttons Fix - Automated Test Script

set -e

echo "=========================================="
echo "标注按钮修复验证脚本"
echo "Annotation Buttons Fix Verification"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_step() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1"
        return 1
    fi
}

echo "步骤 1: 检查 .env 配置"
echo "----------------------------------------"

# 检查 JWT 配置是否已注释
if grep -q "^# LABEL_STUDIO_USERNAME" .env && grep -q "^# LABEL_STUDIO_PASSWORD" .env; then
    check_step "JWT 配置已正确注释"
else
    echo -e "${RED}✗${NC} JWT 配置未注释，请检查 .env 文件"
    echo "  应该是: # LABEL_STUDIO_USERNAME=..."
    echo "  应该是: # LABEL_STUDIO_PASSWORD=..."
    exit 1
fi

# 检查 API Token 是否已启用
if grep -q "^LABEL_STUDIO_API_TOKEN=" .env; then
    TOKEN=$(grep "^LABEL_STUDIO_API_TOKEN=" .env | cut -d'=' -f2)
    if [ -n "$TOKEN" ]; then
        check_step "API Token 已配置"
        echo "  Token 前缀: ${TOKEN:0:20}..."
    else
        echo -e "${RED}✗${NC} API Token 为空"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} API Token 未启用"
    echo "  请取消注释: LABEL_STUDIO_API_TOKEN=..."
    exit 1
fi

echo ""
echo "步骤 2: 检查 Docker 容器状态"
echo "----------------------------------------"

# 检查 Docker 是否可用
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} Docker 命令不可用，跳过容器检查"
    echo "  请手动运行: docker compose ps"
else
    # 检查容器状态
    if docker compose ps | grep -q "superinsight-app.*Up"; then
        check_step "后端容器正在运行"
    else
        echo -e "${YELLOW}⚠${NC} 后端容器未运行"
        echo "  请运行: docker compose up -d app"
    fi
    
    if docker compose ps | grep -q "superinsight-label-studio.*Up"; then
        check_step "Label Studio 容器正在运行"
    else
        echo -e "${YELLOW}⚠${NC} Label Studio 容器未运行"
        echo "  请运行: docker compose up -d label-studio"
    fi
fi

echo ""
echo "步骤 3: 测试 Label Studio 连接"
echo "----------------------------------------"

# 测试 Label Studio 健康检查
if curl -f -s http://localhost:8080/health > /dev/null 2>&1; then
    check_step "Label Studio 可访问"
else
    echo -e "${YELLOW}⚠${NC} Label Studio 不可访问"
    echo "  URL: http://localhost:8080"
    echo "  请确保 Label Studio 容器正在运行"
fi

echo ""
echo "步骤 4: 测试 API Token 认证"
echo "----------------------------------------"

if [ -n "$TOKEN" ]; then
    # 测试 API Token
    RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Token $TOKEN" http://localhost:8080/api/projects/ 2>/dev/null || echo "000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        check_step "API Token 认证成功"
        PROJECT_COUNT=$(echo "$RESPONSE" | head -n-1 | grep -o '\[' | wc -l)
        echo "  找到 $PROJECT_COUNT 个项目"
    elif [ "$HTTP_CODE" = "401" ]; then
        echo -e "${RED}✗${NC} API Token 认证失败 (401 Unauthorized)"
        echo "  Token 可能无效或已过期"
        echo "  请重新生成 Token:"
        echo "    1. 访问 http://localhost:8080"
        echo "    2. 登录 (admin@example.com / admin)"
        echo "    3. Account & Settings → Legacy Tokens"
        echo "    4. 生成新 Token 并更新 .env 文件"
        exit 1
    elif [ "$HTTP_CODE" = "000" ]; then
        echo -e "${YELLOW}⚠${NC} 无法连接到 Label Studio"
        echo "  请确保 Label Studio 正在运行"
    else
        echo -e "${YELLOW}⚠${NC} 意外的响应码: $HTTP_CODE"
    fi
else
    echo -e "${YELLOW}⚠${NC} 跳过 API Token 测试（Token 未配置）"
fi

echo ""
echo "步骤 5: 检查后端日志"
echo "----------------------------------------"

if command -v docker &> /dev/null; then
    echo "最近的后端日志:"
    docker compose logs --tail=20 app 2>/dev/null | grep -i "label studio" || echo "  (未找到 Label Studio 相关日志)"
else
    echo -e "${YELLOW}⚠${NC} Docker 不可用，无法检查日志"
    echo "  请手动运行: docker compose logs app | grep -i 'label studio'"
fi

echo ""
echo "=========================================="
echo "验证完成！"
echo "=========================================="
echo ""

# 总结
echo "下一步操作:"
echo "1. 如果所有检查都通过，重启后端容器:"
echo "   docker compose restart app"
echo ""
echo "2. 测试标注按钮:"
echo "   - 打开: http://localhost:5173"
echo "   - 进入任务详情页面"
echo "   - 点击 '开始标注' 按钮"
echo "   - 点击 '在新窗口打开' 按钮"
echo ""
echo "3. 如果遇到问题，查看详细文档:"
echo "   - 快速参考: QUICK_FIX_REFERENCE.md"
echo "   - 详细指南: FIX_ANNOTATION_BUTTONS_GUIDE.md"
echo "   - 技术分析: LABEL_STUDIO_AUTH_SOLUTION.md"
echo ""
