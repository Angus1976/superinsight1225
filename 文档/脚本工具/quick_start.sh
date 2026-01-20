#!/bin/bash

# SuperInsight i18n 快速启动脚本
# 用于本地开发环境的一键启动

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装"
        exit 1
    fi
    print_success "Python 3 已安装"
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js 未安装"
        exit 1
    fi
    print_success "Node.js 已安装"
    
    # 检查 npm
    if ! command -v npm &> /dev/null; then
        print_error "npm 未安装"
        exit 1
    fi
    print_success "npm 已安装"
}

# 启动后端
start_backend() {
    print_info "启动后端服务..."
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_warning "虚拟环境不存在，创建中..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt 不存在"
        exit 1
    fi
    
    print_info "安装 Python 依赖..."
    pip install -q -r requirements.txt
    
    print_success "后端依赖安装完成"
    
    # 启动 API 服务
    print_info "启动 API 服务 (http://localhost:8000)..."
    python3 -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    
    # 等待后端启动
    sleep 3
    
    # 检查后端是否运行
    if curl -s http://localhost:8000/health/i18n > /dev/null; then
        print_success "后端服务已启动 (PID: $BACKEND_PID)"
    else
        print_error "后端服务启动失败"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
}

# 启动前端
start_frontend() {
    print_info "启动前端应用..."
    
    # 进入前端目录
    cd frontend
    
    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        print_warning "node_modules 不存在，安装中..."
        npm install -q
    fi
    
    print_success "前端依赖已准备"
    
    # 启动开发服务器
    print_info "启动前端开发服务器 (http://localhost:5173)..."
    npm run dev &
    FRONTEND_PID=$!
    
    # 等待前端启动
    sleep 5
    
    print_success "前端应用已启动 (PID: $FRONTEND_PID)"
    
    cd ..
}

# 显示启动信息
show_startup_info() {
    echo ""
    echo "========================================================================"
    echo "🎉 SuperInsight i18n 系统已启动！"
    echo "========================================================================"
    echo ""
    echo "📍 访问地址:"
    echo "   🌐 前端应用: http://localhost:5173"
    echo "   🔌 API 服务: http://localhost:8000"
    echo "   📚 API 文档: http://localhost:8000/docs"
    echo "   ✅ 健康检查: http://localhost:8000/health/i18n"
    echo ""
    echo "👤 测试账户:"
    echo "   1. 管理员: admin@superinsight.com / Admin@123456"
    echo "   2. 分析师: analyst@superinsight.com / Analyst@123456"
    echo "   3. 编辑: editor@superinsight.com / Editor@123456"
    echo "   4. 用户: user@superinsight.com / User@123456"
    echo "   5. 访客: guest@superinsight.com / Guest@123456"
    echo ""
    echo "🧪 API 测试:"
    echo "   • 获取语言列表: curl http://localhost:8000/api/i18n/languages"
    echo "   • 获取翻译: curl 'http://localhost:8000/api/i18n/translations?language=zh'"
    echo ""
    echo "📖 文档:"
    echo "   • 启动指南: LOCAL_STARTUP_GUIDE.md"
    echo "   • 用户指南: docs/i18n/user_guide.md"
    echo "   • API 文档: docs/i18n/api_documentation.md"
    echo ""
    echo "⚠️  按 Ctrl+C 停止服务"
    echo "========================================================================"
    echo ""
}

# 清理函数
cleanup() {
    print_warning "正在停止服务..."
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        print_success "后端服务已停止"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_success "前端应用已停止"
    fi
    
    print_success "所有服务已停止"
}

# 设置 Ctrl+C 处理
trap cleanup EXIT INT TERM

# 主函数
main() {
    echo ""
    echo "========================================================================"
    echo "🚀 SuperInsight i18n 快速启动"
    echo "========================================================================"
    echo ""
    
    # 检查依赖
    check_dependencies
    
    echo ""
    
    # 启动后端
    start_backend
    
    echo ""
    
    # 启动前端
    start_frontend
    
    echo ""
    
    # 显示启动信息
    show_startup_info
    
    # 保持运行
    wait
}

# 执行主函数
main "$@"