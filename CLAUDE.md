# SuperInsight AI 数据治理与标注平台

SuperInsight 是一个企业级 AI 数据治理和智能标注平台，为 AI 时代设计。深度集成成熟的"理采存管用"方法论，同时针对大语言模型（LLM）和生成式 AI（GenAI）应用场景进行全面升级。

## 技术栈

### 后端
- **框架**: FastAPI (Python 3.11+)
- **数据库**: PostgreSQL 15+ with JSONB, Redis 7+, Neo4j 5+
- **ORM**: SQLAlchemy 2.0+ with Alembic migrations
- **任务队列**: Celery with Redis broker
- **日志**: structlog
- **测试**: pytest

### 前端
- **框架**: React 19 with TypeScript
- **构建工具**: Vite 7+
- **UI 库**: Ant Design 5+ with Pro Components
- **状态管理**: Zustand
- **数据获取**: TanStack Query (React Query)
- **路由**: React Router DOM 7+
- **测试**: Vitest + Playwright for E2E

### 核心集成
- **标注引擎**: Label Studio (容器化)
- **AI/ML**: Transformers, PyTorch, Ollama, 多个 LLM API
- **数据隐私**: Presidio (analyzer + anonymizer)
- **质量评估**: Ragas framework
- **监控**: Prometheus + Grafana
- **安全**: JWT, bcrypt, cryptography

## 项目结构

```
superinsight-platform/
├── src/                          # 主要源代码
│   ├── api/                      # FastAPI 路由和端点
│   ├── models/                   # SQLAlchemy 数据库模型
│   ├── schemas/                  # Pydantic 请求/响应模式
│   ├── services/                 # 业务逻辑服务
│   ├── security/                 # 认证、授权、审计
│   ├── ai/                       # AI 模型集成
│   ├── quality/                  # 质量评估
│   └── i18n/                     # 国际化
├── frontend/                     # React 前端应用
│   ├── src/
│   │   ├── components/           # 可复用 UI 组件
│   │   ├── pages/                # 页面级组件
│   │   ├── hooks/                # 自定义 React hooks
│   │   ├── stores/               # Zustand 状态管理
│   │   ├── services/             # API 客户端函数
│   │   └── types/                # TypeScript 类型定义
│   └── e2e/                      # Playwright E2E 测试
├── tests/                        # 后端测试套件
├── alembic/                      # 数据库迁移脚本
├── scripts/                      # 实用工具和部署脚本
├── docs/                         # 文档
├── .kiro/                        # Kiro IDE 配置和规范
│   ├── specs/                    # 功能规范
│   ├── steering/                 # 开发规范
│   └── piv-methodology/          # PIV 方法论文档
├── .claude/                      # Claude 命令和参考
│   ├── commands/                 # 自定义命令
│   └── reference/                # 最佳实践文档
└── docker-compose*.yml           # 容器编排
```

## 常用命令

### 开发设置
```bash
# 后端设置
pip install -r requirements.txt
python main.py  # 初始化系统
uvicorn src.app:app --reload  # 启动 API 服务器

# 前端设置
cd frontend
npm install
npm run dev  # 开发服务器

# 数据库操作
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Docker 操作
```bash
# 完整栈启动
docker-compose up -d
./start-fullstack.sh  # 替代启动脚本

# 单个服务
docker-compose up -d postgres redis neo4j label-studio
docker-compose logs -f superinsight-api

# 健康检查
curl http://localhost:8000/health
curl http://localhost:8000/system/status
```

### 测试
```bash
# 后端测试
pytest tests/ -v --cov=src
pytest --cov=src --cov-report=html

# 前端测试
cd frontend
npm run test  # Vitest 单元测试
npm run test:e2e  # Playwright E2E 测试
npm run test:coverage  # 覆盖率报告
```

### 代码质量
```bash
# Python 格式化和检查
black src/ tests/
isort src/ tests/
mypy src/

# 前端检查和类型检查
cd frontend
npm run lint
npm run typecheck
npx tsc --noEmit
```

## Claude 命令

用于辅助开发工作流的斜杠命令。本应用使用的 AI 编码工作流遵循 PIV（Prime、Implement、Validate）循环：

### 规划与执行
| 命令 | 描述 |
|------|------|
| `/core_piv_loop:prime` | 加载项目上下文和代码库理解 |
| `/core_piv_loop:plan-feature` | 通过代码库分析创建全面的实施计划 |
| `/core_piv_loop:execute` | 逐步执行实施计划 |

### 验证
| 命令 | 描述 |
|------|------|
| `/validation:validate` | 运行完整验证：测试、代码检查、覆盖率、前端构建 |
| `/validation:code-review` | 对已更改文件进行技术代码审查 |
| `/validation:code-review-fix` | 修复代码审查中发现的问题 |
| `/validation:execution-report` | 功能实施后生成报告 |
| `/validation:system-review` | 分析实施与计划的差异以改进流程 |

### Bug 修复
| 命令 | 描述 |
|------|------|
| `/github_bug_fix:rca` | 为 GitHub 问题创建根本原因分析文档 |
| `/github_bug_fix:implement-fix` | 根据 RCA 文档实施修复 |

### 杂项
| 命令 | 描述 |
|------|------|
| `/commit` | 创建带有适当标签（feat、fix、docs 等）的原子提交 |
| `/init-project` | 安装依赖项，启动后端和前端服务器 |
| `/create-prd` | 根据对话生成产品需求文档 |

## 代码约定

### 后端 (Python)
- 所有请求/响应模式使用 Pydantic 模型
- 分离模式：`UserCreate`、`UserUpdate`、`UserResponse`
- 使用 `Depends()` 进行数据库会话和验证
- 在 SQLite 中将日期存储为 ISO-8601 TEXT（`YYYY-MM-DD`）
- 通过 PRAGMA 在每个连接上启用外键

### 前端 (React)
- `src/features/` 下基于功能的文件夹结构
- 所有 API 调用使用 TanStack Query（不使用原始 useEffect 获取）
- Tailwind CSS 样式 - 无单独的 CSS 文件
- 使用 react-hook-form + Zod 验证的表单

### API 设计
- `/api/` 下的 RESTful 端点
- POST 返回 201，DELETE 返回 204
- 使用带有描述性错误代码的 HTTPException

## 日志

所有日志使用 **structlog**。在应用启动时配置：
- 开发：带颜色的漂亮控制台输出
- 生产：用于日志聚合的 JSON 格式

```python
import structlog
logger = structlog.get_logger()

# 为所有后续日志绑定上下文
structlog.contextvars.bind_contextvars(request_id=request_id)

# 使用结构化数据记录
logger.info("Habit completed", habit_id=1, streak=5)
```

请求日志中间件自动记录：
- 请求 ID、方法、路径
- 响应状态码和持续时间

## 数据库

### PostgreSQL
主数据库，支持 JSONB 和高级查询。

### Redis
缓存和会话存储。

### Neo4j
知识图谱关系。

### SQLite (仅用于测试)
使用 WAL 模式。始终在连接上运行这些 PRAGMA：
```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
```

## 测试策略

### 测试金字塔
- **70% 单元测试**：纯函数、业务逻辑、验证器
- **20% 集成测试**：带真实数据库的 API 端点
- **10% E2E 测试**：使用 Playwright 的关键用户旅程

### 单元测试
- 测试业务逻辑、日期工具、验证器
- 模拟外部依赖
- 快速执行（毫秒级）

### 集成测试
- 使用内存 SQLite 测试 API 端点
- 使用 `TestClient` 和依赖覆盖
- 测试成功和错误情况

### E2E 测试
- 使用 Playwright 和页面对象模型
- 测试关键流程：创建任务、完成任务、查看日历
- 运行视觉回归测试以确保 UI 一致性

### 测试组织
```
tests/
├── conftest.py              # 共享 fixtures
├── unit/
│   └── test_logic.py        # 业务逻辑测试
├── integration/
│   └── test_api.py          # 带真实数据库的 API 测试
└── e2e/
    ├── pages/               # 页面对象
    └── workflows.spec.js    # 用户旅程测试
```

## 参考文档

在特定领域工作时阅读这些文档：

| 文档 | 何时阅读 |
|------|---------|
| `.kiro/steering/tech.md` | 技术栈、构建系统 |
| `.kiro/steering/structure.md` | 项目结构、组织 |
| `.kiro/steering/product.md` | 产品功能、目标用户 |
| `.kiro/steering/doc-first-workflow.md` | 文档优先开发流程 |
| `.kiro/steering/async-sync-safety.md` | FastAPI 异步安全规则 |
| `.kiro/steering/typescript-export-rules.md` | TypeScript 导出规范 |
| `.kiro/steering/piv-methodology-integration.md` | PIV 方法论集成 |
| `.claude/reference/fastapi-best-practices.md` | 构建 API 端点、Pydantic 模式 |
| `.claude/reference/react-frontend-best-practices.md` | 组件、hooks、状态管理 |
| `.claude/reference/testing-and-logging.md` | structlog 设置、测试模式 |

## 环境配置

关键环境变量在 `.env` 中定义（从 `.env.example` 复制）：
- 数据库连接（PostgreSQL、Redis、Neo4j）
- Label Studio 集成设置
- AI 服务 API 密钥（Ollama、HuggingFace、中文 LLM）
- 安全和加密密钥
- 部署特定设置（TCB、Docker）

## 部署模式

1. **本地开发**：直接 Python + Node.js 执行
2. **Docker Compose**：完整容器化栈
3. **腾讯云 TCB**：使用 `tcb framework deploy` 的云原生部署

## PIV 方法论

本项目使用 PIV (Prime-Implement-Validate) 方法论进行系统化开发：

1. **Prime**: 了解项目上下文和代码库
2. **Plan**: 创建详细的实施计划
3. **Execute**: 按计划实施功能
4. **Validate**: 全面验证实施

详细信息请参阅：
- `.kiro/PIV_QUICK_START.md` - 快速开始指南
- `.kiro/steering/piv-methodology-integration.md` - 完整集成指南
- `.kiro/piv-methodology/` - PIV 命令和参考

## 快速开始

```bash
# 1. 克隆并设置后端
cd backend
pip install -r requirements.txt
python main.py  # 初始化
uvicorn src.app:app --reload

# 2. 设置前端（新终端）
cd frontend
npm install
npm run dev

# 3. 访问应用
# 前端: http://localhost:5173
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

## 核心原则

1. **文档优先** - 代码前更新文档
2. **类型安全** - 使用 TypeScript 和 Pydantic
3. **测试驱动** - 高测试覆盖率
4. **异步安全** - 遵循 FastAPI 异步模式
5. **安全第一** - 企业级安全控制
6. **可观测性** - 全面的日志和监控
