# 核心开发规则

## 原则

- 代码质量: 可读性 > 可维护性 > 性能。函数 20-40 行，卫语句，显式优于隐式
- 文档: 代码即文档，只生成 Spec 三件套，禁止生成报告
- i18n: 前端用户可见文本必须 `t()`，翻译同步 `zh/` 和 `en/`
- 项目 70% 进度: 只扩展/修复/优化，禁止重写，先分析后动手，最小改动
- 文件: 后端 `src/`，前端 `frontend/src/`，文档 `文档/`

## 规则加载策略

**不要主动加载任何 `.kiro/rules/` 文件。** 只在以下情况读取：
1. 用户明确要求（如"按照 i18n 规则检查"）
2. 遇到具体技术问题且自身知识不足以解决时
3. 需要项目特定约定（如导出规范、文件组织）时

可用规则（按需读取）：`typescript-export-rules.md` `i18n-translation-rules.md` `coding-quality-standards.md` `structure.md` `security-review-checklist.md` `python-fastapi-patterns.md` `git-workflow-standards.md` `tdd-workflow.md` `api-design-patterns.md`
