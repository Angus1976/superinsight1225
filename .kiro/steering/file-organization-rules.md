# 文件组织规范

**Version**: 1.0  
**Status**: ✅ Active  
**Last Updated**: 2026-01-28  
**Priority**: HIGH

## 概述

本规范建立了 SuperInsight 项目的文件组织标准，确保所有新增文件都按照功能分类放置在适当的目录中，而不是随意保存在根目录或其他位置。这提高了项目的可维护性、可读性和开发效率。

## 核心原则

### 1. 分类优先
- 所有新增文件必须按功能分类
- 不允许在根目录随意保存文件
- 每个文件类型都有明确的存放位置

### 2. 结构清晰
- 目录结构反映项目架构
- 相关文件聚集在一起
- 便于查找和维护

### 3. 一致性
- 所有开发人员遵循相同规范
- 保持项目结构的一致性
- 便于新成员快速上手

## 文件分类规范

### 1. 源代码文件

#### 后端代码 (`src/`)

**规则**: 所有 Python 源代码必须放在 `src/` 目录下，按功能模块组织

**目录结构**:
```
src/
├── api/                    # API 路由和端点
├── models/                 # 数据库模型
├── schemas/                # Pydantic 请求/响应模型
├── services/               # 业务逻辑服务
├── utils/                  # 工具函数
├── config/                 # 配置管理
├── database/               # 数据库连接和工具
├── security/               # 认证和授权
├── ai/                     # AI/ML 集成
├── quality/                # 质量管理
├── billing/                # 计费系统
├── monitoring/             # 监控和告警
├── sync/                   # 数据同步
├── knowledge_graph/        # 知识图谱
├── label_studio/           # Label Studio 集成
├── i18n/                   # 国际化
├── desensitization/        # 数据脱敏
├── multi_tenant/           # 多租户
└── export/                 # 数据导出
```

**示例**:
- ✅ `src/api/auth.py` - 认证 API
- ✅ `src/services/user_service.py` - 用户服务
- ✅ `src/models/user.py` - 用户模型
- ❌ `auth.py` (根目录)
- ❌ `user_service.py` (根目录)

#### 前端代码 (`frontend/src/`)

**规则**: 所有 TypeScript/React 源代码必须放在 `frontend/src/` 目录下，按功能组织

**目录结构**:
```
frontend/src/
├── components/             # 可复用 UI 组件
├── pages/                  # 页面级组件
├── hooks/                  # 自定义 React hooks
├── stores/                 # Zustand 状态管理
├── services/               # API 客户端函数
├── utils/                  # 工具函数
├── types/                  # TypeScript 类型定义
├── locales/                # 国际化翻译文件
├── styles/                 # 全局样式
└── assets/                 # 静态资源
```

**示例**:
- ✅ `frontend/src/components/UserForm.tsx` - 用户表单组件
- ✅ `frontend/src/hooks/useUser.ts` - 用户 hook
- ✅ `frontend/src/services/userApi.ts` - 用户 API 服务
- ❌ `UserForm.tsx` (根目录)
- ❌ `useUser.ts` (根目录)

### 2. 测试文件

#### 单元测试 (`tests/unit/`)

**规则**: 单元测试文件放在 `tests/unit/` 目录下，按模块组织

**命名规范**: `test_{module_name}.py`

**示例**:
- ✅ `tests/unit/test_user_service.py` - 用户服务单元测试
- ✅ `tests/unit/test_auth_utils.py` - 认证工具单元测试
- ❌ `test_user_service.py` (根目录)

#### 集成测试 (`tests/integration/`)

**规则**: 集成测试文件放在 `tests/integration/` 目录下

**命名规范**: `test_{feature}_integration.py`

**示例**:
- ✅ `tests/integration/test_label_studio_integration.py` - Label Studio 集成测试
- ✅ `tests/integration/docker-compose-integration-test.py` - Docker 集成测试
- ✅ `tests/integration/test_label_studio_sync.py` - Label Studio 同步测试
- ❌ `docker-compose-integration-test.py` (根目录)

#### API 测试 (`tests/api/`)

**规则**: API 端点测试放在 `tests/api/` 目录下

**命名规范**: `test_{endpoint_name}.py`

**示例**:
- ✅ `tests/api/test_login_api.py` - 登录 API 测试
- ✅ `tests/api/test_user_api.py` - 用户 API 测试
- ❌ `test_login_api.py` (根目录)

#### 性能测试 (`tests/performance/`)

**规则**: 性能和压力测试放在 `tests/performance/` 目录下

**示例**:
- ✅ `tests/performance/test_api_performance.py` - API 性能测试
- ✅ `tests/performance/test_database_performance.py` - 数据库性能测试

#### 属性测试 (`tests/property/`)

**规则**: 属性基测试放在 `tests/property/` 目录下

**示例**:
- ✅ `tests/property/test_user_properties.py` - 用户属性测试
- ✅ `tests/property/test_billing_properties.py` - 计费属性测试

### 3. 文档文件

#### 项目文档 (`文档/`)

**规则**: 所有项目文档必须放在 `文档/` 目录下，按功能分类

**分类目录**:
```
文档/
├── 快速开始/               # 快速启动指南
├── 部署指南/               # 系统部署和配置
├── Docker/                 # Docker 容器化
├── 功能实现/               # 功能特性实现
├── 问题修复/               # 问题诊断和修复
├── 状态报告/               # 系统状态报告
├── 国际化翻译/             # 多语言支持
├── 开发流程/               # 开发规范和流程
├── 索引和说明/             # 索引和参考文档
└── 其他/                   # 其他文档
```

**命名规范**: 使用中文命名，清晰表达内容

**示例**:
- ✅ `文档/快速开始/快速启动指南.md` - 快速启动指南
- ✅ `文档/部署指南/Docker部署.md` - Docker 部署指南
- ✅ `文档/问题修复/登录问题修复.md` - 登录问题修复
- ❌ `QUICK_START.md` (根目录)
- ❌ `DEPLOYMENT.md` (根目录)

#### 规范文档 (`.kiro/steering/`)

**规则**: 项目规范和指导文档放在 `.kiro/steering/` 目录下

**示例**:
- ✅ `.kiro/steering/file-organization-rules.md` - 文件组织规范
- ✅ `.kiro/steering/typescript-export-rules.md` - TypeScript 导出规范
- ✅ `.kiro/steering/i18n-translation-rules.md` - 国际化翻译规范

#### 规范文档 (`.kiro/specs/`)

**规则**: 功能规范文档放在 `.kiro/specs/{feature-name}/` 目录下

**结构**:
```
.kiro/specs/{feature-name}/
├── requirements.md         # 需求文档
├── design.md              # 设计文档
├── tasks.md               # 任务列表
└── IMPLEMENTATION_SUMMARY.md  # 实现总结
```

**示例**:
- ✅ `.kiro/specs/label-studio-jwt-auth/requirements.md`
- ✅ `.kiro/specs/audit-security/design.md`
- ❌ `requirements.md` (根目录)

### 4. 脚本文件

#### 自动化脚本 (`scripts/`)

**规则**: 所有自动化脚本必须放在 `scripts/` 目录下，按功能分类

**目录结构**:
```
scripts/
├── deployment/             # 部署脚本
├── testing/                # 测试脚本
├── maintenance/            # 维护脚本
├── utilities/              # 工具脚本
└── docker/                 # Docker 相关脚本
```

**命名规范**: 使用 kebab-case，清晰表达功能

**示例**:
- ✅ `scripts/deployment/deploy-to-tcb.sh` - TCB 部署脚本
- ✅ `scripts/testing/run-all-tests.sh` - 运行所有测试
- ✅ `scripts/maintenance/backup-database.sh` - 数据库备份
- ❌ `deploy.sh` (根目录)
- ❌ `test.sh` (根目录)

### 5. 配置文件

#### 应用配置 (`config/`)

**规则**: 应用配置文件放在 `config/` 目录下

**示例**:
- ✅ `config/knowledge_graph.yaml` - 知识图谱配置
- ✅ `config/real_time_alerts.yaml` - 实时告警配置

#### 环境配置 (根目录)

**规则**: 环境配置文件可以放在根目录

**允许的文件**:
- `.env` - 环境变量
- `.env.example` - 环境变量示例
- `.env.docker` - Docker 环境变量
- `.env.production` - 生产环境变量

#### Docker 配置 (根目录)

**规则**: Docker 配置文件可以放在根目录

**允许的文件**:
- `docker-compose.yml` - 主 Docker Compose 配置
- `docker-compose.*.yml` - 特定场景配置
- `Dockerfile` - 后端 Dockerfile
- `Dockerfile.dev` - 开发 Dockerfile

### 6. 根目录允许的文件

**严格限制**: 根目录只允许以下文件类型

**必需文件**:
- `README.md` - 项目说明
- `requirements.txt` - Python 依赖
- `package.json` - Node.js 依赖 (前端)
- `pyproject.toml` - Python 项目配置
- `setup.py` - Python 安装脚本

**配置文件**:
- `.env*` - 环境变量文件
- `docker-compose*.yml` - Docker 配置
- `Dockerfile*` - Docker 镜像定义
- `alembic.ini` - 数据库迁移配置
- `prometheus.yml` - Prometheus 配置
- `.gitignore` - Git 忽略规则
- `.gitattributes` - Git 属性

**其他**:
- `LICENSE` - 许可证
- `CHANGELOG.md` - 更新日志
- `cloudbaserc.json` - 云开发配置

**❌ 不允许的文件**:
- 源代码文件 (`.py`, `.ts`, `.tsx`)
- 测试文件 (`test_*.py`, `*.test.ts`)
- 文档文件 (`.md` 除了 README.md)
- 脚本文件 (`.sh`, 除了特殊部署脚本)

## 迁移指南

### 现有文件迁移

如果发现根目录中有不符合规范的文件，按以下步骤迁移：

1. **识别文件类型**
   - 源代码 → `src/` 或 `frontend/src/`
   - 测试文件 → `tests/`
   - 文档 → `文档/`
   - 脚本 → `scripts/`

2. **确定具体位置**
   - 查看文件内容
   - 确定功能分类
   - 选择合适的子目录

3. **执行迁移**
   ```bash
   # 移动文件
   mv old_location/file.py new_location/
   
   # 更新导入路径
   # 如果其他文件导入了该文件，需要更新导入语句
   ```

4. **验证迁移**
   - 确保文件在新位置
   - 检查导入是否正确
   - 运行测试验证功能

### 已完成的迁移

**2026-01-28**: 根目录测试脚本迁移

| 原位置 | 新位置 | 说明 |
|--------|--------|------|
| `docker-compose-integration-test.py` | `tests/integration/` | Docker 集成测试 |
| `docker-compose-test-auth.py` | `tests/integration/` | 认证集成测试 |
| `docker-compose-test-auth.sh` | `tests/integration/` | 认证测试脚本 |
| `test_label_studio_sync.py` | `tests/integration/` | Label Studio 同步测试 |
| `test_label_studio_token.py` | `tests/integration/` | Label Studio 令牌测试 |
| `test_login_api.py` | `tests/api/` | 登录 API 测试 |
| `test_login_debug.py` | `tests/api/` | 登录调试测试 |
| `quick_test_label_studio.sh` | `tests/integration/` | Label Studio 快速测试 |
| `restart_and_test.sh` | `tests/integration/` | 重启和测试脚本 |

## 开发流程检查点

### 创建新文件时

- [ ] 确定文件类型 (源代码/测试/文档/脚本)
- [ ] 选择合适的目录
- [ ] 检查是否已有类似文件
- [ ] 遵循命名规范
- [ ] 不在根目录创建文件

### 修改现有文件时

- [ ] 如果文件位置不对，先迁移
- [ ] 更新相关导入
- [ ] 运行测试验证
- [ ] 更新相关文档

### 代码审查时

- [ ] 检查新文件是否在正确位置
- [ ] 验证命名是否符合规范
- [ ] 确认根目录没有新增不允许的文件
- [ ] 检查导入路径是否正确

## 自动化检查

### 检查根目录文件

```bash
#!/bin/bash
# check-root-files.sh

echo "检查根目录不允许的文件..."

# 不允许的文件类型
FORBIDDEN_PATTERNS=(
  "*.py"           # Python 源代码
  "test_*.py"      # 测试文件
  "*.ts"           # TypeScript 源代码
  "*.tsx"          # React 组件
  "*.sh"           # Shell 脚本 (除了特定脚本)
  "*.md"           # Markdown (除了 README.md)
)

for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
  files=$(find . -maxdepth 1 -name "$pattern" -type f 2>/dev/null)
  if [ -n "$files" ]; then
    echo "❌ 发现不允许的文件:"
    echo "$files"
  fi
done

echo "✅ 检查完成"
```

### 验证文件位置

```bash
#!/bin/bash
# verify-file-locations.sh

echo "验证文件位置..."

# 检查 src/ 目录
if [ -d "src" ]; then
  echo "✅ src/ 目录存在"
  python_files=$(find src -name "*.py" | wc -l)
  echo "   Python 文件数: $python_files"
fi

# 检查 tests/ 目录
if [ -d "tests" ]; then
  echo "✅ tests/ 目录存在"
  test_files=$(find tests -name "test_*.py" | wc -l)
  echo "   测试文件数: $test_files"
fi

# 检查 文档/ 目录
if [ -d "文档" ]; then
  echo "✅ 文档/ 目录存在"
  doc_files=$(find 文档 -name "*.md" | wc -l)
  echo "   文档文件数: $doc_files"
fi

# 检查 scripts/ 目录
if [ -d "scripts" ]; then
  echo "✅ scripts/ 目录存在"
  script_files=$(find scripts -name "*.sh" | wc -l)
  echo "   脚本文件数: $script_files"
fi

echo "✅ 验证完成"
```

## 常见问题

### Q: 我应该在哪里放置新的 API 端点？

**A**: 
1. 代码放在 `src/api/{module_name}.py`
2. 测试放在 `tests/api/test_{endpoint_name}.py`
3. 文档放在 `文档/功能实现/{功能名}.md`

### Q: 如何组织前端组件？

**A**:
1. 可复用组件放在 `frontend/src/components/`
2. 页面级组件放在 `frontend/src/pages/`
3. 相关测试放在 `frontend/src/components/__tests__/` 或 `tests/`

### Q: 脚本文件应该放在哪里？

**A**: 
- 自动化脚本放在 `scripts/` 目录
- 按功能分类放在子目录
- 例如: `scripts/deployment/deploy.sh`

### Q: 可以在根目录创建临时文件吗？

**A**: 不可以。所有文件都应该按规范放置。如果需要临时文件：
1. 放在 `.gitignore` 中的目录 (如 `tmp/`)
2. 或使用系统临时目录 (`/tmp/`)
3. 不要提交到 Git

### Q: 如何处理跨模块的共享代码？

**A**:
1. 放在 `src/utils/` (后端) 或 `frontend/src/utils/` (前端)
2. 或创建专门的共享模块
3. 确保导入路径清晰

## 执行规则

### MUST Rules (必须)

1. **MUST** 所有新增源代码放在 `src/` 或 `frontend/src/`
2. **MUST** 所有测试文件放在 `tests/` 目录
3. **MUST** 所有文档放在 `文档/` 目录
4. **MUST** 所有脚本放在 `scripts/` 目录
5. **MUST** 根目录只包含允许的文件
6. **MUST** 遵循命名规范

### SHOULD Rules (应该)

1. **SHOULD** 定期检查根目录是否有不符合规范的文件
2. **SHOULD** 在创建新文件前检查是否已有类似文件
3. **SHOULD** 更新相关文档以反映新增文件

### MUST NOT Rules (禁止)

1. **MUST NOT** 在根目录创建源代码文件
2. **MUST NOT** 在根目录创建测试文件
3. **MUST NOT** 在根目录创建文档文件 (除了 README.md)
4. **MUST NOT** 在根目录创建脚本文件 (除了特定部署脚本)

## 违规处理

### 发现违规文件

1. **立即通知**: 在 PR 中指出违规
2. **要求修正**: 要求开发者迁移文件
3. **PR 拒绝**: 不符合规范的 PR 将被拒绝
4. **重新提交**: 修正后重新提交

### 处理流程

```
发现违规 → 通知开发者 → 开发者修正 → 验证修正 → 接受 PR
```

## 参考资源

- [项目结构规范](./structure.md)
- [开发流程规范](./doc-first-workflow.md)
- [TypeScript 导出规范](./typescript-export-rules.md)
- [国际化翻译规范](./i18n-translation-rules.md)

---

**此规范为强制性规范，所有 SuperInsight 开发必须遵守。**

**违反规范将导致**:
1. PR 被拒绝
2. 需要重新修正
3. 可能影响项目进度

---

**最后更新**: 2026-01-28  
**维护者**: SuperInsight 开发团队  
**反馈**: 如发现规范不完善或有改进建议，请提交 issue
