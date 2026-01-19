---
description: 通过代码库分析创建全面的实施计划 | Create comprehensive feature plan with deep codebase analysis
argument-hint: [功能描述 | feature-description]
---

# Plan Feature: 规划功能 | Plan a New Task

## 功能 | Feature: $ARGUMENTS

## 使命 | Mission

通过系统化的代码库分析、外部研究和战略规划，将功能需求转化为**全面的实施计划**。

Transform a feature request into a **comprehensive implementation plan** through systematic codebase analysis, external research, and strategic planning.

**核心原则**: 在此阶段我们不编写代码。我们的目标是创建一个上下文丰富的实施计划，使 AI 代理能够一次性成功实施。

**关键理念**: 上下文为王。计划必须包含实施所需的所有信息 - 模式、必读文档、验证命令 - 以便执行代理第一次就能成功。

## 规划过程 | Planning Process

### 阶段 1: 功能理解 | Phase 1: Feature Understanding

**深入功能分析**:
- 提取要解决的核心问题
- 识别用户价值和业务影响
- 确定功能类型: 新功能/增强/重构/Bug 修复
- 评估复杂度: 低/中/高
- 映射受影响的系统和组件

**创建或完善用户故事**:
```
作为 <用户类型>
我想要 <操作/目标>
以便 <收益/价值>

As a <type of user>
I want to <action/goal>
So that <benefit/value>
```

### 阶段 2: 代码库情报收集 | Phase 2: Codebase Intelligence Gathering

**1. 项目结构分析**
- 检测主要语言、框架和运行时版本
- 映射目录结构和架构模式
- 识别服务/组件边界和集成点
- 定位配置文件（requirements.txt, package.json, tsconfig.json 等）
- 查找环境设置和构建过程

**2. 模式识别**
- 在代码库中搜索类似实现
- 识别编码约定:
  - 命名模式（snake_case for Python, camelCase for TypeScript）
  - 文件组织和模块结构
  - 错误处理方法
  - 日志模式和标准
- 提取功能领域的常见模式
- 记录要避免的反模式
- 检查 CLAUDE.md 和 `.kiro/steering/` 中的项目特定规则

**SuperInsight 特定模式**:
- **API 端点**: 参考 `src/api/` 中的现有路由
- **数据模型**: 参考 `src/models/` 中的 SQLAlchemy 模型
- **Schema**: 参考 `src/schemas/` 中的 Pydantic 模式
- **前端组件**: 参考 `frontend/src/components/` 和 `frontend/src/pages/`
- **Hooks**: 参考 `frontend/src/hooks/` 中的自定义 hooks
- **API 客户端**: 参考 `frontend/src/services/` 中的 API 调用模式

**3. 依赖分析**
- 列出与功能相关的外部库
- 了解库的集成方式（检查导入、配置）
- 在 `docs/`, `.claude/reference/` 中查找相关文档
- 注意库版本和兼容性要求

**SuperInsight 关键依赖**:
- FastAPI, SQLAlchemy, Pydantic (后端)
- React, Ant Design, TanStack Query (前端)
- Label Studio (标注引擎)
- Presidio (数据脱敏)
- Ragas (质量评估)

**4. 测试模式**
- 识别测试框架和结构（pytest, Vitest）
- 查找类似的测试示例作为参考
- 了解测试组织（单元测试 vs 集成测试）
- 注意覆盖率要求和测试标准（目标: >= 80%）

**5. 集成点**
- 识别需要更新的现有文件
- 确定需要创建的新文件及其位置
- 映射路由/API 注册模式
- 了解数据库/模型模式（如适用）
- 识别认证/授权模式（如相关）

**澄清歧义**:
- 如果此时需求不清楚，在继续之前询问用户澄清
- 获取具体的实施偏好（库、方法、模式）
- 在继续之前解决架构决策

### 阶段 3: 外部研究和文档 | Phase 3: External Research & Documentation

**文档收集**:
- 研究最新的库版本和最佳实践
- 查找带有特定章节锚点的官方文档
- 定位实施示例和教程
- 识别常见陷阱和已知问题
- 检查重大更改和迁移指南

**技术趋势**:
- 研究技术栈的当前最佳实践
- 查找相关的博客文章、指南或案例研究
- 识别性能优化模式
- 记录安全考虑

**编译研究参考**:
```markdown
## 相关文档 | Relevant Documentation

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
  - 具体章节: 依赖注入、异步支持
  - 原因: 实施 API 端点所需
- [Ant Design Pro Components](https://procomponents.ant.design/)
  - 具体章节: ProTable, ProForm
  - 原因: 前端表单和表格组件
- [TanStack Query](https://tanstack.com/query/latest)
  - 具体章节: Mutations, Optimistic Updates
  - 原因: API 调用和状态管理
```

### 阶段 4: 深度战略思考 | Phase 4: Deep Strategic Thinking

**深入思考**:
- 此功能如何融入现有架构？
- 关键依赖和操作顺序是什么？
- 可能出什么问题？（边界情况、竞态条件、错误）
- 如何全面测试？
- 性能影响是什么？
- 是否有安全考虑？
- 这种方法的可维护性如何？

**设计决策**:
- 在替代方法之间选择，并提供清晰的理由
- 为可扩展性和未来修改而设计
- 如需要，规划向后兼容性
- 考虑可扩展性影响

**SuperInsight 特定考虑**:
- **异步安全**: 遵循 `.kiro/steering/async-sync-safety.md`
- **TypeScript 规范**: 遵循 `.kiro/steering/typescript-export-rules.md`
- **数据脱敏**: 考虑 PII 处理
- **多租户**: 考虑租户隔离
- **审计日志**: 记录关键操作

### 阶段 5: 生成计划结构 | Phase 5: Plan Structure Generation

**创建包含以下结构的全面计划**:

```markdown
# Feature: <feature-name>

以下计划应该是完整的，但在开始实施之前验证文档和代码库模式以及任务合理性很重要。

特别注意现有工具、类型和模型的命名。从正确的文件导入等。

## 功能描述 | Feature Description

<详细描述功能、其目的和对用户的价值>

## 用户故事 | User Story

作为 <用户类型>
我想要 <操作/目标>
以便 <收益/价值>

## 问题陈述 | Problem Statement

<清楚地定义此功能解决的具体问题或机会>

## 解决方案陈述 | Solution Statement

<描述建议的解决方案方法以及它如何解决问题>

## 功能元数据 | Feature Metadata

**功能类型**: [新功能/增强/重构/Bug 修复]
**估计复杂度**: [低/中/高]
**主要受影响系统**: [主要组件/服务列表]
**依赖项**: [所需的外部库或服务]

---

## 上下文参考 | CONTEXT REFERENCES

### 相关代码库文件 | Relevant Codebase Files
**重要: 实施前必须阅读这些文件！**

<列出带有行号和相关性的文件>

- `src/api/example.py` (lines 15-45) - 原因: 包含我们将镜像的 X 模式
- `src/models/example.py` (lines 100-120) - 原因: 要遵循的数据库模型结构
- `tests/test_example.py` - 原因: 测试模式示例
- `frontend/src/hooks/useExample.ts` - 原因: React Hook 模式
- `frontend/src/services/exampleApi.ts` - 原因: API 客户端模式

### 要创建的新文件 | New Files to Create

- `src/services/new_service.py` - X 功能的服务实现
- `src/models/new_model.py` - Y 资源的数据模型
- `src/schemas/new_schema.py` - Pydantic 请求/响应模式
- `tests/test_new_service.py` - 新服务的单元测试
- `frontend/src/hooks/useNewFeature.ts` - 自定义 React Hook
- `frontend/src/services/newFeatureApi.ts` - API 客户端

### 相关文档 | Relevant Documentation
**实施前应阅读这些！**

- [文档链接 1](https://example.com/doc1#section)
  - 具体章节: 认证设置
  - 原因: 实施安全端点所需
- [文档链接 2](https://example.com/doc2#integration)
  - 具体章节: 数据库集成
  - 原因: 显示正确的异步数据库模式

### 要遵循的模式 | Patterns to Follow

<从代码库中提取的具体模式 - 包含项目中的实际代码示例>

**命名约定**:
- Python: snake_case for functions/variables, PascalCase for classes
- TypeScript: camelCase for functions/variables, PascalCase for components/types

**错误处理**:
```python
# Python
from fastapi import HTTPException

if not resource:
    raise HTTPException(status_code=404, detail="Resource not found")
```

```typescript
// TypeScript
try {
  const data = await api.get<ResponseType>('/endpoint');
  return data;
} catch (error) {
  message.error('操作失败');
  throw error;
}
```

**日志模式**:
```python
import structlog
logger = structlog.get_logger()

logger.info("Operation completed", user_id=user_id, action="create")
```

**其他相关模式**: [根据功能添加]

---

## 实施计划 | IMPLEMENTATION PLAN

### 阶段 1: 基础 | Phase 1: Foundation

<描述主要实施之前所需的基础工作>

**任务**:
- 设置基础结构（schemas, types, interfaces）
- 配置必要的依赖项
- 创建基础工具或辅助函数

### 阶段 2: 核心实施 | Phase 2: Core Implementation

<描述主要实施工作>

**任务**:
- 实施核心业务逻辑
- 创建服务层组件
- 添加 API 端点或接口
- 实施数据模型

### 阶段 3: 集成 | Phase 3: Integration

<描述功能如何与现有功能集成>

**任务**:
- 连接到现有路由/处理程序
- 注册新组件
- 更新配置文件
- 如需要，添加中间件或拦截器

### 阶段 4: 测试和验证 | Phase 4: Testing & Validation

<描述测试方法>

**任务**:
- 为每个组件实施单元测试
- 为功能工作流创建集成测试
- 添加边界情况测试
- 根据验收标准验证

---

## 逐步任务 | STEP-BY-STEP TASKS

重要: 按顺序从上到下执行每个任务。每个任务都是原子的且可独立测试。

### 任务格式指南 | Task Format Guidelines

使用信息密集的关键字以提高清晰度:

- **CREATE**: 新文件或组件
- **UPDATE**: 修改现有文件
- **ADD**: 向现有代码插入新功能
- **REMOVE**: 删除已弃用的代码
- **REFACTOR**: 重构而不改变行为
- **MIRROR**: 从代码库的其他地方复制模式

### {ACTION} {target_file}

- **IMPLEMENT**: {具体实施细节}
- **PATTERN**: {对现有模式的引用 - file:line}
- **IMPORTS**: {所需的导入和依赖项}
- **GOTCHA**: {要避免的已知问题或约束}
- **VALIDATE**: `{可执行的验证命令}`

<按依赖顺序继续所有任务...>

---

## 测试策略 | TESTING STRATEGY

<根据研究期间发现的项目测试框架和模式定义测试方法>

### 单元测试 | Unit Tests

<基于项目标准的范围和要求>

使用 fixtures 和断言设计单元测试，遵循现有的测试方法

**后端**: pytest, 覆盖率 >= 80%
**前端**: Vitest, 覆盖率 >= 80%

### 集成测试 | Integration Tests

<基于项目标准的范围和要求>

**后端**: 使用 TestClient 测试 API 端点
**前端**: Playwright E2E 测试

### 边界情况 | Edge Cases

<列出此功能必须测试的具体边界情况>

---

## 验证命令 | VALIDATION COMMANDS

<根据阶段 2 中发现的项目工具定义验证命令>

执行每个命令以确保零回归和 100% 功能正确性。

### 级别 1: 语法和风格 | Level 1: Syntax & Style

**后端**:
```bash
black --check src/ tests/
isort --check src/ tests/
mypy src/
```

**前端**:
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run lint
```

### 级别 2: 单元测试 | Level 2: Unit Tests

**后端**:
```bash
pytest tests/test_new_feature.py -v
```

**前端**:
```bash
cd frontend && npm run test -- new-feature
```

### 级别 3: 集成测试 | Level 3: Integration Tests

**后端**:
```bash
pytest tests/integration/test_new_feature_api.py -v
```

**前端**:
```bash
cd frontend && npm run test:e2e -- new-feature
```

### 级别 4: 手动验证 | Level 4: Manual Validation

<功能特定的手动测试步骤 - API 调用、UI 测试等>

```bash
# 测试 API 端点
curl -X POST http://localhost:8000/api/new-endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'

# 访问前端页面
# 打开 http://localhost:5173/new-feature
```

### 级别 5: 附加验证（可选）| Level 5: Additional Validation

<MCP 服务器或其他 CLI 工具（如可用）>

---

## 验收标准 | ACCEPTANCE CRITERIA

<列出完成必须满足的具体、可衡量的标准>

- [ ] 功能实施所有指定的功能
- [ ] 所有验证命令通过，零错误
- [ ] 单元测试覆盖率达到要求（80%+）
- [ ] 集成测试验证端到端工作流
- [ ] 代码遵循项目约定和模式
- [ ] 现有功能无回归
- [ ] 文档已更新（如适用）
- [ ] 性能满足要求（如适用）
- [ ] 安全考虑已解决（如适用）
- [ ] 遵循 `.kiro/steering/` 中的所有规范

---

## 完成清单 | COMPLETION CHECKLIST

- [ ] 所有任务按顺序完成
- [ ] 每个任务验证立即通过
- [ ] 所有验证命令成功执行
- [ ] 完整测试套件通过（单元 + 集成）
- [ ] 无 linting 或类型检查错误
- [ ] 手动测试确认功能工作
- [ ] 所有验收标准都满足
- [ ] 代码审查质量和可维护性

---

## 注释 | NOTES

<附加上下文、设计决策、权衡>
```

## 输出格式 | Output Format

**文件名**: `.agents/plans/{kebab-case-descriptive-name}.md`

- 用简短的描述性功能名称替换 `{kebab-case-descriptive-name}`
- 示例: `add-user-authentication.md`, `implement-search-api.md`, `refactor-database-layer.md`

**目录**: 如果不存在则创建 `.agents/plans/`

## 质量标准 | Quality Criteria

### 上下文完整性 ✓
- [ ] 所有必要的模式已识别和记录
- [ ] 外部库使用已记录并附有链接
- [ ] 集成点已清楚映射
- [ ] 陷阱和反模式已捕获
- [ ] 每个任务都有可执行的验证命令

### 实施就绪 ✓
- [ ] 另一个开发人员可以在没有额外上下文的情况下执行
- [ ] 任务按依赖顺序排列（可以从上到下执行）
- [ ] 每个任务都是原子的且可独立测试
- [ ] 模式引用包含具体的 file:line 编号

### 模式一致性 ✓
- [ ] 任务遵循现有的代码库约定
- [ ] 新模式有清晰的理由
- [ ] 不重新发明现有的模式或工具
- [ ] 测试方法符合项目标准

### 信息密度 ✓
- [ ] 没有通用引用（全部具体且可操作）
- [ ] URL 包含章节锚点（如适用）
- [ ] 任务描述使用代码库关键字
- [ ] 验证命令是非交互式可执行的

## 成功指标 | Success Metrics

**一次性实施**: 执行代理可以在没有额外研究或澄清的情况下完成功能

**验证完整**: 每个任务至少有一个工作验证命令

**上下文丰富**: 计划通过"无先验知识测试" - 不熟悉代码库的人可以仅使用计划内容实施

**信心分数**: #/10 第一次尝试成功的信心

## 报告 | Report

创建计划后，提供:

- 功能和方法的摘要
- 创建的计划文件的完整路径
- 复杂度评估
- 关键实施风险或考虑
- 一次性成功的估计信心分数

## Mission

Transform a feature request into a **comprehensive implementation plan** through systematic codebase analysis, external research, and strategic planning.

**Core Principle**: We do NOT write code in this phase. Our goal is to create a context-rich implementation plan that enables one-pass implementation success for ai agents.

**Key Philosophy**: Context is King. The plan must contain ALL information needed for implementation - patterns, mandatory reading, documentation, validation commands - so the execution agent succeeds on the first attempt.

## Planning Process

### Phase 1: Feature Understanding

**Deep Feature Analysis:**

- Extract the core problem being solved
- Identify user value and business impact
- Determine feature type: New Capability/Enhancement/Refactor/Bug Fix
- Assess complexity: Low/Medium/High
- Map affected systems and components

**Create User Story Format Or Refine If Story Was Provided By The User:**

```
As a <type of user>
I want to <action/goal>
So that <benefit/value>
```

### Phase 2: Codebase Intelligence Gathering

**Use specialized agents and parallel analysis:**

**1. Project Structure Analysis**

- Detect primary language(s), frameworks, and runtime versions
- Map directory structure and architectural patterns
- Identify service/component boundaries and integration points
- Locate configuration files (pyproject.toml, package.json, etc.)
- Find environment setup and build processes

**2. Pattern Recognition** (Use specialized subagents when beneficial)

- Search for similar implementations in codebase
- Identify coding conventions:
  - Naming patterns (CamelCase, snake_case, kebab-case)
  - File organization and module structure
  - Error handling approaches
  - Logging patterns and standards
- Extract common patterns for the feature's domain
- Document anti-patterns to avoid
- Check CLAUDE.md for project-specific rules and conventions

**3. Dependency Analysis**

- Catalog external libraries relevant to feature
- Understand how libraries are integrated (check imports, configs)
- Find relevant documentation in docs/, ai_docs/, .agents/reference or ai-wiki if available
- Note library versions and compatibility requirements

**4. Testing Patterns**

- Identify test framework and structure (pytest, jest, etc.)
- Find similar test examples for reference
- Understand test organization (unit vs integration)
- Note coverage requirements and testing standards

**5. Integration Points**

- Identify existing files that need updates
- Determine new files that need creation and their locations
- Map router/API registration patterns
- Understand database/model patterns if applicable
- Identify authentication/authorization patterns if relevant

**Clarify Ambiguities:**

- If requirements are unclear at this point, ask the user to clarify before you continue
- Get specific implementation preferences (libraries, approaches, patterns)
- Resolve architectural decisions before proceeding

### Phase 3: External Research & Documentation

**Use specialized subagents when beneficial for external research:**

**Documentation Gathering:**

- Research latest library versions and best practices
- Find official documentation with specific section anchors
- Locate implementation examples and tutorials
- Identify common gotchas and known issues
- Check for breaking changes and migration guides

**Technology Trends:**

- Research current best practices for the technology stack
- Find relevant blog posts, guides, or case studies
- Identify performance optimization patterns
- Document security considerations

**Compile Research References:**

```markdown
## Relevant Documentation

- [Library Official Docs](https://example.com/docs#section)
  - Specific feature implementation guide
  - Why: Needed for X functionality
- [Framework Guide](https://example.com/guide#integration)
  - Integration patterns section
  - Why: Shows how to connect components
```

### Phase 4: Deep Strategic Thinking

**Think Harder About:**

- How does this feature fit into the existing architecture?
- What are the critical dependencies and order of operations?
- What could go wrong? (Edge cases, race conditions, errors)
- How will this be tested comprehensively?
- What performance implications exist?
- Are there security considerations?
- How maintainable is this approach?

**Design Decisions:**

- Choose between alternative approaches with clear rationale
- Design for extensibility and future modifications
- Plan for backward compatibility if needed
- Consider scalability implications

### Phase 5: Plan Structure Generation

**Create comprehensive plan with the following structure:**

Whats below here is a template for you to fill for th4e implementation agent:

```markdown
# Feature: <feature-name>

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

<Detailed description of the feature, its purpose, and value to users>

## User Story

As a <type of user>
I want to <action/goal>
So that <benefit/value>

## Problem Statement

<Clearly define the specific problem or opportunity this feature addresses>

## Solution Statement

<Describe the proposed solution approach and how it solves the problem>

## Feature Metadata

**Feature Type**: [New Capability/Enhancement/Refactor/Bug Fix]
**Estimated Complexity**: [Low/Medium/High]
**Primary Systems Affected**: [List of main components/services]
**Dependencies**: [External libraries or services required]

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

<List files with line numbers and relevance>

- `path/to/file.py` (lines 15-45) - Why: Contains pattern for X that we'll mirror
- `path/to/model.py` (lines 100-120) - Why: Database model structure to follow
- `path/to/test.py` - Why: Test pattern example

### New Files to Create

- `path/to/new_service.py` - Service implementation for X functionality
- `path/to/new_model.py` - Data model for Y resource
- `tests/path/to/test_new_service.py` - Unit tests for new service

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Documentation Link 1](https://example.com/doc1#section)
  - Specific section: Authentication setup
  - Why: Required for implementing secure endpoints
- [Documentation Link 2](https://example.com/doc2#integration)
  - Specific section: Database integration
  - Why: Shows proper async database patterns

### Patterns to Follow

<Specific patterns extracted from codebase - include actual code examples from the project>

**Naming Conventions:** (for example)

**Error Handling:** (for example)

**Logging Pattern:** (for example)

**Other Relevant Patterns:** (for example)

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

<Describe foundational work needed before main implementation>

**Tasks:**

- Set up base structures (schemas, types, interfaces)
- Configure necessary dependencies
- Create foundational utilities or helpers

### Phase 2: Core Implementation

<Describe the main implementation work>

**Tasks:**

- Implement core business logic
- Create service layer components
- Add API endpoints or interfaces
- Implement data models

### Phase 3: Integration

<Describe how feature integrates with existing functionality>

**Tasks:**

- Connect to existing routers/handlers
- Register new components
- Update configuration files
- Add middleware or interceptors if needed

### Phase 4: Testing & Validation

<Describe testing approach>

**Tasks:**

- Implement unit tests for each component
- Create integration tests for feature workflow
- Add edge case tests
- Validate against acceptance criteria

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task Format Guidelines

Use information-dense keywords for clarity:

- **CREATE**: New files or components
- **UPDATE**: Modify existing files
- **ADD**: Insert new functionality into existing code
- **REMOVE**: Delete deprecated code
- **REFACTOR**: Restructure without changing behavior
- **MIRROR**: Copy pattern from elsewhere in codebase

### {ACTION} {target_file}

- **IMPLEMENT**: {Specific implementation detail}
- **PATTERN**: {Reference to existing pattern - file:line}
- **IMPORTS**: {Required imports and dependencies}
- **GOTCHA**: {Known issues or constraints to avoid}
- **VALIDATE**: `{executable validation command}`

<Continue with all tasks in dependency order...>

---

## TESTING STRATEGY

<Define testing approach based on project's test framework and patterns discovered in during research>

### Unit Tests

<Scope and requirements based on project standards>

Design unit tests with fixtures and assertions following existing testing approaches

### Integration Tests

<Scope and requirements based on project standards>

### Edge Cases

<List specific edge cases that must be tested for this feature>

---

## VALIDATION COMMANDS

<Define validation commands based on project's tools discovered in Phase 2>

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

<Project-specific linting and formatting commands>

### Level 2: Unit Tests

<Project-specific unit test commands>

### Level 3: Integration Tests

<Project-specific integration test commands>

### Level 4: Manual Validation

<Feature-specific manual testing steps - API calls, UI testing, etc.>

### Level 5: Additional Validation (Optional)

<MCP servers or additional CLI tools if available>

---

## ACCEPTANCE CRITERIA

<List specific, measurable criteria that must be met for completion>

- [ ] Feature implements all specified functionality
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage meets requirements (80%+)
- [ ] Integration tests verify end-to-end workflows
- [ ] Code follows project conventions and patterns
- [ ] No regressions in existing functionality
- [ ] Documentation is updated (if applicable)
- [ ] Performance meets requirements (if applicable)
- [ ] Security considerations addressed (if applicable)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

<Additional context, design decisions, trade-offs>
```

## Output Format

**Filename**: `.agents/plans/{kebab-case-descriptive-name}.md`

- Replace `{kebab-case-descriptive-name}` with short, descriptive feature name
- Examples: `add-user-authentication.md`, `implement-search-api.md`, `refactor-database-layer.md`

**Directory**: Create `.agents/plans/` if it doesn't exist

## Quality Criteria

### Context Completeness ✓

- [ ] All necessary patterns identified and documented
- [ ] External library usage documented with links
- [ ] Integration points clearly mapped
- [ ] Gotchas and anti-patterns captured
- [ ] Every task has executable validation command

### Implementation Ready ✓

- [ ] Another developer could execute without additional context
- [ ] Tasks ordered by dependency (can execute top-to-bottom)
- [ ] Each task is atomic and independently testable
- [ ] Pattern references include specific file:line numbers

### Pattern Consistency ✓

- [ ] Tasks follow existing codebase conventions
- [ ] New patterns justified with clear rationale
- [ ] No reinvention of existing patterns or utils
- [ ] Testing approach matches project standards

### Information Density ✓

- [ ] No generic references (all specific and actionable)
- [ ] URLs include section anchors when applicable
- [ ] Task descriptions use codebase keywords
- [ ] Validation commands are non interactive executable

## Success Metrics

**One-Pass Implementation**: Execution agent can complete feature without additional research or clarification

**Validation Complete**: Every task has at least one working validation command

**Context Rich**: The Plan passes "No Prior Knowledge Test" - someone unfamiliar with codebase can implement using only Plan content

**Confidence Score**: #/10 that execution will succeed on first attempt

## Report

After creating the Plan, provide:

- Summary of feature and approach
- Full path to created Plan file
- Complexity assessment
- Key implementation risks or considerations
- Estimated confidence score for one-pass success