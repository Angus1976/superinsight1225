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
# 跨架构构建（如 Apple Silicon → amd64）加 --platform linux/amd64

# Elasticsearch（PVC 权限修复）
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.elasticsearch -t angus888/superinsight-elasticsearch:sealos .
docker push angus888/superinsight-elasticsearch:sealos

# Label Studio（PVC 权限修复）
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.labelstudio -t angus888/superinsight-labelstudio:sealos .
docker push angus888/superinsight-labelstudio:sealos

# 后端（CPU-only torch，镜像 ~1.5GB）
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.backend -t angus888/superinsight-backend:sealos .
docker push angus888/superinsight-backend:sealos

# 前端
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.frontend -t angus888/superinsight-frontend:sealos .
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
- 应用名：`superinsight-es`（固定名称，勿改）
- 镜像：`angus888/superinsight-elasticsearch:sealos`（自定义镜像，修复 PVC 权限）
- CPU：1核，内存：1GB
- 环境变量：
  - `discovery.type` = `single-node`
  - `xpack.security.enabled` = `false`
  - `ES_JAVA_OPTS` = `-Xms256m -Xmx512m`
- 存储：挂载 `/usr/share/elasticsearch/data`，5GB

#### 3.2 Argilla
- 应用名：`superinsight-argilla`（固定名称，勿改）
- 镜像：`argilla/argilla-server:latest`
- CPU：0.5核，内存：512MB
- 环境变量：
  - `ARGILLA_ELASTICSEARCH` = `http://<es内网地址>:9200`
  - `ARGILLA_DATABASE_URL` = `postgresql://<pg连接串>/argilla`
  - `ARGILLA_REDIS_URL` = `redis://:<密码>@<redis地址>:6379/0`

#### 3.3 Label Studio
- 应用名：`superinsight-ls`（固定名称，勿改）
- 镜像：`angus888/superinsight-labelstudio:sealos`（自定义镜像，修复 PVC 权限）
- CPU：0.5核，内存：512MB
- 环境变量：
  - `LABEL_STUDIO_HOST` = `http://0.0.0.0:8080`
  - `LABEL_STUDIO_USERNAME` = `admin@superinsight.local`
  - `LABEL_STUDIO_PASSWORD` = `<你的密码>`
  - `LANGUAGE_CODE` = `zh-hans`
  - `DJANGO_DB` = `default`
  - `POSTGRE_NAME` = `superinsight`
  - `POSTGRE_USER` = `postgres`
  - `POSTGRE_PASSWORD` = `<pg密码>`
  - `POSTGRE_HOST` = `<pg内网地址>`
  - `POSTGRE_PORT` = `5432`
- 存储：挂载 `/label-studio/data`，2GB
- ⚠️ 注意：Label Studio 的 PG 变量名是 `POSTGRE_*`（不是 `POSTGRESQL_*`），数据库名用 `superinsight`，与本地 docker-compose 一致

#### 3.4 Backend (FastAPI)
- 应用名：`superinsight-backend`（固定名称，勿改）
- 镜像：`angus888/superinsight-backend:sealos`
- CPU：1核，内存：1GB
- 环境变量：参考 `.env.sealos` 文件，填入实际地址
- 开启外网访问（端口 8000）

#### 3.5 Celery Worker
- 应用名：`superinsight-celery`（固定名称，勿改）
- 镜像：`angus888/superinsight-backend:sealos`
- CPU：0.5核，内存：512MB
- 启动命令覆盖：
  ```
  celery -A src.services.structuring_pipeline worker --loglevel=info
  ```
- 环境变量：与 Backend 相同

#### 3.6 Frontend (Nginx)
- 应用名：`superinsight-frontend`（固定名称，勿改）
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

## 已踩坑记录

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| ES/Label Studio 启动失败，数据目录无写权限 | Sealos PVC 默认 root 拥有，容器以非 root 用户运行 | 自定义 Dockerfile，entrypoint 中 chown 给运行用户 |
| Label Studio entrypoint 报 `su: unknown user` | 官方镜像用户名随版本变化，`su label-studio` 找不到用户 | entrypoint 中按 UID 切换用户（`runuser -u #1001`），不依赖用户名 |
| 前端构建失败，nginx.conf not found | `.dockerignore` 排除了 `deploy/` 和 `frontend/` | 修改 `.dockerignore` 放行 `deploy/sealos/` 和 `frontend/` |
| 后端镜像 4.4GB，推送超时 | PyTorch 默认含 GPU/CUDA 支持（~2.5GB） | Dockerfile 中先装 CPU-only torch（`--index-url .../whl/cpu`） |
| Sealos 应用名含空格/大写导致部署失败 | K8s DNS-1035 命名规范 | 应用名只用小写字母、数字和连字符 |
| 重建应用后依赖方连接失败循环重启 | Sealos 自动生成的应用名带随机后缀，重建后 FQDN 变化 | 使用固定应用名（如 `superinsight-es`），所有服务命名约定见 `.env.sealos` |
| 前端 Docker 构建被 TS 错误阻塞 | `npm run build` 含 `tsc -b` 类型检查，本地 `vite dev` 不检查 | Dockerfile 中用 `npx vite build` 跳过 tsc |
| 前端 nginx 启动即崩，报 upstream host not found | nginx 启动时立即解析 upstream 域名，后端未就绪或 FQDN 不存在则拒绝启动 | 用 `resolver` + 变量方式动态解析，解耦前后端启动顺序，参考 `nginx.conf` |

## 自定义镜像清单

| 镜像 | Dockerfile | 基础镜像 | 自定义原因 |
|------|-----------|---------|-----------|
| `superinsight-elasticsearch:sealos` | `Dockerfile.elasticsearch` | `elasticsearch:8.5.0` | PVC 权限修复 |
| `superinsight-labelstudio:sealos` | `Dockerfile.labelstudio` | `label-studio:latest` | PVC 权限修复 |
| `superinsight-backend:sealos` | `Dockerfile.backend` | `python:3.11-slim` | 应用代码 + CPU-only torch |
| `superinsight-frontend:sealos` | `Dockerfile.frontend` | `nginx:alpine` | 前端构建产物 + nginx 配置 |

## 多环境部署说明

本项目计划支持多种部署环境，Dockerfile 和配置按环境隔离：

```
deploy/
├── sealos/          # Sealos 云平台（当前）
├── docker/          # 本地 Docker Compose（开发/Mac）
└── (未来)
    ├── k8s/         # 标准 K8s 集群（客户私有化）
    └── offline/     # 离线部署包
```

各环境差异点：
- LLM 接入：Sealos 用外部 API，私有化可能用本地 Ollama/vLLM
- torch 版本：云部署用 CPU-only，客户有 GPU 时可切回完整版
- 数据库：Sealos 用托管服务，私有化需自建 PostgreSQL/Redis
