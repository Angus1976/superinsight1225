# Label Studio 集成架构说明

**最后更新**: 2026-03-24
**维护者**: 开发团队
**状态**: 已实现

---

## 概述

SuperInsight 通过**独立浏览器标签页**方式集成 Label Studio（LS），而非 iframe 嵌入。前端构建标注 URL 后 `window.open()` 跳转至 LS，后端通过 LS REST API 实现项目创建、数据导入和标注同步。LS 作为独立 Django+React SPA 运行，与 SuperInsight 共享同一 PostgreSQL 实例。

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                      用户浏览器                               │
│                                                              │
│  ┌─────────────────────┐    window.open()    ┌────────────┐ │
│  │  SuperInsight SPA    │ ──────────────────→ │ Label Studio│ │
│  │  (React + Vite)      │                     │ (Django SPA)│ │
│  │  :5173 / :80         │                     │ :8080       │ │
│  └──────────┬───────────┘                     └──────┬──────┘ │
└─────────────┼────────────────────────────────────────┼────────┘
              │ REST API                               │
              ▼                                        ▼
┌─────────────────────┐    LS REST API    ┌────────────────────┐
│  SuperInsight Backend│ ───────────────→  │  Label Studio      │
│  (FastAPI :8000)     │                   │  (Django :8080)    │
└──────────┬──────────┘                    └─────────┬──────────┘
           │                                         │
           └──────────────┬──────────────────────────┘
                          ▼
                 ┌─────────────────┐
                 │   PostgreSQL    │
                 │  (共享实例)      │
                 └─────────────────┘
```

---

## 前端路由与页面流转

### 路由链

```
/tasks                          → TasksPage（任务列表）
/tasks/:id                      → TaskDetailPage（任务详情）
/tasks/:id/annotate             → TaskAnnotatePage（标注入口页）
  └→ window.open(LS_URL)        → Label Studio 独立标签页
```

### 关键文件

| 文件 | 职责 |
|------|------|
| `frontend/src/pages/Tasks/index.tsx` | 任务列表页 |
| `frontend/src/pages/Tasks/TaskDetail.tsx` | 任务详情，含"开始标注"按钮 |
| `frontend/src/pages/Tasks/TaskAnnotate.tsx` | 标注入口，构建 LS URL 并跳转 |
| `frontend/src/hooks/useLabelStudioUrl.ts` | 构建 LS 访问 URL |
| `frontend/src/hooks/useLabelStudio.ts` | LS 项目/数据操作 hook |
| `frontend/src/constants/labelStudio.ts` | LS 相关常量 |

### URL 构建逻辑

`useLabelStudioUrl.ts` 读取环境变量 `VITE_LABEL_STUDIO_URL`，未配置时回退到 `http://localhost:8080`。拼接路径格式：

```
{baseUrl}/projects/{projectId}/data?lang=zh-cn&tab={tabId}
```

---

## 后端 API 与 LS 集成

### 认证方式

| 环境 | 认证方式 | 说明 |
|------|---------|------|
| 本地 Docker | Legacy Token | LS 内置 DRF Token，通过 `LABEL_STUDIO_API_TOKEN` 环境变量传入 |
| Sealos | SSO Token | LS 新版废弃 Legacy Token，需安装 `label-studio-sso` 包，使用 `/api/sso/token` 端点 |

### 后端关键文件

| 文件 | 职责 |
|------|------|
| `src/api/label_studio_api.py` | LS API 代理端点（前端通过后端中转调用 LS） |
| `src/api/label_studio_sync.py` | 标注数据同步 API |
| `src/label_studio/integration.py` | LS 集成核心逻辑（项目创建、数据导入、标注查询） |
| `src/label_studio/jwt_auth.py` | JWT 认证辅助 |
| `src/api/tasks.py` | 任务管理 API（含 LS 项目关联） |

### API 调用链

```
SuperInsight 前端
  → POST /api/tasks/{id}/create-ls-project    创建 LS 项目
  → POST /api/tasks/{id}/import-to-ls         导入数据到 LS
  → GET  /api/tasks/{id}/ls-annotations       查询标注结果
  → POST /api/tasks/{id}/sync-from-ls         从 LS 同步标注

SuperInsight 后端
  → LS REST API (http://label-studio:8080/api/)
    - POST /api/projects                       创建项目
    - POST /api/projects/{id}/import           导入数据
    - GET  /api/projects/{id}/tasks            获取任务列表
    - GET  /api/tasks/{id}/annotations         获取标注
```

---

## 双向数据同步

### 正向同步（SuperInsight → LS）

1. 用户在 SuperInsight 创建标注任务
2. 后端调用 LS API 创建对应项目（`POST /api/projects`）
3. 后端将样本数据导入 LS 项目（`POST /api/projects/{id}/import`）
4. 前端构建 LS URL，用户跳转到 LS 进行标注

### 反向同步（LS → SuperInsight）

1. `useLabelStudioSync` hook 定期轮询 LS 标注状态
2. 后端查询 LS 项目的标注完成数、总任务数
3. 更新 SuperInsight 任务的进度百分比和状态
4. 关键文件：`frontend/src/pages/Tasks/hooks/useLabelStudioSync.ts`

### 同步触发时机

- 进入任务详情页时自动触发一次同步
- 标注入口页轮询同步（可配置间隔）
- 用户手动点击"同步标注"按钮

---

## 品牌化（白标）

### 实现方式

LS 容器启动时通过 `entrypoint-sso.sh` 脚本注入品牌化资源：

1. `branding.css` — 覆盖 LS 默认样式（Logo、配色、页脚）
2. `i18n-inject.js` — 替换界面文本（如 "HumanSignal" → "SuperInsight"）
3. 脚本在 LS Django 模板文件中插入 `<link>` 和 `<script>` 标签

### 品牌化文件

| 文件 | 说明 |
|------|------|
| `deploy/label-studio/Dockerfile` | 本地 LS 镜像构建 |
| `deploy/label-studio/entrypoint-sso.sh` | 启动脚本，注入 SSO + 品牌化 |
| `deploy/label-studio/branding.css` | 品牌样式覆盖 |
| `deploy/label-studio/i18n-inject.js` | 界面文本替换 |

### 已知限制

- 注册页面品牌化不完整（HumanSignal 仍可见），因注册页模板结构与主页不同
- CSS 注入依赖 LS 模板文件路径，LS 版本升级可能需要调整

---

## LS 定制清单与升级指南

### 设计原则

LS 使用原版 `heartexlabs/label-studio:latest` 镜像，**零源码修改**。所有定制通过 `entrypoint-sso.sh` 在容器启动时运行时注入，升级时只需换基础镜像 + 验证 patch 是否兼容。

### 运行时 Patch 清单

| # | Patch 内容 | 目标文件 | 方式 | 升级风险 |
|---|-----------|---------|------|---------|
| 1 | SSO Django App 注册 | `/label-studio/.../settings/label_studio.py` | append Python 代码 | 低：只要 `INSTALLED_APPS`/`MIDDLEWARE` 变量名不变 |
| 2 | SSO URL 路由 | `/label-studio/.../core/urls.py` | sed 注入 `path('api/sso/', ...)` | 低：只要 `urlpatterns` 格式不变 |
| 3 | auto-create user | `/label-studio/.venv/lib/python3.13/.../label_studio_sso/views.py` | Python 脚本替换代码块 | **高**：路径硬编码 `python3.13`，LS 升级 Python 版本必改 |
| 4 | 品牌化 CSS/JS 注入 | `base.html`, `simple.html`, user templates | sed + cp | 中：模板路径/结构可能变化 |
| 5 | 全局文本替换 | 所有 `.html` 模板 | `find + sed 's/Label Studio/问视间/g'` | 低：纯文本替换 |
| 6 | favicon 替换 | static 目录 | cp | 低 |

### 升级步骤

```bash
# 1. 拉取新版 LS 镜像，记录 Python 版本
docker run --rm heartexlabs/label-studio:NEW_VERSION python3 --version
# 输出如 Python 3.14 → 需更新 entrypoint-sso.sh 中的路径

# 2. 检查模板路径是否变化
docker run --rm heartexlabs/label-studio:NEW_VERSION \
  find /label-studio/label_studio/templates -name "*.html" | head -20

# 3. 检查 settings 文件位置
docker run --rm heartexlabs/label-studio:NEW_VERSION \
  ls /label-studio/label_studio/core/settings/

# 4. 如有变化，更新 entrypoint-sso.sh 中对应路径

# 5. 重新构建并测试
docker build -f deploy/label-studio/Dockerfile \
  -t superinsight-ls:test deploy/label-studio/
docker run --rm -p 8080:8080 \
  -e LABEL_STUDIO_SSO_ENABLED=true \
  superinsight-ls:test

# 6. 验证清单（在浏览器中逐项检查）
#    □ LS 正常启动，无 entrypoint 报错
#    □ /user/login/ 页面显示"问视间"品牌
#    □ /api/sso/token 端点可访问（curl 测试）
#    □ ?token=xxx 参数能自动登录
#    □ 品牌 CSS/JS 正常加载（F12 Network 检查）
#    □ 中文界面正常
```

### 需要修改 entrypoint-sso.sh 的场景

| 触发条件 | 需改的位置 |
|---------|-----------|
| LS 升级 Python 版本（如 3.13→3.14） | Patch #3 中 `.venv/lib/python3.13/` 路径 |
| LS 移动模板目录 | Patch #4 中 `LS_TEMPLATE_DIR` 变量 |
| LS 改变 settings 文件结构 | Patch #1 中 `SETTINGS_FILE` 路径和 append 内容 |
| LS 改变 static 目录结构 | Patch #4/6 中 `LS_STATIC_DIR` / `LS_STATIC_BUILD_DIR` |
| `label-studio-sso` 包 API 变化 | Patch #3 中 views.py 替换逻辑 |

### 降低升级风险的建议

1. **固定 LS 版本 tag**：生产环境不用 `latest`，改为 `heartexlabs/label-studio:1.x.x`
2. **entrypoint-sso.sh 已有幂等保护**：每个 patch 用 marker 注释检测是否已应用，重复启动不会重复 patch
3. **Python 版本检测可自动化**：未来可在 entrypoint 中动态获取 Python 版本号，替代硬编码路径

---

## 多环境部署差异

| 维度 | 本地 Docker | Sealos |
|------|------------|--------|
| LS 访问方式 | `localhost:8080`（端口映射） | 需开外网访问，获取独立域名 |
| 前端 LS URL | 回退 `http://localhost:8080` | 必须通过 `VITE_LABEL_STUDIO_URL` 构建时注入 |
| 认证方式 | SSO Token（`label-studio-sso` 包） | SSO Token（同左，两环境统一） |
| 自动登录 | `openLabelStudio` → `getAuthUrl` → `?token=xxx` → `JWTAutoLoginMiddleware` | 同左 |
| 品牌化 | `entrypoint-sso.sh` 注入 | 同上，但需确认 Dockerfile 复用本地 deploy 文件 |
| 数据库 | docker-compose 内部网络 | Sealos 托管 PostgreSQL |
| 反代 | 无（直连端口） | 不可用 sub-path 反代（见下方说明） |

### 环境变量对照

| 变量 | 本地 Docker | Sealos | 说明 |
|------|------------|--------|------|
| `LABEL_STUDIO_URL` | `http://label-studio:8080` | `http://superinsight-ls-xxx.svc.cluster.local:8080` | 后端→LS 内网通信 |
| `VITE_LABEL_STUDIO_URL` | 未设置（回退 `localhost:8080`） | 构建时 `--build-arg` 传入 LS 外网域名 | 浏览器→LS |
| `LABEL_STUDIO_API_TOKEN` | LS UI 生成的 PAT | Django shell 生成的 DRF Token | 后端调 LS API 认证 |
| `LABEL_STUDIO_SSO_ENABLED` | `true` | `true` | 两环境统一启用 |
| `LABEL_STUDIO_SSO_EMAIL` | `admin@example.com` | `admin@superinsight.local` | SSO 用户邮箱 |

### 注意事项

1. **`VITE_LABEL_STUDIO_URL` 必须在 Sealos 构建时注入**：`Dockerfile.frontend` 已有 `ARG VITE_LABEL_STUDIO_URL`，构建时传入 LS 外网域名
2. **本地 Docker 启用 SSO 后需重建 LS 容器**：`docker-compose down label-studio && docker-compose up -d label-studio`，首次启动 `entrypoint-sso.sh` 会 patch Django settings
3. **两环境认证统一为 SSO**：`LABEL_STUDIO_SSO_ENABLED=true` 在 `docker-compose.yml`（本地）和 `.env.sealos`（Sealos）中均已配置

### 部署操作

- Sealos：在控制台为 `superinsight-ls` 开启外网访问，获取外网域名
- `Dockerfile.frontend` 已有 `ARG VITE_LABEL_STUDIO_URL`，构建时传入 LS 外网域名
- 与本地端口映射模式保持一致：前端直连 LS，不经过反代

> ⚠️ LS 是完整 Django+React SPA，**不支持 sub-path 反代部署**（`/ls/` 会破坏内部路由）。必须使用独立域名/端口访问。

> ⚠️ `LABEL_STUDIO_URL`（后端）和 `VITE_LABEL_STUDIO_URL`（前端）在非本地环境必须分开配置：后端走内网调 LS API，前端 `window.open()` 走外网供用户浏览器访问。本地 Docker 两者恰好相同（都是 `localhost:8080`），容易忽略这个区别。

---

## 自动登录流程

用户从 SuperInsight 跳转到 LS 时自动登录，无需二次输入密码。本地 Docker 和 Sealos 使用相同流程：

```
TaskDetail / TaskAnnotate 页面
  → 点击"在新窗口中打开"
  → openLabelStudio(projectId)
    → 前端调用 GET /api/label-studio/projects/{id}/auth-url
    → 后端 generate_authenticated_url() 生成 JWT token
    → 返回 URL: {LABEL_STUDIO_URL}/projects/{id}?token=xxx&lang=zh
    → 前端提取 token，用 VITE_LABEL_STUDIO_URL 重建浏览器可达 URL
    → window.open(重建后的 URL)
    → LS 的 JWTAutoLoginMiddleware 读取 token 参数自动登录
  → 若 getAuthUrl 失败，降级为无 token 的普通 URL（用户需手动登录）
```

> ⚠️ 后端返回的 URL 使用 `LABEL_STUDIO_URL`（内网地址），浏览器不可达。前端必须用 `VITE_LABEL_STUDIO_URL` 替换 base URL 后再打开。

依赖链：`entrypoint-sso.sh` 注入 `label_studio_sso` 包 → Django settings 添加 `JWTAutoLoginMiddleware` → 中间件读取 URL 中的 `token` 参数或 `ls_auth_token` cookie

---

## 关键文件索引

### 前端

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/Tasks/index.tsx` | 任务列表 |
| `frontend/src/pages/Tasks/TaskDetail.tsx` | 任务详情 |
| `frontend/src/pages/Tasks/TaskAnnotate.tsx` | 标注入口 |
| `frontend/src/pages/Tasks/hooks/useLabelStudioSync.ts` | 标注同步 hook |
| `frontend/src/hooks/useLabelStudioUrl.ts` | LS URL 构建 |
| `frontend/src/hooks/useLabelStudio.ts` | LS 操作 hook |
| `frontend/src/services/labelStudioService.ts` | LS 服务层 |
| `frontend/src/services/task.ts` | 任务服务层 |
| `frontend/src/constants/labelStudio.ts` | LS 常量 |
| `frontend/src/components/Tasks/AnnotationGuide.tsx` | 标注指南组件 |

### 后端

| 文件 | 说明 |
|------|------|
| `src/api/tasks.py` | 任务管理 API |
| `src/api/label_studio_api.py` | LS API 代理 |
| `src/api/label_studio_sync.py` | 标注同步 API |
| `src/label_studio/integration.py` | LS 集成核心 |
| `src/label_studio/jwt_auth.py` | JWT 认证 |

### 部署

| 文件 | 说明 |
|------|------|
| `deploy/label-studio/Dockerfile` | 本地 LS 镜像 |
| `deploy/label-studio/entrypoint-sso.sh` | SSO + 品牌化启动脚本 |
| `deploy/label-studio/branding.css` | 品牌样式 |
| `deploy/label-studio/i18n-inject.js` | 文本替换脚本 |
| `deploy/sealos/Dockerfile.frontend` | Sealos 前端镜像 |
| `deploy/sealos/Dockerfile.labelstudio` | Sealos LS 镜像 |
| `deploy/sealos/nginx.conf` | Sealos nginx 配置 |
| `deploy/sealos/.env.sealos` | Sealos 环境变量参考 |
