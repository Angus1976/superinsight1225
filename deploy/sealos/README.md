# SuperInsight Sealos 部署指南

## 架构概览（演示瘦身版）

```
┌─────────────────────────────────────────────────┐
│                  Sealos 平台                      │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Frontend │→│ Backend  │→│ Celery Worker │   │
│  │ (Nginx)  │  │ (FastAPI)│  │  (后台任务)    │   │
│  └──────────┘  └────┬─────┘  └──────┬────────┘   │
│                     │               │             │
│  ┌──────────────────┴───────────────┘             │
│  │                                                │
│  ▼                                                │
│  ┌────────────┐  ┌───────┐   ← Sealos 托管数据库  │
│  │ PostgreSQL │  │ Redis │                        │
│  └────────────┘  └───────┘                        │
│                                                   │
│  ┌──────────────┐  ┌─────────┐  ┌──────────────┐ │
│  │ Label Studio │  │ Argilla │  │Elasticsearch │ │
│  └──────────────┘  └─────────┘  └──────────────┘ │
│                                                   │
│  LLM → 外部 API（DeepSeek / 通义千问）             │
└─────────────────────────────────────────────────┘
```

去掉了：Ollama（改外部API）、Prometheus、Grafana

## 预估费用（偶尔演示场景）

- 演示运行时：~¥0.20/小时
- 闲置（仅存储）：~¥8/月
- 每月演示 4 次 × 2 小时 ≈ ¥10/月

## 部署步骤

### 第 1 步：构建并推送 Docker 镜像

```bash
# 在项目根目录执行

# 后端
docker build -f deploy/sealos/Dockerfile.backend -t angus888/superinsight-backend:sealos .
docker push angus888/superinsight-backend:sealos

# 前端
docker build -f deploy/sealos/Dockerfile.frontend -t angus888/superinsight-frontend:sealos .
docker push angus888/superinsight-frontend:sealos
```

### 第 2 步：在 Sealos 创建托管数据库

1. 登录 https://gzg.sealos.run
2. 进入「数据库」→ 创建 PostgreSQL（0.5核/512MB 够用）
3. 创建 Redis（0.25核/256MB）
4. 记录连接地址和密码

### 第 3 步：在 Sealos 部署应用

按以下顺序在「应用管理」中逐个部署：

#### 3.1 Elasticsearch
- 镜像：`docker.elastic.co/elasticsearch/elasticsearch:8.5.0`
- CPU：1核，内存：1GB
- 环境变量：
  - `discovery.type` = `single-node`
  - `xpack.security.enabled` = `false`
  - `ES_JAVA_OPTS` = `-Xms256m -Xmx512m`
- 存储：挂载 `/usr/share/elasticsearch/data`，5GB

#### 3.2 Argilla
- 镜像：`argilla/argilla-server:latest`
- CPU：0.5核，内存：512MB
- 环境变量：
  - `ARGILLA_ELASTICSEARCH` = `http://<es内网地址>:9200`
  - `ARGILLA_DATABASE_URL` = `postgresql://<pg连接串>/argilla`
  - `ARGILLA_REDIS_URL` = `redis://:<密码>@<redis地址>:6379/0`

#### 3.3 Label Studio
- 镜像：`heartexlabs/label-studio:latest`
- CPU：0.5核，内存：512MB
- 环境变量：
  - `LABEL_STUDIO_HOST` = `http://0.0.0.0:8080`
  - `LABEL_STUDIO_USERNAME` = `admin@superinsight.local`
  - `LABEL_STUDIO_PASSWORD` = `<你的密码>`
  - `LANGUAGE_CODE` = `zh-hans`
- 存储：挂载 `/label-studio/data`，2GB

#### 3.4 Backend (FastAPI)
- 镜像：`angus888/superinsight-backend:sealos`
- CPU：1核，内存：1GB
- 环境变量：参考 `.env.sealos` 文件，填入实际地址
- 开启外网访问（端口 8000）

#### 3.5 Celery Worker
- 镜像：`angus888/superinsight-backend:sealos`
- CPU：0.5核，内存：512MB
- 启动命令覆盖：
  ```
  celery -A src.services.structuring_pipeline worker --loglevel=info
  ```
- 环境变量：与 Backend 相同

#### 3.6 Frontend (Nginx)
- 镜像：`angus888/superinsight-frontend:sealos`
- CPU：0.25核，内存：256MB
- 开启外网访问（端口 80）

### 第 4 步：初始化数据库

进入 Backend 容器终端执行：
```bash
python -c "from main import *; print('DB initialized')"
```

### 第 5 步：验证

1. 访问前端外网地址
2. 用 admin@superinsight.local 登录
3. 检查 Label Studio / Argilla 连通性

## 暂停/恢复（省钱）

演示结束后，在 Sealos 应用管理中暂停所有应用容器。
只有存储持续计费（~¥8/月），CPU/内存不收费。

需要演示时一键恢复所有应用即可。
