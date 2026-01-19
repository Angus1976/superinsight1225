# Claude 命令使用指南

## 概述

本项目已集成 PIV (Prime-Implement-Validate) 方法论的 Claude 自定义命令。这些命令可以帮助你系统化地开发功能、修复 bug 和验证代码质量。

## 如何使用命令

在 Claude Code 中，你可以通过输入 `/` 来触发命令自动完成，然后选择相应的命令。

## 可用命令

### 🎯 核心 PIV 循环

#### `/core_piv_loop:prime`
**用途**: 加载项目上下文和代码库理解

**何时使用**:
- 开始新功能开发前
- 需要了解项目结构时
- 加入新项目时

**输出**: 项目概览报告，包括：
- 项目目的和类型
- 技术栈
- 架构模式
- 当前状态

**示例**:
```
/core_piv_loop:prime
```

---

#### `/core_piv_loop:plan-feature [功能描述]`
**用途**: 通过代码库分析创建全面的实施计划

**何时使用**:
- 开发中等及以上复杂度的新功能
- 需要详细实施计划时
- 想要确保一次性实施成功时

**参数**: 功能描述（简短描述你要实现的功能）

**输出**: 详细的实施计划文件 `.agents/plans/{feature-name}.md`，包括：
- 功能描述和用户故事
- 代码库参考文件
- 逐步任务列表
- 验证命令

**示例**:
```
/core_piv_loop:plan-feature 添加用户个人资料 API 端点
```

---

#### `/core_piv_loop:execute [计划文件路径]`
**用途**: 逐步执行实施计划

**何时使用**:
- 已经创建了实施计划
- 准备开始实施功能

**参数**: 计划文件路径（例如：`.agents/plans/add-user-profile-api.md`）

**输出**: 按计划实施的代码和测试

**示例**:
```
/core_piv_loop:execute .agents/plans/add-user-profile-api.md
```

---

### ✅ 验证命令

#### `/validation:validate`
**用途**: 运行完整验证：测试、代码检查、覆盖率、前端构建

**何时使用**:
- 完成功能实施后
- 提交代码前
- 需要确保代码质量时

**验证内容**:
- 后端：pytest、mypy、black、isort
- 前端：TypeScript 检查、测试、lint

**示例**:
```
/validation:validate
```

---

#### `/validation:code-review`
**用途**: 对已更改文件进行技术代码审查

**何时使用**:
- 完成代码修改后
- 需要第三方视角审查代码
- 寻找潜在问题

**输出**: 代码审查报告，包括：
- 代码质量问题
- 潜在 bug
- 改进建议

**示例**:
```
/validation:code-review
```

---

#### `/validation:code-review-fix`
**用途**: 修复代码审查中发现的问题

**何时使用**:
- 运行 `/validation:code-review` 后
- 发现了需要修复的问题

**示例**:
```
/validation:code-review-fix
```

---

#### `/validation:execution-report`
**用途**: 功能实施后生成报告

**何时使用**:
- 完成功能实施后
- 需要总结实施过程
- 记录经验教训

**输出**: 执行报告，包括：
- 完成的任务
- 创建/修改的文件
- 测试结果
- 验证结果

**示例**:
```
/validation:execution-report
```

---

#### `/validation:system-review`
**用途**: 分析实施与计划的差异以改进流程

**何时使用**:
- 完成功能实施后
- 想要改进开发流程
- 分析计划与实际的差异

**输出**: 系统审查报告，包括：
- 计划与实际的差异
- 流程改进建议
- 经验教训

**示例**:
```
/validation:system-review
```

---

### 🐛 Bug 修复命令

#### `/github_bug_fix:rca [issue-number]`
**用途**: 为 GitHub 问题创建根本原因分析文档

**何时使用**:
- 遇到复杂 bug
- 需要系统化分析问题
- 开始修复前

**参数**: GitHub issue 编号（可选）

**输出**: RCA 文档，包括：
- 问题描述
- 根本原因分析
- 影响范围
- 修复方案

**示例**:
```
/github_bug_fix:rca 123
```

---

#### `/github_bug_fix:implement-fix [rca-file-path]`
**用途**: 根据 RCA 文档实施修复

**何时使用**:
- 已经创建了 RCA 文档
- 准备实施修复

**参数**: RCA 文档路径

**示例**:
```
/github_bug_fix:implement-fix .agents/rca/issue-123-rca.md
```

---

### 🔧 杂项命令

#### `/commit`
**用途**: 创建带有适当标签的原子提交

**何时使用**:
- 完成一个逻辑单元的修改
- 准备提交代码

**提交类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```
/commit
```

---

#### `/init-project`
**用途**: 安装依赖项，启动后端和前端服务器

**何时使用**:
- 首次设置项目
- 需要重新安装依赖

**执行内容**:
- 安装后端依赖
- 安装前端依赖
- 启动后端服务器
- 启动前端服务器

**示例**:
```
/init-project
```

---

#### `/create-prd`
**用途**: 根据对话生成产品需求文档

**何时使用**:
- 讨论了新功能需求
- 需要正式的 PRD 文档

**输出**: PRD 文档，包括：
- 功能描述
- 用户故事
- 验收标准
- 技术要求

**示例**:
```
/create-prd
```

---

## 典型工作流

### 工作流 1: 开发新功能

```
1. /core_piv_loop:prime
   → 了解项目上下文

2. /core_piv_loop:plan-feature 添加用户个人资料功能
   → 创建详细计划

3. /core_piv_loop:execute .agents/plans/add-user-profile.md
   → 实施功能

4. /validation:validate
   → 验证实施

5. /validation:code-review
   → 代码审查

6. /validation:code-review-fix
   → 修复问题（如有）

7. /validation:execution-report
   → 生成报告

8. /commit
   → 提交代码
```

### 工作流 2: 修复 Bug

```
1. /github_bug_fix:rca 123
   → 创建根本原因分析

2. /github_bug_fix:implement-fix .agents/rca/issue-123-rca.md
   → 实施修复

3. /validation:validate
   → 验证修复

4. /commit
   → 提交修复
```

### 工作流 3: 代码审查和改进

```
1. /validation:code-review
   → 审查当前代码

2. /validation:code-review-fix
   → 修复发现的问题

3. /validation:validate
   → 验证修复

4. /commit
   → 提交改进
```

## 命令文件位置

所有命令定义文件位于：
```
.claude/
├── commands/
│   ├── core_piv_loop/
│   │   ├── prime.md
│   │   ├── plan-feature.md
│   │   └── execute.md
│   ├── validation/
│   │   ├── validate.md
│   │   ├── code-review.md
│   │   ├── code-review-fix.md
│   │   ├── execution-report.md
│   │   └── system-review.md
│   ├── github_bug_fix/
│   │   ├── rca.md
│   │   └── implement-fix.md
│   ├── commit.md
│   ├── init-project.md
│   └── create-prd.md
└── reference/
    ├── fastapi-best-practices.md
    ├── react-frontend-best-practices.md
    ├── sqlite-best-practices.md
    ├── testing-and-logging.md
    └── deployment-best-practices.md
```

## 自定义命令

如果你想创建自己的命令：

1. 在 `.claude/commands/` 目录下创建新的 `.md` 文件
2. 使用以下格式：

```markdown
---
description: 命令描述
argument-hint: [参数提示]
---

# 命令名称

## 目标
[命令的目标]

## 过程
[命令执行的步骤]

## 输出
[命令的输出]
```

3. 重启 Claude Code 以加载新命令

## 提示

1. **命令自动完成**: 输入 `/` 会显示所有可用命令
2. **命令帮助**: 每个命令文件都包含详细的使用说明
3. **参数提示**: 某些命令需要参数，会在命令后显示提示
4. **命令链**: 可以连续使用多个命令完成复杂工作流

## 故障排除

### 命令不显示
- 确保 `.claude/commands/` 目录存在
- 检查命令文件格式是否正确
- 重启 Claude Code

### 命令执行失败
- 检查参数是否正确
- 查看命令文件中的详细说明
- 确保项目环境已正确设置

## 更多资源

- **PIV 快速开始**: `.kiro/PIV_QUICK_START.md`
- **PIV 集成指南**: `.kiro/steering/piv-methodology-integration.md`
- **完整文档**: `.kiro/README_PIV_INTEGRATION.md`
- **原始项目**: https://github.com/coleam00/habit-tracker

---

**开始使用 Claude 命令，提高开发效率！**
