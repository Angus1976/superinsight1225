---
description: 加载项目上下文和代码库理解 | Prime agent with codebase understanding
---

# Prime: 加载项目上下文 | Load Project Context

## 目标 | Objective

通过分析结构、文档和关键文件，建立对 SuperInsight AI 平台代码库的全面理解。

Build comprehensive understanding of the SuperInsight AI platform codebase by analyzing structure, documentation, and key files.

## 执行过程 | Process

### 1. 分析项目结构 | Analyze Project Structure

列出所有跟踪的文件：
```bash
git ls-files | head -100
```

显示目录结构：
```bash
# macOS/Linux
tree -L 3 -I 'node_modules|__pycache__|.git|dist|build|venv|data' || ls -R | head -100

# 或查看主要目录
ls -la
ls -la src/
ls -la frontend/src/
```

### 2. 阅读核心文档 | Read Core Documentation

**必读文档**:
- `CLAUDE.md` - 项目配置和 Claude 命令说明
- `README.md` - 项目概述和快速开始
- `.kiro/steering/tech.md` - 技术栈和构建系统
- `.kiro/steering/structure.md` - 项目结构和组织
- `.kiro/steering/product.md` - 产品功能和目标用户
- `.kiro/steering/doc-first-workflow.md` - 文档优先开发流程
- `.kiro/steering/async-sync-safety.md` - FastAPI 异步安全规则
- `.kiro/steering/typescript-export-rules.md` - TypeScript 导出规范

### 3. 识别关键文件 | Identify Key Files

基于 SuperInsight 项目结构，识别并阅读：

**后端关键文件**:
- `src/app.py` - FastAPI 应用入口点
- `src/database/connection.py` - 数据库连接配置
- `src/models/` - SQLAlchemy 数据库模型
- `src/schemas/` - Pydantic 请求/响应模式
- `src/api/` - API 路由和端点
- `src/security/` - 认证、授权、审计
- `requirements.txt` - Python 依赖
- `alembic/` - 数据库迁移

**前端关键文件**:
- `frontend/src/App.tsx` - React 应用入口
- `frontend/src/router/routes.tsx` - 路由配置
- `frontend/src/services/api/` - API 客户端
- `frontend/src/stores/` - Zustand 状态管理
- `frontend/src/hooks/` - 自定义 React hooks
- `frontend/package.json` - 前端依赖
- `frontend/tsconfig.json` - TypeScript 配置
- `frontend/vite.config.ts` - Vite 构建配置

**配置文件**:
- `.env.example` - 环境变量模板
- `docker-compose.yml` - Docker 编排配置
- `alembic.ini` - 数据库迁移配置

### 4. 理解当前状态 | Understand Current State

检查最近活动：
```bash
git log -10 --oneline --graph
```

检查当前分支和状态：
```bash
git status
git branch -a
```

检查未提交的更改：
```bash
git diff --stat
```

## 输出报告 | Output Report

提供简洁的总结，包含以下内容：

### 项目概览 | Project Overview
- **应用类型**: SuperInsight AI 数据治理与标注平台
- **核心功能**: 
  - 安全数据提取
  - AI 预标注（多 LLM 集成）
  - 人机协作标注
  - 质量管理（Ragas 框架）
  - 计费结算
  - 安全合规
- **主要技术**:
  - 后端: FastAPI + Python 3.11+
  - 前端: React 19 + TypeScript + Vite
  - 数据库: PostgreSQL + Redis + Neo4j
  - 标注引擎: Label Studio
- **当前版本/状态**: [从 git 或 package.json 获取]

### 架构 | Architecture
- **整体结构**: 
  - 前后端分离架构
  - 微服务化设计（API、标注、质量、安全等模块）
  - Docker 容器化部署
- **关键架构模式**:
  - RESTful API 设计
  - Repository 模式（数据访问层）
  - Service 层（业务逻辑）
  - Middleware（认证、日志、监控）
  - 异步处理（Celery 任务队列）
- **重要目录及用途**:
  - `src/` - 后端源代码
  - `frontend/` - 前端 React 应用
  - `tests/` - 后端测试
  - `alembic/` - 数据库迁移
  - `docs/` - 文档
  - `.kiro/` - Kiro IDE 配置和规范
  - `scripts/` - 实用脚本

### 技术栈 | Tech Stack

**后端**:
- 语言: Python 3.11+
- 框架: FastAPI 0.100+
- ORM: SQLAlchemy 2.0+
- 数据库: PostgreSQL 15+, Redis 7+, Neo4j 5+
- 任务队列: Celery
- 测试: pytest
- 代码质量: black, isort, mypy

**前端**:
- 语言: TypeScript
- 框架: React 19
- 构建工具: Vite 7+
- UI 库: Ant Design 5+
- 状态管理: Zustand
- 数据获取: TanStack Query
- 路由: React Router DOM 7+
- 测试: Vitest, Playwright

**核心集成**:
- Label Studio (标注引擎)
- Presidio (数据脱敏)
- Ragas (质量评估)
- Prometheus + Grafana (监控)

### 核心原则 | Core Principles

**代码风格和约定**:
- Python: PEP 8, black 格式化, type hints
- TypeScript: 严格模式, ESLint
- 命名: snake_case (Python), camelCase (TypeScript)
- 导入: 绝对导入优先

**文档标准**:
- 文档优先开发（Doc-First Workflow）
- 每个功能需要 requirements.md, design.md, tasks.md
- API 文档自动生成（FastAPI Swagger）

**测试方法**:
- 测试金字塔: 70% 单元测试, 20% 集成测试, 10% E2E
- 覆盖率目标: >= 80%
- 测试框架: pytest (后端), Vitest (前端)

**安全规范**:
- 异步安全: 遵循 `.kiro/steering/async-sync-safety.md`
- 数据脱敏: 自动 PII 检测和脱敏
- 审计日志: 所有关键操作记录
- 权限控制: RBAC + 细粒度权限

### 当前状态 | Current State
- **活跃分支**: [从 git branch 获取]
- **最近更改**: [从 git log 获取最近的提交]
- **开发重点**: [分析最近提交的模式]
- **立即观察**:
  - 检查是否有未提交的更改
  - 检查是否有待解决的冲突
  - 检查是否有待修复的 TODO/FIXME

### 关键发现 | Key Findings
- **优势**: [列出项目的优势]
- **需要注意**: [列出需要特别注意的地方]
- **建议**: [提供改进建议]

**使用清晰的标题和要点使此总结易于浏览。**

## 注意事项 | Notes

- 这是 PIV 循环的第一步，为后续的 Plan 和 Execute 阶段打基础
- 重点理解项目的整体架构和约定，而不是深入每个细节
- 如果发现文档缺失或过时，记录下来以便后续更新
- 特别关注 `.kiro/steering/` 中的开发规范
