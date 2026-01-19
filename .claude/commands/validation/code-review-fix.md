---
description: 修复代码审查中发现的问题 / Process to fix bugs found in manual/AI code review
---

# 代码审查问题修复 / Code Review Fix

我执行了代码审查，发现了以下问题：

**代码审查结果（文件或问题描述）**: $1

**修复范围**: $2

请逐一修复这些问题。如果代码审查结果是一个文件，请先完整阅读该文件以理解所有问题。

## 修复流程 / Fix Process

### 1. 理解问题 / Understand Issues

对于每个问题：
1. **解释问题** - 说明哪里出错了，为什么是问题
2. **展示修复** - 显示修复前后的代码对比
3. **验证修复** - 创建并运行相关测试

### 2. SuperInsight 特定检查 / SuperInsight-Specific Checks

修复时请特别注意以下规范：

**后端 Python 代码**:
- 遵循 `.kiro/steering/async-sync-safety.md` 异步安全规则
- 不要在异步上下文中使用 `threading.Lock`
- 使用 `asyncio.Lock()` 替代
- 确保数据库操作使用异步方式

**前端 TypeScript 代码**:
- 遵循 `.kiro/steering/typescript-export-rules.md` 导出规范
- 确保 index.ts 导出的成员确实存在
- API 调用必须指定泛型类型
- Hook 命名遵循约定（如 `useXxxState`）

### 3. 严重程度分类 / Severity Classification

| 级别 | 描述 | 处理方式 |
|------|------|----------|
| 🔴 Critical | 安全漏洞、数据丢失风险 | 立即修复，阻塞发布 |
| 🟠 High | 功能错误、性能问题 | 优先修复 |
| 🟡 Medium | 代码质量、可维护性 | 计划修复 |
| 🟢 Low | 代码风格、文档 | 可选修复 |

### 4. 修复验证 / Fix Validation

每个修复完成后，运行相应验证：

**后端修复**:
```bash
# 代码格式化
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# 运行相关测试
pytest tests/test_xxx.py -v
```

**前端修复**:
```bash
cd frontend

# TypeScript 检查
npx tsc --noEmit

# 代码检查
npm run lint

# 运行相关测试
npm run test -- --run
```

### 5. 完成所有修复后 / After All Fixes

运行完整验证命令（参见 commands/validation/validate.md）：

```bash
# 后端完整验证
pytest tests/ -v --cov=src
mypy src/

# 前端完整验证
cd frontend
npx tsc --noEmit
npm run test -- --run
npm run lint
```

## 输出报告 / Output Report

修复完成后，提供以下摘要：

```markdown
## 代码审查修复报告

### 修复的问题
1. [问题描述] - ✅ 已修复
   - 文件: [文件路径]
   - 修改: [简要说明]

### 验证结果
- 类型检查: ✅ 通过
- 单元测试: ✅ X 个通过
- 代码检查: ✅ 无警告

### 建议
- [任何后续建议]
```

## 参考文档 / Reference Documents

- `.kiro/steering/async-sync-safety.md` - 异步安全规则
- `.kiro/steering/typescript-export-rules.md` - TypeScript 导出规范
- `.kiro/steering/doc-first-workflow.md` - 文档优先工作流
- `CLAUDE.md` - 项目配置