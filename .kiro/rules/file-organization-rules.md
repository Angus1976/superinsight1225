---
inclusion: manual
---

# 文件组织规范

**Version**: 2.0  
**Last Updated**: 2026-02-04  
**Priority**: HIGH  
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则（必读）

**分类优先 > 结构清晰 > 一致性**

所有文件按功能分类，目录结构反映项目架构。

---

## 🎯 5 条核心规则（日常使用）

1. **源代码** - `src/` (后端) 或 `frontend/src/` (前端)
2. **测试** - `tests/` 目录
3. **文档** - `文档/` 目录
4. **脚本** - `scripts/` 目录
5. **根目录** - 只放配置文件，不放源代码

---

## ⚡ 快速参考（80% 场景够用）

### 文件分类表

| 类型 | 位置 | 说明 |
|------|------|------|
| 后端源代码 | `src/` | 所有 Python 代码 |
| 前端源代码 | `frontend/src/` | 所有 TypeScript/React 代码 |
| 测试 | `tests/` | 单元/集成/API 测试 |
| 文档 | `文档/` | 项目文档 |
| 规范 | `.kiro/steering/` | 开发规范 |
| Spec | `.kiro/specs/{feature}/` | requirements.md + design.md + tasks.md |
| 脚本 | `scripts/` | 自动化脚本 |
| 配置 | `config/` | 应用配置 |

### 根目录规则

**✅ 允许**：
- 配置文件：`.env*`, `docker-compose*.yml`, `Dockerfile*`, `alembic.ini`
- 项目文件：`README.md`, `requirements.txt`, `package.json`, `.gitignore`

**❌ 禁止**：
- 源代码：`.py`, `.ts`, `.tsx`
- 测试文件：`test_*.py`, `*.test.ts`
- 文档：`.md`（除了 README.md）
- 脚本：`.sh`

### 快速检查清单

创建新文件时：
- [ ] 确定文件类型
- [ ] 选择合适的目录
- [ ] 不在根目录创建源代码/测试/文档/脚本

---

## 📚 详细规则（按需查阅）

<details>
<summary><b>命名规范</b>（点击展开）</summary>

- **Python**: `snake_case.py`
- **TypeScript**: `PascalCase.tsx` (组件), `camelCase.ts` (工具)
- **测试**: `test_*.py` 或 `*.test.tsx`

</details>

<details>
<summary><b>目录结构详解</b>（点击展开）</summary>

### 后端 (`src/`)
- `src/api/` - FastAPI 路由
- `src/models/` - 数据库模型
- `src/schemas/` - Pydantic schemas
- `src/services/` - 业务逻辑

### 前端 (`frontend/src/`)
- `components/` - UI 组件
- `pages/` - 页面组件
- `hooks/` - 自定义 hooks
- `stores/` - 状态管理
- `services/` - API 客户端

</details>

---

## 🔗 相关资源

- **项目结构**：`.kiro/steering/structure.md`
- **文档规范**：`.kiro/steering/documentation-minimalism-rules.md`

---

**此规范为强制性规范。违反规范将导致 PR 被拒绝。**
