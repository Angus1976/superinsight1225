# SuperInsight 本地 Docker 全栈启动完整指南

## 当前状态

已启动的服务：
- ✅ Label Studio (8080)
- ✅ Neo4j (7474, 7687)
- ✅ Redis (6379)
- ❌ PostgreSQL (需要修复)
- ⏳ SuperInsight API (待启动)

## 第一步：修复 PostgreSQL 容器

### 1.1 清理现有容器
```bash
# 停止所有容器
docker-compose down

# 删除所有容器和卷
docker-compose down -v

# 验证清理
docker ps -a
```

### 1.2 创建必要的目录结构
```bash
# 创建数据目录
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p data/neo4j
mkdir -p data/label-studio
mkdir -p data/uploads
mkdir -p logs/{postgres,redis,neo4j,label-studio,api}

# 设置权限
chmod -R 755 data/
chmod -R 755 logs/
```

### 1.3 配置环境变量
```bash
# 复制环境配置
cp .env.example .env

# 编辑 .env 文件，确保以下配置正确：
# POSTGRES_DB=superinsight
# POSTGRES_USER=superinsight
# POSTGRES_PASSWORD=password
# REDIS_URL=redis://redis:6379/0
# DATABASE_URL=postgresql://superinsight:password@postgres:5432/superinsight
```

## 第二步：启动基础服务

### 2.1 启动 PostgreSQL
```bash
docker-compose up -d postgres

# 等待 PostgreSQL 就绪
docker-compose exec postgres pg_isready -U superinsight -d superinsight

# 查看日志
docker-compose logs postgres
```

### 2.2 启动 Redis
```bash
docker-compose up -d redis

# 验证 Redis
docker-compose exec redis redis-cli ping
# 应该返回 PONG
```

### 2.3 启动 Neo4j
```bash
docker-compose up -d neo4j

# 等待 Neo4j 就绪（可能需要 30-60 秒）
sleep 30

# 验证 Neo4j
curl http://localhost:7474

# 访问 Neo4j 浏览器
# http://localhost:7474
# 用户名: neo4j
# 密码: password
```

### 2.4 启动 Label Studio
```bash
docker-compose up -d label-studio

# 等待 Label Studio 就绪
sleep 30

# 验证 Label Studio
curl http://localhost:8080/health

# 访问 Label Studio
# http://localhost:8080
# 用户名: admin@superinsight.com
# 密码: admin123
```

## 第三步：初始化数据库

### 3.1 安装 Python 依赖
```bash
pip install -r requirements.txt
```

### 3.2 运行数据库迁移
```bash
# 运行 Alembic 迁移
python -m alembic upgrade head

# 或者使用脚本
python scripts/run_migrations.py
```

### 3.3 创建初始数据
```bash
# 创建测试用户
python create_test_user.py

# 初始化系统数据
python init_test_accounts.py
```

## 第四步：启动 SuperInsight API

### 4.1 构建 API 镜像
```bash
# 使用开发 Dockerfile
docker build -f Dockerfile.dev -t superinsight-api:dev .
```

### 4.2 启动 API 容器
```bash
docker-compose up -d superinsight-api

# 等待 API 启动
sleep 10

# 验证 API
curl http://localhost:8000/health

# 查看 API 日志
docker-compose logs -f superinsight-api
```

### 4.3 访问 API 文档
```
http://localhost:8000/docs
```

## 第五步：验证完整栈

### 5.1 检查所有容器状态
```bash
docker-compose ps

# 应该看到所有容器都是 Up 状态
```

### 5.2 验证服务连接
```bash
# 验证 PostgreSQL
docker-compose exec postgres psql -U superinsight -d superinsight -c "SELECT version();"

# 验证 Redis
docker-compose exec redis redis-cli INFO server

# 验证 Neo4j
curl -u neo4j:password http://localhost:7474/db/neo4j/info

# 验证 Label Studio
curl http://localhost:8080/api/version

# 验证 API
curl http://localhost:8000/system/status
```

### 5.3 查看系统状态
```bash
# 获取完整系统状态
curl http://localhost:8000/system/status | python -m json.tool
```

## 第六步：监控和日志

### 6.1 查看实时日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f neo4j
docker-compose logs -f label-studio
docker-compose logs -f superinsight-api
```

### 6.2 进入容器调试
```bash
# 进入 PostgreSQL
docker-compose exec postgres psql -U superinsight -d superinsight

# 进入 Redis
docker-compose exec redis redis-cli

# 进入 Neo4j
docker-compose exec neo4j cypher-shell -u neo4j -p password

# 进入 API 容器
docker-compose exec superinsight-api bash
```

## 常见问题排查

### 问题 1: PostgreSQL 无法启动
```bash
# 检查日志
docker-compose logs postgres

# 清理并重新启动
docker-compose down -v
mkdir -p data/postgres
docker-compose up -d postgres
```

### 问题 2: 端口被占用
```bash
# 查找占用端口的进程
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :7474  # Neo4j
lsof -i :8080  # Label Studio
lsof -i :8000  # API

# 杀死进程
kill -9 <PID>
```

### 问题 3: 容器内存不足
```bash
# 增加 Docker 内存限制
# 在 Docker Desktop 设置中增加内存分配

# 或者在 docker-compose.yml 中添加资源限制
# services:
#   postgres:
#     deploy:
#       resources:
#         limits:
#           memory: 2G
```

### 问题 4: 网络连接问题
```bash
# 检查网络
docker network ls
docker network inspect superinsight-network

# 重新创建网络
docker network rm superinsight-network
docker-compose up -d
```

## 完整启动脚本

创建 `start_fullstack.sh`:

```bash
#!/bin/bash

set -e

echo "=========================================="
echo "SuperInsight 本地 Docker 全栈启动"
echo "=========================================="

# 清理
echo "清理旧容器..."
docker-compose down -v 2>/dev/null || true

# 创建目录
echo "创建数据目录..."
mkdir -p data/{postgres,redis,neo4j,label-studio,uploads}
mkdir -p logs/{postgres,redis,neo4j,label-studio,api}

# 启动基础服务
echo "启动 PostgreSQL..."
docker-compose up -d postgres
sleep 10

echo "启动 Redis..."
docker-compose up -d redis
sleep 5

echo "启动 Neo4j..."
docker-compose up -d neo4j
sleep 30

echo "启动 Label Studio..."
docker-compose up -d label-studio
sleep 30

# 初始化数据库
echo "初始化数据库..."
pip install -q -r requirements.txt
python -m alembic upgrade head

# 启动 API
echo "启动 SuperInsight API..."
docker-compose up -d superinsight-api
sleep 10

# 验证
echo "验证服务..."
docker-compose ps

echo ""
echo "=========================================="
echo "✓ 所有服务已启动"
echo "=========================================="
echo ""
echo "访问地址："
echo "  - API: http://localhost:8000"
echo "  - API 文档: http://localhost:8000/docs"
echo "  - Label Studio: http://localhost:8080"
echo "  - Neo4j: http://localhost:7474"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo ""
echo "默认凭证："
echo "  - Label Studio: admin@superinsight.com / admin123"
echo "  - Neo4j: neo4j / password"
echo "  - PostgreSQL: superinsight / password"
echo ""
```

使用方法：
```bash
chmod +x start_fullstack.sh
./start_fullstack.sh
```

## 停止和清理

### 停止所有服务
```bash
docker-compose down
```

### 完全清理（包括数据）
```bash
docker-compose down -v
rm -rf data/ logs/
```

### 重启所有服务
```bash
docker-compose restart
```

## 性能优化建议

1. **增加 Docker 内存**: 至少 4GB
2. **增加 Docker CPU**: 至少 2 核
3. **使用 SSD**: 数据存储在 SSD 上
4. **关闭不需要的服务**: 在 docker-compose.yml 中注释掉

## 下一步

1. 访问 http://localhost:8000/docs 查看 API 文档
2. 访问 http://localhost:8080 配置 Label Studio 项目
3. 访问 http://localhost:7474 配置 Neo4j 知识图谱
4. 运行测试: `pytest tests/`
5. 查看系统状态: `curl http://localhost:8000/system/status`
