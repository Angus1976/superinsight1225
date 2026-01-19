---
description: 根据 RCA 文档实现 GitHub Issue 修复 / Implement fix from RCA document for GitHub issue
argument-hint: [github-issue-id]
allowed-tools: Read, Write, Edit, Bash(black:*), Bash(isort:*), Bash(mypy:*), Bash(pytest:*), Bash(npm:*), Bash(npx:*)
---

# 实现修复 / Implement Fix: GitHub Issue #$ARGUMENTS

## 前提条件 / Prerequisites

**此命令根据 RCA 文档实现 GitHub Issue 的修复:**
- 在具有 GitHub origin 的本地 Git 仓库中工作
- RCA 文档存在于 `docs/rca/issue-$ARGUMENTS.md`
- 已安装并认证 GitHub CLI（可选，用于状态更新）

## 要参考的 RCA 文档 / RCA Document to Reference

阅读 RCA: `docs/rca/issue-$ARGUMENTS.md`

**可选 - 查看 GitHub Issue 获取上下文:**
```bash
gh issue view $ARGUMENTS
```

## 实现指令 / Implementation Instructions

### 1. 阅读并理解 RCA / Read and Understand RCA

- 完整阅读整个 RCA 文档
- 审查 GitHub Issue 详情 (Issue #$ARGUMENTS)
- 理解根本原因
- 审查提议的修复策略
- 记录所有要修改的文件
- 审查测试要求

### 2. 验证当前状态 / Verify Current State

在进行更改之前：
- 确认问题仍然存在
- 检查受影响文件的当前状态
- 审查这些文件的任何最近更改

### 3. 实现修复 / Implement the Fix

按照 RCA 的"提议的修复"部分：

**对于每个要修改的文件:**

#### a. 阅读现有文件
- 理解当前实现
- 定位 RCA 中提到的具体代码

#### b. 进行修复
- 按照 RCA 描述实现更改
- 严格遵循修复策略
- 保持代码风格和约定
- 如果修复不明显，添加注释

**SuperInsight 特定注意事项:**
- 遵循 `.kiro/steering/async-sync-safety.md` 异步安全规则
- 遵循 `.kiro/steering/typescript-export-rules.md` TypeScript 导出规范
- 确保多租户数据隔离
- 保持国际化 (i18n) 支持

#### c. 处理相关更改
- 更新受修复影响的任何相关代码
- 确保代码库的一致性
- 如需要，更新导入

### 4. 添加/更新测试 / Add/Update Tests

按照 RCA 的"测试要求"：

**创建测试用例:**
1. 验证修复解决了问题
2. 测试与 bug 相关的边界情况
3. 确保相关功能无回归
4. 测试引入的任何新代码路径

**测试文件位置:**
- 后端: `tests/test_xxx.py`
- 前端: `frontend/src/**/*.test.tsx`
- 遵循项目的测试结构
- 使用描述性测试名称

**测试实现:**
```python
# 后端 Python 测试
def test_issue_$ARGUMENTS_fix():
    """测试 Issue #$ARGUMENTS 已修复。"""
    # Arrange - 设置导致 bug 的场景
    # Act - 执行之前失败的代码
    # Assert - 验证现在正常工作
```

```typescript
// 前端 TypeScript 测试
describe('Issue #$ARGUMENTS Fix', () => {
  it('should resolve the reported issue', () => {
    // Arrange - 设置场景
    // Act - 执行操作
    // Assert - 验证结果
  });
});
```

### 5. 运行验证 / Run Validation

执行 RCA 中的验证命令：

**后端验证:**
```bash
# 代码格式化
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# 运行测试
pytest tests/test_xxx.py -v
```

**前端验证:**
```bash
cd frontend

# TypeScript 检查
npx tsc --noEmit

# 代码检查
npm run lint

# 运行测试
npm run test -- --run
```

**如果验证失败:**
- 修复问题
- 重新运行验证
- 在全部通过之前不要继续

### 6. 验证修复 / Verify Fix

**手动验证:**
- 按照 RCA 中的复现步骤
- 确认问题不再发生
- 测试边界情况
- 检查意外副作用

### 7. 更新文档 / Update Documentation

如需要：
- 更新代码注释
- 更新 API 文档
- 如果面向用户，更新 README
- 添加关于修复的说明
- 如果发现新模式，考虑更新 Steering 规则

## 输出报告 / Output Report

### 修复实现摘要 / Fix Implementation Summary

**GitHub Issue #$ARGUMENTS**: [简要标题]

**Issue URL**: [GitHub Issue URL]

**根本原因 / Root Cause** (来自 RCA):
[根本原因的一行摘要]

### 所做的更改 / Changes Made

**修改的文件 / Files Modified:**
1. **[文件路径]**
   - 更改: [更改了什么]
   - 行号: [行号]

2. **[文件路径]**
   - 更改: [更改了什么]
   - 行号: [行号]

### 添加的测试 / Tests Added

**创建/修改的测试文件:**
1. **[测试文件路径]**
   - 测试用例: [列出添加的测试函数]

**测试覆盖:**
- ✅ 修复验证测试
- ✅ 边界情况测试
- ✅ 回归预防测试

### 验证结果 / Validation Results

```bash
# 后端验证输出
[显示格式化结果]
[显示类型检查结果]
[显示测试结果 - 全部通过]

# 前端验证输出
[显示 TypeScript 检查结果]
[显示 lint 结果]
[显示测试结果 - 全部通过]
```

### 验证 / Verification

**手动测试:**
- ✅ 按照复现步骤 - 问题已解决
- ✅ 测试边界情况 - 全部通过
- ✅ 未引入新问题
- ✅ 原有功能保持正常

### 文件摘要 / Files Summary

**总更改:**
- X 个文件修改
- Y 个文件创建（测试）
- Z 行添加
- W 行删除

### 准备提交 / Ready for Commit

所有更改完成并验证。准备：
```bash
/commit
```

**建议的提交消息:**
```
fix(scope): 解决 GitHub Issue #$ARGUMENTS - [简要描述]

[修复了什么以及如何修复的摘要]

Fixes #$ARGUMENTS
```

**注意:** 在提交消息中使用 `Fixes #$ARGUMENTS` 将在合并到默认分支时自动关闭 GitHub Issue。

### 可选: 更新 GitHub Issue / Optional: Update GitHub Issue

**向 Issue 添加实现评论:**
```bash
gh issue comment $ARGUMENTS --body "修复已在提交 [commit-hash] 中实现。准备审查。"
```

**更新 Issue 标签（如需要）:**
```bash
gh issue edit $ARGUMENTS --add-label "fixed" --remove-label "bug"
```

**关闭 Issue（如果不使用提交消息自动关闭）:**
```bash
gh issue close $ARGUMENTS --comment "已修复并合并。"
```

## 注意事项 / Notes

- 如果 RCA 文档缺失或不完整，请先使用 `/github_bug_fix:rca $ARGUMENTS` 创建
- 如果发现 RCA 分析不正确，记录发现并更新 RCA
- 如果在实现过程中发现其他问题，记录它们以创建单独的 GitHub Issue 和 RCA
- 严格遵循项目编码标准
- 确保所有验证通过后再声明完成
- 提交消息 `Fixes #$ARGUMENTS` 将把提交链接到 GitHub Issue
