# SuperInsight 部署指南

## 📦 部署方式

SuperInsight 支持多种部署方式，适用于不同的场景：

### 1. Docker Compose 一键部署（推荐）✅

**适用场景**：开发、测试、小规模生产环境

**优势**：
- ✅ 一键启动所有服务
- ✅ 自动配置网络和依赖
- ✅ 包含完整的数据库和 LLM 集成
- ✅ 易于维护和更新

**部署步骤**：
```bash
# 1. 克隆仓库
git clone https://github.com/Angus1976/superinsight1225.git
cd superinsight1225

# 2. 运行一键启动脚本
chmod +x start-superinsight.sh
./start-superinsight.sh
```

详细说明请参考 [QUICK_START.md](./QUICK_START.md)

---

### 2. 生产环境部署

**适用场景**：大规模生产环境、高可用部署

**配置文件**：`文档/Docker/docker-compose.prod.yml`

**特性**：
- 🔒 增强的安全配置
- 📊 完整的监控和日志
- 🚀 性能优化配置
- 🔄 高可用支持

**部署步骤**：
```bash
# 1. 使用生产环境配置
docker compose -f docker-compose.yml -f 文档/Docker/docker-compose.prod.yml up -d

# 2. 配置 Nginx 反向代理
# 3. 配置 SSL 证书
# 4. 配置防火墙规则
```

---

### 3. 腾讯云 TCB 部署

**适用场景**：腾讯云环境、Serverless 部署

**配置文件**：`deploy/tcb/`

**部署步骤**：
```bash
# 1. 安装 TCB CLI
npm install -g @cloudbase/cli

# 2. 登录腾讯云
tcb login

# 3. 部署
tcb framework deploy
```

---

### 4. 私有化部署

**适用场景**：企业内网、离线环境

**配置文件**：`deploy/private/`

**特性**：
- 🔐 完全离线部署
- 🏢 企业级安全
- 📦 自定义镜像仓库

**部署步骤**：
```bash
# 1. 构建镜像
docker build -t superinsight-api:latest -f deploy/private/Dockerfile.api .

# 2. 推送到私有镜像仓库
docker tag superinsight-api:latest your-registry/superinsight-api:latest
docker push your-registry/superinsight-api:latest

# 3. 使用私有镜像部署
docker compose -f deploy/private/docker-compose.yml up -d
```

---

### 5. 混合云部署

**适用场景**：云端+本地混合部署

**配置文件**：`deploy/hybrid/`

**特性**：
- ☁️ 云端数据存储
- 💻 本地数据处理
- 🔄 双向数据同步
- 🔒 安全通道

---

## 🔧 服务组件

### 核心服务

| 服务 | 端口 | 说明 | 必需 |
|------|------|------|------|
| PostgreSQL | 5432 | 主数据库 | ✅ |
| Redis | 6379 | 缓存和队列 | ✅ |
| Neo4j | 7474, 7687 | 知识图谱 | ✅ |
| Label Studio | 8080 | 标注平台 | ✅ |
| SuperInsight API | 8000 | 后端 API | ✅ |

### 可选服务

| 服务 | 端口 | 说明 | 启用方式 |
|------|------|------|----------|
| Ollama | 11434 | 本地 LLM | `--profile ollama` |
| Frontend | 5173 | 前端界面 | `--profile frontend` |
| Prometheus | 9090 | 监控 | 生产环境配置 |
| Grafana | 3000 | 可视化 | 生产环境配置 |
| Nginx | 80, 443 | 反向代理 | 生产环境配置 |

---

## 📊 资源要求

### 最小配置（开发/测试）

- **CPU**: 4 核
- **内存**: 8 GB
- **磁盘**: 20 GB
- **网络**: 10 Mbps

### 推荐配置（生产环境）

- **CPU**: 8 核+
- **内存**: 16 GB+
- **磁盘**: 100 GB+ SSD
- **网络**: 100 Mbps+

### 大规模部署

- **CPU**: 16 核+
- **内存**: 32 GB+
- **磁盘**: 500 GB+ SSD
- **网络**: 1 Gbps+
- **GPU**: NVIDIA GPU（用于 Ollama）

---

## 🔐 安全配置

### 必须修改的默认值

在生产环境部署前，**必须**修改以下默认值：

```bash
# .env 文件
POSTGRES_PASSWORD=your_strong_password_here
NEO4J_PASSWORD=your_strong_password_here
LABEL_STUDIO_PASSWORD=your_strong_password_here
JWT_SECRET_KEY=your_random_secret_key_at_least_32_chars
ENCRYPTION_KEY=your_random_32_byte_key_base64_encoded
```

### 安全检查清单

- [ ] 修改所有默认密码
- [ ] 配置 HTTPS/SSL
- [ ] 启用防火墙规则
- [ ] 配置网络隔离
- [ ] 启用审计日志
- [ ] 配置数据加密
- [ ] 设置备份策略
- [ ] 配置监控告警

---

## 🔄 数据备份

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/$DATE"

mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
docker compose exec -T postgres pg_dump -U superinsight superinsight > $BACKUP_DIR/postgres.sql

# 备份 Neo4j
docker compose exec -T neo4j neo4j-admin dump --to=/tmp/neo4j-backup.dump
docker compose cp neo4j:/tmp/neo4j-backup.dump $BACKUP_DIR/neo4j.dump

# 备份上传文件
tar -czf $BACKUP_DIR/uploads.tar.gz uploads/

# 备份配置文件
cp .env $BACKUP_DIR/

echo "备份完成: $BACKUP_DIR"
```

### 恢复数据

```bash
#!/bin/bash
# restore.sh

BACKUP_DIR=$1

# 恢复 PostgreSQL
docker compose exec -T postgres psql -U superinsight superinsight < $BACKUP_DIR/postgres.sql

# 恢复 Neo4j
docker compose cp $BACKUP_DIR/neo4j.dump neo4j:/tmp/neo4j-backup.dump
docker compose exec neo4j neo4j-admin load --from=/tmp/neo4j-backup.dump --force

# 恢复上传文件
tar -xzf $BACKUP_DIR/uploads.tar.gz

echo "恢复完成"
```

---

## 📈 监控和日志

### 日志位置

```
logs/
├── api/          # API 服务日志
├── postgres/     # PostgreSQL 日志
├── redis/        # Redis 日志
├── neo4j/        # Neo4j 日志
├── label-studio/ # Label Studio 日志
└── ollama/       # Ollama 日志
```

### 查看日志

```bash
# 实时查看所有日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f superinsight-api

# 查看最近 100 行
docker compose logs --tail=100 superinsight-api

# 查看错误日志
docker compose logs | grep ERROR
```

### Prometheus 监控

访问 http://localhost:9090 查看监控指标：

- API 请求量和延迟
- 数据库连接池状态
- Redis 缓存命中率
- AI 模型推理性能
- 系统资源使用情况

### Grafana 可视化

访问 http://localhost:3000 查看可视化仪表板：

- 系统概览
- API 性能
- 数据库性能
- 业务指标
- 告警历史

---

## 🔧 故障排查

### 常见问题

#### 1. 端口被占用

```bash
# 查看端口占用
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# 修改端口（编辑 .env）
API_PORT=8001
```

#### 2. 内存不足

```bash
# 查看资源使用
docker stats

# 限制服务内存
# 编辑 docker-compose.yml
services:
  superinsight-api:
    deploy:
      resources:
        limits:
          memory: 2G
```

#### 3. 数据库连接失败

```bash
# 检查数据库状态
docker compose ps postgres

# 查看数据库日志
docker compose logs postgres

# 测试连接
docker compose exec postgres pg_isready -U superinsight

# 重启数据库
docker compose restart postgres
```

#### 4. Ollama 模型下载失败

```bash
# 手动下载模型
docker compose exec ollama ollama pull llama2

# 使用国内镜像
# 编辑 .env
OLLAMA_MIRRORS=https://ollama.ai.cn
```

---

## 🚀 性能优化

### 数据库优化

```sql
-- PostgreSQL 配置优化
-- deploy/private/postgres.conf

shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
```

### Redis 优化

```conf
# deploy/private/redis.conf

maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### API 优化

```bash
# .env 配置
WORKER_CONCURRENCY=8
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=10
REDIS_POOL_SIZE=20
```

---

## 📚 相关文档

- [快速启动指南](./QUICK_START.md)
- [开发指南](./docs/development.md)
- [API 文档](http://localhost:8000/docs)
- [架构设计](./docs/architecture.md)
- [安全指南](./docs/security.md)

---

## 🆘 获取帮助

- **GitHub Issues**: https://github.com/Angus1976/superinsight1225/issues
- **文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## 📝 更新日志

### v1.0.0 (2026-01-20)
- ✅ 完成 Docker Compose 一键部署
- ✅ 集成所有核心服务
- ✅ 添加 Ollama LLM 支持
- ✅ 完善监控和日志
- ✅ 添加自动化脚本
