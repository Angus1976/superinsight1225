---
name: superdata-kiro-dev
description: Guides agents in the superdata repo per KIRO steering—on-demand .kiro/rules/, Spec triplets (code wins if stale), tiered global context, token-saving habits. Use for this repo, KIRO, SuperInsight, or 全局分析/项目全貌/按需加载.
---

# Superdata KIRO + Cursor

## 权威与维护

- **Steering 正文以** `.kiro/steering/CORE.md` **为准**；本 skill 是 Cursor 侧的压缩版，表格或措辞若与 CORE 冲突，按 CORE 执行并应回头更新本文件。

## 核心原则（压缩）

| 维度 | 要点 |
|------|------|
| 代码 | 可读性优先；函数约 20–40 行；卫语句；显式优于隐式；防御性编程 |
| 文档 | 只维护 Spec 三件套；**禁止生成报告**（与 CORE 一致） |
| i18n | 前端可见文案 `t()`，同步 `frontend/src/locales/zh/` 与 `en/` |
| 进度 ~85% | 小步修复/优化/配置；禁大重写；多文件或架构变更先与用户对齐方案 |
| 路径 | 后端 `src/`，前端 `frontend/src/`，说明文档 `文档/`（索引 `文档/文档总索引.md`） |
| 真源 | **以代码为准**：`.kiro/specs/`、`project-progress.json`、规则里的「现状」描述均可能滞后。先读代码/路由/类型确认行为；再改代码或把三件套更新到与实现一致，**不要**按过时文档改对的行为 |

## 省 Token

1. 不遍历整棵 `.kiro/specs/`：只打开**当前任务相关**目录下的文件或用户点名的路径。
2. `.kiro/rules/` **按需**加载；见下表；关键词扩展见 `.kiro/rules/智能加载映射表.md`。
3. 单次任务优先 **≤2–3 个**规则文件；多场景合并一次读。
4. **先搜后读**：ripgrep / 符号跳转 / 小范围读文件，避免通读大文档。
5. Hooks 提醒见 `.kiro/hooks/README.md`；不必每次载入全文。

## 场景 → `.kiro/rules/` 文件（路径前缀均为 `.kiro/rules/`）

| 场景 | 文件 |
|------|------|
| 前端组件/页面 | `i18n-translation-rules.md` |
| 后端 API/路由 | `python-fastapi-patterns.md` |
| 安全/认证/校验/权限 | `security-review-checklist.md` |
| TS 导出/模块/类型 | `typescript-export-rules.md` |
| 新建文件/目录结构 | `structure.md` |
| 测试/TDD | `tdd-workflow.md` |
| git commit | `git-workflow-standards.md` |
| API 设计/分页/错误码 | `api-design-patterns.md` |
| 审查/重构/质量 | `coding-quality-standards.md` |
| 异步/并发/事件循环 | `async-sync-safety-quick-reference.md` |
| Sealos/PVC/容器 | 仓库根 `deploy/sealos/README.md` |

多场景可同时读多个文件。

## 全局分析（分级，默认省 Token）

用户提到「全局分析」「整体分析」「项目全貌」「全面了解」等时：

- **轻量（默认优先）**：`.kiro/rules/structure.md` + `.kiro/rules/tech.md` — 适合「技术栈/目录」类问题。
- **完整**：再补上 `.kiro/rules/product.md`、`文档/文档总索引.md`、`.kiro/project-progress.json`（进度文件可能旧，**与代码冲突以代码为准**）。

若有对话中的长记忆/知识图谱（如 SuperInsight、Optimization-Map），可与上述材料**结合**叙述，不必为凑全而多读无关文件。

`ai-development-efficiency.md`、`auto-approve-guide.md` 等仅在用户明确要求时再读。

## Spec 目录

- 功能规格：`.kiro/specs/<主题>/`，常见三件套 `requirements.md`、`design.md`、`tasks.md`；流程说明见 `.kiro/specs/README.md`。
- **新功能/大改动**：仍维护三件套并与实现对齐；规划前若 Spec 可能旧，**先验证代码**再落笔。

## 延伸阅读（按需点开）

- `.kiro/rules/智能加载映射表.md` — 关键词 → 规则
- `.kiro/hooks/README.md` — 保存时提醒与 hook 列表
