---
description: 为 GitHub Issue 分析并记录根本原因 / Analyze and document root cause for a GitHub issue
argument-hint: [github-issue-id]
---

# 根本原因分析 / Root Cause Analysis: GitHub Issue #$ARGUMENTS

## 目标 / Objective

调查本仓库的 GitHub Issue #$ARGUMENTS，识别根本原因，并记录发现以供后续实现。

**前提条件 / Prerequisites:**
- 在具有 GitHub origin 的本地 Git 仓库中工作
- 已安装并认证 GitHub CLI (`gh auth status`)
- 来自本仓库的有效 GitHub Issue ID

## 调查流程 / Investigation Process

### 1. 获取 GitHub Issue 详情 / Fetch GitHub Issue Details

**使用 GitHub CLI 获取 Issue 信息:**

```bash
gh issue view $ARGUMENTS
```

这将获取：
- Issue 标题和描述
- 报告者和创建日期
- 标签和状态
- 评论和讨论

### 2. 搜索代码库 / Search Codebase

**识别相关代码:**
- 搜索 Issue 中提到的组件
- 查找相关函数、类或模块
- 检查类似实现
- 查找模式或最近的更改

**SuperInsight 关键搜索位置:**
- `src/` - 后端 Python 代码
- `frontend/src/` - 前端 TypeScript 代码
- `src/api/` - API 路由
- `src/models/` - 数据库模型
- `src/security/` - 安全相关代码
- `frontend/src/hooks/` - React Hooks
- `frontend/src/services/` - API 服务

使用 grep/search 查找：
- Issue 中的错误消息
- 相关函数名
- 组件标识符

### 3. 审查最近历史 / Review Recent History

检查受影响区域的最近更改：
```bash
git log --oneline -20 -- [relevant-paths]
```

查找：
- 受影响代码的最近修改
- 相关的 bug 修复
- 可能引入问题的重构

### 4. 调查根本原因 / Investigate Root Cause

**分析代码以确定:**
- 实际的 bug 或问题是什么？
- 为什么会发生？
- 原始意图是什么？
- 这是逻辑错误、边界情况还是缺少验证？
- 是否有相关问题或症状？

**考虑 SuperInsight 特定问题:**
- 异步/同步混用（参见 `.kiro/steering/async-sync-safety.md`）
- TypeScript 类型问题（参见 `.kiro/steering/typescript-export-rules.md`）
- 多租户数据隔离问题
- Label Studio 集成问题
- 国际化 (i18n) 问题
- 权限和安全问题

**考虑:**
- 输入验证失败
- 未处理的边界情况
- 竞态条件或时序问题
- 错误的假设
- 缺少错误处理
- 组件间的集成问题

### 5. 评估影响 / Assess Impact

**确定:**
- 这个问题有多广泛？
- 哪些功能受影响？
- 是否有变通方案？
- 严重程度是什么？
- 是否可能导致数据损坏或安全问题？

### 6. 提出修复方案 / Propose Fix Approach

**设计解决方案:**
- 需要更改什么？
- 哪些文件将被修改？
- 修复策略是什么？
- 是否有替代方案？
- 需要什么测试？
- 是否有任何风险或副作用？

## 输出: 创建 RCA 文档 / Output: Create RCA Document

将分析保存为: `docs/rca/issue-$ARGUMENTS.md`

### 必需的 RCA 文档结构 / Required RCA Document Structure

```markdown
# 根本原因分析 / Root Cause Analysis: GitHub Issue #$ARGUMENTS

## Issue 摘要 / Issue Summary

- **GitHub Issue ID**: #$ARGUMENTS
- **Issue URL**: [GitHub Issue 链接]
- **标题 / Title**: [来自 GitHub 的 Issue 标题]
- **报告者 / Reporter**: [GitHub 用户名]
- **严重程度 / Severity**: [Critical/High/Medium/Low]
- **状态 / Status**: [当前 GitHub Issue 状态]

## 问题描述 / Problem Description

[问题的清晰描述]

**预期行为 / Expected Behavior:**
[应该发生什么]

**实际行为 / Actual Behavior:**
[实际发生了什么]

**症状 / Symptoms:**
- [列出可观察的症状]

## 复现 / Reproduction

**复现步骤 / Steps to Reproduce:**
1. [步骤 1]
2. [步骤 2]
3. [观察问题]

**已验证复现 / Reproduction Verified:** [是/否]

## 根本原因 / Root Cause

### 受影响的组件 / Affected Components

- **文件 / Files**: [带路径的受影响文件列表]
- **函数/类 / Functions/Classes**: [具体代码位置]
- **依赖 / Dependencies**: [涉及的任何外部依赖]

### 分析 / Analysis

[根本原因的详细解释]

**为什么会发生 / Why This Occurs:**
[底层问题的解释]

**代码位置 / Code Location:**
```
[文件路径:行号]
[显示问题的相关代码片段]
```

### 相关问题 / Related Issues

- [任何相关问题或模式]

### SuperInsight 特定考虑 / SuperInsight-Specific Considerations

- **是否违反 Steering 规则**: [是/否，哪条规则]
- **是否涉及异步安全**: [是/否]
- **是否涉及 TypeScript 导出**: [是/否]
- **是否涉及多租户**: [是/否]

## 影响评估 / Impact Assessment

**范围 / Scope:**
- [这有多广泛？]

**受影响的功能 / Affected Features:**
- [列出受影响的功能]

**严重程度理由 / Severity Justification:**
[为什么是这个严重程度]

**数据/安全问题 / Data/Security Concerns:**
[任何数据损坏或安全影响]

## 提议的修复 / Proposed Fix

### 修复策略 / Fix Strategy

[修复的高级方案]

### 要修改的文件 / Files to Modify

1. **[文件路径]**
   - 更改: [需要更改什么]
   - 原因: [为什么这个更改能修复问题]

2. **[文件路径]**
   - 更改: [需要更改什么]
   - 原因: [为什么这个更改能修复问题]

### 替代方案 / Alternative Approaches

[其他可能的解决方案以及为什么提议的方案更好]

### 风险和考虑 / Risks and Considerations

- [此修复的任何风险]
- [需要注意的副作用]
- [如果有的话，破坏性更改]

### 测试要求 / Testing Requirements

**需要的测试用例 / Test Cases Needed:**
1. [测试用例 1 - 验证修复有效]
2. [测试用例 2 - 验证无回归]
3. [测试用例 3 - 边界情况]

**验证命令 / Validation Commands:**
```bash
# 后端验证
pytest tests/test_xxx.py -v
mypy src/

# 前端验证
cd frontend
npx tsc --noEmit
npm run test -- --run
```

## 实现计划 / Implementation Plan

[实现步骤的简要概述]

此 RCA 文档应由 `/github_bug_fix:implement-fix` 命令使用。

## 后续步骤 / Next Steps

1. 审查此 RCA 文档
2. 运行: `/github_bug_fix:implement-fix $ARGUMENTS` 实现修复
3. 实现完成后运行: `/commit`
```
