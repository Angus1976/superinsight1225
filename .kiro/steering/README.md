# Steering 说明

**策略**: 对话开始只加载 `CORE.md`（~50 行），其他规则按需加载。

## 目录结构

- `.kiro/steering/CORE.md` - 核心规则（自动加载）
- `.kiro/rules/` - 详细规则（按需加载）

## 详细规则索引

| 关键词 | 文档 |
|--------|------|
| TypeScript、导出、export | `typescript-export-rules.md` |
| i18n、翻译、国际化 | `i18n-translation-rules.md` |
| 代码质量、函数长度 | `coding-quality-standards.md` |
| 项目结构、目录 | `structure.md` |
| 安全、OWASP、注入 | `security-review-checklist.md` |
| FastAPI、Python | `python-fastapi-patterns.md` |
| Git、commit | `git-workflow-standards.md` |
| TDD、测试 | `tdd-workflow.md` |
| API、REST | `api-design-patterns.md` |
