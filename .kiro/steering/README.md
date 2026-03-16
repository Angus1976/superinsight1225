# Steering Rules 说明

**最后更新**: 2026-02-04  
**维护者**: Angus Liu

---

## 🚀 重要变更：按需加载策略

**从 2026-02-04 开始，Kiro 只在对话开始时加载 `CORE.md`，其他文档按需引用。**

### 为什么这样做？

- **节省 Token**: 对话开始时只加载 ~100 行核心规则，节省 90% Token
- **提高速度**: 加载时间从 ~10 秒降至 ~1 秒
- **按需加载**: 遇到具体问题时再读取详细文档

### 如何使用？

**对于 AI（Kiro）**：
- 对话开始时自动加载 `CORE.md`
- **智能加载**：根据对话内容自动判断并加载相关文档
  - 识别关键词：TypeScript、国际化、i18n、文档生成、项目结构等
  - 主动加载相关规则文档，无需用户明确要求
  - 例如：用户提到 "TypeScript 导出报错" → 自动加载 `typescript-export-rules.md`

**对于开发人员**：
- 日常开发只需记住 `CORE.md` 中的核心原则
- 遇到具体问题时查阅详细规则文档
- AI 会根据你的问题自动加载相关规则

---

## 📋 文档结构

### ⭐ .kiro/steering/（自动加载目录）
**只包含 2 个文件，对话开始时自动加载**

- **CORE.md** - 核心开发规则（唯一的规则文档）
- **README.md** - 说明文档（本文件）

### 📁 .kiro/rules/（按需加载目录）
**包含所有详细规则文档，不会自动加载**

#### 🎯 智能加载指南
- **智能加载映射表.md** - 关键词到文档的映射关系（AI 专用）

#### 🔴 CRITICAL（关键规则）
- **coding-quality-standards.md** - 完整的代码质量标准
- **async-sync-safety-quick-reference.md** - 异步安全规则

#### 🟡 HIGH（高优先级）
- **ai-development-efficiency.md** - 完整的 AI 开发效率规范
- **typescript-export-rules.md** - TypeScript 导出规范
- **i18n-translation-rules.md** - 国际化翻译规范
- **file-organization-rules.md** - 完整的文件组织规范
- **documentation-minimalism-rules.md** - 完整的文档规范
- **document-generation-rules.md** - 文档生成规范

#### 🟢 MEDIUM（项目信息）
- **product.md** - 产品介绍
- **structure.md** - 项目结构
- **tech.md** - 技术栈

#### 🔵 INFO（工具指南）
- **auto-approve-guide.md** - Kiro 自动确认配置

#### 🟣 ECC-ADAPTED（来自 everything-claude-code 适配）
- **security-review-checklist.md** - 安全审查清单（OWASP Top 10）
- **git-workflow-standards.md** - Git 工作流规范（Conventional Commits）
- **python-fastapi-patterns.md** - Python/FastAPI 最佳实践
- **tdd-workflow.md** - TDD 工作流（RED-GREEN-REFACTOR）
- **api-design-patterns.md** - API 设计规范（REST、分页、错误码）

---

## 📊 加载策略对比

| 项目 | 旧策略 | 新策略 | 节省 |
|------|--------|--------|------|
| 对话开始加载文档数 | 13 个 | 1 个 | 92% |
| 对话开始加载行数 | ~1500 行 | ~100 行 | 93% |
| 对话开始 Token 消耗 | ~8000 tokens | ~800 tokens | 90% |
| 加载时间 | ~10 秒 | ~1 秒 | 90% |

---

## 💡 使用示例

### 场景 1：日常开发（不需要额外文档）
```
用户："帮我优化这个函数"
AI：参考 CORE.md 中的代码质量原则 → 直接优化
```

### 场景 2：TypeScript 导出问题（智能加载）
```
用户："TypeScript 导出报错 TS2308"
AI：
1. 识别关键词 "TypeScript 导出"
2. 自动加载 typescript-export-rules.md
3. 根据详细规则解决问题
```

### 场景 3：国际化翻译（智能加载）
```
用户："前端的翻译文件怎么组织？"
AI：
1. 识别关键词 "翻译"
2. 自动加载 i18n-translation-rules.md
3. 提供详细的翻译规范
```

### 场景 4：文档生成（智能加载）
```
用户："帮我生成一个需求文档"
AI：
1. 识别关键词 "文档生成"
2. 自动加载 document-generation-rules.md
3. 按规范生成文档并保存到正确位置
```

---

## 🎯 核心原则速查

### 代码质量
**可读性 > 可维护性 > 可测试性 > 健壮性 > 性能**

### AI 开发
**短而精的上下文 > 长而全的上下文**

### 文档
**代码即文档 > 必要的文档 > 冗长的文档**

### 文件组织
**分类优先 > 结构清晰 > 一致性**

---

## 🛠️ 维护指南

### 修改 CORE.md
- CORE.md 是唯一自动加载的文档，修改时要特别谨慎
- 只保留最核心的原则和检查清单
- 保持在 100 行左右

### 修改详细规则文档
- 所有详细规则文档都在 `.kiro/rules/` 目录
- 可以包含详细内容，不影响对话开始时的加载
- 保持总分结构，方便按需查阅

### 添加新规则
1. 评估是否应该加入 CORE.md（非常谨慎）
2. 如果不是核心规则，在 `.kiro/rules/` 目录创建新文档
3. 在 CORE.md 的"详细规则"部分添加索引

---

## 📝 变更日志

### 2026-03-16 - everything-claude-code 适配集成
- ✅ 新增 5 个 ECC 适配规则文档到 `.kiro/rules/`
- ✅ 新增 2 个 Kiro hooks（写入前安全扫描 + 任务完成后验证）
- ✅ 更新智能加载映射表，添加 ECC 相关关键词
- ✅ 更新 CORE.md 索引，添加 ECC-ADAPTED 分类
- ✅ 完全保留原有项目结构、Spec 和规则

### 2026-02-04 - 按需加载策略（第二次优化）
- ✅ 创建 `.kiro/rules/` 目录存放所有详细规则文档
- ✅ 将 11 个详细文档从 `.kiro/steering/` 移至 `.kiro/rules/`
- ✅ `.kiro/steering/` 只保留 CORE.md 和 README.md
- ✅ 彻底避免详细文档被自动加载
- ✅ 对话开始时 Token 消耗降低 95%+

### 2026-02-04 - 按需加载策略（第一次优化）
- ✅ 创建 CORE.md 作为唯一自动加载文档
- ✅ 所有其他文档标记为 `inclusion: manual`
- ✅ 删除过时的 async-sync-safety.md（保留快速参考版本）
- ✅ 对话开始时 Token 消耗降低 90%

### 2026-02-04 - 总分结构优化
- ✅ 所有规范文档采用总分结构
- ✅ 精简项目信息类文档
- ✅ 建立文档协同关系

---

## 🔗 相关资源

- **模板库**：`.kiro/templates/`
- **项目文档**：`文档/`
- **代码示例**：`examples/`
- **测试用例**：`tests/`

---

**记住：现在对话开始时只加载 CORE.md，其他文档按需引用。这大幅提升了效率！**
