#!/bin/bash

# SuperInsight 容器重建脚本
# 用于重建前后端容器以应用翻译修复

set -e

# Docker 路径配置
DOCKER_PATH="/Applications/Docker.app/Contents/Resources/bin/docker"

echo "🐳 SuperInsight 容器重建脚本"
echo "================================"
echo ""

# 检查 Docker 是否安装
if [ ! -f "$DOCKER_PATH" ]; then
    echo "❌ Docker 未找到"
    echo ""
    echo "预期路径: $DOCKER_PATH"
    echo ""
    echo "请先安装 Docker Desktop："
    echo "  访问: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

echo "✅ Docker 已找到: $DOCKER_PATH"
echo ""

# 检查 Docker Desktop 是否运行
if ! "$DOCKER_PATH" info &> /dev/null; then
    echo "❌ Docker Desktop 未运行"
    echo ""
    echo "请启动 Docker Desktop 应用程序："
    echo "  1. 打开 Finder"
    echo "  2. 进入 Applications 文件夹"
    echo "  3. 双击 Docker.app"
    echo "  4. 等待 Docker 图标出现在菜单栏"
    echo "  5. 重新运行此脚本"
    exit 1
fi

echo "✅ Docker Desktop 正在运行"
echo ""

# 停止现有容器
echo "🛑 停止现有容器..."
"$DOCKER_PATH" compose down || true
echo ""

# 重建前端容器
echo "🔨 重建前端容器（包含翻译修复）..."
"$DOCKER_PATH" compose build frontend --no-cache
echo ""

# 重建后端容器
echo "🔨 重建后端容器..."
"$DOCKER_PATH" compose build app --no-cache
echo ""

# 启动所有服务
echo "🚀 启动所有服务..."
"$DOCKER_PATH" compose up -d
echo ""

# 等待服务启动
echo "⏳ 等待服务启动（30秒）..."
sleep 30
echo ""

# 检查服务状态
echo "📊 服务状态："
"$DOCKER_PATH" compose ps
echo ""

# 显示日志
echo "📝 最近的日志："
echo ""
echo "--- 前端日志 ---"
"$DOCKER_PATH" compose logs --tail=20 frontend
echo ""
echo "--- 后端日志 ---"
"$DOCKER_PATH" compose logs --tail=20 app
echo ""

echo "✅ 容器重建完成！"
echo ""
echo "访问地址："
echo "  前端: http://localhost:5173"
echo "  管理后台: http://localhost:5173/admin"
echo "  后端 API: http://localhost:8000"
echo "  API 文档: http://localhost:8000/docs"
echo ""
echo "验证翻译修复："
echo "  1. 访问管理后台: http://localhost:5173/admin"
echo "  2. 测试所有页面（控制台、计费、权限、配额）"
echo "  3. 切换语言（中文 ↔ 英文）"
echo "  4. 检查浏览器控制台（F12）无 i18n 警告"
echo ""
echo "查看实时日志："
echo "  $DOCKER_PATH compose logs -f frontend"
echo "  $DOCKER_PATH compose logs -f app"
echo ""
echo "停止服务："
echo "  $DOCKER_PATH compose down"
