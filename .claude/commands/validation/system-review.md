---
description: 分析实现与计划的差异以改进流程 / Analyze implementation against plan for process improvements
---

# 系统审查 / System Review

对实现与计划的对齐程度进行元级分析，识别流程改进点。

## 目的 / Purpose

**系统审查不是代码审查。** 你不是在寻找代码中的 bug，而是在寻找流程中的问题。

**你的任务**:

- 分析计划遵循和偏离模式
- 识别哪些偏离是合理的，哪些是有问题的
- 发现可以防止未来问题的流程改进
- 建议更新第一层资产（CLAUDE.md、计划模板、命令、Steering 规则）

**理念**:

- 好的偏离揭示计划的局限性 → 改进计划
- 坏的偏离揭示需求不清晰 → 改进沟通
- 重复的问题揭示缺少自动化 → 创建命令或 Hook

## 背景与输入 / Context & Inputs

你将分析四个关键工件：

**计划命令 / Plan Command:**
阅读以理解计划流程和指导计划创建的指令。
`.claude/commands/core_piv_loop/plan-feature.md`

**生成的计划 / Generated Plan:**
阅读以理解代理应该做什么。
计划文件: $1

**执行命令 / Execute Command:**
阅读以理解执行流程和指导实现的指令。
`.claude/commands/core_piv_loop/execute.md`

**执行报告 / Execution Report:**
阅读以理解代理实际做了什么以及为什么。
执行报告: $2

**SuperInsight 特定资产 / SuperInsight-Specific Assets:**
- `.kiro/steering/` - 项目规范和规则
- `.kiro/specs/[feature]/` - 功能规格文档
- `CLAUDE.md` - 项目配置

## 分析工作流 / Analysis Workflow

### 步骤 1: 理解计划方案 / Understand the Planned Approach

阅读生成的计划 ($1) 并提取：

- 计划了哪些功能？
- 指定了什么架构？
- 定义了哪些验证步骤？
- 引用了哪些模式？
- 引用了哪些 Steering 规则？

### 步骤 2: 理解实际实现 / Understand the Actual Implementation

阅读执行报告 ($2) 并提取：

- 实现了什么？
- 哪些偏离了计划？
- 遇到了哪些挑战？
- 跳过了什么，为什么？

### 步骤 3: 分类每个偏离 / Classify Each Divergence

对于执行报告中识别的每个偏离，分类为：

**好的偏离 ✅** (合理的):

- 计划假设了代码库中不存在的东西
- 实现过程中发现了更好的模式
- 需要性能优化
- 发现了需要不同方案的安全问题
- 发现了 Steering 规则中的新要求

**坏的偏离 ❌** (有问题的):

- 忽略了计划中的明确约束
- 创建了新架构而不是遵循现有模式
- 走捷径引入技术债务
- 误解了需求
- 违反了 Steering 规则（如 async-sync-safety.md）

### 步骤 4: 追溯根本原因 / Trace Root Causes

对于每个有问题的偏离，识别根本原因：

- 计划是否不清晰？在哪里？为什么？
- 是否缺少上下文？在哪里？为什么？
- 是否缺少验证？在哪里？为什么？
- 是否重复了手动步骤？在哪里？为什么？
- 是否缺少 Steering 规则？应该添加什么？

### 步骤 5: 生成流程改进 / Generate Process Improvements

基于偏离的模式，建议：

- **CLAUDE.md 更新**: 需要记录的通用模式或反模式
- **计划命令更新**: 需要澄清的指令或缺失的步骤
- **新命令**: 应该自动化的手动流程
- **验证补充**: 可以更早发现问题的检查
- **Steering 规则更新**: 需要添加或修改的规则
- **Kiro Hook 补充**: 可以自动化的检查

## 输出格式 / Output Format

将分析保存到: `.agents/system-reviews/[feature-name]-review.md`

或（如果使用 Kiro Spec）: `.kiro/specs/[feature-name]/system-review.md`

### 报告结构 / Report Structure:

#### 元信息 / Meta Information

- **审查的计划 / Plan reviewed**: [路径 $1]
- **执行报告 / Execution report**: [路径 $2]
- **日期 / Date**: [当前日期]
- **相关 Spec / Related Spec**: [如适用]

#### 总体对齐分数 / Overall Alignment Score: \_\_/10

评分指南：

- 10: 完美遵循，所有偏离都是合理的
- 7-9: 轻微的合理偏离
- 4-6: 合理和有问题的偏离混合
- 1-3: 主要是有问题的偏离

#### 偏离分析 / Divergence Analysis

对于执行报告中的每个偏离：

```yaml
divergence: [改变了什么]
planned: [计划指定的内容]
actual: [实际实现的内容]
reason: [代理在报告中陈述的原因]
classification: good ✅ | bad ❌
justified: yes/no
root_cause: [计划不清晰 | 缺少上下文 | 缺少 Steering 规则 | 等]
```

#### 模式遵循 / Pattern Compliance

评估对文档化模式的遵循：

- [ ] 遵循代码库架构
- [ ] 使用文档化模式（来自 CLAUDE.md）
- [ ] 正确应用测试模式
- [ ] 满足验证要求
- [ ] 遵循 async-sync-safety.md 规则
- [ ] 遵循 typescript-export-rules.md 规则
- [ ] 遵循 doc-first-workflow.md 规则

#### 系统改进行动 / System Improvement Actions

基于分析，推荐具体行动：

**更新 CLAUDE.md:**

- [ ] 记录实现过程中发现的 [模式 X]
- [ ] 添加 [Y] 的反模式警告
- [ ] 澄清 [技术约束 Z]

**更新计划命令 ($1):**

- [ ] 添加 [缺失步骤] 的指令
- [ ] 澄清 [模糊指令]
- [ ] 添加 [X] 的验证要求

**创建新命令:**

- [ ] `/[command-name]` 用于 [重复 3+ 次的手动流程]

**更新执行命令:**

- [ ] 添加 [验证步骤] 到执行检查清单

**更新 Steering 规则:**

- [ ] 在 `.kiro/steering/` 中添加 [新规则]
- [ ] 更新 [现有规则] 以包含 [新内容]

**创建 Kiro Hook:**

- [ ] 创建 Hook 自动检查 [重复问题]

#### 关键学习 / Key Learnings

**顺利之处 / What worked well:**

- [具体进展顺利的事项]

**需要改进之处 / What needs improvement:**

- [识别的具体流程差距]

**下次实现 / For next implementation:**

- [要尝试的具体改进]

## 重要提示 / Important

- **具体化**: 不要说"计划不清晰"，要说"计划没有指定使用哪种认证模式"
- **关注模式**: 一次性问题不可操作。寻找重复的问题。
- **行动导向**: 每个发现都应该有具体的资产更新建议
- **建议改进**: 不只是分析，实际建议要添加到 CLAUDE.md 或命令中的文本
- **考虑 Steering**: 检查是否需要新的或更新的 Steering 规则
- **考虑 Hook**: 检查是否可以通过 Kiro Hook 自动化检查