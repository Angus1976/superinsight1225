# SuperInsight Docker 操作指南

## 📋 目录

1. [快速启动](#快速启动)
2. [服务管理](#服务管理)
3. [日志和监控](#日志和监控)
4. [数据库操作](#数据库操作)
5. [故障排查](#故障排查)
6. [备份和恢复](#备份和恢复)

---

## 快速启动

### 一键启动

```bash
bash QUICK_DOCKER_STARTUP.sh
```

### 手动启动

```bash
# 1. 清理旧容器
docker-compose -f docker-compose.local.yml down -v

# 2. 创建数据目录
mkdir -p data/{postgres,redis,neo4j,label-studio,uploads}
mkdir -p logs/{postgres,redis,neo4j,label-studio,api}

# 3. 启动所有服务
docker-compose -f docker-compose.local.yml up -d

# 4. 验证服务
docker-compose -f docker-compose.local.yml ps
```

---

## 服务管理

### 查看服务状态

```bash
# 查看所有容器
docker-compose -f docker-compose.local.yml ps

# 查看详细信息
docker-compose -f docker-compose.local.yml ps -a

# 查看容器资源使用
docker stats

# 查看特定容器信息
docker inspect <container_id>
```

### 启动服务

```bash
# 启动所有服务
docker-compose -f docker-compose.local.yml up -d

# 启动特定服务
docker-compose -f docker-compose.local.yml up -d postgres
docker-compose -f docker-compose.local.yml up -d redis
docker-compose -f docker-compose.local.yml up -d neo4j
docker-compose -f docker-compose.local.yml up -d label-studio
```

### 停止服务

```bash
# 停止所有服务（保留数据）
docker-compose -f docker-compose.local.yml stop

# 停止特定服务
docker-compose -f docker-compose.local.yml stop postgres

# 停止并删除容器（保留数据）
docker-compose -f docker-compose.local.yml down

# 停止并删除容器和数据
docker-compose -f docker-compose.local.yml down -v
```

### 重启服务

```bash
# 重启所有服务
docker-compose -f docker-compose.local.yml restart

# 重启特定服务
docker-compose -f docker-compose.local.yml restart postgres
docker-compose -f docker-compose.local.yml restart redis
docker-compose -f docker-compose.local.yml restart neo4j
docker-compose -f docker-compose.local.yml restart label-studio
```

### 查看容器信息

```bash
# 查看容器网络
docker network inspect superinsight-network

# 查看容器卷
docker volume ls

# 查看容器日志大小
docker ps -a --format "table {{.Names}}\t{{.Size}}"
```

---

## 日志和监控

### 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.local.yml logs

# 实时查看所有日志
docker-compose -f docker-compose.local.yml logs -f

# 查看最后 100 行日志
docker-compose -f docker-compose.local.yml logs --tail=100

# 查看特定服务日志
docker-compose -f docker-compose.local.yml logs postgres
docker-compose -f docker-compose.local.yml logs redis
docker-compose -f docker-compose.local.yml logs neo4j
docker-compose -f docker-compose.local.yml logs label-studio

# 实时查看特定服务日志
docker-compose -f docker-compose.local.yml logs -f postgres

# 查看特定时间范围的日志
docker-compose -f docker-compose.local.yml logs --since 2026-01-09T14:00:00
docker-compose -f docker-compose.local.yml logs --until 2026-01-09T15:00:00
```

### 监控资源使用

```bash
# 实时监控所有容器
docker stats

# 监控特定容器
docker stats superinsight-postgres
docker stats superinsight-redis
docker stats superinsight-neo4j
docker stats superinsight-label-studio

# 查看容器进程
docker top <container_id>

# 查看容器网络统计
docker stats --no-stream
```

### 查看事件

```bash
# 查看 Docker 事件
docker events

# 查看特定容器的事件
docker events --filter "container=superinsight-postgres"

# 查看特定类型的事件
docker events --filter "type=container"
```

---

## 数据库操作

### PostgreSQL 操作

```bash
# 进入 PostgreSQL
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight

# 执行 SQL 命令
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "SELECT version();"

# 列出所有数据库
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -l

# 列出所有表
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "\dt"

# 备份数据库
docker-compose -f docker-compose.local.yml exec postgres pg_dump -U superinsight superinsight > backup.sql

# 恢复数据库
docker-compose -f docker-compose.local.yml exec -T postgres psql -U superinsight superinsight < backup.sql

# 查看数据库大小
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "SELECT pg_size_pretty(pg_database_size('superinsight'));"

# 查看表大小
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# 查看活跃连接
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "SELECT count(*) FROM pg_stat_activity;"

# 查看慢查询
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### Redis 操作

```bash
# 进入 Redis
docker-compose -f docker-compose.local.yml exec redis redis-cli

# 执行 Redis 命令
docker-compose -f docker-compose.local.yml exec redis redis-cli PING

# 查看 Redis 信息
docker-compose -f docker-compose.local.yml exec redis redis-cli INFO

# 查看内存使用
docker-compose -f docker-compose.local.yml exec redis redis-cli INFO memory

# 查看所有键
docker-compose -f docker-compose.local.yml exec redis redis-cli KEYS "*"

# 查看键的类型
docker-compose -f docker-compose.local.yml exec redis redis-cli TYPE <key>

# 查看键的值
docker-compose -f docker-compose.local.yml exec redis redis-cli GET <key>

# 删除键
docker-compose -f docker-compose.local.yml exec redis redis-cli DEL <key>

# 清空数据库
docker-compose -f docker-compose.local.yml exec redis redis-cli FLUSHDB

# 备份数据
docker-compose -f docker-compose.local.yml exec redis redis-cli BGSAVE

# 查看备份状态
docker-compose -f docker-compose.local.yml exec redis redis-cli LASTSAVE
```

### Neo4j 操作

```bash
# 进入 Neo4j
docker-compose -f docker-compose.local.yml exec neo4j cypher-shell -u neo4j -p password

# 查看 Neo4j 版本
curl -u neo4j:password http://localhost:7474/db/neo4j/info

# 查看数据库统计
curl -u neo4j:password http://localhost:7474/db/neo4j/stats

# 访问 Neo4j Browser
# http://localhost:7474

# 执行 Cypher 查询
docker-compose -f docker-compose.local.yml exec neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n);"

# 导出数据
docker-compose -f docker-compose.local.yml exec neo4j neo4j-admin database dump neo4j --to-path=/data/backups

# 导入数据
docker-compose -f docker-compose.local.yml exec neo4j neo4j-admin database load neo4j --from-path=/data/backups
```

---

## 故障排查

### 常见问题

#### 问题 1: 容器无法启动

```bash
# 查看错误日志
docker-compose -f docker-compose.local.yml logs <service>

# 检查容器状态
docker-compose -f docker-compose.local.yml ps

# 查看容器详情
docker inspect <container_id>

# 重启容器
docker-compose -f docker-compose.local.yml restart <service>
```

#### 问题 2: 端口被占用

```bash
# 查找占用端口的进程
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :7474  # Neo4j
lsof -i :8080  # Label Studio

# 杀死进程
kill -9 <PID>

# 或者修改 docker-compose.local.yml 中的端口映射
```

#### 问题 3: 网络连接问题

```bash
# 检查网络
docker network ls
docker network inspect superinsight-network

# 测试容器间通信
docker-compose -f docker-compose.local.yml exec postgres ping redis

# 重新创建网络
docker network rm superinsight-network 2>/dev/null || true
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
```

#### 问题 4: 内存不足

```bash
# 检查 Docker 内存使用
docker stats

# 检查系统内存
free -h

# 增加 Docker 内存限制
# 在 Docker Desktop 设置中增加内存分配（建议 4GB+）

# 清理未使用的镜像和容器
docker system prune -f
```

#### 问题 5: 磁盘空间不足

```bash
# 检查磁盘使用
df -h

# 查看 Docker 磁盘使用
docker system df

# 清理未使用的镜像
docker image prune -f

# 清理未使用的容器
docker container prune -f

# 清理未使用的卷
docker volume prune -f

# 完整清理
docker system prune -f
```

### 诊断工具

```bash
# 运行完整诊断
bash docker_diagnostic.sh diagnose

# 修复 PostgreSQL
bash docker_diagnostic.sh fix-postgres

# 修复所有服务
bash docker_diagnostic.sh fix-all

# 清理磁盘空间
bash docker_diagnostic.sh cleanup
```

---

## 备份和恢复

### 备份数据库

```bash
# 备份 PostgreSQL
docker-compose -f docker-compose.local.yml exec postgres pg_dump -U superinsight superinsight > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份 Redis
docker-compose -f docker-compose.local.yml exec redis redis-cli BGSAVE
docker cp superinsight-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d_%H%M%S).rdb

# 备份 Neo4j
docker-compose -f docker-compose.local.yml exec neo4j neo4j-admin database dump neo4j --to-path=/data/backups

# 备份所有数据目录
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/
```

### 恢复数据库

```bash
# 恢复 PostgreSQL
docker-compose -f docker-compose.local.yml exec -T postgres psql -U superinsight superinsight < backup.sql

# 恢复 Redis
docker cp redis_backup.rdb superinsight-redis:/data/dump.rdb
docker-compose -f docker-compose.local.yml restart redis

# 恢复 Neo4j
docker-compose -f docker-compose.local.yml exec neo4j neo4j-admin database load neo4j --from-path=/data/backups

# 恢复所有数据
tar -xzf backup.tar.gz
```

### 定期备份脚本

```bash
#!/bin/bash

# 创建备份目录
BACKUP_DIR="./backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
echo "备份 PostgreSQL..."
docker-compose -f docker-compose.local.yml exec postgres pg_dump -U superinsight superinsight > $BACKUP_DIR/postgres_backup.sql

# 备份 Redis
echo "备份 Redis..."
docker-compose -f docker-compose.local.yml exec redis redis-cli BGSAVE
docker cp superinsight-redis:/data/dump.rdb $BACKUP_DIR/redis_backup.rdb

# 备份 Neo4j
echo "备份 Neo4j..."
docker-compose -f docker-compose.local.yml exec neo4j neo4j-admin database dump neo4j --to-path=/data/backups

# 压缩备份
echo "压缩备份..."
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR

# 删除旧备份（保留 7 天）
find ./backups -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;

echo "备份完成: $BACKUP_DIR.tar.gz"
```

---

## 性能优化

### 数据库优化

```bash
# PostgreSQL 性能调优
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight -c "
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
docker-compose -f docker-compose.local.yml restart postgres
```

### Redis 优化

```bash
# 查看 Redis 配置
docker-compose -f docker-compose.local.yml exec redis redis-cli CONFIG GET "*"

# 设置最大内存
docker-compose -f docker-compose.local.yml exec redis redis-cli CONFIG SET maxmemory 1gb

# 设置淘汰策略
docker-compose -f docker-compose.local.yml exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

## 清理和维护

### 清理容器

```bash
# 删除已停止的容器
docker container prune -f

# 删除特定容器
docker rm <container_id>

# 强制删除运行中的容器
docker rm -f <container_id>
```

### 清理镜像

```bash
# 删除未使用的镜像
docker image prune -f

# 删除所有镜像
docker image prune -a -f

# 删除特定镜像
docker rmi <image_id>
```

### 清理卷

```bash
# 删除未使用的卷
docker volume prune -f

# 删除特定卷
docker volume rm <volume_name>

# 列出所有卷
docker volume ls
```

### 完整清理

```bash
# 删除所有未使用的资源
docker system prune -f

# 删除所有资源（包括已使用的）
docker system prune -a -f
```

---

## 常用快捷命令

```bash
# 查看所有容器
alias dps='docker-compose -f docker-compose.local.yml ps'

# 查看日志
alias dlogs='docker-compose -f docker-compose.local.yml logs -f'

# 进入 PostgreSQL
alias dpg='docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight'

# 进入 Redis
alias dredis='docker-compose -f docker-compose.local.yml exec redis redis-cli'

# 进入 Neo4j
alias dneo4j='docker-compose -f docker-compose.local.yml exec neo4j cypher-shell -u neo4j -p password'

# 启动所有服务
alias dup='docker-compose -f docker-compose.local.yml up -d'

# 停止所有服务
alias ddown='docker-compose -f docker-compose.local.yml down'

# 重启所有服务
alias drestart='docker-compose -f docker-compose.local.yml restart'

# 查看资源使用
alias dstats='docker stats'
```

---

## 获取帮助

### 查看文档

- 快速启动: `QUICK_DOCKER_STARTUP.sh`
- 完整指南: `DOCKER_FULLSTACK_COMPLETE_GUIDE.md`
- 启动总结: `DOCKER_STARTUP_COMPLETE_SUMMARY.md`
- 操作指南: `DOCKER_OPERATIONS_GUIDE.md`

### 运行诊断

```bash
bash docker_diagnostic.sh diagnose
```

### 查看日志

```bash
docker-compose -f docker-compose.local.yml logs -f
```

---

**最后更新**: 2026-01-09
**版本**: 1.0
