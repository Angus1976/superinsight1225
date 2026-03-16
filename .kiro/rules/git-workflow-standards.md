---
inclusion: manual
---

# Git 工作流规范 (Git Workflow Standards)

**Version**: 1.0
**Status**: ✅ Active
**Last Updated**: 2026-03-16
**Priority**: HIGH
**来源**: 参考 everything-claude-code git-workflow 规则，适配本项目
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则

**小步提交 > 原子性 > 可追溯性**

---

## 🎯 Commit 规范（Conventional Commits）

### 格式
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Type 类型
| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(annotation): 添加 AI 预标注批量处理` |
| `fix` | 修复 Bug | `fix(auth): 修复 JWT token 刷新竞态条件` |
| `refactor` | 重构（不改功能） | `refactor(api): 统一错误响应格式` |
| `docs` | 文档更新 | `docs: 更新部署指南` |
| `test` | 测试相关 | `test(quality): 添加 Ragas 评估单元测试` |
| `chore` | 构建/工具 | `chore: 升级 SQLAlchemy 到 2.0.35` |
| `perf` | 性能优化 | `perf(query): 优化标注数据分页查询` |
| `security` | 安全修复 | `security(upload): 限制文件上传类型` |

### Scope 范围（本项目）
- `api` - API 路由和端点
- `auth` - 认证授权
- `annotation` - 标注功能
- `quality` - 质量评估
- `sync` - 数据同步
- `i18n` - 国际化
- `frontend` - 前端通用
- `db` - 数据库和迁移
- `docker` - 容器化
- `config` - 配置管理

### 规则
- Description 用中文或英文，保持一致
- 不超过 72 个字符
- 不以句号结尾
- 使用祈使语气（"添加" 而非 "添加了"）

---

## 🌿 分支策略

```
main (生产)
  └── develop (开发)
       ├── feature/annotation-batch  (功能分支)
       ├── fix/jwt-refresh           (修复分支)
       └── refactor/api-response     (重构分支)
```

### 分支命名
- `feature/<简短描述>` - 新功能
- `fix/<简短描述>` - Bug 修复
- `refactor/<简短描述>` - 重构
- `hotfix/<简短描述>` - 紧急修复（从 main 分出）

### 合并规则
- feature → develop：Squash merge
- develop → main：Merge commit
- hotfix → main：直接 merge，然后 cherry-pick 到 develop

---

## 📋 PR 检查清单

- [ ] Commit message 符合 Conventional Commits 格式
- [ ] 分支名称符合命名规范
- [ ] 代码通过 lint 和 type check
- [ ] 新功能有对应测试
- [ ] 前端改动包含 i18n 翻译
- [ ] 安全审查通过（见 security-review-checklist.md）
- [ ] 数据库变更有 Alembic migration

---

## ⚠️ 禁止事项

- 禁止直接 push 到 main 分支
- 禁止在 commit 中包含 `.env`、密钥、token
- 禁止 force push 到共享分支
- 禁止超大 commit（单次改动 > 500 行需拆分）

---

## 🔗 相关资源

- **安全审查**: `.kiro/rules/security-review-checklist.md`
- **代码质量**: `.kiro/rules/coding-quality-standards.md`
