# PIV 方法论集成指南

**Version**: 1.0  
**Status**: ✅ Active  
**Last Updated**: 2026-01-19  
**Priority**: HIGH  
**来源**: [habit-tracker](https://github.com/coleam00/habit-tracker)

## 概述

PIV (Prime-Implement-Validate) 是一个系统化的 AI 辅助开发循环，旨在提高开发效率和代码质量。本文档说明如何在 SuperInsight 项目中应用 PIV 方法论。

## PIV 循环图

```
┌─────────────────────────────────────────────────────────┐
│                     PIV 循环                             │
│                                                          │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐     │
│  │  Prime   │ ───► │Implement │ ───► │ Validate │     │
│  │  准备    │      │  实现    │      │  验证    │     │
│  └──────────┘      └──────────┘      └──────────┘     │
│       │                                      │          │
│       │                                      │          │
│       └──────────────────────────────────────┘          │
│                   反馈循环                               │
└─────────────────────────────────────────────────────────┘
```

## 三个阶段详解

### 阶段 1: Prime (准备)

**目标**: 建立对代码库的全面理解

**步骤**:
1. 分析项目结构
2. 阅读核心文档
3. 识别关键文件
4. 理解当前状态

**输出**: 项目概览报告

**参考文档**: `.kiro/piv-methodology/commands/core_piv_loop/prime.md`

### 阶段 2: Plan Feature (规划功能)

**目标**: 将功能需求转化为详细的实现计划

**步骤**:
1. **功能理解** - 深入分析功能需求
2. **代码库情报收集** - 识别模式、依赖、测试方法
3. **外部研究** - 查找文档、最佳实践
4. **战略思考** - 设计决策、边界情况
5. **生成计划** - 创建详细的实现计划

**输出**: `.agents/plans/{feature-name}.md`

**参考文档**: `.kiro/piv-methodology/commands/core_piv_loop/plan-feature.md`

### 阶段 3: Execute (执行)

**目标**: 按计划实现功能

**步骤**:
1. 阅读并理解计划
2. 按顺序执行任务
3. 实现测试策略
4. 运行验证命令
5. 最终验证

**输出**: 完成的功能实现

**参考文档**: `.kiro/piv-methodology/commands/core_piv_loop/execute.md`

### 阶段 4: Validate (验证)

**目标**: 确保代码质量和功能正确性

**验证层级**:
1. **语法和风格** - Linting, formatting
2. **单元测试** - 组件级测试
3. **集成测试** - 端到端测试
4. **手动验证** - 功能测试
5. **额外验证** - 性能、安全等

**参考文档**: `.kiro/piv-methodology/commands/validation/validate.md`

## 在 SuperInsight 中的应用

### 项目结构映射

| PIV 概念 | SuperInsight 位置 |
|---------|------------------|
| Plans | `.agents/plans/` 或 `.kiro/specs/{feature}/tasks.md` |
| Reference Docs | `.kiro/steering/` |
| Core Documentation | `README.md`, `docs/` |
| Test Files | `tests/`, `frontend/src/**/*.test.tsx` |

### 工作流程示例

#### 场景: 添加新的 API 端点

**1. Prime (准备)**
```bash
# 分析项目结构
git ls-files | grep -E "(api|routers)" | head -20

# 阅读相关文档
cat .kiro/steering/tech.md
cat .kiro/steering/structure.md
cat .kiro/steering/async-sync-safety.md
```

**2. Plan Feature (规划)**
```markdown
# 创建计划文件
.agents/plans/add-user-profile-api.md

## 功能描述
添加用户个人资料 API 端点

## 代码库参考
- `src/api/auth.py` (lines 15-45) - 认证模式
- `src/schemas/user.py` (lines 10-30) - 用户模型
- `tests/test_api_auth.py` - 测试模式

## 实现步骤
1. CREATE src/schemas/profile.py - 定义 ProfileSchema
2. UPDATE src/api/users.py - 添加 GET /api/users/{id}/profile
3. CREATE tests/test_api_profile.py - 单元测试
4. VALIDATE: npx tsc --noEmit (前端)
5. VALIDATE: pytest tests/test_api_profile.py -v
```

**3. Execute (执行)**
```bash
# 按计划执行每个任务
# 每完成一个任务，运行验证命令
```

**4. Validate (验证)**
```bash
# 后端验证
cd backend
pytest tests/ -v --cov=src
mypy src/

# 前端验证
cd frontend
npx tsc --noEmit
npm run test
npm run lint
```

## 与现有工作流的集成

### 与 Doc-First 工作流的关系

PIV 方法论与我们的 Doc-First 工作流互补：

| 阶段 | Doc-First | PIV |
|-----|-----------|-----|
| 需求 | requirements.md | Prime + Feature Understanding |
| 设计 | design.md | Plan Feature (Pattern Recognition) |
| 任务 | tasks.md | Plan Feature (Step-by-Step Tasks) |
| 实现 | 代码 | Execute |
| 验证 | 测试 | Validate |

**建议整合方式**:
1. 使用 Doc-First 创建 requirements.md 和 design.md
2. 使用 PIV Plan Feature 创建详细的 tasks.md
3. 使用 PIV Execute 执行任务
4. 使用 PIV Validate 验证实现

### 与 Spec 工作流的关系

```
.kiro/specs/{feature}/
├── requirements.md    ← Doc-First 创建
├── design.md          ← Doc-First 创建
├── tasks.md           ← PIV Plan Feature 创建
└── implementation/    ← PIV Execute 执行
```

## 最佳实践

### 1. 计划文件命名

使用 kebab-case 命名:
- ✅ `add-user-authentication.md`
- ✅ `implement-search-api.md`
- ✅ `refactor-database-layer.md`
- ❌ `AddUserAuth.md`
- ❌ `search_api.md`

### 2. 任务粒度

每个任务应该:
- 独立可测试
- 5-15 分钟完成
- 有明确的验证命令

**示例**:
```markdown
### CREATE src/schemas/profile.py
- **IMPLEMENT**: ProfileSchema with name, email, avatar fields
- **PATTERN**: Mirror UserSchema from src/schemas/user.py:15-30
- **IMPORTS**: from pydantic import BaseModel, EmailStr
- **VALIDATE**: `python -c "from src.schemas.profile import ProfileSchema; print('OK')"`
```

### 3. 验证命令

每个任务必须有可执行的验证命令:
- ✅ `pytest tests/test_profile.py::test_create_profile -v`
- ✅ `npx tsc --noEmit`
- ✅ `curl -X GET http://localhost:8000/api/profile/1`
- ❌ "测试一下"
- ❌ "确保正常工作"

### 4. 模式引用

引用现有模式时，包含具体位置:
- ✅ `src/api/auth.py:45-60 - JWT token generation pattern`
- ✅ `frontend/src/hooks/useAuth.ts:20-35 - TanStack Query pattern`
- ❌ "参考 auth 文件"
- ❌ "使用类似的模式"

## 工具和脚本

### 创建计划模板

```bash
# 创建新的功能计划
cat > .agents/plans/my-feature.md << 'EOF'
# Feature: My Feature

## Feature Description
[描述功能]

## User Story
As a [user type]
I want to [action]
So that [benefit]

## CONTEXT REFERENCES
### Relevant Codebase Files
- [列出相关文件]

### Patterns to Follow
- [列出模式]

## STEP-BY-STEP TASKS
[详细任务列表]

## VALIDATION COMMANDS
[验证命令]
EOF
```

### 执行验证

```bash
# 创建验证脚本
cat > scripts/validate-all.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Backend Validation ==="
cd backend
pytest tests/ -v --cov=src
mypy src/

echo "=== Frontend Validation ==="
cd ../frontend
npx tsc --noEmit
npm run test
npm run lint

echo "=== All validations passed! ==="
EOF

chmod +x scripts/validate-all.sh
```

## 参考资源

### 内部文档
- `.kiro/piv-methodology/commands/` - PIV 命令文档
- `.kiro/piv-methodology/reference/` - 最佳实践参考
- `.kiro/steering/doc-first-workflow.md` - Doc-First 工作流
- `.kiro/steering/typescript-export-rules.md` - TypeScript 规范

### 外部资源
- [habit-tracker GitHub](https://github.com/coleam00/habit-tracker)
- [PIV Loop Diagram](https://github.com/coleam00/habit-tracker/blob/main/PIVLoopDiagram.png)
- [Top 1% Agentic Engineering](https://github.com/coleam00/habit-tracker/blob/main/Top1%25AgenticEngineering.png)

## 常见问题

### Q: PIV 和 Doc-First 有什么区别？

**A**: Doc-First 关注需求和设计文档，PIV 关注实现计划和执行。两者互补：
- Doc-First: 定义"做什么"和"为什么"
- PIV: 定义"怎么做"和"如何验证"

### Q: 是否每个功能都需要创建计划文件？

**A**: 建议对中等及以上复杂度的功能创建计划。简单的 bug 修复可以直接实现。

### Q: 计划文件应该多详细？

**A**: 详细到另一个开发者（或 AI）可以不需要额外上下文就能实现。包含：
- 具体的文件路径和行号
- 代码模式示例
- 可执行的验证命令
- 边界情况和注意事项

### Q: 如何处理计划执行中的偏差？

**A**: 
1. 记录偏差原因
2. 更新计划文件
3. 继续执行
4. 在验证阶段总结经验教训

## 成功指标

### 计划质量指标
- ✅ 一次性实现成功率 > 80%
- ✅ 每个任务都有验证命令
- ✅ 通过"无先验知识测试"（新人可以执行）

### 执行质量指标
- ✅ 所有验证命令通过
- ✅ 测试覆盖率 > 80%
- ✅ 无 linting 或类型错误
- ✅ 符合项目规范

---

**此方法论为推荐性方法论，鼓励在复杂功能开发中使用。**
