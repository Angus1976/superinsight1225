---
description: 对已更改文件进行技术代码审查 | Technical code review for quality and bugs
---

# Code Review: 代码审查 | Technical Code Review

对最近更改的文件执行技术代码审查。

Perform technical code review on recently changed files.

## 核心原则 | Core Principles

**审查理念**:
- 简单是最终的复杂 - 每一行都应证明其存在的必要性
- 代码被阅读的次数远多于被编写的次数 - 优化可读性
- 最好的代码往往是你不写的代码
- 优雅源于意图的清晰和表达的经济

## 审查内容 | What to Review

### 1. 收集代码库上下文 | Gather Codebase Context

首先了解代码库标准和模式。检查:

**SuperInsight 特定文档**:
- `CLAUDE.md` - 项目配置
- `README.md` - 项目概述
- `.kiro/steering/tech.md` - 技术栈
- `.kiro/steering/structure.md` - 项目结构
- `.kiro/steering/async-sync-safety.md` - 异步安全规则
- `.kiro/steering/typescript-export-rules.md` - TypeScript 规范
- `.kiro/steering/doc-first-workflow.md` - 文档优先流程
- `.claude/reference/` - 最佳实践参考

### 2. 检查更改的文件 | Check Changed Files

运行这些命令:

```bash
git status
git diff HEAD
git diff --stat HEAD
```

检查新文件列表:

```bash
git ls-files --others --exclude-standard
```

完整阅读每个新文件。完整阅读每个更改的文件（不仅仅是 diff）以理解完整上下文。

### 3. 分析问题 | Analyze Issues

对于每个更改或新文件，分析:

#### 1. 逻辑错误 | Logic Errors
- Off-by-one 错误
- 不正确的条件判断
- 缺少错误处理
- 竞态条件
- 异步/同步混用（检查 `.kiro/steering/async-sync-safety.md`）

#### 2. 安全问题 | Security Issues
- SQL 注入漏洞
- XSS 漏洞
- 不安全的数据处理
- 暴露的密钥或 API keys
- PII 数据未脱敏
- 权限检查缺失

#### 3. 性能问题 | Performance Problems
- N+1 查询
- 低效算法
- 内存泄漏
- 不必要的计算
- 阻塞的异步操作

#### 4. 代码质量 | Code Quality
- 违反 DRY 原则
- 过于复杂的函数
- 糟糕的命名
- 缺少类型提示/注解
- 未使用的导入或变量

#### 5. 遵循代码库标准 | Adherence to Standards

**后端 (Python)**:
- [ ] 遵循 PEP 8 风格
- [ ] 使用 type hints
- [ ] 使用 structlog 进行日志记录
- [ ] 遵循异步安全规则
- [ ] Pydantic 模式正确定义
- [ ] 数据库模型正确定义
- [ ] API 端点有适当的错误处理

**前端 (TypeScript)**:
- [ ] 遵循 TypeScript 导出规范
- [ ] 所有 API 调用有泛型类型
- [ ] Hook 命名正确（useTasks 而非 useTaskList）
- [ ] 组件使用 Ant Design 组件
- [ ] 使用 TanStack Query 进行数据获取
- [ ] 状态管理使用 Zustand

**测试**:
- [ ] 单元测试覆盖率 >= 80%
- [ ] 测试文件命名正确
- [ ] 使用适当的 fixtures
- [ ] 边界情况已测试

## 验证问题是真实的 | Verify Issues Are Real

- 为发现的问题运行特定测试
- 确认类型错误是合法的
- 用上下文验证安全问题

## 输出格式 | Output Format

保存新文件到 `.agents/code-reviews/[appropriate-name].md`

**统计 | Stats:**

- 修改的文件 | Files Modified: 0
- 添加的文件 | Files Added: 0
- 删除的文件 | Files Deleted: 0
- 新增行数 | New lines: 0
- 删除行数 | Deleted lines: 0

**对于发现的每个问题 | For each issue found:**

```
severity: critical|high|medium|low
file: path/to/file.py
line: 42
issue: [一行描述 | one-line description]
detail: [为什么这是问题的解释 | explanation of why this is a problem]
suggestion: [如何修复 | how to fix it]
reference: [相关规范文档 | relevant standard document]
```

**严重性级别 | Severity Levels:**
- `critical`: 安全漏洞、数据丢失风险
- `high`: 功能性 bug、性能严重问题
- `medium`: 代码质量问题、小的性能问题
- `low`: 风格问题、建议性改进

**示例 | Example:**

```
severity: high
file: src/api/users.py
line: 45
issue: 在异步函数中使用 threading.Lock
detail: threading.Lock 会阻塞异步事件循环，导致 API 挂起
suggestion: 使用 asyncio.Lock() 替代 threading.Lock()
reference: .kiro/steering/async-sync-safety.md
```

```
severity: medium
file: frontend/src/hooks/index.ts
line: 12
issue: 导出不存在的函数 useTaskList
detail: useTask.ts 中实际导出的是 useTasks（复数形式）
suggestion: 将 useTaskList 改为 useTasks
reference: .kiro/steering/typescript-export-rules.md
```

如果未发现问题: "代码审查通过。未检测到技术问题。| Code review passed. No technical issues detected."

## 重要提示 | Important

- 具体（行号，而非模糊的抱怨）
- 关注真正的 bug，而非风格
- 建议修复，不要只是抱怨
- 将安全问题标记为 CRITICAL
- 引用相关的规范文档
- 考虑 SuperInsight 的特定要求（多租户、数据脱敏、审计日志等）