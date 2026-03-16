# 核心开发规则

## 🎯 核心原则

**代码质量**: 可读性 > 可维护性 > 可测试性 > 健壮性 > 性能
- 函数 20-40 行，卫语句提前返回，显式优于隐式

**AI 开发**: 短而精 > 长而全
- 每次只做一件事，拆小步，渐进式给上下文

**文档**: 代码即文档 > 必要的文档 > 冗长的文档
- 只生成 Spec 三件套，禁止生成诊断/执行报告

**i18n**: 所有前端用户可见文本必须用 `t()` 包裹
- 翻译 key 同步写入 `frontend/src/locales/zh/` 和 `en/`

**项目进度**: 当前 70%（60-85% 阶段）
- 只允许扩展、修复、优化，禁止推倒重来
- 先分析现有代码，优先复用，最小改动

**文件组织**: 
- 源代码: `src/`(后端) `frontend/src/`(前端)
- 文档: `文档/` 目录（查 `文档/文档总索引.md`）

---

## 📋 检查清单

- [ ] 函数超 40 行？用卫语句？有魔法值？
- [ ] 能拆更小步骤？只给必要上下文？
- [ ] 用户可见文本用 `t()`？翻译 JSON 同步？
- [ ] 先分析现有代码？优先复用？最小改动？

---

## 🔗 按需加载

遇到具体问题时，AI 自动加载 `.kiro/rules/` 下的详细规则：
- TypeScript/导出 → `typescript-export-rules.md`
- i18n/翻译 → `i18n-translation-rules.md`
- 代码质量 → `coding-quality-standards.md`
- 项目结构 → `structure.md`
- 安全/OWASP → `security-review-checklist.md`
- FastAPI → `python-fastapi-patterns.md`
