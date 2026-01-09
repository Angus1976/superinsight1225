#!/bin/bash

# 设置Docker路径
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

echo "🚀 开始启动SuperInsight全栈应用..."
echo ""

# 1. 检查基础设施服务
echo "📋 检查基础设施服务状态..."
docker compose -f docker-compose.fullstack.yml ps | grep -E "postgres|redis|neo4j|label-studio"
echo ""

# 2. 构建后端镜像
echo "🔨 构建后端镜像..."
docker build -f Dockerfile.backend -t superinsight-api:latest . 2>&1 | tail -20
echo ""

# 3. 构建前端镜像
echo "🔨 构建前端镜像..."
docker build -f frontend/Dockerfile -t superinsight-frontend:latest ./frontend 2>&1 | tail -20
echo ""

# 4. 启动后端和前端容器
echo "🚀 启动后端和前端容器..."
docker compose -f docker-compose.fullstack.yml up -d superinsight-api superinsight-frontend 2>&1
echo ""

# 5. 等待服务就绪
echo "⏳ 等待服务就绪..."
sleep 10

# 6. 检查所有容器状态
echo "✅ 容器状态："
docker compose -f docker-compose.fullstack.yml ps
echo ""

# 7. 验证服务
echo "🔍 验证服务..."
echo "后端 API: http://localhost:8000"
echo "前端: http://localhost:5173"
echo "Label Studio: http://localhost:8080"
echo "Neo4j: http://localhost:7474"
echo ""

echo "✨ 启动完成！"
