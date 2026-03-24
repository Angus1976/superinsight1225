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
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.elasticsearch -t angus888/superinsight-elasticsearch:sealos-v4 .
docker push angus888/superinsight-elasticsearch:sealos-v4

# Label Studio（PVC 权限修复 + SSO + 品牌化）
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.labelstudio -t angus888/superinsight-labelstudio:sealos-v4 .
docker push angus888/superinsight-labelstudio:sealos-v4

# 后端（CPU-only torch，镜像 ~1.5GB）
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.backend -t angus888/superinsight-backend:sealos-v4 .
docker push angus888/superinsight-backend:sealos-v4

# Celery Worker（基于后端镜像）
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.celery -t angus888/superinsight-celery:sealos-v4 .
docker push angus888/superinsight-celery:sealos-v4

# 前端（构建时传入 LS 外网地址）
docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.frontend \
  --build-arg VITE_LABEL_STUDIO_URL=https://<LS外网域名> \
  -t angus888/superinsight-frontend:sealos-v4 .
docker push angus888/superinsight-frontend:sealos-v4
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
  - `LABEL_STUDIO_HOST` = `https://<LS外网域名>`（必须用外网地址，LS 用此值生成静态资源 URL）
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
- ⚠️ 必须开启外网访问：前端通过 `window.open()` 在用户浏览器中直接打开 LS 标注页面，走公网而非 Sealos 内网。不开外网 = 无法标注。外网域名同时用于前端构建时的 `VITE_LABEL_STUDIO_URL`
- ⚠️ 注意：Label Studio 的 PG 变量名是 `POSTGRE_*`（不是 `POSTGRESQL_*`），数据库名用 `superinsight`，与本地 docker-compose 一致

#### 3.4 Backend (FastAPI)
- 应用名：`superinsight-backend`（固定名称，勿改）
- 镜像：`angus888/superinsight-backend:sealos`
- CPU：1核，内存：1GB
- 环境变量：参考 `.env.sealos` 文件，填入实际地址
- 开启外网访问（端口 8000）

#### 3.5 Celery Worker
- 应用名：`superinsight-celery`（固定名称，勿改）
- 镜像：`angus888/superinsight-celery:sealos`（专用镜像，CMD 写死启动命令）
- CPU：0.5核，内存：1GB
- 运行命令/命令参数：留空（CMD 已内置）
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
| Sealos UI 运行命令/命令参数无法正确拆分多参数命令 | UI 将命令参数合并为单个字符串传给 shell，`/bin/sh -c xxx` 变成 `/bin/sh "-c xxx"` | 单独建 Dockerfile 写死 CMD，不在 Sealos UI 覆盖启动命令 |
| Celery Worker 反复 OOM 重启，日志无报错 | prefork 默认按宿主机 CPU 核数（非容器 limit）创建 worker，16 核节点 fork 16 进程撑爆内存 | CMD 中显式 `--concurrency=N`，N 按内存估算（每 worker ~60-80MB） |
| 前端跳转 LS 标注页面 404 / 连接失败 | `VITE_LABEL_STUDIO_URL` 未在 `Dockerfile.frontend` 中声明，前端回退到 `localhost:8080`，Sealos 环境不可达 | Sealos 给 `superinsight-ls` 开外网访问，`Dockerfile.frontend` 新增 `ARG VITE_LABEL_STUDIO_URL`，构建时传入 LS 外网域名 |
| 尝试用 nginx 反代 `/ls/` 路径访问 LS 失败 | LS 是完整 Django+React SPA，内部路由硬编码根路径，sub-path 反代会破坏静态资源和 API 路由 | 放弃 sub-path 反代，必须用独立域名/端口访问，与本地端口映射模式保持一致 |
| 前端跳转 LS 正常但后端调 LS API 失败（或反过来） | `LABEL_STUDIO_URL`（后端，内网）和 `VITE_LABEL_STUDIO_URL`（前端，浏览器可达）在非本地环境必须分开配置。本地 Docker 两者恰好相同容易忽略 | 后端 `.env.sealos` 中 `LABEL_STUDIO_URL` 用内网 FQDN，`Dockerfile.frontend` 构建时 `VITE_LABEL_STUDIO_URL` 传 LS 外网域名。涉及：`.env.sealos` ↔ `Dockerfile.frontend` ↔ `useLabelStudioUrl.ts` ↔ `integration.py` |
| 前端 production build 报 `Cannot read properties of undefined (reading 'version')` | Vite `manualChunks` 将 React 和 antd 拆到不同 chunk，antd 5.x 在模块顶层调用 `React.version.split('.')`，ESM 初始化顺序导致 React 未就绪（dev 模式不触发） | React + antd + pro-components 必须归入同一 chunk，参考 `vite.config.ts` 中 `manualChunks` |
| API 请求 502，路径变成 `/api/api/...` 双重前缀 | 前端 `constants/api.ts` 路径已含 `/api/`，`VITE_API_BASE_URL=/api` 又加一层；nginx `proxy_pass $backend/api/` 再拼一层 | `VITE_API_BASE_URL` 设为空，nginx `proxy_pass $backend`（直接透传），三处联动：`constants/api.ts` ↔ `Dockerfile.frontend` ↔ `nginx.conf` |
| nginx 反代 502，DNS 解析服务名失败 | Sealos 控制台显示的内网域名可能有拼写偏差（如 `ubtindlowirp` vs 实际 `ubtjndlpwirp`） | 在容器内 `env \| grep _SERVICE_HOST` 从 K8s 注入的环境变量反推真实服务名，再写入 nginx.conf |
| 后端 500 报 `MissingGreenlet` | `DATABASE_URL` 用了 `postgresql+asyncpg://`，但后端是同步 SQLAlchemy（`create_engine`） | 改为 `postgresql+psycopg2://` 或 `postgresql://`，backend 和 celery 需同步修改 |
| LS API 全部 401，Token/JWT/PAT 均无效 | LS 新版认证后端为 `TokenAuthenticationPhaseout`，Legacy Token 已废弃，标准 DRF API 认证不可用 | 安装 `label-studio-sso` 包，用 `/api/sso/token` 端点（绕过 DRF 中间件，直接查 `authtoken_token` 表）。Sealos `Dockerfile.labelstudio` 必须复用本地 `deploy/label-studio/` 的 SSO + 品牌化文件 |
| SSO token 端点返回 401 | `/api/sso/token` 需要 admin 用户的 DRF Token（`is_staff=True`），通过 Django shell `Token.objects.create(user=admin)` 生成，不能用组织 token 或 session cookie | 进 LS 容器 `label-studio shell`，用 `rest_framework.authtoken.models.Token` 创建，设为 `LABEL_STUDIO_API_TOKEN` 环境变量 |
| 点击"在新窗口中打开"后 LS 要求手动登录，无自动登录 | `openLabelStudio` 直接用 `VITE_LABEL_STUDIO_URL` 拼 URL 打开，未调后端 `getAuthUrl` 获取 SSO token。本地 Docker 因 LS 无强制登录不易发现 | 修改 `useLabelStudio.ts` 的 `openLabelStudio`：先调 `getAuthUrl` 获取 token → 用前端 `VITE_LABEL_STUDIO_URL` 重建 URL → `window.open`。降级：auth 失败时回退无 token URL |
| TaskDetail 页面不显示"开始标注"和"在新窗口中打开"按钮 | 整个标注卡片被 `label_studio_project_id &&` 包裹，Sealos 新建任务无 project ID 则整块不渲染 | 拆分条件：始终显示"开始标注"（annotate 页面会自动创建项目），"在新窗口中打开"仅在有 project ID 时显示 |
| Sealos LS 登录页仍显示 HumanSignal logo 和英文 | LS Docker 镜像未重新构建推送，`entrypoint-sso.sh` 的品牌化 patch 未生效 | 重新构建并推送 LS 镜像：`docker build --platform linux/amd64 -f deploy/sealos/Dockerfile.labelstudio -t angus888/superinsight-labelstudio:sealos . && docker push` |
| LS 外网访问页面空白，静态资源全部 502 | `LABEL_STUDIO_HOST=http://0.0.0.0:8080`，LS 用此值生成 HTML 中静态资源绝对 URL，浏览器无法访问容器内地址 | `LABEL_STUDIO_HOST` 必须设为 LS 外网域名（如 `https://xxx.sealosgzg.site`）。三变量区分：`LABEL_STUDIO_HOST`（LS 自身，外网）、`LABEL_STUDIO_URL`（后端→LS，内网）、`VITE_LABEL_STUDIO_URL`（前端构建时，外网） |
| SSO 自动登录失败，浏览器跳转登录页 | `JWTAutoLoginMiddleware` 被追加到 MIDDLEWARE 末尾（第 20 位），`AuthenticationMiddleware`（第 7 位）先判定未认证并重定向 | `entrypoint-sso.sh` 中将 `JWTAutoLoginMiddleware` 插入到 `AuthenticationMiddleware` 之前，而非追加到末尾 |
| LS 镜像更新后 entrypoint patch 不生效 | patch 用 marker 做幂等检查，但 PVC 持久化了旧文件，marker 已存在导致新 patch 跳过 | 更新 LS 镜像后需手动清除 marker（`sed -i '/SSO_PATCHED/,$d' label_studio.py`）或删除重建 LS 应用 |
| 登录成功但页面一闪跳回仪表盘，AI助手等页面无法访问 | `auth_simple.py` 的 `SECRET_KEY` 硬编码，与 `auth.py` 从 `JWT_SECRET_KEY` 环境变量读取的值不一致，导致签发的 token 验证失败 401。`business_metrics.py` 用 `auto_error=False` 静默降级使 dashboard 正常，掩盖了问题 | `auth_simple.py` 改为 `os.getenv("JWT_SECRET_KEY", ...)`，确保所有 auth 模块使用同一密钥源 |
| LS 容器内执行 Django 命令（如生成 Token）失败，报 `ModuleNotFoundError: No module named 'core'` | LS 的 settings 用相对导入 `from core.settings.base import *`，需要 `/label-studio/label_studio` 也在 `sys.path` 中；且容器是 Alpine（ash），多行 Python 粘贴会被拆散 | 用 `printf` 写单行脚本到文件再执行：`printf 'import django,os,sys\nsys.path.insert(0,"/label-studio")\nsys.path.insert(0,"/label-studio/label_studio")\nos.environ["DJANGO_SETTINGS_MODULE"]="label_studio.core.settings.label_studio"\ndjango.setup()\n...\n' > /tmp/script.py && cd /label-studio && python3 /tmp/script.py` |
| SSO Bearer JWT 写入 `DEFAULT_AUTHENTICATION_CLASSES` 后仍 401 | LS 所有 API View 显式设置 `authentication_classes = [TokenAuthenticationPhaseout, SessionAuthentication]`，完全绕过全局 DRF 设置 | 必须 monkey-patch `TokenAuthenticationPhaseout.authenticate` 本身，在 legacy token 失败后回退到 SSO Bearer JWT 验证。patch 写在 `entrypoint-sso.sh` 中追加到 `jwt_auth/auth.py` |
| LS 升级（基础镜像更新）后 SSO/品牌化失效 | `heartexlabs/label-studio:latest` 升级可能改变 Python 版本、`views.py` 代码结构、`jwt_auth/auth.py` 认证逻辑 | 升级流程：1) 拉新基础镜像 2) 重新构建 `Dockerfile.labelstudio` 3) 验证：`entrypoint-sso.sh` 动态路径检测是否正常、`views.py` patch 目标代码是否匹配、`jwt_auth/auth.py` patch 是否兼容、Bearer JWT 认证是否通过 |
| 升版后 Celery 仍跑旧代码 | `Dockerfile.celery` 的 `FROM` 硬编码了 backend 镜像版本 tag，升版时忘记同步更新 | 升版时联动更新：`README.md` 镜像清单 + 构建命令 + `Dockerfile.celery` 的 `FROM` tag，三处必须一致 |
| SSO 自动登录仍跳转登录页（middleware 正常、curl 容器内通过） | `generate_authenticated_url` 用 SuperInsight 的 `jwt_secret_key` 自签 JWT token，但 LS 的 `JWTAutoLoginMiddleware` 只认 LS 自己的 `SECRET_KEY`，跨系统密钥不互通 | `generate_authenticated_url` 改为调用 LS 的 `POST /api/sso/token` 获取 LS 签发的 token（与 `get_login_url` 同一方式）。规则：给 LS 的 SSO token 必须由 LS 自身签发，不可用 SuperInsight 密钥 |

## SuperInsight ↔ Label Studio 认证体系

### 认证架构

```
┌──────────────┐    SSO JWT     ┌──────────────┐
│  SuperInsight │ ──────────→  │ Label Studio  │
│   Backend     │              │  (Django)     │
│              │  ①Token auth  │              │
│  integration │ ──────────→  │ /api/sso/token│
│  .py         │  ②Bearer JWT │              │
│              │ ──────────→  │ /api/projects/│
└──────────────┘              └──────────────┘
       ↑                            ↑
       │ JWT_SECRET_KEY             │ SECRET_KEY
       │                           │ (Django settings)
       │                           │
  .env.sealos                entrypoint-sso.sh
  LABEL_STUDIO_API_TOKEN     (动态 patch)
  LABEL_STUDIO_SSO_ENABLED
  LABEL_STUDIO_SSO_EMAIL
```

### 认证流程（SSO 模式）

1. 后端持有 LS admin 的 DRF Token（`LABEL_STUDIO_API_TOKEN`）
2. 调用 `POST /api/sso/token`（带 `Token <api_token>` header + `{"email": "admin@superinsight.local"}`）
3. LS 返回短期 JWT（600s，用 Django `SECRET_KEY` 签名，audience=`label-studio-sso`）
4. 后端用 `Bearer <jwt>` 调用 LS API（创建项目、导入任务等）
5. JWT 过期后自动重新获取（`_ensure_sso_token()` 有 30s 提前刷新）

### 涉及文件清单（改什么 / 不改什么）

| 文件 | 作用 | 是否需要改动 |
|------|------|-------------|
| `deploy/label-studio/entrypoint-sso.sh` | LS 启动时动态 patch：SSO settings、Bearer auth、品牌化 | ⚠️ LS 升级时可能需要适配 |
| `deploy/label-studio/settings_sso.py` | SSO Django settings（JWT claim、cookie、expiry） | 一般不改 |
| `deploy/label-studio/branding.css` | LS 品牌化样式 | 一般不改 |
| `deploy/label-studio/i18n-inject.js` | LS 中文化脚本 | 一般不改 |
| `deploy/sealos/Dockerfile.labelstudio` | LS 镜像构建（安装 sso 包 + 复制文件 + PVC 修复） | ⚠️ LS 升级时重新构建 |
| `src/label_studio/config.py` | 后端 LS 配置（读环境变量，选择 auth 方式） | 一般不改 |
| `src/label_studio/integration.py` | 后端 LS 集成（`_ensure_sso_token`、`_get_headers`、API 调用） | 一般不改 |
| `deploy/sealos/.env.sealos` | 环境变量（Token、URL、SSO 开关） | ⚠️ LS 重建后需更新 Token |

### LS 镜像包含什么

`Dockerfile.labelstudio` 基于 `heartexlabs/label-studio:latest`，额外包含：

1. `label-studio-sso` Python 包（提供 `/api/sso/token` 端点）
2. `settings_sso.py`（SSO Django 配置）
3. `entrypoint-sso.sh`（启动时动态 patch 5 项内容）：
   - patch `label_studio.py`：注册 `label_studio_sso` app + DRF auth classes
   - 创建 `bearer_auth.py`：DRF Bearer JWT 认证类
   - patch `jwt_auth/auth.py`：`TokenAuthenticationPhaseout` 添加 SSO Bearer 回退
   - patch `views.py`：SSO 用户自动创建
   - patch `urls.py`：注册 `/api/sso/` URL
4. 品牌化文件（`branding.css`、`i18n-inject.js`）
5. PVC 权限修复（`sealos-entrypoint.sh` 先 chown 再启动）

### 部署 / 升级 LS 操作手册

#### 首次部署

```bash
# 1. 构建 LS 镜像
docker build --platform linux/amd64 \
  -f deploy/sealos/Dockerfile.labelstudio \
  -t angus888/superinsight-labelstudio:sealos .
docker push angus888/superinsight-labelstudio:sealos

# 2. Sealos 创建 LS 应用（参考上方 3.3 节）

# 3. 等 LS 启动完成，进 LS 容器生成 DRF Token
printf 'import django,os,sys\nsys.path.insert(0,"/label-studio")\nsys.path.insert(0,"/label-studio/label_studio")\nos.environ["DJANGO_SETTINGS_MODULE"]="label_studio.core.settings.label_studio"\ndjango.setup()\nfrom django.contrib.auth import get_user_model\nfrom rest_framework.authtoken.models import Token\nUser=get_user_model()\nu=User.objects.get(email="admin@superinsight.local")\nt,_=Token.objects.get_or_create(user=u)\nprint("Token:",t.key)\n' > /tmp/gen_token.py && cd /label-studio && python3 /tmp/gen_token.py

# 4. 将输出的 Token 填入后端环境变量 LABEL_STUDIO_API_TOKEN
# 5. 重启后端
```

#### LS 重建（删除重建应用）

LS 重建后 FQDN 会变（带随机后缀），且 DRF Token 丢失：

```bash
# 1. 更新后端环境变量
#    LABEL_STUDIO_URL=http://<新FQDN>:8080

# 2. 进 LS 容器重新生成 DRF Token（同上）
#    更新 LABEL_STUDIO_API_TOKEN

# 3. 重启后端

# 4. 在后端容器重新同步已有任务（FAILED→SYNCED）
python3 -c "
import asyncio
from src.label_studio.integration import label_studio_integration
from src.database.connection import db_manager
from src.database.models import TaskModel
db_manager.initialize()
async def fix():
    with db_manager.get_session() as s:
        tasks = s.query(TaskModel).filter(TaskModel.label_studio_project_id == None).all()
        for t in tasks:
            from src.api.label_studio_sync import label_studio_sync_service
            r = await label_studio_sync_service.create_project_for_task(str(t.id), t.name, t.description, t.annotation_type or 'text_classification')
            if r['success']:
                t.label_studio_project_id = r['project_id']
                t.label_studio_sync_status = 'synced'
                from datetime import datetime
                t.label_studio_last_sync = datetime.utcnow()
                print(f'  {t.name} → project {r[\"project_id\"]}')
        s.commit()
asyncio.run(fix())
"
```

#### LS 基础镜像升级

`heartexlabs/label-studio:latest` 升级可能破坏 entrypoint patch：

```bash
# 1. 拉取新基础镜像
docker pull heartexlabs/label-studio:latest

# 2. 重新构建
docker build --platform linux/amd64 \
  -f deploy/sealos/Dockerfile.labelstudio \
  -t angus888/superinsight-labelstudio:sealos-v4 .

# 3. 验证 patch 是否生效（进容器检查）
grep "SSO_BEARER_FALLBACK_PATCHED" /label-studio/label_studio/jwt_auth/auth.py
grep "label_studio_sso" /label-studio/label_studio/core/settings/label_studio.py
grep "AUTO_CREATE_PATCHED" $(python3 -c "import label_studio_sso,os;print(os.path.join(os.path.dirname(label_studio_sso.__file__),'views.py'))")

# 4. 测试 SSO token 获取
python3 -c "
import httpx
r = httpx.post('http://localhost:8080/api/sso/token',
  headers={'Authorization':'Token <api_token>','Content-Type':'application/json'},
  json={'email':'admin@superinsight.local'}, timeout=10)
print(r.status_code, r.text[:100])
"

# 5. 如果 patch 失败，检查：
#    - jwt_auth/auth.py 中 TokenAuthenticationPhaseout 类是否还存在
#    - views.py 中 "Validate user exists" 代码块是否变化
#    - Python 版本是否变化导致 label_studio_sso 包路径变化
```

### 后端环境变量（LS 相关）

| 变量 | 说明 | 示例 |
|------|------|------|
| `LABEL_STUDIO_URL` | LS 内网地址（后端→LS） | `http://superinsight-ls-xxx.ns-xxx.svc.cluster.local:8080` |
| `LABEL_STUDIO_API_TOKEN` | LS admin 的 DRF Token（40 位 hex） | `21d44d803c...` |
| `LABEL_STUDIO_SSO_ENABLED` | 启用 SSO 模式 | `true` |
| `LABEL_STUDIO_SSO_EMAIL` | SSO 登录邮箱 | `admin@superinsight.local` |
| `VITE_LABEL_STUDIO_URL` | LS 外网地址（前端构建时注入） | `https://xxx.gzg.sealos.run` |

### 验证清单

部署或升级后按顺序验证：

```bash
# 在后端容器执行
# 1. LS 健康检查
curl -s "$LABEL_STUDIO_URL/api/health"
# 期望: {"status": "UP"}

# 2. SSO token 获取
python3 -c "
import httpx,os
r=httpx.post(f'{os.environ[\"LABEL_STUDIO_URL\"]}/api/sso/token',
  headers={'Authorization':f'Token {os.environ[\"LABEL_STUDIO_API_TOKEN\"]}','Content-Type':'application/json'},
  json={'email':os.environ.get('LABEL_STUDIO_SSO_EMAIL','admin@superinsight.local')},timeout=10)
print(f'Status:{r.status_code}')
jwt=r.json().get('token','')[:20]
print(f'JWT:{jwt}...')
"

# 3. 用 JWT 创建项目
# （参考本次对话中的测试脚本）

# 4. Redis 连通
python3 -c "import redis,os;r=redis.from_url(os.environ['REDIS_URL'],decode_responses=True,socket_connect_timeout=5);r.ping();print('Redis OK')"
```

## 自定义镜像清单

| 镜像 | Dockerfile | 基础镜像 | 自定义原因 | 当前版本 |
|------|-----------|---------|-----------|----------|
| `superinsight-elasticsearch` | `Dockerfile.elasticsearch` | `elasticsearch:8.5.0` | PVC 权限修复 | `sealos-v4` |
| `superinsight-labelstudio` | `Dockerfile.labelstudio` | `label-studio:latest` | PVC 权限修复 + SSO 认证 + Bearer JWT patch + 品牌化 + i18n | `sealos-v4` |
| `superinsight-backend` | `Dockerfile.backend` | `python:3.11-slim` | 应用代码 + CPU-only torch + LS 反向同步 | `sealos-v4` |
| `superinsight-frontend` | `Dockerfile.frontend` | `nginx:alpine` | 前端构建产物 + nginx 配置 + 同步按钮 | `sealos-v4` |
| `superinsight-celery` | `Dockerfile.celery` | `superinsight-backend:sealos-v4` | 写死 Celery CMD，绕开 Sealos UI 参数拆分问题 | `sealos-v4` |

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
