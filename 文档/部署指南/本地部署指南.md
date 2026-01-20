# SuperInsight 平台本地部署指南

## 前置条件

✅ Docker Desktop 已安装并启动
✅ 相关数据库已安装
✅ Python 3.9+ 已安装
✅ Git 已安装

## 快速开始

### 1. 环境配置

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑 .env 文件，配置本地环境
# 主要配置项：
# - DATABASE_URL: PostgreSQL 连接字符串
# - REDIS_URL: Redis 连接字符串
# - LABEL_STUDIO_URL: Label Studio 地址
# - SECRET_KEY: JWT 密钥
```

### 2. 启动 Docker 容器

```bash
# 启动所有服务（PostgreSQL, Redis, Neo4j, Label Studio）
docker-compose up -d

# 验证容器状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 3. 初始化数据库

```bash
# 运行数据库迁移
python3 -m alembic upgrade head

# 创建初始用户和权限
python3 scripts/run_migrations.py
```

### 4. 启动应用程序

#### 方式 1: 直接运行（开发模式）

```bash
# 安装依赖
pip3 install -r requirements.txt

# 启动应用
python3 -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

#### 方式 2: 使用 Docker Compose（推荐）

```bash
# 构建并启动应用容器
docker-compose up -d superinsight-api

# 查看应用日志
docker-compose logs -f superinsight-api
```

### 5. 验证部署

```bash
# 检查应用健康状态
curl http://localhost:8000/health

# 查看 API 文档
# 浏览器访问: http://localhost:8000/docs

# 查看系统状态
curl http://localhost:8000/system/status

# 查看所有服务
curl http://localhost:8000/system/services
```

## 服务访问地址

| 服务 | 地址 | 用途 |
|------|------|------|
| SuperInsight API | http://localhost:8000 | 主应用 API |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| PostgreSQL | localhost:5432 | 数据库 |
| Redis | localhost:6379 | 缓存 |
| Neo4j | http://localhost:7474 | 图数据库 UI |
| Neo4j Bolt | localhost:7687 | 图数据库连接 |
| Label Studio | http://localhost:8080 | 标注平台 |

## 默认凭证

### Label Studio
- 用户名: admin@superinsight.com
- 密码: admin123

### PostgreSQL
- 用户名: superinsight
- 密码: password
- 数据库: superinsight

### Neo4j
- 用户名: neo4j
- 密码: password

## 主要 API 端点

### 系统管理
- `GET /health` - 健康检查
- `GET /system/status` - 系统状态
- `GET /system/services` - 所有服务状态
- `GET /system/metrics` - 系统指标

### 数据提取
- `POST /api/v1/extraction/extract` - 提取数据
- `GET /api/v1/extraction/tasks/{task_id}` - 获取任务状态
- `GET /api/v1/extraction/results/{task_id}` - 获取提取结果

### 质量管理
- `POST /api/v1/quality/evaluate` - 评估质量
- `GET /api/v1/quality/metrics` - 获取质量指标
- `POST /api/v1/quality/workorders` - 创建工单

### AI 标注
- `POST /api/ai/preannotate` - AI 预标注
- `GET /api/ai/models` - 获取可用模型
- `POST /api/ai/evaluate` - 评估 AI 性能

### 计费
- `GET /api/billing/usage` - 获取使用统计
- `GET /api/billing/invoices` - 获取发票
- `POST /api/billing/calculate` - 计算费用

### 安全
- `POST /api/security/login` - 用户登录
- `POST /api/security/users` - 创建用户
- `GET /api/security/permissions` - 获取权限

### 知识图谱
- `POST /api/v1/knowledge-graph/entities` - 创建实体
- `POST /api/v1/knowledge-graph/relations` - 创建关系
- `GET /api/v1/knowledge-graph/query` - 查询图数据

## 用户角色和权限

### 系统管理员 (Admin)
- 完全访问所有功能
- 用户和权限管理
- 系统配置
- 监控和告警

### 业务专家 (Business Expert)
- 数据提取和处理
- 质量评估
- 工单管理
- 报表查看

### 标注员 (Annotator)
- 数据标注
- 标注任务查看
- 个人统计查看

### 查看者 (Viewer)
- 只读访问
- 报表查看
- 统计数据查看

## 测试各角色功能

### 1. 创建测试用户

```bash
# 创建管理员用户
curl -X POST http://localhost:8000/api/security/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "admin123",
    "full_name": "System Administrator",
    "role": "ADMIN"
  }'

# 创建业务专家用户
curl -X POST http://localhost:8000/api/security/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "expert",
    "email": "expert@example.com",
    "password": "expert123",
    "full_name": "Business Expert",
    "role": "BUSINESS_EXPERT"
  }'

# 创建标注员用户
curl -X POST http://localhost:8000/api/security/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "annotator",
    "email": "annotator@example.com",
    "password": "annotator123",
    "full_name": "Data Annotator",
    "role": "ANNOTATOR"
  }'

# 创建查看者用户
curl -X POST http://localhost:8000/api/security/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "viewer",
    "email": "viewer@example.com",
    "password": "viewer123",
    "full_name": "Report Viewer",
    "role": "VIEWER"
  }'
```

### 2. 用户登录

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'

# 响应示例：
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "user": {
#     "id": "uuid",
#     "username": "admin",
#     "role": "ADMIN"
#   }
# }
```

### 3. 测试数据提取功能

```bash
# 使用 Token 进行数据提取
curl -X POST http://localhost:8000/api/v1/extraction/extract \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "database",
    "source_config": {
      "host": "localhost",
      "port": 5432,
      "database": "test_db",
      "username": "user",
      "password": "pass"
    },
    "query": "SELECT * FROM users LIMIT 100"
  }'
```

### 4. 测试质量评估

```bash
# 评估数据质量
curl -X POST http://localhost:8000/api/v1/quality/evaluate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"text": "这是一条测试数据", "label": "正常"},
      {"text": "这是另一条测试数据", "label": "正常"}
    ],
    "metrics": ["completeness", "accuracy", "consistency"]
  }'
```

### 5. 测试 AI 预标注

```bash
# 获取 AI 预标注
curl -X POST http://localhost:8000/api/ai/preannotate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["这是一条需要标注的文本"],
    "model": "bert-base-chinese",
    "task_type": "classification"
  }'
```

## 故障排除

### 问题 1: 数据库连接失败

```bash
# 检查 PostgreSQL 容器状态
docker-compose ps postgres

# 查看 PostgreSQL 日志
docker-compose logs postgres

# 重启 PostgreSQL
docker-compose restart postgres
```

### 问题 2: Redis 连接失败

```bash
# 检查 Redis 容器状态
docker-compose ps redis

# 测试 Redis 连接
redis-cli -h localhost -p 6379 ping

# 重启 Redis
docker-compose restart redis
```

### 问题 3: Label Studio 无法访问

```bash
# 检查 Label Studio 容器状态
docker-compose ps label-studio

# 查看 Label Studio 日志
docker-compose logs label-studio

# 重启 Label Studio
docker-compose restart label-studio
```

### 问题 4: 应用启动失败

```bash
# 查看应用日志
docker-compose logs superinsight-api

# 检查依赖是否安装
pip3 install -r requirements.txt

# 检查数据库迁移
python3 -m alembic current
python3 -m alembic upgrade head
```

## 性能优化

### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_annotations_task_id ON annotations(task_id);

-- 分析表
ANALYZE users;
ANALYZE tasks;
ANALYZE annotations;
```

### 2. Redis 缓存配置

```python
# 在 .env 中配置
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
```

### 3. 应用配置优化

```python
# 在 src/config/settings.py 中配置
WORKER_THREADS=4
ASYNC_WORKERS=8
CONNECTION_POOL_SIZE=20
```

## 监控和日志

### 查看系统指标

```bash
# 获取系统指标
curl http://localhost:8000/system/metrics

# 获取 Prometheus 格式指标
curl http://localhost:8000/metrics
```

### 查看应用日志

```bash
# 实时查看日志
docker-compose logs -f superinsight-api

# 查看特定服务日志
docker-compose logs postgres
docker-compose logs redis
docker-compose logs neo4j
```

### 监控数据库

```bash
# 连接到 PostgreSQL
psql -h localhost -U superinsight -d superinsight

# 查看活跃连接
SELECT * FROM pg_stat_activity;

# 查看表大小
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
```

## 清理和重置

### 清理所有容器和数据

```bash
# 停止所有容器
docker-compose down

# 删除所有数据卷
docker-compose down -v

# 删除所有镜像
docker-compose down --rmi all
```

### 重置数据库

```bash
# 删除数据库
dropdb -h localhost -U superinsight superinsight

# 重新创建数据库
createdb -h localhost -U superinsight superinsight

# 运行迁移
python3 -m alembic upgrade head
```

## 下一步

1. ✅ 验证所有服务正常运行
2. ✅ 创建测试用户和项目
3. ✅ 测试各个功能模块
4. ✅ 配置监控和告警
5. ✅ 准备生产部署

## 支持和帮助

- 查看 API 文档: http://localhost:8000/docs
- 查看系统状态: http://localhost:8000/system/status
- 查看健康检查: http://localhost:8000/health
- 查看错误日志: docker-compose logs superinsight-api
