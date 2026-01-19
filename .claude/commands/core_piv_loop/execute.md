---
description: 逐步执行实施计划 | Execute an implementation plan step by step
argument-hint: [计划文件路径 | path-to-plan]
---

# Execute: 执行实施计划 | Implement from Plan

## 要执行的计划 | Plan to Execute

读取计划文件: `$ARGUMENTS`

## 执行说明 | Execution Instructions

### 1. 阅读并理解 | Read and Understand

- 仔细阅读整个计划
- 理解所有任务及其依赖关系
- 注意要运行的验证命令
- 审查测试策略

### 2. 按顺序执行任务 | Execute Tasks in Order

对于"逐步任务"中的每个任务:

#### a. 导航到任务
- 识别所需的文件和操作
- 如果修改，阅读现有的相关文件

#### b. 实施任务
- 严格按照详细规范执行
- 保持与现有代码模式的一致性
- 包含适当的类型提示和文档
- 在适当的地方添加结构化日志

#### c. 边做边验证
- 每次文件更改后，检查语法
- 确保导入正确
- 验证类型定义正确

**SuperInsight 特定注意事项**:
- 遵循 `.kiro/steering/async-sync-safety.md` 的异步规则
- 遵循 `.kiro/steering/typescript-export-rules.md` 的 TypeScript 规范
- 使用 structlog 进行日志记录
- 为所有 API 调用添加泛型类型

### 3. 实施测试策略 | Implement Testing Strategy

完成实施任务后:

- 创建计划中指定的所有测试文件
- 实施提到的所有测试用例
- 遵循概述的测试方法
- 确保测试覆盖边界情况

**测试要求**:
- 后端: pytest, 覆盖率 >= 80%
- 前端: Vitest, 覆盖率 >= 80%
- E2E: Playwright（如适用）

### 4. 运行验证命令 | Run Validation Commands

按顺序执行计划中的所有验证命令:

**后端验证**:
```bash
# 格式化和类型检查
black --check src/ tests/
isort --check src/ tests/
mypy src/

# 运行测试
pytest tests/ -v --cov=src
```

**前端验证**:
```bash
cd frontend

# TypeScript 检查
npx tsc --noEmit

# 测试
npm run test

# Linting
npm run lint

# 构建
npm run build
```

如果任何命令失败:
- 修复问题
- 重新运行命令
- 仅在通过时继续

### 5. 最终验证 | Final Verification

完成前:

- ✅ 计划中的所有任务已完成
- ✅ 所有测试已创建并通过
- ✅ 所有验证命令通过
- ✅ 代码遵循项目约定
- ✅ 文档已添加/更新（如需要）
- ✅ 遵循所有 `.kiro/steering/` 规范

## 输出报告 | Output Report

提供摘要:

### 已完成的任务 | Completed Tasks
- 已完成任务列表
- 已创建的文件（带路径）
- 已修改的文件（带路径）

### 已添加的测试 | Tests Added
- 已创建的测试文件
- 已实施的测试用例
- 测试结果

### 验证结果 | Validation Results
```bash
# 每个验证命令的输出
```

### 准备提交 | Ready for Commit
- 确认所有更改已完成
- 确认所有验证通过
- 准备好使用 `/commit` 命令

## 注意事项 | Notes

- 如果遇到计划中未解决的问题，记录下来
- 如果需要偏离计划，解释原因
- 如果测试失败，修复实施直到通过
- 不要跳过验证步骤
- 特别注意 SuperInsight 的异步安全和 TypeScript 规范
