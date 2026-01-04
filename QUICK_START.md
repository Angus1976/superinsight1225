# SuperInsight 平台快速启动指南

## 🚀 5分钟快速启动

### 前置条件
- ✅ Docker Desktop 已安装并启动
- ✅ 相关数据库已安装
- ✅ Python 3.9+ 已安装

### 步骤 1: 启动所有服务

```bash
# 使用部署脚本启动（推荐）
bash deploy_local.sh start

# 或者手动启动
docker-compose up -d
```

**预期输出:**
```
Creating superinsight-postgres ... done
Creating superinsight-redis ... done
Creating superinsight-neo4j ... done
Creating superinsight-label-studio ... done
Creating superinsight-api ... done
```

### 步骤 2: 验证服务状态

```bash
# 查看所有容器状态
docker-compose ps

# 检查应用健康状态
curl http://localhost:8000/health
```

**预期输出:**
```json
{
  "overall_status": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "neo4j": "healthy"
  }
}
```

### 步骤 3: 访问应用

打开浏览器访问以下地址：

| 服务 | 地址 | 说明 |
|------|------|------|
| **API 文档** | http://localhost:8000/docs | Swagger UI，可直接测试 API |
| **系统状态** | http://localhost:8000/system/status | 查看系统运行状态 |
| **Label Studio** | http://localhost:8080 | 数据标注平台 |
| **Neo4j** | http://localhost:7474 | 图数据库管理界面 |

### 步骤 4: 测试各角色功能

```bash
# 运行测试脚本
python3 test_roles_and_features.py
```

**预期输出:**
```
============================================================
                    SuperInsight 平台测试套件
============================================================

检查 API 健康状态
✓ API 正在运行
  整体状态: healthy

创建测试用户
✓ 创建用户: 系统管理员 (ADMIN)
✓ 创建用户: 业务专家 (BUSINESS_EXPERT)
✓ 创建用户: 数据标注员 (ANNOTATOR)
✓ 创建用户: 报表查看者 (VIEWER)

用户登录
✓ 登录成功: 系统管理员
✓ 登录成功: 业务专家
✓ 登录成功: 数据标注员
✓ 登录成功: 报表查看者

...

============================================================
                        测试总结
============================================================

总计: 20 个测试
通过: 20
失败: 0

所有测试通过！✓
```

## 📋 常用命令

### 启动/停止服务

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
bash deploy_local.sh logs postgres
bash deploy_local.sh logs redis
```

### 数据库操作

```bash
# 连接到 PostgreSQL
psql -h localhost -U superinsight -d superinsight

# 查看数据库表
\dt

# 查看表结构
\d table_name

# 退出
\q
```

### 应用操作

```bash
# 查看应用日志
docker-compose logs -f superinsight-api

# 进入应用容器
docker-compose exec superinsight-api bash

# 运行数据库迁移
docker-compose exec superinsight-api python -m alembic upgrade head

# 创建初始数据
docker-compose exec superinsight-api python scripts/run_migrations.py
```

## 🔐 默认凭证

### Label Studio
- **用户名**: admin@superinsight.com
- **密码**: admin123

### PostgreSQL
- **用户名**: superinsight
- **密码**: password
- **数据库**: superinsight

### Neo4j
- **用户名**: neo4j
- **密码**: password

## 🧪 测试用户

运行 `test_roles_and_features.py` 后会自动创建以下测试用户：

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| admin_test | admin123 | 管理员 | 完全访问 |
| expert_test | expert123 | 业务专家 | 数据处理、质量评估 |
| annotator_test | annotator123 | 标注员 | 数据标注 |
| viewer_test | viewer123 | 查看者 | 只读访问 |

## 📊 主要功能测试

### 1. 系统管理员功能

```bash
# 查看系统状态
curl http://localhost:8000/system/status

# 查看所有服务
curl http://localhost:8000/system/services

# 查看系统指标
curl http://localhost:8000/system/metrics

# 创建新用户
curl -X POST http://localhost:8000/api/security/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "full_name": "New User",
    "role": "VIEWER"
  }'
```

### 2. 业务专家功能

```bash
# 登录获取 Token
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "expert_test",
    "password": "expert123"
  }' | jq -r '.access_token')

# 查看 API 信息
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/info

# 查看健康状态
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/health
```

### 3. 数据提取功能

```bash
# 提取数据
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
```

### 4. 质量评估功能

```bash
# 评估数据质量
curl -X POST http://localhost:8000/api/v1/quality/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"text": "这是一条测试数据", "label": "正常"},
      {"text": "这是另一条测试数据", "label": "正常"}
    ],
    "metrics": ["completeness", "accuracy", "consistency"]
  }'
```

## 🐛 故障排除

### 问题 1: 无法连接到 API

```bash
# 检查容器是否运行
docker-compose ps

# 查看应用日志
docker-compose logs superinsight-api

# 重启应用
docker-compose restart superinsight-api
```

### 问题 2: 数据库连接失败

```bash
# 检查 PostgreSQL 容器
docker-compose ps postgres

# 查看 PostgreSQL 日志
docker-compose logs postgres

# 测试数据库连接
psql -h localhost -U superinsight -d superinsight -c "SELECT 1"

# 重启数据库
docker-compose restart postgres
```

### 问题 3: Redis 连接失败

```bash
# 检查 Redis 容器
docker-compose ps redis

# 测试 Redis 连接
redis-cli -h localhost -p 6379 ping

# 重启 Redis
docker-compose restart redis
```

### 问题 4: 测试脚本失败

```bash
# 确保 API 正在运行
curl http://localhost:8000/health

# 检查 Python 依赖
pip3 install requests

# 运行测试脚本
python3 test_roles_and_features.py
```

## 📚 API 文档

访问 http://localhost:8000/docs 查看完整的 API 文档。

### 主要 API 端点

#### 系统管理
- `GET /health` - 健康检查
- `GET /system/status` - 系统状态
- `GET /system/services` - 所有服务状态
- `GET /system/metrics` - 系统指标

#### 安全
- `POST /api/security/login` - 用户登录
- `POST /api/security/users` - 创建用户
- `GET /api/security/permissions` - 获取权限

#### 数据提取
- `POST /api/v1/extraction/extract` - 提取数据
- `GET /api/v1/extraction/tasks/{task_id}` - 获取任务状态
- `GET /api/v1/extraction/results/{task_id}` - 获取提取结果

#### 质量管理
- `POST /api/v1/quality/evaluate` - 评估质量
- `GET /api/v1/quality/metrics` - 获取质量指标

#### AI 标注
- `POST /api/ai/preannotate` - AI 预标注
- `GET /api/ai/models` - 获取可用模型

## 🎯 下一步

1. ✅ 验证所有服务正常运行
2. ✅ 创建测试用户和项目
3. ✅ 测试各个功能模块
4. ✅ 配置监控和告警
5. ✅ 准备生产部署

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
