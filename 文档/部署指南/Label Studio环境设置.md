# Label Studio iframe 集成环境配置指南

## 概述

本指南详细说明了 Label Studio iframe 集成系统的环境配置要求、安装步骤和配置选项，帮助开发者和运维人员快速搭建和配置系统环境。

## 系统要求

### 操作系统支持

#### 服务器环境
```yaml
推荐操作系统:
  - Ubuntu 20.04 LTS / 22.04 LTS
  - CentOS 8 / RHEL 8
  - Debian 11
  - Amazon Linux 2

开发环境:
  - macOS 11+ (Big Sur)
  - Windows 10+ (WSL2)
  - Ubuntu Desktop 20.04+
```

#### 容器化环境
```yaml
容器运行时:
  - Docker 20.10+
  - containerd 1.5+
  - Podman 3.0+ (可选)

编排平台:
  - Kubernetes 1.20+
  - Docker Compose 2.0+
  - Docker Swarm (可选)
```

### 硬件要求

#### 最小配置
```yaml
开发环境:
  CPU: 2 核心 (x86_64)
  内存: 4GB RAM
  存储: 20GB 可用空间
  网络: 宽带连接

测试环境:
  CPU: 4 核心 (x86_64)
  内存: 8GB RAM
  存储: 50GB SSD
  网络: 100Mbps

生产环境:
  CPU: 8 核心 (x86_64)
  内存: 16GB RAM
  存储: 100GB SSD
  网络: 1Gbps
```

#### 推荐配置
```yaml
开发环境:
  CPU: 4 核心 (x86_64)
  内存: 8GB RAM
  存储: 50GB SSD

测试环境:
  CPU: 8 核心 (x86_64)
  内存: 16GB RAM
  存储: 100GB SSD

生产环境:
  CPU: 16+ 核心 (x86_64)
  内存: 32GB+ RAM
  存储: 500GB+ NVMe SSD
  备份存储: 1TB+
```

## 软件依赖

### 核心依赖

#### Node.js 环境
```bash
# 推荐版本
Node.js: 16.x LTS / 18.x LTS
npm: 8.x+
yarn: 1.22.x (可选)

# 安装 Node.js (使用 nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 16
nvm use 16
nvm alias default 16

# 验证安装
node --version
npm --version
```

#### Python 环境
```bash
# 推荐版本
Python: 3.9+ / 3.10+ / 3.11
pip: 21.x+
virtualenv: 20.x+

# Ubuntu/Debian 安装
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev python3-pip

# CentOS/RHEL 安装
sudo dnf install python39 python39-devel python39-pip

# macOS 安装
brew install python@3.9

# 验证安装
python3 --version
pip3 --version
```

#### 数据库系统
```bash
# PostgreSQL 13+
# Ubuntu/Debian
sudo apt install postgresql-13 postgresql-client-13 postgresql-contrib-13

# CentOS/RHEL
sudo dnf install postgresql13-server postgresql13-contrib

# macOS
brew install postgresql@13

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE superinsight;
CREATE USER superinsight WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE superinsight TO superinsight;
\q
```

```bash
# Redis 6+
# Ubuntu/Debian
sudo apt install redis-server

# CentOS/RHEL
sudo dnf install redis

# macOS
brew install redis

# 启动服务
sudo systemctl start redis
sudo systemctl enable redis

# 验证安装
redis-cli ping
```

### 容器化环境

#### Docker 安装
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# CentOS/RHEL
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker

# macOS
brew install --cask docker

# 验证安装
docker --version
docker run hello-world
```

#### Docker Compose 安装
```bash
# Linux
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# macOS (已包含在 Docker Desktop 中)
# 或使用 Homebrew
brew install docker-compose

# 验证安装
docker-compose --version
```

### Web 服务器

#### Nginx 安装和配置
```bash
# Ubuntu/Debian
sudo apt install nginx

# CentOS/RHEL
sudo dnf install nginx

# macOS
brew install nginx

# 启动服务
sudo systemctl start nginx
sudo systemctl enable nginx

# 验证安装
nginx -v
curl http://localhost
```

**基础配置**:
```nginx
# /etc/nginx/sites-available/superinsight
server {
    listen 80;
    server_name localhost;
    
    # 前端静态文件
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

# 启用配置
sudo ln -s /etc/nginx/sites-available/superinsight /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 环境配置

### 开发环境配置

#### 项目初始化
```bash
# 克隆项目
git clone https://github.com/superinsight/platform.git
cd platform

# 创建环境配置文件
cp .env.example .env.development
```

#### 环境变量配置
```bash
# .env.development
# 基础配置
NODE_ENV=development
PORT=3000
API_PORT=8000

# 数据库配置
DATABASE_URL=postgresql://superinsight:password@localhost:5432/superinsight_dev
REDIS_URL=redis://localhost:6379/0

# Label Studio 配置
LABEL_STUDIO_URL=http://localhost:8080
LABEL_STUDIO_API_KEY=dev-api-key
LABEL_STUDIO_USERNAME=admin@example.com
LABEL_STUDIO_PASSWORD=password

# 安全配置
JWT_SECRET=dev-jwt-secret-key-change-in-production
JWT_EXPIRES_IN=24h
ENCRYPTION_KEY=dev-encryption-key-32-chars-long
BCRYPT_ROUNDS=10

# iframe 集成配置
IFRAME_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
IFRAME_REQUIRE_SIGNATURE=false
IFRAME_ENCRYPTION_ENABLED=false
IFRAME_TIMEOUT=30000
IFRAME_RETRY_ATTEMPTS=3

# 文件上传配置
UPLOAD_MAX_SIZE=100MB
UPLOAD_ALLOWED_TYPES=jpg,jpeg,png,gif,pdf,txt,json,csv
UPLOAD_STORAGE_PATH=./uploads

# 日志配置
LOG_LEVEL=debug
LOG_FORMAT=dev
LOG_FILE=./logs/app.log

# 开发工具配置
ENABLE_CORS=true
ENABLE_SWAGGER=true
ENABLE_GRAPHQL_PLAYGROUND=true
ENABLE_HOT_RELOAD=true
```

#### 依赖安装
```bash
# 后端依赖
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
# 或使用 yarn
yarn install
```

#### 数据库初始化
```bash
# 创建开发数据库
createdb -U postgres superinsight_dev

# 运行数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 加载测试数据 (可选)
python manage.py loaddata fixtures/test_data.json
```

#### 服务启动
```bash
# 启动后端服务
source venv/bin/activate
python main.py

# 启动前端服务 (新终端)
cd frontend
npm start

# 启动 Label Studio (新终端)
label-studio start --port 8080
```

### 测试环境配置

#### 环境变量配置
```bash
# .env.test
NODE_ENV=test
PORT=3000
API_PORT=8000

# 数据库配置
DATABASE_URL=postgresql://superinsight:secure_password@localhost:5432/superinsight_test
REDIS_URL=redis://localhost:6379/1

# Label Studio 配置
LABEL_STUDIO_URL=https://test-label-studio.example.com
LABEL_STUDIO_API_KEY=test-api-key
LABEL_STUDIO_USERNAME=admin@test.example.com
LABEL_STUDIO_PASSWORD=secure_test_password

# 安全配置
JWT_SECRET=test-jwt-secret-key-64-chars-long-change-in-production
JWT_EXPIRES_IN=8h
ENCRYPTION_KEY=test-encryption-key-32-chars-long
BCRYPT_ROUNDS=12

# iframe 集成配置
IFRAME_ALLOWED_ORIGINS=https://test.example.com
IFRAME_REQUIRE_SIGNATURE=true
IFRAME_ENCRYPTION_ENABLED=true
IFRAME_TIMEOUT=30000
IFRAME_RETRY_ATTEMPTS=3

# SSL 配置
SSL_CERT_PATH=/etc/ssl/certs/test.example.com.crt
SSL_KEY_PATH=/etc/ssl/private/test.example.com.key
FORCE_HTTPS=true

# 监控配置
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
ALERT_WEBHOOK_URL=https://hooks.slack.com/test-webhook

# 备份配置
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=7
BACKUP_S3_BUCKET=superinsight-test-backups
```

#### Docker Compose 配置
```yaml
# docker-compose.test.yml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: superinsight_test
      POSTGRES_USER: superinsight
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_test_data:/var/lib/postgresql/data
      - ./scripts/init-test-db.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_test_data:/data
    command: redis-server --appendonly yes

  label-studio:
    image: heartexlabs/label-studio:latest
    environment:
      DJANGO_DB: default
      POSTGRE_NAME: superinsight_test
      POSTGRE_USER: superinsight
      POSTGRE_PASSWORD: secure_password
      POSTGRE_HOST: postgres
      POSTGRE_PORT: 5432
      LABEL_STUDIO_USERNAME: admin@test.example.com
      LABEL_STUDIO_PASSWORD: secure_test_password
    ports:
      - "8080:8080"
    depends_on:
      - postgres
    volumes:
      - label_studio_test_data:/label-studio/data

  backend:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    environment:
      NODE_ENV: test
      DATABASE_URL: postgresql://superinsight:secure_password@postgres:5432/superinsight_test
      REDIS_URL: redis://redis:6379/1
      LABEL_STUDIO_URL: http://label-studio:8080
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - label-studio
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    environment:
      NODE_ENV: test
      REACT_APP_API_URL: http://backend:8000
      REACT_APP_LABEL_STUDIO_URL: http://label-studio:8080
    ports:
      - "3000:3000"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/test.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - frontend
      - backend

volumes:
  postgres_test_data:
  redis_test_data:
  label_studio_test_data:
```

### 生产环境配置

#### 环境变量配置
```bash
# .env.production
NODE_ENV=production
PORT=3000
API_PORT=8000

# 数据库配置 (使用环境变量或密钥管理)
DATABASE_URL=${DATABASE_URL}
REDIS_URL=${REDIS_URL}

# Label Studio 配置
LABEL_STUDIO_URL=https://label-studio.example.com
LABEL_STUDIO_API_KEY=${LABEL_STUDIO_API_KEY}
LABEL_STUDIO_USERNAME=${LABEL_STUDIO_USERNAME}
LABEL_STUDIO_PASSWORD=${LABEL_STUDIO_PASSWORD}

# 安全配置
JWT_SECRET=${JWT_SECRET}
JWT_EXPIRES_IN=1h
ENCRYPTION_KEY=${ENCRYPTION_KEY}
BCRYPT_ROUNDS=14

# iframe 集成配置
IFRAME_ALLOWED_ORIGINS=https://app.example.com
IFRAME_REQUIRE_SIGNATURE=true
IFRAME_ENCRYPTION_ENABLED=true
IFRAME_TIMEOUT=30000
IFRAME_RETRY_ATTEMPTS=3

# SSL 配置
SSL_CERT_PATH=/etc/ssl/certs/example.com.crt
SSL_KEY_PATH=/etc/ssl/private/example.com.key
FORCE_HTTPS=true
HSTS_MAX_AGE=31536000

# 性能配置
ENABLE_GZIP=true
ENABLE_CACHING=true
CACHE_TTL=3600
MAX_REQUEST_SIZE=10MB
REQUEST_TIMEOUT=30000

# 监控和日志
LOG_LEVEL=info
LOG_FORMAT=json
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
SENTRY_DSN=${SENTRY_DSN}

# 备份和存储
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
S3_BUCKET=${S3_BUCKET}
S3_ACCESS_KEY=${S3_ACCESS_KEY}
S3_SECRET_KEY=${S3_SECRET_KEY}

# 邮件配置
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=587
SMTP_USER=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASSWORD}
SMTP_FROM=noreply@example.com
```

#### Kubernetes 配置

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
  PORT: "3000"
  API_PORT: "8000"
  LABEL_STUDIO_URL: "https://label-studio.example.com"
  IFRAME_ALLOWED_ORIGINS: "https://app.example.com"
  IFRAME_REQUIRE_SIGNATURE: "true"
  IFRAME_ENCRYPTION_ENABLED: "true"
  IFRAME_TIMEOUT: "30000"
  IFRAME_RETRY_ATTEMPTS: "3"
  SSL_CERT_PATH: "/etc/ssl/certs/tls.crt"
  SSL_KEY_PATH: "/etc/ssl/private/tls.key"
  FORCE_HTTPS: "true"
  HSTS_MAX_AGE: "31536000"
  ENABLE_GZIP: "true"
  ENABLE_CACHING: "true"
  CACHE_TTL: "3600"
  MAX_REQUEST_SIZE: "10MB"
  REQUEST_TIMEOUT: "30000"
  LOG_LEVEL: "info"
  LOG_FORMAT: "json"
  ENABLE_MONITORING: "true"
  PROMETHEUS_PORT: "9090"
  BACKUP_ENABLED: "true"
  BACKUP_SCHEDULE: "0 2 * * *"
  BACKUP_RETENTION_DAYS: "30"
  SMTP_PORT: "587"
  SMTP_FROM: "noreply@example.com"
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
  REDIS_URL: <base64-encoded-redis-url>
  LABEL_STUDIO_API_KEY: <base64-encoded-api-key>
  LABEL_STUDIO_USERNAME: <base64-encoded-username>
  LABEL_STUDIO_PASSWORD: <base64-encoded-password>
  JWT_SECRET: <base64-encoded-jwt-secret>
  ENCRYPTION_KEY: <base64-encoded-encryption-key>
  SENTRY_DSN: <base64-encoded-sentry-dsn>
  S3_BUCKET: <base64-encoded-s3-bucket>
  S3_ACCESS_KEY: <base64-encoded-s3-access-key>
  S3_SECRET_KEY: <base64-encoded-s3-secret-key>
  SMTP_HOST: <base64-encoded-smtp-host>
  SMTP_USER: <base64-encoded-smtp-user>
  SMTP_PASSWORD: <base64-encoded-smtp-password>
```

## 安全配置

### SSL/TLS 配置

#### 证书获取和配置
```bash
# 使用 Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d example.com -d www.example.com

# 自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

#### Nginx SSL 配置
```nginx
# /etc/nginx/sites-available/superinsight-ssl
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # CSP
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-src 'self' https://label-studio.example.com;";

    # 其他配置...
}
```

### 防火墙配置

#### UFW 配置 (Ubuntu)
```bash
# 启用 UFW
sudo ufw enable

# 允许 SSH
sudo ufw allow ssh

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允许数据库访问 (仅限本地)
sudo ufw allow from 127.0.0.1 to any port 5432
sudo ufw allow from 127.0.0.1 to any port 6379

# 允许监控端口 (仅限内网)
sudo ufw allow from 10.0.0.0/8 to any port 9090

# 查看状态
sudo ufw status verbose
```

#### iptables 配置 (CentOS/RHEL)
```bash
# 保存当前规则
sudo iptables-save > /etc/iptables/rules.v4

# 允许已建立的连接
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 允许本地回环
sudo iptables -A INPUT -i lo -j ACCEPT

# 允许 SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 拒绝其他连接
sudo iptables -A INPUT -j DROP

# 保存规则
sudo service iptables save
```

## 监控配置

### Prometheus 配置
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
      - targets: ['localhost:3000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'superinsight-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 30s

  - job_name: 'label-studio'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana 配置
```yaml
# monitoring/grafana.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true

dashboards:
  - name: 'SuperInsight Dashboard'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
```

## 备份配置

### 数据库备份
```bash
#!/bin/bash
# scripts/backup-database.sh

set -e

# 配置
DB_NAME="superinsight"
DB_USER="superinsight"
BACKUP_DIR="/backup/database"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump -h localhost -U $DB_USER -d $DB_NAME > $BACKUP_FILE

# 压缩备份文件
gzip $BACKUP_FILE

# 上传到 S3 (可选)
if [ ! -z "$S3_BUCKET" ]; then
    aws s3 cp "${BACKUP_FILE}.gz" "s3://$S3_BUCKET/database/"
fi

# 清理旧备份 (保留30天)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Database backup completed: ${BACKUP_FILE}.gz"
```

### 文件备份
```bash
#!/bin/bash
# scripts/backup-files.sh

set -e

# 配置
SOURCE_DIR="/app/uploads"
BACKUP_DIR="/backup/files"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/files_${DATE}.tar.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
tar -czf $BACKUP_FILE -C $(dirname $SOURCE_DIR) $(basename $SOURCE_DIR)

# 上传到 S3 (可选)
if [ ! -z "$S3_BUCKET" ]; then
    aws s3 cp $BACKUP_FILE "s3://$S3_BUCKET/files/"
fi

# 清理旧备份 (保留30天)
find $BACKUP_DIR -name "files_*.tar.gz" -mtime +30 -delete

echo "Files backup completed: $BACKUP_FILE"
```

### 自动备份配置
```bash
# 添加到 crontab
sudo crontab -e

# 每天凌晨2点备份数据库
0 2 * * * /path/to/scripts/backup-database.sh

# 每天凌晨3点备份文件
0 3 * * * /path/to/scripts/backup-files.sh

# 每周日凌晨4点完整备份
0 4 * * 0 /path/to/scripts/full-backup.sh
```

## 故障排除

### 常见问题

#### 端口冲突
```bash
# 检查端口占用
sudo netstat -tlnp | grep :3000
sudo lsof -i :3000

# 杀死占用进程
sudo kill -9 <PID>

# 更改端口配置
export PORT=3001
```

#### 权限问题
```bash
# 检查文件权限
ls -la /path/to/file

# 修改权限
sudo chmod 755 /path/to/directory
sudo chmod 644 /path/to/file

# 修改所有者
sudo chown user:group /path/to/file
```

#### 内存不足
```bash
# 检查内存使用
free -h
top
htop

# 增加交换空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 磁盘空间不足
```bash
# 检查磁盘使用
df -h
du -sh /*

# 清理日志文件
sudo journalctl --vacuum-time=7d
sudo find /var/log -name "*.log" -mtime +7 -delete

# 清理 Docker
docker system prune -a
```

### 日志分析

#### 应用日志
```bash
# 查看应用日志
tail -f /app/logs/app.log

# 搜索错误
grep -i error /app/logs/app.log

# 按时间过滤
grep "2024-01-05" /app/logs/app.log
```

#### 系统日志
```bash
# 查看系统日志
sudo journalctl -f

# 查看特定服务日志
sudo journalctl -u nginx -f
sudo journalctl -u postgresql -f

# 查看内核日志
dmesg | tail
```

#### Docker 日志
```bash
# 查看容器日志
docker logs -f container_name

# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
```

---

**版本**: v1.0  
**更新日期**: 2026年1月5日  
**维护团队**: SuperInsight DevOps 团队