# 质量计费闭环系统 - 部署和运维手册

## 1. 环境要求

### 1.1 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4 核 | 8 核或更多 |
| 内存 | 8 GB | 16 GB 或更多 |
| 存储 | 100 GB SSD | 500 GB SSD |
| 网络 | 100 Mbps | 1 Gbps |

### 1.2 软件要求

| 软件 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 应用运行时 |
| PostgreSQL | 14+ | 主数据库 |
| Redis | 7+ | 缓存和消息队列 |
| Celery | 5+ | 异步任务处理 |
| Nginx | 1.24+ | 反向代理 |
| Docker | 24+ | 容器化部署 |

## 2. 快速开始

### 2.1 克隆代码

```bash
git clone https://github.com/superinsight/quality-billing-loop.git
cd quality-billing-loop
```

### 2.2 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑配置：

```env
# 应用配置
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=your-secret-key-here

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/quality_billing
DATABASE_POOL_SIZE=20

# Redis 配置
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your-redis-password

# Celery 配置
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 监控配置
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 2.3 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2.4 初始化数据库

```bash
# 运行数据库迁移
python manage.py migrate

# 创建初始数据
python manage.py init_data
```

### 2.5 启动服务

```bash
# 启动 Redis
redis-server

# 启动 Celery Worker
celery -A quality_billing worker -l info -Q default,high_priority,low_priority

# 启动 Celery Beat (定时任务)
celery -A quality_billing beat -l info

# 启动应用
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 3. Docker 部署

### 3.1 使用 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/quality_billing
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery:
    build: .
    command: celery -A quality_billing worker -l info
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/quality_billing
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery-beat:
    build: .
    command: celery -A quality_billing beat -l info
    depends_on:
      - redis
    restart: unless-stopped

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=quality_billing
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:1.24
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 3.2 启动容器

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 4. Kubernetes 部署

### 4.1 创建命名空间

```bash
kubectl create namespace quality-billing
```

### 4.2 应用配置

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quality-billing-api
  namespace: quality-billing
spec:
  replicas: 3
  selector:
    matchLabels:
      app: quality-billing-api
  template:
    metadata:
      labels:
        app: quality-billing-api
    spec:
      containers:
      - name: api
        image: quality-billing:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
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

### 4.3 部署

```bash
kubectl apply -f k8s/
```

## 5. 数据库管理

### 5.1 备份策略

```bash
# 每日全量备份
pg_dump -h localhost -U postgres quality_billing > backup_$(date +%Y%m%d).sql

# WAL 归档 (增量备份)
archive_command = 'cp %p /backup/wal/%f'
```

### 5.2 恢复流程

```bash
# 停止应用
systemctl stop quality-billing

# 恢复数据库
psql -h localhost -U postgres -d quality_billing < backup_20250101.sql

# 启动应用
systemctl start quality-billing
```

### 5.3 数据库优化

```sql
-- 添加关键索引
CREATE INDEX CONCURRENTLY idx_tickets_status ON tickets(status);
CREATE INDEX CONCURRENTLY idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX CONCURRENTLY idx_evaluations_ticket_id ON evaluations(ticket_id);
CREATE INDEX CONCURRENTLY idx_billing_period ON billing_records(billing_period);

-- 定期维护
VACUUM ANALYZE tickets;
REINDEX TABLE tickets;
```

## 6. 监控配置

### 6.1 Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'quality-billing'
    static_configs:
      - targets: ['app:9090']
    metrics_path: /metrics
```

### 6.2 关键指标

| 指标 | 描述 | 告警阈值 |
|------|------|----------|
| http_request_duration_seconds | API 响应时间 | > 1s |
| http_requests_total{status="5xx"} | 5xx 错误数 | > 10/分钟 |
| celery_task_failed_total | 失败任务数 | > 5/分钟 |
| db_connection_pool_size | 连接池使用 | > 80% |

### 6.3 Grafana 仪表盘

导入预配置仪表盘：

```bash
# 导入仪表盘
curl -X POST http://admin:admin@localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @grafana-dashboard.json
```

## 7. 日志管理

### 7.1 日志格式

```json
{
  "timestamp": "2025-01-01T10:00:00.000Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "req-123",
  "method": "POST",
  "path": "/api/tickets",
  "status": 200,
  "duration_ms": 50
}
```

### 7.2 日志收集

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/quality-billing/*.log
    json.keys_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "quality-billing-%{+yyyy.MM.dd}"
```

## 8. 安全配置

### 8.1 TLS 配置

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.superinsight.com;

    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 8.2 防火墙规则

```bash
# 只允许必要端口
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

## 9. 故障排除

### 9.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 连接数据库失败 | 配置错误或服务未启动 | 检查 DATABASE_URL 和 PostgreSQL 状态 |
| Celery 任务堆积 | Worker 不足或任务执行慢 | 增加 Worker 数量或优化任务 |
| API 响应慢 | 数据库查询慢或缓存失效 | 检查慢查询日志，重建缓存 |
| 内存使用高 | 内存泄漏或缓存过大 | 重启服务，调整缓存配置 |

### 9.2 日志分析

```bash
# 查看错误日志
grep -i error /var/log/quality-billing/app.log | tail -100

# 查看慢请求
cat /var/log/quality-billing/app.log | jq 'select(.duration_ms > 1000)'

# 统计错误类型
cat /var/log/quality-billing/app.log | jq -r '.error_code' | sort | uniq -c | sort -rn
```

### 9.3 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# 数据库连接检查
curl http://localhost:8000/health/db

# Redis 连接检查
curl http://localhost:8000/health/redis
```

## 10. 升级流程

### 10.1 准备工作

```bash
# 备份数据库
pg_dump quality_billing > pre_upgrade_backup.sql

# 备份配置
cp .env .env.backup
```

### 10.2 执行升级

```bash
# 拉取新版本
git fetch origin
git checkout v1.2.0

# 安装新依赖
pip install -r requirements.txt

# 运行迁移
python manage.py migrate

# 重启服务
systemctl restart quality-billing
```

### 10.3 回滚方案

```bash
# 切换回旧版本
git checkout v1.1.0

# 恢复数据库（如需要）
psql quality_billing < pre_upgrade_backup.sql

# 重启服务
systemctl restart quality-billing
```

---

*本文档最后更新: 2025-01-01*
