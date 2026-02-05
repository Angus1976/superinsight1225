# 详细规则文档目录

**目录**: `.kiro/rules/`  
**用途**: 存放所有详细规则文档，按需加载  
**最后更新**: 2026-02-04

---

## 📌 重要说明

**此目录下的文档不会在对话开始时自动加载。**

- 对话开始时只加载 `.kiro/steering/CORE.md`
- 当需要详细规则时，AI 会按需引用此目录下的文档
- 使用方式：`#File:.kiro/rules/{文档名}`

---

## 📁 文档列表

### 🔴 CRITICAL（关键规则）

| 文档 | 说明 | 大小 |
|------|------|------|
| coding-quality-standards.md | 完整的代码质量标准 | 7.5K |
| async-sync-safety-quick-reference.md | 异步安全规则 | 4.4K |

### 🟡 HIGH（高优先级）

| 文档 | 说明 | 大小 |
|------|------|------|
| ai-development-efficiency.md | 完整的 AI 开发效率规范 | 12K |
| typescript-export-rules.md | TypeScript 导出规范 | 4.6K |
| i18n-translation-rules.md | 国际化翻译规范 | 3.0K |
| file-organization-rules.md | 完整的文件组织规范 | 2.5K |
| documentation-minimalism-rules.md | 完整的文档规范 | 3.3K |

### 🟢 MEDIUM（项目信息）

| 文档 | 说明 | 大小 |
|------|------|------|
| product.md | 产品介绍 | 1.1K |
| structure.md | 项目结构 | 2.3K |
| tech.md | 技术栈 | 1.7K |

### 🔵 INFO（工具指南）

| 文档 | 说明 | 大小 |
|------|------|------|
| auto-approve-guide.md | Kiro 自动确认配置 | 1.4K |

---

## 💡 使用示例

### 场景 1：需要完整的代码质量标准

```
AI：读取 #File:.kiro/rules/coding-quality-standards.md
```

### 场景 2：遇到 TypeScript 导出问题

```
AI：读取 #File:.kiro/rules/typescript-export-rules.md
```

### 场景 3：需要了解项目结构

```
AI：读取 #File:.kiro/rules/structure.md
```

---

## 🔄 与 steering 目录的关系

| 目录 | 用途 | 加载方式 | 文档数量 |
|------|------|---------|---------|
| `.kiro/steering/` | 核心规则 | 自动加载 | 2 个（CORE.md + README.md） |
| `.kiro/rules/` | 详细规则 | 按需加载 | 11 个 |

---

## 📊 优化效果

**移动前**（所有文档在 `.kiro/steering/`）：
- 对话开始加载 13 个文档
- Token 消耗 ~8000 tokens
- 加载时间 ~10 秒

**移动后**（详细文档在 `.kiro/rules/`）：
- 对话开始加载 1 个文档（CORE.md）
- Token 消耗 ~800 tokens
- 加载时间 ~1 秒

**改善**：
- Token 消耗 ↓ 90%
- 加载时间 ↓ 90%
- 彻底避免详细文档被自动加载

---

## 🛠️ 维护指南

### 添加新规则文档

1. 在 `.kiro/rules/` 目录创建新文档
2. 使用总分结构（核心原则 → 快速参考 → 详细规则）
3. 在 `.kiro/steering/CORE.md` 的"详细规则"部分添加索引
4. 更新本 README.md 的文档列表

### 修改现有文档

1. 直接修改 `.kiro/rules/` 目录下的文档
2. 不需要担心 Token 消耗（不会自动加载）
3. 保持总分结构，方便按需查阅

### 删除过时文档

1. 从 `.kiro/rules/` 目录删除文档
2. 从 `.kiro/steering/CORE.md` 的索引中删除
3. 更新本 README.md 的文档列表

---

**记住：此目录下的文档不会自动加载，只在需要时按需引用。**
