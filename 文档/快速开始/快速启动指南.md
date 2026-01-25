# SuperInsight 快速启动指南

## 📋 前置要求

- Docker 20.10+ 
- Docker Compose 2.0+ (或 docker-compose 1.29+)
- 至少 8GB 可用内存
- 至少 20GB 可用磁盘空间

## 🚀 一键启动

### 方式一：使用启动脚本（推荐）

```bash
# 1. 赋予执行权限
chmod +x start-superinsight.sh

# 2. 运行启动脚本
./start-superinsight.sh
```

脚本会自动：
- ✅ 检查 Docker 环境
- ✅ 初始化配置文件
- ✅ 创建必要目录
- ✅ 启动所有服务
- ✅ 检查服务健康状态
- ✅ 显示访问信息

### 方式二：手动启动

```bash
# 1. 复制环境变量配置
cp .env.example .env

# 2. 编辑 .env 文件，修改必要的配置（特别是密码）
nano .env  # 或使用其他编辑器

# 3. 创建必要的目录
mkdir -p data/{postgres,redis,neo4j,label-studio,ollama}
mkdir -p logs/{postgres,redis,neo4j,label-studio,api,ollama}
mkdir -p uploads exports

# 4. 启动服务
docker compose up -d

# 5. 查看服务状态
docker compose ps

# 6. 查看日志
docker compose logs -f
```

## 🌐 访问地址

启动成功后，可以通过以下地址访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| **API 文档** | http://localhost:8000/docs | FastAPI Swagger 文档 |
| **API 健康检查** | http://localhost:8000/health | 服务健康状态 |
| **Label Studio** | http://localhost:8080 | 数据标注平台 |
| **Neo4j 浏览器** | http://localhost:7474 | 知识图谱浏览器 |
| **Ollama API** | http://localhost:11434 | 本地 LLM 服务（可选） |

## 👤 默认登录信息

### Label Studio
- **用户名**: `admin@superinsight.com`
- **密码**: 见 `.env` 文件中的 `LABEL_STUDIO_PASSWORD`

### Neo4j
- **用户名**: `neo4j`
- **密码**: 见 `.env` 文件中的 `NEO4J_PASSWORD`

### API 测试用户
演示环境接受任意密码：
- `admin` - 系统管理员
- `business_expert` - 业务专家
- `tech_expert` - 技术专家
- `annotator1` - 数据标注员

## 🔧 常用命令

### 服务管理

```bash
# 启动所有服务
docker compose up -d

# 启动特定服务
docker compose up -d postgres redis

# 停止所有服务
docker compose down

# 停止并删除数据卷（⚠️ 会删除所有数据）
docker compose down -v

# 重启服务
docker compose restart

# 重启特定服务
docker compose restart superinsight-api
```

### 日志查看

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f superinsight-api

# 查看最近 100 行日志
docker compose logs --tail=100 superinsight-api

# 查看实时日志（不包含历史）
docker compose logs -f --tail=0
```

### 服务状态

```bash
# 查看服务状态
docker compose ps

# 查看服务详细信息
docker compose ps -a

# 查看资源使用情况
docker stats
```

### 数据库操作

```bash
# 进入 PostgreSQL 容器
docker compose exec postgres psql -U superinsight -d superinsight

# 备份数据库
docker compose exec postgres pg_dump -U superinsight superinsight > backup.sql

# 恢复数据库
docker compose exec -T postgres psql -U superinsight superinsight < backup.sql

# 进入 Redis 容器
docker compose exec redis redis-cli

# 进入 Neo4j Cypher Shell
docker compose exec neo4j cypher-shell -u neo4j -p password
```

### 容器操作

```bash
# 进入 API 容器
docker compose exec superinsight-api bash

# 在容器中执行命令
docker compose exec superinsight-api python -c "print('Hello')"

# 查看容器日志文件
docker compose exec superinsight-api ls -la /app/logs
```

## 🎯 启动特定配置

### 启动 Ollama 本地 LLM

```bash
# 启动包含 Ollama 的服务
docker compose --profile ollama up -d

# 下载模型（例如 llama2）
docker compose exec ollama ollama pull llama2

# 列出已下载的模型
docker compose exec ollama ollama list

# 测试模型
docker compose exec ollama ollama run llama2 "Hello, how are you?"
```

### 启动前端开发服务器

```bash
# 启动包含前端的服务
docker compose --profile frontend up -d

# 访问前端
# http://localhost:5173
```

### 同时启动所有服务（包括可选服务）

```bash
docker compose --profile ollama --profile frontend up -d
```

## 🔍 故障排查

### 服务无法启动

```bash
# 1. 查看服务日志
docker compose logs superinsight-api

# 2. 检查端口占用
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# 3. 检查 Docker 资源
docker system df

# 4. 清理未使用的资源
docker system prune -a
```

### 数据库连接失败

```bash
# 1. 检查数据库是否运行
docker compose ps postgres

# 2. 检查数据库日志
docker compose logs postgres

# 3. 测试数据库连接
docker compose exec postgres pg_isready -U superinsight

# 4. 重启数据库
docker compose restart postgres
```

### 内存不足

```bash
# 1. 查看资源使用
docker stats

# 2. 限制服务内存（编辑 docker-compose.yml）
services:
  superinsight-api:
    deploy:
      resources:
        limits:
          memory: 2G

# 3. 增加 Docker 内存限制（Docker Desktop 设置）
```

### 磁盘空间不足

```bash
# 1. 查看磁盘使用
docker system df

# 2. 清理未使用的镜像
docker image prune -a

# 3. 清理未使用的卷
docker volume prune

# 4. 清理构建缓存
docker builder prune
```

## 📊 性能优化

### 生产环境配置

1. **修改 .env 文件**：
```bash
DEBUG=false
LOG_LEVEL=WARNING
WORKER_CONCURRENCY=8
DB_POOL_SIZE=50
```

2. **使用生产环境配置**：
```bash
docker compose -f docker-compose.yml -f 文档/Docker/docker-compose.prod.yml up -d
```

### 数据库优化

```bash
# 编辑 PostgreSQL 配置
# deploy/private/postgres.conf

# 常用优化参数
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
```

## 🔐 安全建议

### 生产环境部署前必做

1. **修改所有默认密码**：
   - PostgreSQL 密码
   - Neo4j 密码
   - Label Studio 密码
   - JWT 密钥

2. **启用 HTTPS**：
   - 配置 Nginx 反向代理
   - 使用 Let's Encrypt 证书

3. **限制网络访问**：
   - 使用防火墙规则
   - 配置 Docker 网络隔离

4. **启用审计日志**：
```bash
AUDIT_LOG_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=90
```

5. **数据加密**：
```bash
DATA_ENCRYPTION_ENABLED=true
ENCRYPTION_ALGORITHM=AES-256-GCM
```

## 📚 更多资源

- [完整文档](./README.md)
- [API 文档](http://localhost:8000/docs)
- [架构设计](./docs/architecture.md)
- [开发指南](./docs/development.md)
- [故障排查](./docs/troubleshooting.md)

## 🆘 获取帮助

如果遇到问题：

1. 查看日志：`docker compose logs -f`
2. 检查服务状态：`docker compose ps`
3. 查看健康检查：`curl http://localhost:8000/health`
4. 提交 Issue：[GitHub Issues](https://github.com/Angus1976/superinsight1225/issues)

## 🎉 下一步

启动成功后，你可以：

1. 访问 API 文档了解可用接口
2. 登录 Label Studio 创建标注项目
3. 使用 Neo4j 浏览器查看知识图谱
4. 测试 AI 预标注功能
5. 查看系统监控指标

祝使用愉快！🚀
