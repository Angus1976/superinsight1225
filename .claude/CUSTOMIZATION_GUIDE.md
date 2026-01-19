# Claude 命令自定义指南

## 概述

本指南说明如何根据 SuperInsight 项目的实际情况自定义和适配 Claude 命令。这些命令基于 [habit-tracker](https://github.com/coleam00/habit-tracker) 项目的 PIV 方法论。

## 命令文件结构

每个命令文件都是一个 Markdown 文件，包含以下部分：

```markdown
---
description: 命令的简短描述
argument-hint: [参数提示]（可选）
---

# 命令标题

## 目标
命令的目标和用途

## 过程
执行步骤

## 输出
期望的输出结果
```

## 已适配的命令

### 1. `/init-project` ✅

**原始版本**: 针对 habit-tracker（使用 uv、SQLite）

**适配版本**: 针对 SuperInsight（使用 pip、PostgreSQL、Docker）

**主要变更**:
- 依赖安装：`uv sync` → `pip install -r requirements.txt`
- 系统初始化：添加 `python main.py`
- 数据库：SQLite → PostgreSQL（需要 .env 配置）
- 添加 Docker 启动选项

**文件位置**: `.claude/commands/init-project.md`

---

### 2. `/validation:validate` ✅

**原始版本**: 针对 habit-tracker（使用 ruff）

**适配版本**: 针对 SuperInsight（使用 black、isort、mypy）

**主要变更**:
- Linting: `ruff` → `black` + `isort` + `mypy`
- 添加前端 TypeScript 检查
- 添加前端测试和 linting
- 更新健康检查端点

**文件位置**: `.claude/commands/validation/validate.md`

---

### 3. `/commit` ✅

**原始版本**: 简单的提交指令

**适配版本**: 详细的 Conventional Commits 规范

**主要变更**:
- 添加详细的提交消息格式说明
- 添加类型和作用域示例
- 添加最佳实践指南
- 添加提交消息模板

**文件位置**: `.claude/commands/commit.md`

---

## 需要适配的命令

### 1. `/core_piv_loop:prime`

**当前状态**: 通用版本

**建议适配**:
- 添加 SuperInsight 特定的项目结构说明
- 添加关键文件列表（src/app.py、frontend/src/App.tsx 等）
- 添加技术栈说明（PostgreSQL、Redis、Neo4j、Label Studio）

**适配步骤**:
1. 打开 `.claude/commands/core_piv_loop/prime.md`
2. 更新"Identify Key Files"部分
3. 添加 SuperInsight 特定的架构说明

---

### 2. `/core_piv_loop:plan-feature`

**当前状态**: 通用版本

**建议适配**:
- 添加 SuperInsight 的代码约定引用
- 添加项目特定的模式示例
- 更新验证命令为 SuperInsight 的命令

**适配步骤**:
1. 打开 `.claude/commands/core_piv_loop/plan-feature.md`
2. 在"Patterns to Follow"部分添加 SuperInsight 示例
3. 更新"VALIDATION COMMANDS"部分

---

### 3. `/validation:code-review`

**当前状态**: 通用版本

**建议适配**:
- 添加 SuperInsight 的代码规范引用
- 添加 TypeScript 导出规范检查
- 添加异步安全规范检查

**适配步骤**:
1. 打开 `.claude/commands/validation/code-review.md`
2. 添加对 `.kiro/steering/` 规范的引用
3. 添加项目特定的检查项

---

## 自定义命令示例

### 示例 1: 创建数据库迁移命令

创建 `.claude/commands/db-migrate.md`:

```markdown
---
description: Create and apply database migration
argument-hint: [migration-message]
---

# Database Migration

Create a new Alembic migration and apply it.

## Process

### 1. Create Migration

```bash
alembic revision --autogenerate -m "$ARGUMENTS"
```

### 2. Review Migration

Check the generated migration file in `alembic/versions/`.

### 3. Apply Migration

```bash
alembic upgrade head
```

### 4. Verify

```bash
# Check current revision
alembic current

# Check migration history
alembic history
```

## Output

- Migration file created in `alembic/versions/`
- Database schema updated
- Migration applied successfully
```

---

### 示例 2: 创建 Docker 重启命令

创建 `.claude/commands/docker-restart.md`:

```markdown
---
description: Restart Docker services
---

# Restart Docker Services

Stop and restart all Docker services for SuperInsight.

## Process

### 1. Stop Services

```bash
docker-compose down
```

### 2. Remove Volumes (Optional)

```bash
# Only if you want to reset data
docker-compose down -v
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Check Status

```bash
docker-compose ps
docker-compose logs -f superinsight-api
```

## Output

- All services restarted
- Logs showing successful startup
- Services accessible at configured ports
```

---

## 命令适配清单

使用此清单确保命令已正确适配：

### 通用检查
- [ ] 命令描述清晰准确
- [ ] 参数提示正确（如需要）
- [ ] 步骤顺序合理
- [ ] 输出描述明确

### SuperInsight 特定检查
- [ ] 使用正确的包管理器（pip 而非 uv）
- [ ] 使用正确的数据库（PostgreSQL 而非 SQLite）
- [ ] 引用正确的文件路径（src/ 而非 app/）
- [ ] 使用正确的端口（8000 for API, 5173 for frontend）
- [ ] 引用项目特定的规范文档（.kiro/steering/）

### 验证命令检查
- [ ] 使用 black、isort、mypy（而非 ruff）
- [ ] 包含前端 TypeScript 检查
- [ ] 包含前端测试和 linting
- [ ] 使用正确的健康检查端点

### 文档引用检查
- [ ] 引用 CLAUDE.md 而非 habit-tracker 文档
- [ ] 引用 .kiro/steering/ 规范
- [ ] 引用 .claude/reference/ 最佳实践

---

## 命令测试

在适配命令后，按以下步骤测试：

### 1. 语法测试

```bash
# 检查 Markdown 语法
cat .claude/commands/your-command.md
```

### 2. 命令可用性测试

在 Claude Code 中：
1. 输入 `/`
2. 查找你的命令
3. 确认命令出现在列表中

### 3. 执行测试

1. 执行命令
2. 验证输出是否符合预期
3. 检查是否有错误

### 4. 文档测试

1. 阅读命令输出
2. 确认说明清晰
3. 验证示例正确

---

## 命令维护

### 定期检查

每月检查一次：
- [ ] 命令是否仍然有效
- [ ] 依赖是否有更新
- [ ] 路径是否仍然正确
- [ ] 文档引用是否有效

### 更新流程

当项目结构或工具链变更时：

1. **识别影响**: 确定哪些命令受影响
2. **更新命令**: 修改命令文件
3. **测试命令**: 验证更新后的命令
4. **更新文档**: 更新相关文档
5. **通知团队**: 告知团队命令变更

---

## 最佳实践

### 1. 保持命令简单

- 每个命令专注于一个任务
- 避免过于复杂的逻辑
- 提供清晰的步骤

### 2. 提供上下文

- 说明何时使用命令
- 提供使用示例
- 解释预期输出

### 3. 错误处理

- 说明常见错误
- 提供故障排除步骤
- 包含回滚方法

### 4. 文档引用

- 引用项目特定的文档
- 提供相关资源链接
- 保持引用最新

### 5. 版本控制

- 在命令文件中记录版本
- 记录重大变更
- 保留变更历史

---

## 参考资源

### 内部资源
- **项目配置**: `CLAUDE.md`
- **命令指南**: `.claude/COMMANDS_GUIDE.md`
- **PIV 方法论**: `.kiro/steering/piv-methodology-integration.md`
- **开发规范**: `.kiro/steering/`

### 外部资源
- **原始项目**: https://github.com/coleam00/habit-tracker
- **Conventional Commits**: https://www.conventionalcommits.org/
- **Markdown 语法**: https://www.markdownguide.org/

---

## 获取帮助

如果在适配命令时遇到问题：

1. 查看原始 habit-tracker 项目的命令
2. 参考 `.claude/COMMANDS_GUIDE.md`
3. 查看 `.kiro/steering/` 中的规范文档
4. 参考本指南的示例

---

**记住**: 命令是为了提高效率，不是增加复杂性。保持简单、清晰、有用！
