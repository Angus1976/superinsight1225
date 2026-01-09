#!/bin/bash

# SuperInsight Docker 快速启动脚本
# 用法: bash QUICK_DOCKER_STARTUP.sh

set -e

echo "=========================================="
echo "SuperInsight Docker 快速启动"
echo "=========================================="
echo ""

# 清理旧容器
echo "1️⃣  清理旧容器..."
docker-compose -f docker-compose.local.yml down -v 2>/dev/null || true
echo "✓ 清理完成"
echo ""

# 创建目录
echo "2️⃣  创建数据目录..."
mkdir -p data/{postgres,redis,neo4j,label-studio,uploads}
mkdir -p logs/{postgres,redis,neo4j,label-studio,api}
chmod -R 755 data/ logs/
echo "✓ 目录已创建"
echo ""

# 启动服务
echo "3️⃣  启动 Docker 服务..."
docker-compose -f docker-compose.local.yml up -d
echo "✓ 服务已启动"
echo ""

# 等待服务就绪
echo "4️⃣  等待服务就绪..."
sleep 20
echo "✓ 服务已就绪"
echo ""

# 验证服务
echo "5️⃣  验证服务状态..."
docker-compose -f docker-compose.local.yml ps
echo ""

# 显示访问信息
echo "=========================================="
echo "✅ 所有服务已启动"
echo "=========================================="
echo ""
echo "📍 访问地址："
echo ""
echo "  数据库和缓存："
echo "    - PostgreSQL: localhost:5432"
echo "    - Redis: localhost:6379"
echo "    - Neo4j: http://localhost:7474"
echo ""
echo "  Web 界面："
echo "    - Label Studio: http://localhost:8080"
echo "      用户名: admin@superinsight.com"
echo "      密码: admin123"
echo ""
echo "    - Neo4j Browser: http://localhost:7474"
echo "      用户名: neo4j"
echo "      密码: password"
echo ""
echo "📝 常用命令："
echo ""
echo "  查看日志:"
echo "    docker-compose -f docker-compose.local.yml logs -f"
echo ""
echo "  进入 PostgreSQL:"
echo "    docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight"
echo ""
echo "  进入 Redis:"
echo "    docker-compose -f docker-compose.local.yml exec redis redis-cli"
echo ""
echo "  停止服务:"
echo "    docker-compose -f docker-compose.local.yml down"
echo ""
echo "🚀 下一步："
echo ""
echo "  1. 启动 API 服务:"
echo "     pip install -r requirements.txt"
echo "     python -m alembic upgrade head"
echo "     python main.py"
echo ""
echo "  2. 或者使用 Docker 启动 API:"
echo "     docker build -f Dockerfile.dev -t superinsight-api:dev ."
echo "     docker run -d --name superinsight-api --network superinsight-network -p 8000:8000 superinsight-api:dev"
echo ""
echo "=========================================="
