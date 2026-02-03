---
inclusion: manual
---

# 文档最小化规范

**版本**: 2.0  
**状态**: ✅ Active  
**最后更新**: 2026-02-04  
**优先级**: HIGH  
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则（必读）

**代码即文档 > 必要的文档 > 冗长的文档**

**信息爆炸 = 无用信息** - 只生成必要的文档。

---

## 🎯 3 条核心规则（日常使用）

1. **只生成 Spec 三件套** - requirements.md + design.md + tasks.md
2. **文档大小限制** - requirements < 5000字，design < 3000字，tasks < 2000字
3. **代码即文档** - 好的代码 + 好的命名 + 必要的注释 > 冗长的文档

---

## ⚡ 快速参考（80% 场景够用）

### 必须生成的文档

| 文档 | 大小限制 | 内容 |
|------|---------|------|
| requirements.md | < 5000字 | 用户故事、验收标准、优先级 |
| design.md | < 3000字 | 架构决策、关键接口、数据模型 |
| tasks.md | < 2000字 | 任务分解、时间估计、依赖关系 |

### 禁止生成的文档

- 诊断报告、执行报告、实现总结、完成总结
- 测试指南、测试检查清单、测试准备文档
- 快速启动指南、资源索引
- README（除非项目级）
- 重复的代码示例（应该在代码中）
- 过度详细的 API 文档（应该用 OpenAPI/Swagger）

### 快速检查清单

创建新文档前：
- [ ] 这个文档是必须的吗？
- [ ] 是否已有类似文档？
- [ ] 能否合并到现有文档？
- [ ] 内容是否超过限制？

---

## 📚 详细规则（按需查阅）

<details>
<summary><b>规则 1: 一个文档一个目的</b>（点击展开）</summary>

**❌ 错误**:
```
DIAGNOSIS_REPORT.md (诊断)
IMPLEMENTATION_SUMMARY.md (实现)
EXECUTION_REPORT.md (执行)
MANUAL_TESTING_GUIDE.md (测试)
MANUAL_TESTING_CHECKLIST.md (检查)
QUICK_START_MANUAL_TESTING.md (快速启动)
TASK_5_1_COMPLETION_SUMMARY.md (完成)
```

**✅ 正确**:
```
requirements.md (需求)
design.md (设计)
tasks.md (任务)
```

</details>

<details>
<summary><b>规则 2: 文档大小限制</b>（点击展开）</summary>

- **requirements.md**: < 5000 字
- **design.md**: < 3000 字
- **tasks.md**: < 2000 字

超过限制则拆分或删除非必要内容。

</details>

<details>
<summary><b>规则 3: 内容精简</b>（点击展开）</summary>

**删除**:
- 重复信息
- 冗余解释
- 过度详细的步骤
- 多个版本的同一内容

**保留**:
- 核心信息
- 关键决策
- 必要的上下文

</details>

<details>
<summary><b>规则 4: 测试文档</b>（点击展开）</summary>

**不生成**:
- 测试指南
- 测试检查清单
- 测试报告
- 测试总结

**替代方案**:
- 在 tasks.md 中简要说明测试方法
- 在代码注释中说明测试用例
- 在 CI/CD 中自动生成测试报告

</details>

<details>
<summary><b>规则 5: 实现文档</b>（点击展开）</summary>

**不生成**:
- 诊断报告
- 执行报告
- 实现总结
- 完成总结

**替代方案**:
- 在 tasks.md 中更新进度
- 在 Git commit 中记录变更
- 在代码中添加注释

</details>

---

## 🔗 相关资源

- **Spec 工作流**：`.kiro/templates/spec-workflow-guide.md`
- **文件组织规范**：`.kiro/steering/file-organization-rules.md`
- **AI 开发效率**：`.kiro/steering/ai-development-efficiency.md`

---

**此规范为强制性规范。**

违反规范的文档将被删除。

