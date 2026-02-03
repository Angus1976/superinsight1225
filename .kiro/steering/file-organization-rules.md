# 文件组织规范

**Version**: 2.0  
**Last Updated**: 2026-02-03  
**Priority**: HIGH

## 核心原则

1. **分类优先** - 所有文件按功能分类
2. **结构清晰** - 目录结构反映项目架构
3. **一致性** - 所有开发人员遵循相同规范

## 文件分类

### 源代码
- **后端**: `src/` - 所有 Python 源代码
- **前端**: `frontend/src/` - 所有 TypeScript/React 代码

### 测试
- **单元测试**: `tests/unit/`
- **集成测试**: `tests/integration/`
- **API 测试**: `tests/api/`

### 文档
- **项目文档**: `文档/` - 按功能分类
- **规范文档**: `.kiro/steering/` - 开发规范
- **功能规范**: `.kiro/specs/{feature-name}/` - 每个功能 3 个文件
  - requirements.md
  - design.md
  - tasks.md

### 脚本
- **自动化脚本**: `scripts/` - 按功能分类

### 配置
- **应用配置**: `config/`
- **环境配置**: 根目录 (`.env*`)
- **Docker 配置**: 根目录 (`docker-compose*.yml`, `Dockerfile*`)

## 根目录允许的文件

**必需文件**:
- `README.md`, `requirements.txt`, `package.json`
- `.env*`, `docker-compose*.yml`, `Dockerfile*`
- `alembic.ini`, `prometheus.yml`
- `.gitignore`, `LICENSE`, `CHANGELOG.md`

**禁止**:
- 源代码文件 (`.py`, `.ts`, `.tsx`)
- 测试文件 (`test_*.py`, `*.test.ts`)
- 文档文件 (`.md` 除了 README.md)
- 脚本文件 (`.sh`)

## 开发流程检查点

### 创建新文件时
- [ ] 确定文件类型
- [ ] 选择合适的目录
- [ ] 遵循命名规范
- [ ] 不在根目录创建

### 代码审查时
- [ ] 检查文件位置是否正确
- [ ] 验证命名是否符合规范
- [ ] 确认根目录没有新增不允许的文件

## 执行规则

### MUST (必须)
1. 所有新增源代码放在 `src/` 或 `frontend/src/`
2. 所有测试文件放在 `tests/` 目录
3. 所有文档放在 `文档/` 目录
4. 所有脚本放在 `scripts/` 目录
5. 根目录只包含允许的文件

### MUST NOT (禁止)
1. 在根目录创建源代码文件
2. 在根目录创建测试文件
3. 在根目录创建文档文件 (除了 README.md)
4. 在根目录创建脚本文件

## 违规处理

发现违规文件 → 通知开发者 → 开发者修正 → 验证修正 → 接受 PR

---

**此规范为强制性规范。违反规范将导致 PR 被拒绝。**
