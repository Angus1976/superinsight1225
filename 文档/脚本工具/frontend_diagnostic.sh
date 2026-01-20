#!/bin/bash

echo "=== SuperInsight 前端诊断脚本 ==="
echo "时间: $(date)"
echo ""

# 设置Docker路径
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

echo "1. 检查Docker容器状态..."
docker compose -f docker-compose.fullstack.yml ps | grep frontend

echo ""
echo "2. 检查前端容器健康状态..."
docker compose -f docker-compose.fullstack.yml exec superinsight-frontend sh -c "curl -I http://localhost:5173/"

echo ""
echo "3. 检查端口监听..."
docker compose -f docker-compose.fullstack.yml exec superinsight-frontend sh -c "netstat -tlnp | grep 5173"

echo ""
echo "4. 测试前端页面访问..."
echo "主页:"
curl -s -I http://localhost:5173/ | head -3

echo ""
echo "登录页:"
curl -s -I http://localhost:5173/login | head -3

echo ""
echo "5. 检查前端日志 (最近10行)..."
docker compose -f docker-compose.fullstack.yml logs superinsight-frontend --tail=10

echo ""
echo "6. 检查网络连接..."
echo "从宿主机到容器的连接:"
nc -zv localhost 5173

echo ""
echo "=== 诊断完成 ==="
echo ""
echo "如果所有检查都正常，请尝试以下解决方案："
echo "1. 清除浏览器缓存 (Ctrl+Shift+R 或 Cmd+Shift+R)"
echo "2. 尝试无痕模式/隐私模式"
echo "3. 尝试不同的浏览器"
echo "4. 检查防火墙设置"
echo "5. 重启Docker Desktop"
echo ""
echo "访问地址:"
echo "- 前端: http://localhost:5173/login"
echo "- 后端: http://localhost:8000/docs"