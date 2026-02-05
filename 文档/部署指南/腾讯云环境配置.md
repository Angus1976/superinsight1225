# TCB 部署环境变量配置指南

## 概述

在 TCB 云托管部署 SuperInsight 时，需要配置以下环境变量。根据您的需求，分为**必需**和**可选**两类。

---

## 🔴 必需环境变量（REQUIRED）

这些变量必须配置，否则应用无法正常运行。

### 1. 数据库配置

```env
# PostgreSQL 数据库
DATABASE_URL=postgresql://superinsight:your_strong_password@your_postgres_host:5432/superinsight
POSTGRES_DB=superinsight
POSTGRES_USER=superinsight
POSTGRES_PASSWORD=your_strong_password
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432

# Redis 缓存
REDIS_URL=redis://your_redis_host:6379/0
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password (如果有)

# Neo4j 图数据库
NEO4J_URI=bolt://your_neo4j_host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

**说明**:
- 如果使用 TCB 云数据库，替换为 TCB 提供的连接字符串
- 如果使用本地/自建数据库，填入对应的主机地址和凭证

### 2. API 服务配置

```env
# API 服务
API_PORT=8000
API_HOST=0.0.0.0
DEBUG=false
LOG_LEVEL=INFO
```

### 3. 安全配置

```env
# JWT 密钥（用于用户认证）
JWT_SECRET_KEY=your_random_secret_key_at_least_32_characters_long
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 加密密钥（用于数据加密）
ENCRYPTION_KEY=your_random_32_byte_key_base64_encoded
```

**生成方法**:
```bash
# 生成 JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成 ENCRYPTION_KEY
python -c "import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

### 4. Label Studio 配置

```env
# Label Studio 标注平台
LABEL_STUDIO_URL=http://your_label_studio_host:8080
LABEL_STUDIO_USERNAME=admin@superinsight.com
LABEL_STUDIO_PASSWORD=your_label_studio_password
LABEL_STUDIO_API_TOKEN=your_label_studio_api_token
```

**说明**:
- 如果 Label Studio 在 TCB 同一环境，使用内部地址
- 如果在外部，使用公网地址

---

## 🟡 可选环境变量（OPTIONAL）

根据您的功能需求选择配置。

### 1. LLM 配置（AI 标注功能）

选择至少一个 LLM 提供商：

#### OpenAI（推荐）
```env
OPENAI_API_KEY=sk-your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
```

#### Azure OpenAI
```env
AZURE_OPENAI_ENABLED=true
AZURE_API_KEY=your_azure_api_key
AZURE_API_BASE=https://your-resource.openai.azure.com
AZURE_API_VERSION=2023-05-15
AZURE_DEPLOYMENT_NAME=your_deployment_name
```

#### 本地 Ollama
```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://your_ollama_host:11434
```

#### 国内 LLM

**阿里云通义千问**:
```env
ALIBABA_API_KEY=your_alibaba_api_key
ALIBABA_MODEL=qwen-turbo
```

**百度文心一言**:
```env
BAIDU_API_KEY=your_baidu_api_key
BAIDU_SECRET_KEY=your_baidu_secret_key
```

**腾讯混元**:
```env
HUNYUAN_API_KEY=your_hunyuan_api_key
HUNYUAN_SECRET_KEY=your_hunyuan_secret_key
```

**智谱 ChatGLM**:
```env
ZHIPU_API_KEY=your_zhipu_api_key
```

### 2. 文件存储配置

#### 本地存储（默认）
```env
UPLOAD_DIR=/app/uploads
EXPORT_DIR=/app/exports
```

#### S3 存储（可选）
```env
S3_ENABLED=true
S3_BUCKET=your_bucket_name
S3_REGION=us-east-1
S3_ACCESS_KEY=your_s3_access_key
S3_SECRET_KEY=your_s3_secret_key
```

### 3. 监控配置

```env
# Prometheus 监控
PROMETHEUS_ENABLED=false
PROMETHEUS_PORT=9090

# Grafana 可视化
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

### 4. 通知配置

#### 钉钉通知
```env
DINGTALK_ENABLED=true
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=your_dingtalk_secret
```

#### 企业微信通知
```env
WECHAT_WORK_ENABLED=true
WECHAT_WORK_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

#### Slack 通知
```env
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
```

### 5. 邮件配置

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_email_password
SMTP_FROM_EMAIL=noreply@superinsight.com
SMTP_USE_TLS=true
```

### 6. 性能配置

```env
# Worker 并发数
WORKER_CONCURRENCY=4

# 数据库连接池
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis 连接池
REDIS_POOL_SIZE=10
```

### 7. 合规配置

```env
# 数据脱敏
DESENSITIZATION_ENABLED=true
DESENSITIZATION_LEVEL=medium

# 审计日志
AUDIT_LOG_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=90

# 数据加密
DATA_ENCRYPTION_ENABLED=true
ENCRYPTION_ALGORITHM=AES-256-GCM
```

---

## 📋 TCB 环境变量配置步骤

### 方法 1: 通过 TCB 控制台配置

1. 登录 [TCB 控制台](https://console.cloud.tencent.com/tcb)
2. 选择您的环境（cloud2）
3. 进入 **云托管** → **服务** → **您的服务**
4. 点击 **编辑** → **环境变量**
5. 添加上述环境变量
6. 保存并重新部署

### 方法 2: 通过 cloudbaserc.json 配置

编辑 `cloudbaserc.json`，在 `envVariables` 中添加：

```json
{
  "envId": "cloud2-3gegxdemf86cb89a",
  "functionRoot": "./",
  "cloudHostingConfig": {
    "envVariables": {
      "DATABASE_URL": "postgresql://...",
      "REDIS_URL": "redis://...",
      "JWT_SECRET_KEY": "your_secret_key",
      "ENCRYPTION_KEY": "your_encryption_key",
      "OPENAI_API_KEY": "sk-...",
      "LABEL_STUDIO_URL": "http://..."
    }
  }
}
```

然后运行：
```bash
tcb framework:deploy --verbose
```

---

## 🚀 快速开始配置

### 最小化配置（仅基础功能）

```env
# 数据库
DATABASE_URL=postgresql://superinsight:password@db_host:5432/superinsight
REDIS_URL=redis://redis_host:6379/0
NEO4J_URI=bolt://neo4j_host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# API
API_PORT=8000
API_HOST=0.0.0.0
DEBUG=false

# 安全
JWT_SECRET_KEY=your_random_secret_key_32_chars_minimum
ENCRYPTION_KEY=your_base64_encoded_32_byte_key

# Label Studio
LABEL_STUDIO_URL=http://label_studio_host:8080
LABEL_STUDIO_API_TOKEN=your_token
```

### 完整配置（包含 AI 功能）

在最小化配置基础上，添加：

```env
# OpenAI LLM
OPENAI_API_KEY=sk-your_key
OPENAI_MODEL=gpt-3.5-turbo

# 或国内 LLM
ALIBABA_API_KEY=your_key
ALIBABA_MODEL=qwen-turbo

# 监控
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=your_password

# 通知
DINGTALK_ENABLED=true
DINGTALK_WEBHOOK_URL=your_webhook_url
```

---

## ⚠️ 安全建议

1. **不要在代码中硬编码密钥** - 使用环境变量
2. **使用强密码** - 至少 16 个字符，包含大小写字母、数字、特殊符号
3. **定期轮换密钥** - 特别是 JWT_SECRET_KEY 和 ENCRYPTION_KEY
4. **使用 TCB 密钥管理** - 不要在 cloudbaserc.json 中存储敏感信息
5. **限制数据库访问** - 只允许 TCB 服务访问数据库
6. **启用审计日志** - 设置 `AUDIT_LOG_ENABLED=true`

---

## 🔍 验证配置

部署后，检查应用是否正常运行：

```bash
# 检查健康状态
curl https://your_tcb_domain/health

# 查看日志
tcb logs --service superinsight

# 检查环境变量是否正确加载
curl https://your_tcb_domain/api/v1/system/status
```

---

## 📞 常见问题

### Q: 数据库连接失败怎么办？
**A**: 检查：
- 数据库主机地址和端口是否正确
- 用户名和密码是否正确
- TCB 服务是否有权限访问数据库（检查防火墙/安全组）

### Q: LLM 调用失败怎么办？
**A**: 检查：
- API Key 是否正确
- API 端点是否可访问
- 是否超过 API 配额

### Q: 如何更新环境变量？
**A**: 
1. 在 TCB 控制台更新环境变量
2. 重新部署服务：`tcb framework:deploy --verbose`
3. 或直接编辑 cloudbaserc.json 后部署

---

## 📚 相关文档

- [TCB 云托管文档](https://cloud.tencent.com/document/product/1243)
- [TCB 环境变量配置](https://cloud.tencent.com/document/product/1243/49619)
- [SuperInsight 部署指南](./TCB_DEPLOY_README.md)
- [完整环境变量示例](./.env.example)

