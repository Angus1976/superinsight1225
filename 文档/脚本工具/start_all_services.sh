#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     SuperInsight 完整服务启动脚本${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# 检查 Python 版本
echo -e "${YELLOW}[1/5] 检查 Python 版本...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python3 未安装${NC}"
    exit 1
fi
echo ""

# 检查 Node.js 版本
echo -e "${YELLOW}[2/5] 检查 Node.js 版本...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION${NC}"
else
    echo -e "${RED}✗ Node.js 未安装${NC}"
    exit 1
fi
echo ""

# 创建测试用户
echo -e "${YELLOW}[3/5] 创建测试用户...${NC}"
python3 create_test_users_for_login.py 2>&1 | grep -E "✓|✗|Summary"
echo ""

# 启动后端
echo -e "${YELLOW}[4/5] 启动后端 API 服务...${NC}"
echo "启动命令: python3 main.py"
nohup python3 main.py > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ 后端进程 ID: $BACKEND_PID${NC}"
echo "  日志文件: backend.log"
echo ""

# 启动前端
echo -e "${YELLOW}[5/5] 启动前端开发服务器...${NC}"
echo "启动命令: cd frontend && npm run dev"
cd frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✓ 前端进程 ID: $FRONTEND_PID${NC}"
echo "  日志文件: frontend.log"
echo ""

# 等待服务启动
echo -e "${YELLOW}等待服务启动（30秒）...${NC}"
sleep 30
echo ""

# 验证服务
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}验证服务状态${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# 检查后端
echo -e "${BLUE}后端 API (http://localhost:8000)${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端运行正常${NC}"
else
    echo -e "${RED}✗ 后端无法访问${NC}"
    echo "  查看日志: tail -f backend.log"
fi
echo ""

# 检查前端
echo -e "${BLUE}前端开发服务器 (http://localhost:5173)${NC}"
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 前端运行正常${NC}"
else
    echo -e "${RED}✗ 前端无法访问${NC}"
    echo "  查看日志: tail -f frontend.log"
fi
echo ""

# 测试登录
echo -e "${BLUE}测试登录端点${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}')

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ 登录端点正常${NC}"
elif echo "$RESPONSE" | grep -q "Invalid"; then
    echo -e "${YELLOW}⚠ 用户不存在，请运行: python3 create_test_users_for_login.py${NC}"
else
    echo -e "${RED}✗ 登录端点无法访问${NC}"
fi
echo ""

# 总结
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ 服务启动完成！${NC}"
echo ""
echo -e "${YELLOW}访问地址:${NC}"
echo "  前端登录: http://localhost:5173/login"
echo "  后端 API: http://localhost:8000"
echo ""
echo -e "${YELLOW}测试账号:${NC}"
echo "  用户名: admin_user"
echo "  密码: Admin@123456"
echo ""
echo -e "${YELLOW}进程信息:${NC}"
echo "  后端 PID: $BACKEND_PID"
echo "  前端 PID: $FRONTEND_PID"
echo ""
echo -e "${YELLOW}查看日志:${NC}"
echo "  后端: tail -f backend.log"
echo "  前端: tail -f frontend.log"
echo ""
echo -e "${YELLOW}停止服务:${NC}"
echo "  kill $BACKEND_PID  # 停止后端"
echo "  kill $FRONTEND_PID # 停止前端"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# 保存 PID 到文件
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

echo -e "${GREEN}✓ 所有服务已启动！${NC}"
echo "  在浏览器中打开: http://localhost:5173/login"
