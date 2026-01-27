#!/bin/bash

echo "=========================================="
echo "重启容器并测试"
echo "=========================================="
echo ""

# Step 1: 重启后端容器
echo "1️⃣  重启后端容器..."
echo "   执行命令: docker compose restart app"
echo ""

if command -v docker &> /dev/null; then
    docker compose restart app
    
    if [ $? -eq 0 ]; then
        echo "   ✅ 后端容器重启成功"
    else
        echo "   ❌ 后端容器重启失败"
        echo "   请手动执行: docker compose restart app"
        exit 1
    fi
else
    echo "   ⚠️  Docker 命令不可用"
    echo "   请手动执行以下命令:"
    echo ""
    echo "   docker compose restart app"
    echo ""
    echo "   或重启所有容器:"
    echo "   docker compose restart"
    echo ""
    read -p "   按回车键继续（确认已手动重启）..."
fi

echo ""

# Step 2: 等待容器启动
echo "2️⃣  等待容器启动..."
echo "   等待 10 秒..."
sleep 10
echo "   ✅ 等待完成"
echo ""

# Step 3: 检查容器状态
echo "3️⃣  检查容器状态..."
if command -v docker &> /dev/null; then
    echo "   后端容器状态:"
    docker ps | grep -E "CONTAINER|app" || echo "   ⚠️  未找到 app 容器"
    echo ""
    echo "   Label Studio 容器状态:"
    docker ps | grep -E "CONTAINER|label-studio" || echo "   ⚠️  未找到 label-studio 容器"
else
    echo "   ⚠️  Docker 命令不可用，跳过状态检查"
    echo "   请手动执行: docker ps"
fi
echo ""

# Step 4: 查看后端日志
echo "4️⃣  查看后端启动日志..."
if command -v docker &> /dev/null; then
    echo "   最近 20 行日志:"
    echo "   ----------------------------------------"
    docker logs --tail 20 superinsight-api 2>&1 || docker logs --tail 20 app 2>&1 || echo "   ⚠️  无法获取日志"
    echo "   ----------------------------------------"
else
    echo "   ⚠️  Docker 命令不可用"
    echo "   请手动执行: docker logs --tail 50 superinsight-api"
fi
echo ""

# Step 5: 测试 API 健康检查
echo "5️⃣  测试 API 健康检查..."
sleep 2

HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>&1)
if [ $? -eq 0 ]; then
    echo "   ✅ API 健康检查成功"
    echo "   响应: $HEALTH_RESPONSE"
else
    echo "   ❌ API 健康检查失败"
    echo "   错误: $HEALTH_RESPONSE"
    echo ""
    echo "   可能原因:"
    echo "   - 容器还在启动中（再等待几秒）"
    echo "   - 端口 8000 未映射"
    echo "   - 容器启动失败"
    echo ""
    echo "   请检查容器日志:"
    echo "   docker logs superinsight-api"
fi
echo ""

# Step 6: 运行快速连接测试
echo "6️⃣  运行 Label Studio 连接测试..."
if [ -f "./quick_test_label_studio.sh" ]; then
    ./quick_test_label_studio.sh
else
    echo "   ⚠️  测试脚本不存在"
    echo "   请手动运行: ./quick_test_label_studio.sh"
fi
echo ""

# Summary
echo "=========================================="
echo "重启完成"
echo "=========================================="
echo ""
echo "📋 下一步操作:"
echo ""
echo "1. 如果健康检查失败，查看日志:"
echo "   docker logs -f superinsight-api"
echo ""
echo "2. 如果连接测试失败，检查配置:"
echo "   cat .env | grep LABEL_STUDIO"
echo ""
echo "3. 运行完整功能测试:"
echo "   python test_label_studio_sync.py"
echo ""
echo "4. 在浏览器中测试:"
echo "   http://localhost:5173"
echo ""
