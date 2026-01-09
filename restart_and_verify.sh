#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     SuperInsight 前后端服务重启与集成验证${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# 1. 检查 Docker 服务
echo -e "${YELLOW}[1/6] 检查 Docker 服务状态...${NC}"
docker-compose -f docker-compose.local.yml ps
echo ""

# 2. 创建测试用户
echo -e "${YELLOW}[2/6] 创建测试用户...${NC}"
python create_test_users_for_login.py 2>&1 | tail -20
echo ""

# 3. 启动后端 API
echo -e "${YELLOW}[3/6] 启动后端 API 服务 (http://localhost:8000)...${NC}"
echo "请在新的终端窗口中运行: python main.py"
echo ""

# 4. 启动前端开发服务器
echo -e "${YELLOW}[4/6] 启动前端开发服务器 (http://localhost:5173)...${NC}"
echo "请在另一个新的终端窗口中运行: cd frontend && npm run dev"
echo ""

# 5. 等待用户启动服务
echo -e "${YELLOW}[5/6] 等待服务启动...${NC}"
echo "请等待 30 秒让服务启动..."
sleep 30
echo ""

# 6. 验证集成
echo -e "${YELLOW}[6/6] 验证前后端集成...${NC}"
echo ""

# 检查后端 API
echo -e "${BLUE}检查后端 API (http://localhost:8000/health)...${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端 API 运行正常${NC}"
else
    echo -e "${RED}✗ 后端 API 无法访问${NC}"
    echo "  请确保已在终端中运行: python main.py"
fi
echo ""

# 检查前端
echo -e "${BLUE}检查前端开发服务器 (http://localhost:5173)...${NC}"
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 前端开发服务器运行正常${NC}"
else
    echo -e "${RED}✗ 前端开发服务器无法访问${NC}"
    echo "  请确保已在终端中运行: cd frontend && npm run dev"
fi
echo ""

# 检查 API 登录端点
echo -e "${BLUE}检查 API 登录端点 (POST /api/security/login)...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}' 2>&1)

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ 登录端点正常工作${NC}"
    echo "  返回: $(echo $RESPONSE | head -c 100)..."
elif echo "$RESPONSE" | grep -q "Invalid username"; then
    echo -e "${YELLOW}⚠ 登录端点可访问，但用户不存在${NC}"
    echo "  请运行: python create_test_users_for_login.py"
else
    echo -e "${RED}✗ 登录端点无法访问${NC}"
    echo "  错误: $RESPONSE"
fi
echo ""

# 检查前端 API 配置
echo -e "${BLUE}检查前端 API 配置...${NC}"
if grep -q "VITE_API_BASE_URL=http://localhost:8000" frontend/.env.development; then
    echo -e "${GREEN}✓ 前端 API 基础 URL 配置正确${NC}"
else
    echo -e "${RED}✗ 前端 API 基础 URL 配置错误${NC}"
fi
echo ""

# 总结
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}验证完成！${NC}"
echo ""
echo -e "${YELLOW}访问地址:${NC}"
echo "  前端登录页: http://localhost:5173/login"
echo "  后端 API: http://localhost:8000"
echo ""
echo -e "${YELLOW}测试账号:${NC}"
echo "  用户名: admin_user"
echo "  密码: Admin@123456"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
