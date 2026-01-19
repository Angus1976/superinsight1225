---
description: 生成实现报告用于系统审查 / Generate implementation report for system review
---

# 执行报告 / Execution Report

审查并深入分析刚刚完成的实现。

## 背景 / Context

你刚刚完成了一个功能的实现。在继续之前，请反思：

- 你实现了什么
- 与计划的对齐程度
- 遇到了哪些挑战
- 哪些地方偏离了计划，为什么

## 生成报告 / Generate Report

**保存位置**: `.agents/execution-reports/[feature-name].md`

**或者（如果使用 Kiro Spec）**: `.kiro/specs/[feature-name]/execution-report.md`

### 元信息 / Meta Information

- **计划文件 / Plan file**: [指导此实现的计划路径]
- **规格文件 / Spec files** (如适用):
  - requirements.md: [路径]
  - design.md: [路径]
  - tasks.md: [路径]
- **新增文件 / Files added**: [带路径的列表]
- **修改文件 / Files modified**: [带路径的列表]
- **代码变更 / Lines changed**: +X -Y

### 验证结果 / Validation Results

**后端验证 / Backend Validation**:
- 代码格式 (black/isort): ✓/✗ [失败详情]
- 类型检查 (mypy): ✓/✗ [失败详情]
- 单元测试 (pytest): ✓/✗ [X 通过, Y 失败]
- 集成测试: ✓/✗ [X 通过, Y 失败]
- 异步安全检查: ✓/✗ [是否遵循 async-sync-safety.md]

**前端验证 / Frontend Validation**:
- TypeScript 编译 (tsc): ✓/✗ [失败详情]
- 代码检查 (ESLint): ✓/✗ [失败详情]
- 单元测试 (Vitest): ✓/✗ [X 通过, Y 失败]
- E2E 测试 (Playwright): ✓/✗ [X 通过, Y 失败]
- 导出规范检查: ✓/✗ [是否遵循 typescript-export-rules.md]

### 顺利之处 / What Went Well

列出进展顺利的具体事项：

- [具体示例]

### 遇到的挑战 / Challenges Encountered

列出具体困难：

- [困难是什么，为什么困难]

**SuperInsight 常见挑战**:
- 异步/同步混用问题
- TypeScript 类型推断
- 多租户数据隔离
- Label Studio 集成
- 国际化 (i18n) 处理

### 与计划的偏离 / Divergences from Plan

对于每个偏离，记录：

**[偏离标题]**

- **计划 / Planned**: [计划指定的内容]
- **实际 / Actual**: [实际实现的内容]
- **原因 / Reason**: [为什么发生偏离]
- **类型 / Type**: [发现更好方案 | 计划假设错误 | 安全考虑 | 性能问题 | 其他]

### 跳过的项目 / Skipped Items

列出计划中未实现的内容：

- [跳过了什么]
- **原因 / Reason**: [为什么跳过]

### 建议 / Recommendations

基于此次实现，下次应该改变什么？

- **计划命令改进 / Plan command improvements**: [建议]
- **执行命令改进 / Execute command improvements**: [建议]
- **CLAUDE.md 补充 / CLAUDE.md additions**: [建议]
- **Steering 规则补充 / Steering rules additions**: [建议]
- **Kiro Spec 改进 / Kiro Spec improvements**: [建议]

### SuperInsight 特定学习 / SuperInsight-Specific Learnings

- **架构模式**: [发现的新模式或反模式]
- **技术债务**: [引入或解决的技术债务]
- **文档更新**: [需要更新的文档]
- **规范遵循**: [对 steering 规则的遵循情况]