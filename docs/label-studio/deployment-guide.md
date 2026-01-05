# Label Studio iframe 集成部署指南

## 概述

本指南详细介绍了如何在不同环境中部署 Label Studio iframe 集成系统，包括开发环境、测试环境和生产环境的部署步骤、配置要求和最佳实践。

## 系统架构

### 部署架构图

```mermaid
graph TB
    subgraph "负载均衡层"
        LB[Nginx/HAProxy]
    end
    
    subgraph "前端服务"
        FE1[Frontend Instance 1]
        FE2[Frontend Instance 2]
    end
    
    subgraph "后端服务"
        BE1[Backend Instance 1]
        BE2[Backend Instance 2]
    end
    
    subgraph "Label Studio 服务"
        LS1[Label Studio Instance 1]
        LS2[Label Studio Instance 2]
    end
    
    subgraph "数据层"
        DB[(PostgreSQL)]
        REDIS[(Redis)]
        STORAGE[File Storage]
    end
    
    subgraph "监控层"
        MONITOR[Prometheus]
        GRAFANA[Grafana]
        ALERT[AlertManager]
    end
    
    LB --> FE1
    LB --> FE2
    FE1 --> BE1
    FE2 --> BE2
    BE1 --> LS1
    BE2 --> LS2
    
    BE1 --> DB
    BE2 --> DB
    BE1 --> REDIS
    BE2 --> REDIS
    
    LS1 --> DB
    LS2 --> DB
    LS1 --> STORAGE
    LS2 --> STORAGE
    
    MONITOR --> FE1
    MONITOR --> FE2
    MONITOR --> BE1
    MONITOR --> BE2
    MONITOR --> LS1
    MONITOR --> LS2
    
    GRAFANA --> MONITOR
    ALERT --> MONITOR
```

## 环境要求

### 硬件要求

#### 最小配置
```yaml
开发环境:
  CPU: 2 核心
  内存: 4GB
  存储: 20GB SSD
  网络: 100Mbps

测试环境:
  CPU: 4 核心
  内存: 8GB
  存储: 50GB SSD
  网络: 1Gbps

生产环境:
  CPU: 8 核心
  内存: 16GB
  存储: 100GB SSD
  网络: 10Gbps
```

#### 推荐配置
```yaml
开发环境:
  CPU: 4 核心
  内存: 8GB
  存储: 50GB SSD

测试环境:
  CPU: 8 核心
  内存: 16GB
  存储: 100GB SSD

生产环境:
  CPU: 16 核心
  内存: 32GB
  存储: 500GB SSD
  备份存储: 1TB
```

### 软件要求

#### 基础软件
```yaml
操作系统:
  - Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
  - macOS 11+ (开发环境)
  - Windows 10+ (开发环境)

容器化:
  - Docker 20.10+
  - Docker Compose 2.0+
  - Kubernetes 1.20+ (生产环境)

数据库:
  - PostgreSQL 13+
  - Redis 6+

Web 服务器:
  - Nginx 1.20+
  - Apache 2.4+ (可选)

监控:
  - Prometheus 2.30+
  - Grafana 8.0+
```

#### 开发工具
```yaml
前端:
  - Node.js 16+
  - npm 8+ / yarn 1.22+
  - TypeScript 4.9+

后端:
  - Python 3.9+
  - pip 21+
  - virtualenv / conda

版本控制:
  - Git 2.30+
```

## 开发环境部署

### 1. 环境准备

#### 安装 Docker 和 Docker Compose

**Ubuntu/Debian**:
```bash
# 更新包索引
sudo apt update

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 添加用户到 docker 组
sudo usermod -aG docker $USER
```

**macOS**:
```bash
# 使用 Homebrew
brew install docker docker-compose

# 或下载 Docker Desktop
# https://www.docker.com/products/docker-desktop
```

#### 安装 Node.js 和 Python

**Node.js**:
```bash
# 使用 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 16
nvm use 16
```

**Python**:
```bash
# Ubuntu/Debian
sudo apt install python3.9 python3.9-venv python3.9-dev

# macOS
brew install python@3.9
```

### 2. 项目设置

#### 克隆项目
```bash
git clone https://github.com/superinsight/platform.git
cd platform
```

#### 环境配置
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑环境配置
nano .env
```

**.env 配置示例**:
```bash
# 基础配置
NODE_ENV=development
PORT=3000
API_PORT=8000

# 数据库配置
DATABASE_URL=postgresql://postgres:password@localhost:5432/superinsight
REDIS_URL=redis://localhost:6379

# Label Studio 配置
LABEL_STUDIO_URL=http://localhost:8080
LABEL_STUDIO_API_KEY=your-api-key

# 安全配置
JWT_SECRET=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key

# iframe 配置
IFRAME_ALLOWED_ORIGINS=http://localhost:3000
IFRAME_REQUIRE_SIGNATURE=true
IFRAME_ENCRYPTION_ENABLED=true
```

### 3. 服务启动

#### 使用 Docker Compose
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: superinsight
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  label-studio:
    image: heartexlabs/label-studio:latest
    environment:
      DJANGO_DB: default
      POSTGRE_NAME: superinsight
      POSTGRE_USER: postgres
      POSTGRE_PASSWORD: password
      POSTGRE_HOST: postgres
      POSTGRE_PORT: 5432
    ports:
      - "8080:8080"
    depends_on:
      - postgres
    volumes:
      - label_studio_data:/label-studio/data

  backend:
    build: .
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/superinsight
      REDIS_URL: redis://redis:6379
      LABEL_STUDIO_URL: http://label-studio:8080
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - label-studio
    volumes:
      - ./src:/app/src
      - ./uploads:/app/uploads

  frontend:
    build: ./frontend
    environment:
      REACT_APP_API_URL: http://localhost:8000
      REACT_APP_LABEL_STUDIO_URL: http://localhost:8080
    ports:
      - "3000:3000"
    depends_on:
      - backend
    volumes:
      - ./frontend/src:/app/src

volumes:
  postgres_data:
  redis_data:
  label_studio_data:
```

#### 手动启动服务

**启动数据库**:
```bash
# PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Redis
sudo systemctl start redis
sudo systemctl enable redis
```

**启动后端服务**:
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
python manage.py migrate

# 启动服务
python main.py
```

**启动前端服务**:
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

**启动 Label Studio**:
```bash
# 使用 Docker
docker run -it -p 8080:8080 \
  -e DJANGO_DB=default \
  -e POSTGRE_NAME=superinsight \
  -e POSTGRE_USER=postgres \
  -e POSTGRE_PASSWORD=password \
  -e POSTGRE_HOST=localhost \
  -e POSTGRE_PORT=5432 \
  heartexlabs/label-studio:latest

# 或使用 pip 安装
pip install label-studio
label-studio start
```

### 4. 验证部署

#### 健康检查
```bash
# 检查服务状态
curl http://localhost:3000/health  # 前端
curl http://localhost:8000/health  # 后端
curl http://localhost:8080/health  # Label Studio

# 检查数据库连接
psql -h localhost -U postgres -d superinsight -c "SELECT version();"

# 检查 Redis 连接
redis-cli ping
```

#### 功能测试
```bash
# 创建测试用户
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 登录测试
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 创建测试项目
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"name":"Test Project","description":"Test project for iframe integration"}'
```

## 测试环境部署

### 1. 环境配置

#### 服务器准备
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y curl wget git nginx certbot python3-certbot-nginx

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

#### SSL 证书配置
```bash
# 获取 Let's Encrypt 证书
sudo certbot --nginx -d test.superinsight.com

# 设置自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. 配置文件

#### Nginx 配置
```nginx
# /etc/nginx/sites-available/superinsight-test
server {
    listen 80;
    server_name test.superinsight.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name test.superinsight.com;

    ssl_certificate /etc/letsencrypt/live/test.superinsight.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/test.superinsight.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Label Studio
    location /label-studio/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 环境配置
```bash
# .env.test
NODE_ENV=test
PORT=3000
API_PORT=8000

# 数据库配置
DATABASE_URL=postgresql://superinsight:secure_password@localhost:5432/superinsight_test
REDIS_URL=redis://localhost:6379/1

# Label Studio 配置
LABEL_STUDIO_URL=https://test.superinsight.com/label-studio
LABEL_STUDIO_API_KEY=test-api-key

# 安全配置
JWT_SECRET=test-jwt-secret-key
ENCRYPTION_KEY=test-encryption-key

# iframe 配置
IFRAME_ALLOWED_ORIGINS=https://test.superinsight.com
IFRAME_REQUIRE_SIGNATURE=true
IFRAME_ENCRYPTION_ENABLED=true

# 监控配置
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
```

### 3. 部署脚本

#### 自动化部署脚本
```bash
#!/bin/bash
# deploy-test.sh

set -e

echo "Starting test environment deployment..."

# 拉取最新代码
git pull origin main

# 构建 Docker 镜像
docker-compose -f docker-compose.test.yml build

# 停止旧服务
docker-compose -f docker-compose.test.yml down

# 启动新服务
docker-compose -f docker-compose.test.yml up -d

# 等待服务启动
sleep 30

# 运行健康检查
./scripts/health-check.sh

# 运行集成测试
npm run test:integration

echo "Test environment deployment completed successfully!"
```

#### 健康检查脚本
```bash
#!/bin/bash
# scripts/health-check.sh

set -e

echo "Running health checks..."

# 检查前端
if curl -f -s https://test.superinsight.com/health > /dev/null; then
    echo "✓ Frontend is healthy"
else
    echo "✗ Frontend health check failed"
    exit 1
fi

# 检查后端
if curl -f -s https://test.superinsight.com/api/health > /dev/null; then
    echo "✓ Backend is healthy"
else
    echo "✗ Backend health check failed"
    exit 1
fi

# 检查 Label Studio
if curl -f -s https://test.superinsight.com/label-studio/health > /dev/null; then
    echo "✓ Label Studio is healthy"
else
    echo "✗ Label Studio health check failed"
    exit 1
fi

# 检查数据库连接
if docker exec superinsight_postgres_1 pg_isready -U superinsight; then
    echo "✓ Database is healthy"
else
    echo "✗ Database health check failed"
    exit 1
fi

# 检查 Redis 连接
if docker exec superinsight_redis_1 redis-cli ping | grep -q PONG; then
    echo "✓ Redis is healthy"
else
    echo "✗ Redis health check failed"
    exit 1
fi

echo "All health checks passed!"
```

## 生产环境部署

### 1. 基础设施准备

#### 服务器集群配置
```yaml
# infrastructure.yml
load_balancer:
  type: nginx
  instances: 2
  config:
    ssl_termination: true
    health_check: enabled
    rate_limiting: enabled

frontend:
  instances: 3
  resources:
    cpu: 2
    memory: 4Gi
    storage: 20Gi

backend:
  instances: 3
  resources:
    cpu: 4
    memory: 8Gi
    storage: 50Gi

label_studio:
  instances: 2
  resources:
    cpu: 4
    memory: 8Gi
    storage: 100Gi

database:
  type: postgresql
  version: 13
  instances: 1
  resources:
    cpu: 8
    memory: 16Gi
    storage: 500Gi
  backup:
    enabled: true
    schedule: "0 2 * * *"
    retention: 30d

cache:
  type: redis
  instances: 1
  resources:
    cpu: 2
    memory: 4Gi
    storage: 20Gi
```

#### Kubernetes 部署配置

**Namespace**:
```yaml
# k8s/namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: superinsight-prod
```

**ConfigMap**:
```yaml
# k8s/configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: superinsight-config
  namespace: superinsight-prod
data:
  NODE_ENV: "production"
  LABEL_STUDIO_URL: "https://api.superinsight.com/label-studio"
  IFRAME_ALLOWED_ORIGINS: "https://app.superinsight.com"
  IFRAME_REQUIRE_SIGNATURE: "true"
  IFRAME_ENCRYPTION_ENABLED: "true"
```

**Secret**:
```yaml
# k8s/secret.yml
apiVersion: v1
kind: Secret
metadata:
  name: superinsight-secrets
  namespace: superinsight-prod
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  JWT_SECRET: <base64-encoded-jwt-secret>
  ENCRYPTION_KEY: <base64-encoded-encryption-key>
  LABEL_STUDIO_API_KEY: <base64-encoded-api-key>
```

**Frontend Deployment**:
```yaml
# k8s/frontend-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: superinsight-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: superinsight/frontend:latest
        ports:
        - containerPort: 3000
        envFrom:
        - configMapRef:
            name: superinsight-config
        - secretRef:
            name: superinsight-secrets
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**Backend Deployment**:
```yaml
# k8s/backend-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: superinsight-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: superinsight/backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: superinsight-config
        - secretRef:
            name: superinsight-secrets
        resources:
          requests:
            cpu: 2
            memory: 4Gi
          limits:
            cpu: 4
            memory: 8Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**Service**:
```yaml
# k8s/services.yml
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: superinsight-prod
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: superinsight-prod
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

**Ingress**:
```yaml
# k8s/ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: superinsight-ingress
  namespace: superinsight-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - app.superinsight.com
    - api.superinsight.com
    secretName: superinsight-tls
  rules:
  - host: app.superinsight.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
  - host: api.superinsight.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
```

### 2. 部署流程

#### CI/CD 流水线
```yaml
# .github/workflows/deploy-prod.yml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '16'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run tests
      run: npm run test:ci
    
    - name: Run integration tests
      run: npm run test:integration

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push images
      uses: docker/build-push-action@v3
      with:
        context: .
        push: true
        tags: |
          ghcr.io/superinsight/frontend:latest
          ghcr.io/superinsight/frontend:${{ github.sha }}
          ghcr.io/superinsight/backend:latest
          ghcr.io/superinsight/backend:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.24.0'
    
    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
    
    - name: Deploy to Kubernetes
      run: |
        kubectl apply -f k8s/
        kubectl rollout status deployment/frontend -n superinsight-prod
        kubectl rollout status deployment/backend -n superinsight-prod
    
    - name: Run smoke tests
      run: |
        ./scripts/smoke-tests.sh
```

#### 部署脚本
```bash
#!/bin/bash
# scripts/deploy-prod.sh

set -e

echo "Starting production deployment..."

# 检查环境
if [[ "$NODE_ENV" != "production" ]]; then
    echo "Error: NODE_ENV must be set to 'production'"
    exit 1
fi

# 备份数据库
echo "Creating database backup..."
kubectl exec -n superinsight-prod deployment/postgres -- \
    pg_dump -U superinsight superinsight > backup_$(date +%Y%m%d_%H%M%S).sql

# 更新镜像
echo "Updating container images..."
kubectl set image deployment/frontend frontend=superinsight/frontend:$IMAGE_TAG -n superinsight-prod
kubectl set image deployment/backend backend=superinsight/backend:$IMAGE_TAG -n superinsight-prod

# 等待部署完成
echo "Waiting for deployment to complete..."
kubectl rollout status deployment/frontend -n superinsight-prod --timeout=600s
kubectl rollout status deployment/backend -n superinsight-prod --timeout=600s

# 运行健康检查
echo "Running health checks..."
./scripts/health-check-prod.sh

# 运行烟雾测试
echo "Running smoke tests..."
./scripts/smoke-tests.sh

echo "Production deployment completed successfully!"
```

### 3. 监控和告警

#### Prometheus 配置
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'superinsight-frontend'
    static_configs:
      - targets: ['frontend-service:80']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'superinsight-backend'
    static_configs:
      - targets: ['backend-service:80']
    metrics_path: '/api/metrics'
    scrape_interval: 30s

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### 告警规则
```yaml
# monitoring/alert_rules.yml
groups:
- name: superinsight
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }} seconds"

  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pod is crash looping"
      description: "Pod {{ $labels.pod }} is crash looping"

  - alert: DatabaseConnectionFailure
    expr: up{job="postgres"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database connection failure"
      description: "Cannot connect to PostgreSQL database"
```

#### Grafana 仪表板
```json
{
  "dashboard": {
    "title": "SuperInsight Production Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, http_request_duration_seconds)",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      },
      {
        "title": "Active Users",
        "type": "singlestat",
        "targets": [
          {
            "expr": "active_users_total",
            "legendFormat": "Active Users"
          }
        ]
      }
    ]
  }
}
```

## 验证和测试

### 1. 自动化测试

#### 集成测试
```typescript
// tests/integration/iframe-integration.test.ts
import { test, expect } from '@playwright/test';

test.describe('Label Studio iframe Integration', () => {
  test('should load iframe and establish communication', async ({ page }) => {
    await page.goto('/projects/1/tasks/1/annotate');
    
    // 等待 iframe 加载
    const iframe = page.frameLocator('iframe[data-testid="label-studio-iframe"]');
    await iframe.locator('[data-testid="annotation-canvas"]').waitFor();
    
    // 验证通信
    const messagePromise = page.waitForEvent('console', msg => 
      msg.text().includes('PostMessage bridge connected')
    );
    
    await iframe.locator('[data-testid="annotation-tool"]').click();
    await messagePromise;
    
    expect(await iframe.locator('[data-testid="annotation-canvas"]').isVisible()).toBe(true);
  });

  test('should sync annotation data', async ({ page }) => {
    await page.goto('/projects/1/tasks/1/annotate');
    
    const iframe = page.frameLocator('iframe[data-testid="label-studio-iframe"]');
    
    // 创建标注
    await iframe.locator('[data-testid="rectangle-tool"]').click();
    await iframe.locator('[data-testid="annotation-canvas"]').click({ position: { x: 100, y: 100 } });
    await iframe.locator('[data-testid="annotation-canvas"]').click({ position: { x: 200, y: 200 } });
    
    // 保存标注
    await iframe.locator('[data-testid="save-button"]').click();
    
    // 验证同步
    await page.waitForResponse(response => 
      response.url().includes('/api/annotations') && response.status() === 200
    );
    
    // 刷新页面验证数据持久化
    await page.reload();
    await iframe.locator('[data-testid="annotation-canvas"]').waitFor();
    
    const annotations = await iframe.locator('[data-testid="annotation-item"]').count();
    expect(annotations).toBeGreaterThan(0);
  });
});
```

#### 性能测试
```typescript
// tests/performance/load-test.ts
import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test('iframe load time should be under 3 seconds', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/projects/1/tasks/1/annotate');
    
    const iframe = page.frameLocator('iframe[data-testid="label-studio-iframe"]');
    await iframe.locator('[data-testid="annotation-canvas"]').waitFor();
    
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(3000);
  });

  test('annotation operations should be responsive', async ({ page }) => {
    await page.goto('/projects/1/tasks/1/annotate');
    
    const iframe = page.frameLocator('iframe[data-testid="label-studio-iframe"]');
    await iframe.locator('[data-testid="annotation-canvas"]').waitFor();
    
    // 测试标注工具响应时间
    const startTime = Date.now();
    await iframe.locator('[data-testid="rectangle-tool"]').click();
    const responseTime = Date.now() - startTime;
    
    expect(responseTime).toBeLessThan(100);
  });
});
```

### 2. 用户验收测试

#### 测试用例清单
```markdown
## 基础功能测试
- [ ] 用户登录和权限验证
- [ ] 项目创建和配置
- [ ] 数据上传和管理
- [ ] iframe 加载和初始化
- [ ] 标注工具使用
- [ ] 数据保存和同步
- [ ] 标注审核流程
- [ ] 数据导出功能

## 性能测试
- [ ] 页面加载时间 < 3秒
- [ ] iframe 初始化时间 < 2秒
- [ ] 标注操作响应时间 < 100ms
- [ ] 数据同步延迟 < 500ms
- [ ] 大文件处理能力
- [ ] 并发用户支持

## 兼容性测试
- [ ] Chrome 90+ 支持
- [ ] Firefox 88+ 支持
- [ ] Safari 14+ 支持
- [ ] Edge 90+ 支持
- [ ] 移动端响应式设计
- [ ] 不同屏幕分辨率适配

## 安全测试
- [ ] HTTPS 强制重定向
- [ ] CSP 策略生效
- [ ] XSS 防护
- [ ] CSRF 防护
- [ ] 权限控制有效性
- [ ] 数据加密传输

## 错误处理测试
- [ ] 网络中断恢复
- [ ] 服务器错误处理
- [ ] 权限不足提示
- [ ] 数据验证错误
- [ ] iframe 加载失败处理
```

#### 测试报告模板
```markdown
# Label Studio iframe 集成验收测试报告

## 测试概述
- 测试环境: [生产环境/测试环境]
- 测试时间: [开始时间] - [结束时间]
- 测试人员: [测试人员列表]
- 测试版本: [版本号]

## 测试结果汇总
- 总测试用例数: [数量]
- 通过用例数: [数量]
- 失败用例数: [数量]
- 通过率: [百分比]

## 功能测试结果
### 基础功能
- [✓] 用户登录和权限验证
- [✓] 项目创建和配置
- [✗] 数据上传和管理 (发现问题: 大文件上传超时)
- [✓] iframe 加载和初始化
- [✓] 标注工具使用
- [✓] 数据保存和同步
- [✓] 标注审核流程
- [✓] 数据导出功能

### 性能测试结果
- 页面加载时间: 2.1秒 (✓ < 3秒)
- iframe 初始化时间: 1.8秒 (✓ < 2秒)
- 标注操作响应时间: 85ms (✓ < 100ms)
- 数据同步延迟: 320ms (✓ < 500ms)

## 发现的问题
1. **大文件上传超时**
   - 严重程度: 中等
   - 描述: 超过100MB的文件上传会超时
   - 影响: 影响大数据集的使用
   - 建议: 增加上传超时时间或实现分片上传

2. **Safari 兼容性问题**
   - 严重程度: 低
   - 描述: Safari 14.0 版本下部分CSS样式异常
   - 影响: 影响Safari用户体验
   - 建议: 更新CSS兼容性代码

## 测试结论
系统整体功能正常，性能指标达标，建议修复发现的问题后可以上线。

## 签字确认
- 测试负责人: [姓名] [日期]
- 项目经理: [姓名] [日期]
- 技术负责人: [姓名] [日期]
```

## 维护和监控

### 1. 日常维护

#### 监控检查清单
```markdown
## 每日检查
- [ ] 系统运行状态
- [ ] 错误日志审查
- [ ] 性能指标监控
- [ ] 用户反馈处理
- [ ] 数据备份验证

## 每周检查
- [ ] 安全补丁更新
- [ ] 存储空间检查
- [ ] 数据库性能优化
- [ ] 用户活跃度分析
- [ ] 系统资源使用情况

## 每月检查
- [ ] 系统版本更新
- [ ] 安全审计
- [ ] 容量规划评估
- [ ] 灾难恢复测试
- [ ] 用户满意度调查
```

### 2. 故障响应

#### 故障等级定义
```yaml
P0 - 紧急:
  定义: 系统完全不可用
  响应时间: 15分钟
  解决时间: 2小时
  通知: 立即通知所有相关人员

P1 - 高:
  定义: 核心功能不可用
  响应时间: 1小时
  解决时间: 4小时
  通知: 通知技术团队和管理层

P2 - 中:
  定义: 部分功能异常
  响应时间: 4小时
  解决时间: 24小时
  通知: 通知技术团队

P3 - 低:
  定义: 轻微问题或改进建议
  响应时间: 24小时
  解决时间: 1周
  通知: 记录到问题跟踪系统
```

#### 故障处理流程
```mermaid
graph TD
    A[故障发现] --> B[故障分类]
    B --> C{严重程度}
    C -->|P0| D[立即响应]
    C -->|P1| E[1小时内响应]
    C -->|P2| F[4小时内响应]
    C -->|P3| G[24小时内响应]
    
    D --> H[组建应急团队]
    E --> H
    F --> I[分配处理人员]
    G --> I
    
    H --> J[问题诊断]
    I --> J
    J --> K[制定解决方案]
    K --> L[实施修复]
    L --> M[验证修复]
    M --> N{修复成功?}
    N -->|否| K
    N -->|是| O[更新文档]
    O --> P[总结报告]
```

---

**版本**: v1.0  
**更新日期**: 2026年1月5日  
**维护团队**: SuperInsight DevOps 团队