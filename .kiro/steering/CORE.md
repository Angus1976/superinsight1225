# 核心规则

## 原则
- 代码: 可读性优先，函数 20-40 行，卫语句，显式优于隐式，防御性编程
- 文档: 只生成 Spec 三件套，禁止生成报告
- i18n: 前端可见文本必须 `t()`，同步写入 `frontend/src/locales/zh/` 和 `en/`
- 进度 85%: 只做小幅修复/优化/配置调整，禁止重写和大改。涉及多文件改动或架构调整时必须先与用户确认方案再动手
- 文件: 后端 `src/`，前端 `frontend/src/`，文档 `文档/`（索引见 `文档/文档总索引.md`）

## 触发规则

遇到以下场景时，读取 `.kiro/rules/` 下对应文件：

| 场景 | 读取 |
|------|------|
| 写/改前端组件或页面 | `i18n-translation-rules.md` |
| 写/改后端 API 或路由 | `python-fastapi-patterns.md` |
| 涉及安全/认证/输入验证/权限 | `security-review-checklist.md` |
| TypeScript 导出/模块/类型问题 | `typescript-export-rules.md` |
| 新建文件或调整目录结构 | `structure.md` |
| 用户要求写测试或 TDD | `tdd-workflow.md` |
| 准备 git commit | `git-workflow-standards.md` |
| API 设计/分页/错误码 | `api-design-patterns.md` |
| 代码审查/重构/质量优化 | `coding-quality-standards.md` |
| 异步/并发/事件循环问题 | `async-sync-safety-quick-reference.md` |

多个场景同时出现时，可一次读取多个规则文件。

### 全局分析模式

当用户提到"全局分析"、"整体分析"、"项目全貌"、"全面了解"等关键词时，一次性读取：
1. `.kiro/rules/product.md` — 产品介绍
2. `.kiro/rules/structure.md` — 项目结构
3. `.kiro/rules/tech.md` — 技术栈
4. `.kiro/project-progress.json` — 项目进度
5. `文档/文档总索引.md` — 文档全景

读取后结合长记忆（knowledge graph）中的项目信息进行综合分析，包括：
- SuperInsight 项目概况、前后端架构
- SuperInsight-Optimization-Map 历史优化地图（已完成/待优化/备用代码）

其他规则文件（如 `ai-development-efficiency.md`、`auto-approve-guide.md` 等）只在用户明确要求时读取。
