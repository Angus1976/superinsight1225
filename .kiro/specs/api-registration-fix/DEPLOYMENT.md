# API 注册修复 - 部署指南

## 概述

本文档提供 API 注册修复功能的部署步骤、验证方法和回滚策略。

## 部署前检查清单

### 1. 代码审查
- [ ] 所有代码变更已通过 PR 审查
- [ ] TypeScript 类型检查通过 (`npx tsc --noEmit`)
- [ ] Python 类型检查通过 (`mypy src/`)
- [ ] 单元测试通过 (`pytest tests/test_api_registration.py tests/test_api_endpoints.py -v`)

### 2. 环境准备
- [ ] 数据库迁移已执行 (`alembic upgrade head`)
- [ ] Redis 服务运行正常
- [ ] PostgreSQL 服务运行正常
- [ ] 环境变量配置正确

### 3. 备份
- [ ] 数据库备份完成
- [ ] 配置文件备份完成
- [ ] 当前 Docker 镜像标记为回滚版本

## 部署步骤

### 方式一：Docker Compose 部署

```bash
# 1. 停止当前服务
docker-compose down

# 2. 拉取最新代码
git pull origin main

# 3. 重新构建镜像
docker-compose build --no-cache superinsight-api

# 4. 启动服务
docker-compose up -d

# 5. 查看启动日志
docker-compose logs -f superinsight-api
```

### 方式二：本地开发部署

```bash
# 1. 停止当前服务
pkill -f "uvicorn src.app:app"

# 2. 拉取最新代码
git pull origin main

# 3. 安装依赖（如有更新）
pip install -r requirements.txt

# 4. 启动服务
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

# 5. 查看日志
tail -f backend.log
```

### 方式三：生产环境部署

```bash
# 1. 创建新版本标签
git tag -a v2.3.1 -m "API Registration Fix"
git push origin v2.3.1

# 2. 构建生产镜像
docker build -t superinsight-api:v2.3.1 -f Dockerfile.backend .

# 3. 推送到镜像仓库
docker push your-registry/superinsight-api:v2.3.1

# 4. 更新 Kubernetes 部署（如适用）
kubectl set image deployment/superinsight-api \
  superinsight-api=your-registry/superinsight-api:v2.3.1

# 5. 监控滚动更新
kubectl rollout status deployment/superinsight-api
```

## 部署验证

### 1. 健康检查

```bash
# 检查服务健康状态
curl http://localhost:8000/health | jq

# 预期响应包含：
# - "status": "healthy"
# - "api_registration_status": "healthy"
# - "registered_apis_count": >= 35
# - "failed_apis_count": 0
```

### 2. API 注册状态检查

```bash
# 检查 API 注册信息
curl http://localhost:8000/api/info | jq

# 预期响应：
# - 所有 12 个高优先级 API 在 registered_apis 列表中
# - failed_apis 列表为空
```

### 3. 各模块 API 验证

```bash
# License 模块
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/license
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/license/usage
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/license/activation

# Quality 模块
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/quality/rules
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/quality/reports
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/quality/workflow

# Augmentation 模块
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/augmentation

# Security 模块
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/security/sessions
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/security/sso
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/security/rbac
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/security/data-permissions

# Versioning 模块
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/versioning

# 预期：所有返回 200 或 401（需要认证）
```

### 4. 前端页面验证

访问以下页面，确认无 404 错误：

| 模块 | URL | 预期状态 |
|------|-----|---------|
| License | http://localhost:5173/license | 正常加载 |
| License 激活 | http://localhost:5173/license/activate | 正常加载 |
| License 使用 | http://localhost:5173/license/usage | 正常加载 |
| Quality 规则 | http://localhost:5173/quality/rules | 正常加载 |
| Quality 报告 | http://localhost:5173/quality/reports | 正常加载 |
| Quality 工作流 | http://localhost:5173/quality/workflow/tasks | 正常加载 |
| Augmentation | http://localhost:5173/augmentation | 正常加载 |
| Security 会话 | http://localhost:5173/security/sessions | 正常加载 |
| Security SSO | http://localhost:5173/security/sso | 正常加载 |
| Security RBAC | http://localhost:5173/security/rbac | 正常加载 |
| Security 数据权限 | http://localhost:5173/security/data-permissions | 正常加载 |

### 5. 日志验证

```bash
# 检查启动日志中的 API 注册摘要
docker logs superinsight-api 2>&1 | grep -A 20 "API Registration Summary"

# 预期输出：
# ✅ API Registration Summary
# ├── Total Registered: 35+
# ├── Failed: 0
# └── High Priority APIs: 12/12 registered
```

### 6. 性能验证

```bash
# 检查启动时间
time docker-compose up -d superinsight-api

# 预期：启动时间增加 < 2秒

# 检查 API 响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# 预期：响应时间 < 100ms
```

## 回滚策略

### 快速回滚（Docker）

```bash
# 1. 停止当前服务
docker-compose down

# 2. 切换到上一个版本
git checkout v2.3.0

# 3. 重新构建并启动
docker-compose build superinsight-api
docker-compose up -d

# 4. 验证回滚成功
curl http://localhost:8000/health
```

### 快速回滚（Kubernetes）

```bash
# 回滚到上一个版本
kubectl rollout undo deployment/superinsight-api

# 或回滚到指定版本
kubectl rollout undo deployment/superinsight-api --to-revision=2

# 监控回滚状态
kubectl rollout status deployment/superinsight-api
```

### 数据库回滚（如需要）

```bash
# 回滚数据库迁移
alembic downgrade -1

# 或回滚到指定版本
alembic downgrade <revision_id>
```

## 监控和告警

### 关键指标

| 指标 | 阈值 | 告警级别 |
|------|------|---------|
| API 注册失败数 | > 0 | Critical |
| 健康检查失败 | 连续 3 次 | Critical |
| API 响应时间 | > 500ms | Warning |
| 错误率 | > 1% | Warning |

### Prometheus 查询

```promql
# API 注册状态
superinsight_api_registered_count

# API 注册失败数
superinsight_api_failed_count

# API 响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Grafana 仪表盘

导入 `deploy/monitoring/grafana/dashboards/api-registration.json` 仪表盘。

## 故障排除

### 问题 1：API 注册失败

**症状**：`/api/info` 显示 failed_apis 不为空

**排查步骤**：
1. 检查日志中的错误信息
2. 验证相关模块文件是否存在
3. 检查依赖是否正确安装

```bash
# 查看详细错误日志
docker logs superinsight-api 2>&1 | grep -i "error\|failed"
```

### 问题 2：前端页面 404

**症状**：前端页面显示 404 错误

**排查步骤**：
1. 检查 `frontend/src/router/routes.tsx` 路由配置
2. 验证后端 API 是否正常响应
3. 检查浏览器控制台错误

### 问题 3：启动超时

**症状**：服务启动时间过长或超时

**排查步骤**：
1. 检查数据库连接
2. 检查 Redis 连接
3. 检查外部服务依赖

```bash
# 检查数据库连接
docker exec superinsight-api python -c "from src.database import get_db; print('DB OK')"

# 检查 Redis 连接
docker exec superinsight-api python -c "import redis; r = redis.Redis(); r.ping(); print('Redis OK')"
```

## 联系方式

- **技术支持**：api-support@superinsight.ai
- **紧急联系**：+86-xxx-xxxx-xxxx
- **Slack 频道**：#superinsight-api-support

---

**文档版本**：1.0  
**创建日期**：2026-01-19  
**最后更新**：2026-01-19
