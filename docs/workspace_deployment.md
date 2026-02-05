# Label Studio Enterprise Workspace 运维手册

**版本**: 1.0
**最后更新**: 2026-01-30
**适用环境**: 生产环境、测试环境

---

## 目录

1. [系统要求](#系统要求)
2. [部署配置](#部署配置)
3. [数据库迁移](#数据库迁移)
4. [服务部署](#服务部署)
5. [监控配置](#监控配置)
6. [故障排查](#故障排查)
7. [备份恢复](#备份恢复)
8. [性能优化](#性能优化)

---

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 20 GB SSD | 100 GB SSD |
| 网络 | 100 Mbps | 1 Gbps |

### 软件要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.10+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |
| Redis | 6+ (可选，用于缓存) |
| Label Studio | 1.8+ |

### 依赖服务

- **PostgreSQL**: 主数据库存储
- **Label Studio**: 标注服务 (需要独立部署或使用 SaaS)
- **Redis**: 缓存层 (可选)

---

## 部署配置

### 环境变量

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/superinsight
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Label Studio 配置
LABEL_STUDIO_URL=http://localhost:8080
LABEL_STUDIO_API_TOKEN=your-api-token

# JWT 配置
JWT_SECRET_KEY=your-secure-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Redis 配置 (可选)
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# 性能配置
PROXY_TIMEOUT=60
MAX_CONCURRENT_REQUESTS=100
```

### 配置文件示例

**config/production.yaml**

```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

database:
  url: ${DATABASE_URL}
  pool_size: 10
  max_overflow: 20
  echo: false

label_studio:
  url: ${LABEL_STUDIO_URL}
  token: ${LABEL_STUDIO_API_TOKEN}
  timeout: 60
  max_retries: 3

workspace:
  max_members_per_workspace: 1000
  max_projects_per_workspace: 100
  soft_delete_retention_days: 30

cache:
  enabled: true
  backend: redis
  url: ${REDIS_URL}
  default_ttl: 300

logging:
  level: INFO
  format: json
  handlers:
    - console
    - file
  file_path: /var/log/superinsight/workspace.log
```

---

## 数据库迁移

### 迁移步骤

1. **备份现有数据库**

```bash
pg_dump -h localhost -U postgres -d superinsight > backup_$(date +%Y%m%d).sql
```

2. **检查迁移状态**

```bash
alembic current
```

3. **执行迁移**

```bash
# 升级到最新版本
alembic upgrade head

# 或升级到特定版本
alembic upgrade 019_add_ls_workspace_tables
```

4. **验证迁移**

```bash
# 检查表是否创建
psql -d superinsight -c "\dt *workspace*"

# 预期输出：
#  Schema |            Name             | Type  | Owner
# --------+-----------------------------+-------+-------
#  public | label_studio_workspaces     | table | postgres
#  public | label_studio_workspace_members | table | postgres
#  public | workspace_projects          | table | postgres
#  public | project_members             | table | postgres
```

### 回滚迁移

```bash
# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade 018_add_label_studio_sync_fields
```

### 新创建的表结构

**label_studio_workspaces**

| 列名 | 类型 | 描述 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(255) | 工作空间名称 (唯一) |
| description | TEXT | 描述 |
| owner_id | UUID | 所有者用户 ID |
| settings | JSONB | 设置 |
| is_active | BOOLEAN | 是否启用 |
| is_deleted | BOOLEAN | 是否已删除 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| deleted_at | TIMESTAMP | 删除时间 |

**label_studio_workspace_members**

| 列名 | 类型 | 描述 |
|------|------|------|
| id | UUID | 主键 |
| workspace_id | UUID | 工作空间 ID |
| user_id | UUID | 用户 ID |
| role | ENUM | 角色 |
| is_active | BOOLEAN | 是否活跃 |
| joined_at | TIMESTAMP | 加入时间 |
| updated_at | TIMESTAMP | 更新时间 |

**workspace_projects**

| 列名 | 类型 | 描述 |
|------|------|------|
| id | UUID | 主键 |
| workspace_id | UUID | 工作空间 ID |
| label_studio_project_id | VARCHAR(100) | Label Studio 项目 ID |
| superinsight_project_id | UUID | SuperInsight 项目 ID |
| project_metadata | JSONB | 元数据 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

---

## 服务部署

### Docker 部署

**Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 运行
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**docker-compose.yml**

```yaml
version: '3.8'

services:
  superinsight:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/superinsight
      - LABEL_STUDIO_URL=http://label-studio:8080
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: superinsight
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

### Kubernetes 部署

**deployment.yaml**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: superinsight-workspace
  labels:
    app: superinsight
    component: workspace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: superinsight
      component: workspace
  template:
    metadata:
      labels:
        app: superinsight
        component: workspace
    spec:
      containers:
      - name: workspace
        image: superinsight/workspace:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: superinsight-secrets
              key: database-url
        - name: LABEL_STUDIO_URL
          value: "http://label-studio:8080"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 部署检查清单

- [ ] 数据库迁移已执行
- [ ] 环境变量已配置
- [ ] Label Studio 连接已验证
- [ ] 健康检查端点正常
- [ ] 日志收集已配置
- [ ] 监控告警已设置

---

## 监控配置

### 关键指标

| 指标 | 描述 | 告警阈值 |
|------|------|----------|
| `workspace_api_latency_p95` | API 95分位延迟 | > 500ms |
| `workspace_api_error_rate` | API 错误率 | > 1% |
| `workspace_member_count` | 成员总数 | 无 (监控) |
| `workspace_project_count` | 项目总数 | 无 (监控) |
| `db_connection_pool_used` | 数据库连接池使用率 | > 80% |
| `proxy_request_duration` | 代理请求时长 | > 200ms |
| `permission_check_duration` | 权限检查时长 | > 10ms |

### Prometheus 指标

```python
# 在代码中暴露的指标
workspace_operations_total = Counter(
    'workspace_operations_total',
    'Total workspace operations',
    ['operation', 'status']
)

workspace_api_latency = Histogram(
    'workspace_api_latency_seconds',
    'API latency in seconds',
    ['endpoint', 'method'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

workspace_member_gauge = Gauge(
    'workspace_member_total',
    'Total members across all workspaces'
)
```

### Grafana 仪表板

推荐创建以下面板：

1. **API 性能概览**
   - 请求速率 (QPS)
   - 延迟分布 (P50, P95, P99)
   - 错误率

2. **工作空间统计**
   - 活跃工作空间数
   - 成员分布
   - 项目关联数

3. **系统资源**
   - CPU 使用率
   - 内存使用率
   - 数据库连接数

### 告警配置示例

**Alertmanager 规则**

```yaml
groups:
- name: workspace-alerts
  rules:
  - alert: WorkspaceAPIHighLatency
    expr: histogram_quantile(0.95, workspace_api_latency_seconds) > 0.5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Workspace API 延迟过高"
      description: "P95 延迟超过 500ms，当前值: {{ $value }}"

  - alert: WorkspaceAPIHighErrorRate
    expr: rate(workspace_operations_total{status="error"}[5m]) / rate(workspace_operations_total[5m]) > 0.01
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Workspace API 错误率过高"
      description: "错误率超过 1%，当前值: {{ $value | humanizePercentage }}"
```

---

## 故障排查

### 常见问题诊断

#### 1. API 响应慢

**症状**: API 响应时间超过 500ms

**排查步骤**:

```bash
# 1. 检查数据库连接池状态
psql -d superinsight -c "SELECT count(*) FROM pg_stat_activity WHERE datname='superinsight';"

# 2. 检查慢查询
psql -d superinsight -c "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# 3. 检查 Label Studio 连接
curl -w "@curl-format.txt" -o /dev/null -s "http://label-studio:8080/api/health"
```

**解决方案**:
- 增加数据库连接池大小
- 添加必要的索引
- 检查 Label Studio 服务状态

#### 2. 权限验证失败

**症状**: 用户报告 403 错误

**排查步骤**:

```bash
# 检查用户成员记录
psql -d superinsight -c "
SELECT w.name, m.role, m.is_active
FROM label_studio_workspace_members m
JOIN label_studio_workspaces w ON w.id = m.workspace_id
WHERE m.user_id = 'user-uuid-here';
"
```

**常见原因**:
- 用户不是工作空间成员
- 用户角色权限不足
- 成员记录被设为 inactive

#### 3. 数据库连接错误

**症状**: 日志显示 "Connection refused" 或 "Too many connections"

**排查步骤**:

```bash
# 检查数据库状态
pg_isready -h localhost -p 5432

# 检查连接数
psql -d superinsight -c "SELECT count(*) FROM pg_stat_activity;"

# 检查最大连接数
psql -d superinsight -c "SHOW max_connections;"
```

**解决方案**:
- 重启数据库服务
- 增加 max_connections 配置
- 优化连接池配置

### 日志分析

**日志位置**:
- 应用日志: `/var/log/superinsight/workspace.log`
- 数据库日志: `/var/log/postgresql/postgresql-14-main.log`

**常用日志查询**:

```bash
# 查找错误日志
grep -i "error" /var/log/superinsight/workspace.log | tail -100

# 查找特定用户的操作
grep "user_id=xxx" /var/log/superinsight/workspace.log

# 统计错误类型
grep "ERROR" /var/log/superinsight/workspace.log | awk '{print $5}' | sort | uniq -c | sort -rn
```

---

## 备份恢复

### 备份策略

| 类型 | 频率 | 保留期 |
|------|------|--------|
| 全量备份 | 每日 | 30 天 |
| 增量备份 | 每小时 | 7 天 |
| 事务日志 | 实时 | 7 天 |

### 备份脚本

```bash
#!/bin/bash
# backup_workspace.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/superinsight"
DB_NAME="superinsight"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump -h localhost -U postgres -d $DB_NAME \
    -t label_studio_workspaces \
    -t label_studio_workspace_members \
    -t workspace_projects \
    -t project_members \
    -F c -f "$BACKUP_DIR/workspace_$DATE.dump"

# 清理旧备份 (保留 30 天)
find $BACKUP_DIR -name "workspace_*.dump" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/workspace_$DATE.dump"
```

### 恢复步骤

```bash
# 1. 停止服务
systemctl stop superinsight

# 2. 恢复数据
pg_restore -h localhost -U postgres -d superinsight \
    --clean --if-exists \
    /backup/superinsight/workspace_20260130_120000.dump

# 3. 验证数据
psql -d superinsight -c "SELECT count(*) FROM label_studio_workspaces;"

# 4. 重启服务
systemctl start superinsight
```

---

## 性能优化

### 数据库优化

**推荐索引**:

```sql
-- 已在迁移中创建的索引
CREATE INDEX ix_ls_workspace_name ON label_studio_workspaces(name);
CREATE INDEX ix_ls_workspace_owner ON label_studio_workspaces(owner_id);
CREATE INDEX ix_ls_wm_workspace ON label_studio_workspace_members(workspace_id);
CREATE INDEX ix_ls_wm_user ON label_studio_workspace_members(user_id);
CREATE INDEX ix_wp_workspace ON workspace_projects(workspace_id);

-- 可选的复合索引 (根据查询模式添加)
CREATE INDEX ix_ls_wm_composite ON label_studio_workspace_members(workspace_id, user_id, is_active);
```

**查询优化建议**:

```sql
-- 定期分析表
ANALYZE label_studio_workspaces;
ANALYZE label_studio_workspace_members;
ANALYZE workspace_projects;

-- 检查索引使用情况
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;
```

### 缓存配置

**Redis 缓存键设计**:

| 键模式 | 用途 | TTL |
|--------|------|-----|
| `ws:{id}` | 工作空间详情 | 5 分钟 |
| `ws:{id}:members` | 成员列表 | 2 分钟 |
| `ws:{id}:projects` | 项目列表 | 2 分钟 |
| `user:{id}:workspaces` | 用户工作空间列表 | 2 分钟 |
| `perm:{ws_id}:{user_id}` | 用户权限 | 1 分钟 |

### 连接池优化

```python
# SQLAlchemy 连接池配置
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # 基础连接数
    max_overflow=20,        # 最大溢出连接
    pool_timeout=30,        # 获取连接超时
    pool_recycle=1800,      # 连接回收时间
    pool_pre_ping=True,     # 连接健康检查
)
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-01-30 | 初始版本 |

---

## 相关文档

- [API 文档](./workspace_api.md)
- [用户手册](./workspace_user_guide.md)
