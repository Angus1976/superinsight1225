# SuperInsight Docker 全栈启动成功 ✓

## 启动状态

### ✅ 已启动的服务

| 服务 | 状态 | 端口 | 健康检查 |
|------|------|------|---------|
| PostgreSQL | ✅ Up (Healthy) | 5432 | ✓ |
| Redis | ✅ Up (Healthy) | 6379 | ✓ |
| Neo4j | ✅ Up (Healthy) | 7474, 7687 | ✓ |
| Label Studio | ✅ Up (Healthy) | 8080 | ✓ |

## 访问地址

### 数据库和缓存
- **PostgreSQL**: `postgresql://superinsight:password@localhost:5432/superinsight`
- **Redis**: `redis://localhost:6379`
- **Neo4j**: `bolt://localhost:7687` 或 `http://localhost:7474`

### Web 界面
- **Label Studio**: http://localhost:8080
  - 用户名: `admin@superinsight.com`
  - 密码: `admin123`
- **Neo4j Browser**: http://localhost:7474
  - 用户名: `neo4j`
  - 密码: `password`

## 验证服务连接

### 1. 验证 PostgreSQL
```bash
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "SELECT version();"
```

### 2. 验证 Redis
```bash
docker-compose -f docker-compose.local.yml exec redis redis-cli ping
# 应该返回 PONG
```

### 3. 验证 Neo4j
```bash
curl -u neo4j:password http://localhost:7474/db/neo4j/info
```

### 4. 验证 Label Studio
```bash
curl http://localhost:8080/health
```

## 下一步：启动 SuperInsight API

### 方案 A: 本地运行 API（推荐用于开发）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行数据库迁移
python -m alembic upgrade head

# 3. 启动 API 服务
python main.py
```

API 将在 http://localhost:8000 启动

### 方案 B: Docker 容器运行 API

```bash
# 1. 构建 API 镜像（需要网络连接）
docker build -f Dockerfile.dev -t superinsight-api:dev .

# 2. 运行 API 容器
docker run -d \
  --name superinsight-api \
  --network superinsight-network \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://superinsight:password@postgres:5432/superinsight \
  -e REDIS_URL=redis://redis:6379/0 \
  -e LABEL_STUDIO_URL=http://label-studio:8080 \
  -e NEO4J_URI=bolt://neo4j:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=password \
  superinsight-api:dev
```

## 常用命令

### 查看日志
```bash
# 所有服务
docker-compose -f docker-compose.local.yml logs -f

# 特定服务
docker-compose -f docker-compose.local.yml logs -f postgres
docker-compose -f docker-compose.local.yml logs -f redis
docker-compose -f docker-compose.local.yml logs -f neo4j
docker-compose -f docker-compose.local.yml logs -f label-studio
```

### 进入容器
```bash
# PostgreSQL
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight

# Redis
docker-compose -f docker-compose.local.yml exec redis redis-cli

# Neo4j
docker-compose -f docker-compose.local.yml exec neo4j cypher-shell -u neo4j -p password
```

### 停止服务
```bash
# 停止所有容器（保留数据）
docker-compose -f docker-compose.local.yml stop

# 停止并删除容器（保留数据）
docker-compose -f docker-compose.local.yml down

# 停止并删除容器和数据
docker-compose -f docker-compose.local.yml down -v
```

### 重启服务
```bash
docker-compose -f docker-compose.local.yml restart
```

### 查看容器状态
```bash
docker-compose -f docker-compose.local.yml ps
```

## 初始化数据库

### 1. 运行迁移
```bash
python -m alembic upgrade head
```

### 2. 创建测试用户
```bash
python create_test_user.py
```

### 3. 初始化系统数据
```bash
python init_test_accounts.py
```

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   SuperInsight Platform                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Frontend   │  │  API Server  │  │   Workers    │   │
│  │  (React)     │  │  (FastAPI)   │  │  (Celery)    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│         │                  │                  │           │
│         └──────────────────┼──────────────────┘           │
│                            │                              │
│  ┌─────────────────────────┼─────────────────────────┐   │
│  │                         │                         │   │
│  ▼                         ▼                         ▼   │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│ │ PostgreSQL   │  │    Redis     │  │    Neo4j     │   │
│ │  (Database)  │  │   (Cache)    │  │  (Graph DB)  │   │
│ └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Label Studio (Annotation Tool)           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## 性能指标

### 资源使用情况
```bash
docker stats
```

### 数据库连接
```bash
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "SELECT count(*) FROM pg_stat_activity;"
```

### Redis 内存使用
```bash
docker-compose -f docker-compose.local.yml exec redis redis-cli INFO memory
```

## 故障排查

### PostgreSQL 无法连接
```bash
# 查看日志
docker-compose -f docker-compose.local.yml logs postgres

# 检查健康状态
docker-compose -f docker-compose.local.yml exec postgres pg_isready -U superinsight -d superinsight

# 重启
docker-compose -f docker-compose.local.yml restart postgres
```

### Redis 无法连接
```bash
# 查看日志
docker-compose -f docker-compose.local.yml logs redis

# 检查健康状态
docker-compose -f docker-compose.local.yml exec redis redis-cli ping

# 重启
docker-compose -f docker-compose.local.yml restart redis
```

### Neo4j 无法连接
```bash
# 查看日志
docker-compose -f docker-compose.local.yml logs neo4j

# 检查健康状态
curl http://localhost:7474

# 重启
docker-compose -f docker-compose.local.yml restart neo4j
```

### Label Studio 无法连接
```bash
# 查看日志
docker-compose -f docker-compose.local.yml logs label-studio

# 检查健康状态
curl http://localhost:8080/health

# 重启
docker-compose -f docker-compose.local.yml restart label-studio
```

## 备份和恢复

### 备份数据库
```bash
# PostgreSQL
docker-compose -f docker-compose.local.yml exec postgres pg_dump -U superinsight superinsight > backup.sql

# Redis
docker-compose -f docker-compose.local.yml exec redis redis-cli BGSAVE
docker cp superinsight-redis:/data/dump.rdb ./redis_backup.rdb
```

### 恢复数据库
```bash
# PostgreSQL
docker-compose -f docker-compose.local.yml exec -T postgres psql -U superinsight superinsight < backup.sql

# Redis
docker cp redis_backup.rdb superinsight-redis:/data/dump.rdb
docker-compose -f docker-compose.local.yml restart redis
```

## 监控和日志

### 实时监控
```bash
# 查看所有容器的资源使用
docker stats

# 查看特定容器的日志
docker-compose -f docker-compose.local.yml logs -f <service_name>
```

### 日志文件位置
- PostgreSQL: `logs/postgres/`
- Redis: `logs/redis/`
- Neo4j: `logs/neo4j/`
- Label Studio: `logs/label-studio/`

## 下一步

1. ✅ 基础服务已启动
2. ⏳ 启动 SuperInsight API
3. ⏳ 初始化数据库
4. ⏳ 配置 Label Studio 项目
5. ⏳ 配置 Neo4j 知识图谱
6. ⏳ 运行测试
7. ⏳ 访问前端应用

## 获取帮助

### 查看完整指南
- 详细启动指南: `DOCKER_FULLSTACK_COMPLETE_GUIDE.md`
- 诊断脚本: `bash docker_diagnostic.sh diagnose`

### 常见问题
- 端口被占用: 修改 docker-compose.local.yml 中的端口映射
- 内存不足: 增加 Docker Desktop 的内存分配
- 网络问题: 检查 Docker 网络配置

### 联系支持
如有问题，请：
1. 查看日志: `docker-compose -f docker-compose.local.yml logs`
2. 运行诊断: `bash docker_diagnostic.sh diagnose`
3. 检查网络: `docker network inspect superinsight-network`

---

**启动时间**: 2026-01-09 14:33 UTC
**状态**: ✅ 所有服务正常运行
**下一步**: 启动 SuperInsight API 服务
