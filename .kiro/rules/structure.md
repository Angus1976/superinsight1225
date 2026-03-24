---
inclusion: manual
---

# 项目结构与组织

**类型**: 项目信息  
**优先级**: MEDIUM  
**加载方式**: 手动加载（按需引用）

---

## 快速导航

| 目录 | 用途 |
|------|------|
| `src/` | 后端源代码（Python/FastAPI） |
| `frontend/` | 前端应用（React/TypeScript） |
| `tests/` | 测试套件 |
| `.kiro/` | Kiro 配置和 Spec |
| `scripts/` | 工具和部署脚本 |
| `文档/` | 项目文档 |

---

## 后端结构 (`src/`)

### 核心组件
- `app.py` - FastAPI 主应用
- `config/` - 配置管理
- `database/` - 数据库连接和模型
- `system/` - 系统集成、监控、日志

### 功能模块（领域驱动设计）
- `api/` - API 路由
- `models/` - 数据库模型
- `schemas/` - Pydantic schemas
- `ai/` - AI 模型集成
- `quality/` - 质量评估
- `security/` - 认证授权审计
- `i18n/` - 国际化

### 专业服务
- `knowledge_graph/` - Neo4j 图数据库
- `sync/` - 数据同步
- `monitoring/` - 系统监控
- `desensitization/` - 数据脱敏

---

## 前端结构 (`frontend/`)

```
src/
├── components/    # UI 组件
├── pages/         # 页面组件
├── hooks/         # 自定义 hooks
├── stores/        # Zustand 状态管理
├── services/      # API 客户端
├── utils/         # 工具函数
└── types/         # TypeScript 类型
```

---

## 架构模式

### API 组织
- RESTful 端点按领域组织 (`/api/v1/{domain}`)
- 统一错误处理和响应格式
- FastAPI/OpenAPI 自动文档

### 数据库设计
- DB 连接池配置在 `src/config/settings.py`（读 `DATABASE_POOL_SIZE` 等环境变量），实际连接在 `src/database/connection.py`。`src/core/database.py` 是旧路径，勿改
- 多租户架构，租户隔离
- 关键操作审计日志
- JSONB 字段支持灵活 schema
- Neo4j 图数据库存储知识关系

### 安全架构
- RBAC 细粒度权限控制
- 自动数据脱敏中间件
- 完整审计追踪
- 实时安全监控

### 质量与监控
- Ragas 语义质量评估
- Prometheus 指标收集
- 多层级健康检查
- 业务指标追踪

---

## 开发约定

### 文件命名
- Python: `snake_case.py`
- TypeScript: `PascalCase.tsx` (组件), `camelCase.ts` (工具)
- 测试: `test_*.py` 或 `*.test.tsx`

### 模块组织
- 每个领域模块：`models.py`, `schemas.py`, `service.py`, `api.py`
- 共享工具：`src/utils/`
- 数据库模型：`src/models/`

### 导入约定
- 从 `src/` 根目录绝对导入
- 分组：标准库、第三方、本地模块
- 使用 `from src.module import specific_item` 模式