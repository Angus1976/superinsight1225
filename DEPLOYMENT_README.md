# SuperInsight 平台本地部署完整指南

## 📖 文档概览

本部署包包含以下文档和脚本：

| 文件 | 说明 |
|------|------|
| **QUICK_START.md** | 5分钟快速启动指南（推荐首先阅读） |
| **LOCAL_DEPLOYMENT_GUIDE.md** | 详细的本地部署指南 |
| **deploy_local.sh** | 自动化部署脚本 |
| **test_roles_and_features.py** | 角色和功能测试脚本 |
| **DEPLOYMENT_README.md** | 本文件 |

## 🚀 快速开始（3步）

### 1️⃣ 启动所有服务

```bash
bash deploy_local.sh start
```

### 2️⃣ 验证部署

```bash
curl http://localhost:8000/health
```

### 3️⃣ 测试功能

```bash
python3 test_roles_and_features.py
```

## 📋 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   SuperInsight 平台                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   FastAPI    │  │   Security   │  │  Monitoring  │   │
│  │  Application │  │   Module     │  │   System     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│         │                 │                  │            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ PostgreSQL   │  │    Redis     │  │    Neo4j     │   │
│  │  Database    │  │    Cache     │  │  Graph DB    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│         │                 │                  │            │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Label Studio (标注平台)                   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## 🔧 服务配置

### PostgreSQL
- **容器名**: superinsight-postgres
- **端口**: 5432
- **用户**: superinsight
- **密码**: password
- **数据库**: superinsight

### Redis
- **容器名**: superinsight-redis
- **端口**: 6379
- **用途**: 缓存和会话存储

### Neo4j
- **容器名**: superinsight-neo4j
- **HTTP 端口**: 7474
- **Bolt 端口**: 7687
- **用户**: neo4j
- **密码**: password

### Label Studio
- **容器名**: superinsight-label-studio
- **端口**: 8080
- **用户**: admin@superinsight.com
- **密码**: admin123

### SuperInsight API
- **容器名**: superinsight-api
- **端口**: 8000
- **文档**: http://localhost:8000/docs

## 👥 用户角色和权限

### 1. 系统管理员 (ADMIN)
**权限:**
- ✅ 完全访问所有功能
- ✅ 用户和权限管理
- ✅ 系统配置
- ✅ 监控和告警
- ✅ 查看系统状态和指标

**可用 API:**
- `/system/status` - 系统状态
- `/system/services` - 所有服务
- `/system/metrics` - 系统指标
- `/api/security/users` - 用户管理

### 2. 业务专家 (BUSINESS_EXPERT)
**权限:**
- ✅ 数据提取和处理
- ✅ 质量评估
- ✅ 工单管理
- ✅ 报表查看
- ❌ 用户管理
- ❌ 系统配置

**可用 API:**
- `/api/v1/extraction/*` - 数据提取
- `/api/v1/quality/*` - 质量管理
- `/api/v1/tickets/*` - 工单管理
- `/api/billing/*` - 计费查看

### 3. 标注员 (ANNOTATOR)
**权限:**
- ✅ 数据标注
- ✅ 标注任务查看
- ✅ 个人统计查看
- ❌ 数据提取
- ❌ 系统管理

**可用 API:**
- `/api/v1/tasks/*` - 任务管理
- `/api/v1/annotations/*` - 标注操作
- `/api/v1/evaluation/*` - 个人评估

### 4. 查看者 (VIEWER)
**权限:**
- ✅ 只读访问
- ✅ 报表查看
- ✅ 统计数据查看
- ❌ 数据修改
- ❌ 系统管理

**可用 API:**
- `/api/v1/reports/*` - 报表查看
- `/api/v1/analytics/*` - 分析数据

## 🧪 测试场景

### 场景 1: 管理员操作

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin_test",
    "password": "admin123"
  }' | jq -r '.access_token')

# 2. 查看系统状态
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/system/status

# 3. 创建新用户
curl -X POST http://localhost:8000/api/security/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "full_name": "New User",
    "role": "VIEWER"
  }'
```

### 场景 2: 业务专家操作

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "expert_test",
    "password": "expert123"
  }' | jq -r '.access_token')

# 2. 提取数据
curl -X POST http://localhost:8000/api/v1/extraction/extract \
  -H "Authorization: Bearer $TOKEN" \
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

# 3. 评估质量
curl -X POST http://localhost:8000/api/v1/quality/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"text": "测试数据1", "label": "正常"},
      {"text": "测试数据2", "label": "正常"}
    ],
    "metrics": ["completeness", "accuracy"]
  }'
```

### 场景 3: 标注员操作

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "annotator_test",
    "password": "annotator123"
  }' | jq -r '.access_token')

# 2. 查看任务
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/tasks

# 3. 提交标注
curl -X POST http://localhost:8000/api/v1/annotations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_123",
    "annotation": {
      "label": "正确",
      "confidence": 0.95
    }
  }'
```

## 📊 监控和日志

### 查看系统指标

```bash
# 获取系统指标
curl http://localhost:8000/system/metrics

# 获取 Prometheus 格式指标
curl http://localhost:8000/metrics

# 获取系统状态
curl http://localhost:8000/system/status
```

### 查看应用日志

```bash
# 实时查看所有日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f superinsight-api
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f neo4j
docker-compose logs -f label-studio

# 查看最后 100 行日志
docker-compose logs --tail=100 superinsight-api
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

# 查看索引
SELECT * FROM pg_indexes WHERE schemaname = 'public';
```

## 🔍 故障排除

### 问题 1: 容器无法启动

```bash
# 查看容器日志
docker-compose logs postgres
docker-compose logs redis
docker-compose logs neo4j
docker-compose logs label-studio
docker-compose logs superinsight-api

# 重启容器
docker-compose restart

# 完全重建
docker-compose down -v
docker-compose up -d
```

### 问题 2: 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 测试连接
psql -h localhost -U superinsight -d superinsight -c "SELECT 1"

# 查看 PostgreSQL 日志
docker-compose logs postgres

# 重启 PostgreSQL
docker-compose restart postgres
```

### 问题 3: API 无法访问

```bash
# 检查应用容器
docker-compose ps superinsight-api

# 查看应用日志
docker-compose logs superinsight-api

# 检查端口是否被占用
lsof -i :8000

# 重启应用
docker-compose restart superinsight-api
```

### 问题 4: 测试脚本失败

```bash
# 确保 API 正在运行
curl http://localhost:8000/health

# 检查 Python 依赖
pip3 install requests

# 运行测试脚本
python3 test_roles_and_features.py

# 查看详细错误
python3 -u test_roles_and_features.py 2>&1 | tee test_output.log
```

## 🛠️ 常用命令

### 部署脚本命令

```bash
# 启动所有服务
bash deploy_local.sh start

# 停止所有服务
bash deploy_local.sh stop

# 重启所有服务
bash deploy_local.sh restart

# 查看服务状态
bash deploy_local.sh status

# 查看日志
bash deploy_local.sh logs

# 查看特定服务日志
bash deploy_local.sh logs superinsight-api

# 清理所有数据
bash deploy_local.sh clean
```

### Docker Compose 命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec superinsight-api bash

# 重启服务
docker-compose restart

# 删除所有数据
docker-compose down -v
```

### 数据库命令

```bash
# 连接到 PostgreSQL
psql -h localhost -U superinsight -d superinsight

# 运行迁移
python3 -m alembic upgrade head

# 创建初始数据
python3 scripts/run_migrations.py

# 备份数据库
pg_dump -h localhost -U superinsight -d superinsight > backup.sql

# 恢复数据库
psql -h localhost -U superinsight -d superinsight < backup.sql
```

## 📈 性能优化

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

-- 查看表大小
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 2. Redis 优化

```bash
# 查看 Redis 信息
redis-cli -h localhost -p 6379 INFO

# 查看内存使用
redis-cli -h localhost -p 6379 INFO memory

# 清理过期键
redis-cli -h localhost -p 6379 FLUSHDB

# 查看键数量
redis-cli -h localhost -p 6379 DBSIZE
```

### 3. 应用优化

```python
# 在 .env 中配置
WORKER_THREADS=4
ASYNC_WORKERS=8
CONNECTION_POOL_SIZE=20
CACHE_TTL=3600
```

## 🔐 安全建议

### 生产环境配置

1. **更改默认密码**
   ```bash
   # 更改 PostgreSQL 密码
   ALTER USER superinsight WITH PASSWORD 'new_password';
   
   # 更改 Neo4j 密码
   # 通过 Neo4j 管理界面更改
   ```

2. **配置 HTTPS**
   ```bash
   # 生成 SSL 证书
   openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
   
   # 在 docker-compose.yml 中配置
   ```

3. **配置防火墙**
   ```bash
   # 只允许必要的端口
   # 8000 - API
   # 8080 - Label Studio
   # 5432 - PostgreSQL (仅内部)
   # 6379 - Redis (仅内部)
   # 7474, 7687 - Neo4j (仅内部)
   ```

4. **启用认证**
   ```bash
   # 在 .env 中配置
   JWT_SECRET_KEY=your_secure_secret_key
   SECRET_KEY=your_secure_secret_key
   ```

## 📚 相关文档

- [QUICK_START.md](QUICK_START.md) - 快速启动指南
- [LOCAL_DEPLOYMENT_GUIDE.md](LOCAL_DEPLOYMENT_GUIDE.md) - 详细部署指南
- [API 文档](http://localhost:8000/docs) - 完整 API 文档

## 🎯 下一步

1. ✅ 完成本地部署
2. ✅ 验证所有服务正常运行
3. ✅ 创建测试用户和项目
4. ✅ 测试各个功能模块
5. ✅ 配置监控和告警
6. ✅ 准备生产部署

## 📞 支持

- 查看 API 文档: http://localhost:8000/docs
- 查看系统状态: http://localhost:8000/system/status
- 查看健康检查: http://localhost:8000/health
- 查看错误日志: `docker-compose logs superinsight-api`

## 🎉 完成！

恭喜！SuperInsight 平台已成功部署。现在你可以：

1. 访问 API 文档进行 API 测试
2. 使用测试用户登录系统
3. 测试各个功能模块
4. 查看系统监控和指标
5. 开始使用平台进行数据处理和标注

祝你使用愉快！🚀
