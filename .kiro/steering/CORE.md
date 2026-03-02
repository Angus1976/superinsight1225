# 核心开发规则（对话开始时唯一加载）

**Version**: 1.0  
**Last Updated**: 2026-02-04  
**Priority**: CRITICAL

---

## 🎯 核心原则（必读）

### 代码质量
**可读性 > 可维护性 > 可测试性 > 健壮性 > 性能**

- 函数 20-40 行，类 200-400 行
- 卫语句：提前返回，减少嵌套
- 显式优于隐式：不用魔法，不用可变默认值
- 防御性编程：永远不信任外部输入

### AI 开发效率
**短而精的上下文 > 长而全的上下文**

- 每次只做一件事
- 拆小步：大任务拆成可验证的小步
- 渐进式给上下文：先给核心问题，需要时再补充
- 明确约束和格式：告诉 AI 只输出什么
- 用 Spec 工作流：观全局（Spec 文件），做细节（单个任务）

### 文档规范
**代码即文档 > 必要的文档 > 冗长的文档**

- 只生成 Spec 三件套：requirements.md + design.md + tasks.md
- 文档大小限制：requirements < 5000字，design < 3000字，tasks < 2000字
- 禁止生成：诊断报告、执行报告、实现总结、测试指南

### 国际化（i18n）
**所有前端用户可见文本必须使用 i18n，禁止硬编码中文或英文**

- 新增页面、新增/修改功能时，所有用户可见字符串必须用 `t()` 包裹
- 使用 `useTranslation('aiAnnotation')` 等命名空间 hook
- 翻译 key 同步写入 `frontend/src/locales/zh/` 和 `frontend/src/locales/en/` 对应 JSON
- 区分字符串与对象属性：HTML 属性用字符串 `t('key')`，JSX 子元素用 `{t('key')}`
- 不国际化的内容：代码注释、console.log、mock 数据中的 name 字段
- 详细规范 → `.kiro/rules/i18n-translation-rules.md`

### 文件组织
**分类优先 > 结构清晰 > 一致性**

- 源代码：`src/` (后端) 或 `frontend/src/` (前端)
- 测试：`tests/` 目录
- 文档：`文档/` 目录（按分类组织，见文档总索引）
- 脚本：`scripts/` 目录
- 根目录：只放配置文件，不放源代码

### 项目文档索引
**快速查找项目文档 → 查看 `文档/文档总索引.md`**

- 📚 **64 个文档**，按 10 个分类组织
- 🔍 **按场景查找**：快速启动、Docker 部署、云端部署、多语言支持、问题排查
- 👥 **按角色查找**：项目经理、后端开发、前端开发、测试工程师、运维工程师
- 📊 **项目历史**：需求、设计、实现、问题修复、任务完成、状态报告

**重要文档快速链接**：
- 快速启动：`文档/快速开始/快速启动指南.md`
- 部署指南：`文档/部署指南/部署说明.md`
- 问题修复：`文档/问题修复/` 目录
- 任务进度：`文档/任务完成/` 目录

---

## 📋 快速检查清单

### 代码质量
- [ ] 函数是否超过 40 行？
- [ ] 是否使用了卫语句？
- [ ] 是否有魔法值？
- [ ] 错误处理是否清晰？

### AI 开发
- [ ] 能拆成更小的步骤吗？
- [ ] 只给了必要的上下文吗？
- [ ] 明确了输出格式吗？
- [ ] 对话超过 10 轮了吗？

### 文档
- [ ] 这个文档是必须的吗？
- [ ] 能否合并到现有文档？
- [ ] 内容是否超过限制？
- [ ] 是否按分类保存到 `文档/` 对应子目录？
- [ ] 是否更新了 `文档/文档总索引.md`？

### 文件组织
- [ ] 文件是否放在正确的目录？
- [ ] 根目录是否有不该有的文件？
- [ ] 文档是否按分类保存？

### 国际化（i18n）
- [ ] 新增/修改的用户可见文本是否都用了 `t()`？
- [ ] 中文和英文翻译 JSON 是否同步更新？
- [ ] 翻译 key 是否有重复？

---

## 🔗 详细规则（按需查阅）

当需要更详细的规则时，请参考 `.kiro/rules/` 目录下的文档：

**智能加载指南**: `.kiro/rules/智能加载映射表.md` - 关键词到文档的映射关系

### CRITICAL（关键规则）
- `.kiro/rules/coding-quality-standards.md` - 完整的代码质量标准
- `.kiro/rules/async-sync-safety-quick-reference.md` - 异步安全规则

### HIGH（高优先级）
- `.kiro/rules/ai-development-efficiency.md` - 完整的 AI 开发效率规范
- `.kiro/rules/typescript-export-rules.md` - TypeScript 导出规范
- `.kiro/rules/i18n-translation-rules.md` - 国际化翻译规范
- `.kiro/rules/file-organization-rules.md` - 完整的文件组织规范
- `.kiro/rules/documentation-minimalism-rules.md` - 完整的文档规范
- `.kiro/rules/document-generation-rules.md` - 文档生成规范

### MEDIUM（项目信息）
- `.kiro/rules/product.md` - 产品介绍
- `.kiro/rules/structure.md` - 项目结构
- `.kiro/rules/tech.md` - 技术栈

### INFO（工具指南）
- `.kiro/rules/auto-approve-guide.md` - Kiro 自动确认配置

### 项目文档（重要）
- `文档/文档总索引.md` - **项目所有文档的总索引**（64 个文档，10 个分类）
- `文档/快速开始/` - 快速启动和入门指南
- `文档/部署指南/` - 系统部署和环境配置
- `文档/问题修复/` - 问题诊断和修复记录
- `文档/任务完成/` - 任务完成报告和进度
- `文档/国际化翻译/` - 多语言支持文档

---

## 💡 使用说明

**对于 AI（Kiro）**：
- 对话开始时只加载此文档（CORE.md）
- **智能加载**：根据对话内容自动判断并加载相关文档
  - TypeScript 问题 → 自动加载 `.kiro/rules/typescript-export-rules.md`
  - 国际化问题 → 自动加载 `.kiro/rules/i18n-translation-rules.md`
  - 文档生成 → 自动加载 `.kiro/rules/document-generation-rules.md`
  - 项目结构 → 自动加载 `.kiro/rules/structure.md`
  - 代码质量 → 自动加载 `.kiro/rules/coding-quality-standards.md`
- 主动识别关键词，无需用户明确要求

**对于开发人员**：
- 日常开发只需记住核心原则和检查清单
- 遇到具体问题时查阅详细规则文档

---

**记住：这是唯一在对话开始时加载的文档。其他文档由 AI 根据对话内容智能加载。**
