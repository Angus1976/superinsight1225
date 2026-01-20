# SuperInsight Docker 全栈完整启动指南

## 当前状态分析

### 已启动的容器（非 docker-compose）
- Label Studio (beautiful_panini)
- Neo4j (pensive_antonelli)
- Redis (sad_mendel)
- PostgreSQL (jolly_davinci) - **已停止，状态异常**

### 问题
1. 容器是通过 `docker run` 启动的，不是通过 `docker-compose` 启动
2. PostgreSQL 容器已停止（Exit Code 1）
3. 没有使用 docker-compose 网络
4. 容器之间无法通过服务名通信

## 解决方案

### 步骤 1: 完全清理现有容器

```bash
# 停止所有容器
docker stop $(docker ps -aq) 2>/dev/null || true

# 删除所有容器
docker rm $(docker ps -aq) 2>/dev/null || true

# 删除所有卷
docker volume prune -f

# 验证清理
docker ps -a
docker volume ls
```

### 步骤 2: 准备环境

```bash
# 创建必要的目录
mkdir -p data/{postgres,redis,neo4j,label-studio,uploads}
mkdir -p logs/{postgres,redis,neo4j,label-studio,api}

# 设置权限
chmod -R 755 data/ logs/

# 确保 .env 文件存在
if [ ! -f .env ]; then
    cp .env.example .env
fi
```

### 步骤 3: 使用 docker-compose 启动完整栈

```bash
# 启动所有服务
docker-compose up -d

# 等待服务就绪
sleep 30

# 验证所有容器
docker-compose ps
```

### 步骤 4: 初始化数据库

```bash
# 安装依赖
pip install -r requirements.txt

# 运行迁移
python -m alembic upgrade head

# 创建初始数据
python create_test_user.py
python init_test_accounts.py
```

### 步骤 5: 验证服务

```bash
# 检查所有服务状态
docker-compose ps

# 验证 PostgreSQL
docker-compose exec postgres psql -U superinsight -d superinsight -c "SELECT version();"

# 验证 Redis
docker-compose exec redis redis-cli ping

# 验证 Neo4j
curl -u neo4j:password http://localhost:7474/db/neo4j/info

# 验证 Label Studio
curl http://localhost:8080/health

# 验证 API
curl http://localhost:8000/health
```

## 快速启动命令

### 一键启动（推荐）

```bash
# 清理旧容器
docker-compose down -v 2>/dev/null || true

# 创建目录
mkdir -p data/{postgres,redis,neo4j,label-studio,uploads}
mkdir -p logs/{postgres,redis,neo4j,label-studio,api}

# 启动所有服务
docker-compose up -d

# 等待服务启动
sleep 30

# 初始化数据库
pip install -q -r requirements.txt
python -m alembic upgrade head

# 验证
docker-compose ps
```

### 分步启动

```bash
# 1. 启动基础服务
docker-compose up -d postgres redis neo4j

# 2. 等待基础服务就绪
sleep 20

# 3. 启动 Label Studio
docker-compose up -d label-studio

# 4. 等待 Label Studio 就绪
sleep 30

# 5. 初始化数据库
pip install -q -r requirements.txt
python -m alembic upgrade head

# 6. 启动 API
docker-compose up -d superinsight-api

# 7. 验证
docker-compose ps
```

## 访问地址

| 服务 | 地址 | 用户名 | 密码 |
|------|------|--------|------|
| API | http://localhost:8000 | - | - |
| API 文档 | http://localhost:8000/docs | - | - |
| Label Studio | http://localhost:8080 | admin@superinsight.com | admin123 |
| Neo4j | http://localhost:7474 | neo4j | password |
| PostgreSQL | localhost:5432 | superinsight | password |
| Redis | localhost:6379 | - | - |

## 常见问题排查

### 问题 1: PostgreSQL 无法启动

```bash
# 查看日志
docker-compose logs postgres

# 清理并重新启动
docker-compose down -v
rm -rf data/postgres
mkdir -p data/postgres
docker-compose up -d postgres

# 等待就绪
sleep 10
docker-compose exec postgres pg_isready -U superinsight -d superinsight
```

### 问题 2: 容器无法通信

```bash
# 检查网络
docker network ls
docker network inspect superinsight-network

# 重新创建网络
docker network rm superinsight-network 2>/dev/null || true
docker-compose down
docker-compose up -d
```

### 问题 3: 端口被占用

```bash
# 查找占用端口的进程
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :7474  # Neo4j
lsof -i :8080  # Label Studio
lsof -i :8000  # API

# 杀死进程
kill -9 <PID>

# 或者修改 docker-compose.yml 中的端口
```

### 问题 4: 内存不足

```bash
# 检查 Docker 内存使用
docker stats

# 增加 Docker 内存限制
# 在 Docker Desktop 设置中增加内存分配（建议 4GB+）

# 或者在 docker-compose.yml 中添加资源限制
```

## 监控和日志

### 查看实时日志

```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f neo4j
docker-compose logs -f label-studio
docker-compose logs -f superinsight-api
```

### 进入容器调试

```bash
# PostgreSQL
docker-compose exec postgres psql -U superinsight -d superinsight

# Redis
docker-compose exec redis redis-cli

# Neo4j
docker-compose exec neo4j cypher-shell -u neo4j -p password

# API
docker-compose exec superinsight-api bash
```

### 查看容器资源使用

```bash
# 实时监控
docker stats

# 查看容器详情
docker inspect <container_id>
```

## 停止和清理

### 停止服务

```bash
# 停止所有容器（保留数据）
docker-compose stop

# 停止并删除容器（保留数据）
docker-compose down

# 停止并删除容器和数据
docker-compose down -v
```

### 清理磁盘空间

```bash
# 删除未使用的镜像
docker image prune -f

# 删除未使用的容器
docker container prune -f

# 删除未使用的卷
docker volume prune -f

# 删除未使用的网络
docker network prune -f

# 完整清理
docker system prune -f
```

## 性能优化

### Docker 配置建议

1. **内存**: 至少 4GB（建议 8GB）
2. **CPU**: 至少 2 核（建议 4 核）
3. **磁盘**: 至少 20GB 可用空间
4. **存储驱动**: 使用 SSD

### 数据库优化

```bash
# PostgreSQL 性能调优
docker-compose exec postgres psql -U superinsight -d superinsight -c "
  ALTER SYSTEM SET shared_buffers = '256MB';
  ALTER SYSTEM SET effective_cache_size = '1GB';
  ALTER SYSTEM SET maintenance_work_mem = '64MB';
  ALTER SYSTEM SET checkpoint_completion_target = 0.9;
  ALTER SYSTEM SET wal_buffers = '16MB';
  ALTER SYSTEM SET default_statistics_target = 100;
  ALTER SYSTEM SET random_page_cost = 1.1;
  ALTER SYSTEM SET effective_io_concurrency = 200;
  ALTER SYSTEM SET work_mem = '4MB';
  ALTER SYSTEM SET min_wal_size = '1GB';
  ALTER SYSTEM SET max_wal_size = '4GB';
"

# 重启 PostgreSQL
docker-compose restart postgres
```

## 备份和恢复

### 备份数据库

```bash
# 备份 PostgreSQL
docker-compose exec postgres pg_dump -U superinsight superinsight > backup.sql

# 备份 Redis
docker-compose exec redis redis-cli BGSAVE
docker cp superinsight-redis:/data/dump.rdb ./redis_backup.rdb

# 备份 Neo4j
docker-compose exec neo4j neo4j-admin database dump neo4j --to-path=/data/backups
```

### 恢复数据库

```bash
# 恢复 PostgreSQL
docker-compose exec -T postgres psql -U superinsight superinsight < backup.sql

# 恢复 Redis
docker cp redis_backup.rdb superinsight-redis:/data/dump.rdb
docker-compose restart redis

# 恢复 Neo4j
docker-compose exec neo4j neo4j-admin database load neo4j --from-path=/data/backups
```

## 下一步

1. 访问 http://localhost:8000/docs 查看 API 文档
2. 访问 http://localhost:8080 配置 Label Studio 项目
3. 访问 http://localhost:7474 配置 Neo4j 知识图谱
4. 运行测试: `pytest tests/`
5. 查看系统状态: `curl http://localhost:8000/system/status`

## 获取帮助

### 查看日志

```bash
# 查看特定容器的日志
docker-compose logs <service_name>

# 查看最后 100 行日志
docker-compose logs --tail=100 <service_name>

# 实时查看日志
docker-compose logs -f <service_name>
```

### 运行诊断

```bash
# 运行诊断脚本
bash docker_diagnostic.sh diagnose

# 修复 PostgreSQL
bash docker_diagnostic.sh fix-postgres

# 修复所有服务
bash docker_diagnostic.sh fix-all

# 清理磁盘
bash docker_diagnostic.sh cleanup
```

### 联系支持

如有问题，请：
1. 查看日志: `docker-compose logs`
2. 运行诊断: `bash docker_diagnostic.sh diagnose`
3. 检查网络: `docker network inspect superinsight-network`
4. 检查卷: `docker volume ls`
