# 需求文档：AI 工作流引擎

## 简介

将 AI 智能助手页面 (`/ai-assistant`) 从"自由对话 + 散落配置"模式升级为"工作流驱动 + 角色权限控制"模式。核心目标是建立「角色 → 工作流 → 技能 → 数据源 → 输出方式」的完整权限链路，由管理员配置工作流，不同角色按权限选择并执行工作流，同时将现有散落的数据源配置、权限表、输出方式等统一收敛到工作流配置中。保留自由对话能力（通过 LLM 直连工作流实现），并增强今日统计功能。

工作流引擎的后端 API 采用双通道架构，统一服务两类调用方：
1. **内部前端通道**：本项目 `/ai-assistant` 页面，通过 JWT 认证，用户在 UI 中选择工作流并交互
2. **外部客户 API 通道**：客户的各种 APP/前端系统，通过 API Key 认证调用 Service Engine（`POST /api/v1/service/request`），在请求中携带 `workflow_id` 和权限参数

两个通道共享同一套工作流引擎核心逻辑（WorkflowService），区别仅在认证方式和入口端点。

## 术语表

- **Workflow（工作流）**: 管理员预配置的执行单元，包含唯一 ID、名称、描述、关联技能列表、数据源授权范围、输出方式、角色可见性等属性
- **Workflow_Engine（工作流引擎）**: 负责工作流的创建、存储、权限校验、执行调度的后端服务模块
- **Role（角色）**: 系统中的用户角色，包括 admin（管理员）、business_expert（业务专家）、annotator（标注员）、viewer（观察者）
- **Skill（技能）**: 部署在 OpenClaw 网关上的 AI 技能包（AISkill），如数据查询、数据摘要、智能标注辅助等
- **Data_Source（数据源）**: 系统中可供 AI 访问的数据模块，包含总分结构（数据源 → 数据表），如标注任务、标注效率、用户活跃度等
- **Data_Table（数据表）**: 数据源下的明细表，授权粒度需与客户 API 传参授权一致
- **Output_Mode（输出方式）**: AI 响应的输出格式，如合并输出（merge）、对比输出（compare）等
- **Permission_Chain（权限链路）**: 角色 → 工作流 → 技能 → 数据源/数据表 → 输出方式 的完整授权链
- **Authorization_Request（授权请求）**: 当工作流执行遇到权限不足时，系统向客户 API 发起的动态授权请求，包含所需授权的具体内容和范围，由客户系统决定是否授予（高阶功能，本期预留接口）
- **API_Permission（API 传参权限）**: 客户通过 API 传参传入的权限列表，作为权限的最终权威来源，优先级高于前端管理员配置
- **Preset_Workflow（预置工作流）**: 由系统预定义的工作流，用于替代现有快捷操作，与权限冲突时权限优先
- **Chat_Page（对话页面）**: `/ai-assistant` 页面中的对话交互区域
- **Admin_Panel（管理面板）**: 管理员用于配置工作流的界面
- **Stats_Panel（统计面板）**: 显示当前角色当日统计数据的面板组件
- **Workflow_Selector（工作流选择器）**: 用户发送消息前选择工作流的 UI 组件
- **Internal_Channel（内部前端通道）**: 本项目 `/ai-assistant` 页面的调用通道，JWT 认证，用户通过 UI 选择工作流
- **External_Channel（外部客户 API 通道）**: 客户 APP 通过 Service Engine（`POST /api/v1/service/request`）的调用通道，API Key 认证，请求中携带 `workflow_id`
- **Service_Engine（服务引擎）**: 现有的统一外部 API 入口（`src/service_engine/`），支持 query/chat/decision/skill 四种请求类型，通过 API Key 认证和 scope 权限控制

## 现有实现与差异分析

### 现有后端模块（保留复用）

| 模块 | 文件 | 工作流引擎中的角色 |
|------|------|-------------------|
| AIDataSourceConfigModel | `src/ai/data_source_config.py` | 作为工作流数据源授权的基础数据（哪些数据源已启用），工作流只能授权已启用的数据源 |
| AIDataSourceRolePermission | `src/models/ai_data_source_role_permission.py` | 作为工作流权限的补充约束上限，工作流授权范围不得超过角色基础权限 |
| AISkillRolePermission | `src/models/ai_skill_role_permission.py` | 同上，工作流关联的技能不得超过角色已授权的技能范围 |
| RolePermissionService | `src/ai/role_permission_service.py` | 被 WorkflowService 内部调用，用于校验权限上限 |
| SkillPermissionService | `src/ai/skill_permission_service.py` | 被 WorkflowService 内部调用，用于校验技能授权上限 |
| AIDataSourceService | `src/ai/data_source_config.py` | 被 WorkflowService 内部调用，用于查询数据源数据和校验数据源存在性 |
| AIAccessLog + AIAccessLogService | `src/models/ai_access_log.py`, `src/ai/access_log_service.py` | 扩展新增 `workflow_execute` 事件类型，复用现有日志基础设施 |
| OpenClawChatService | `src/ai/openclaw_chat_service.py` | 工作流执行时复用，工作流引擎仅负责参数编排 |
| LLMSwitcher | `src/ai/llm_switcher.py` | 自由对话工作流（无技能关联）时复用 |
| AISkill / AIGateway | `src/models/ai_integration.py` | 工作流关联技能时引用 AISkill.id |
| Service Engine (RequestRouter) | `src/service_engine/` | 外部客户 API 通道入口，扩展支持 `workflow_id` 参数，复用 WorkflowService 核心逻辑 |

### 现有前端组件（替换移除）

| 组件 | 文件 | 变更方式 |
|------|------|---------|
| 模式切换 Segmented (direct/openclaw) | `AIAssistant/index.tsx` | **移除** — 由 WorkflowSelector 替代，工作流配置决定是否使用技能 |
| 技能勾选面板 (skill checkbox panel) | `AIAssistant/index.tsx` | **移除** — 技能由工作流配置预定义，用户无需手动选择 |
| ConfigPanel | `AIAssistant/components/ConfigPanel.tsx` | **移除** — 数据源、权限、输出方式全部收敛到工作流配置 |
| DataSourceConfigModal | `AIAssistant/components/DataSourceConfigModal.tsx` | **移除** — 数据源授权在工作流管理界面配置 |
| PermissionTableModal | `AIAssistant/components/PermissionTableModal.tsx` | **移除** — 角色权限在工作流管理界面配置 |
| OutputModeModal | `AIAssistant/components/OutputModeModal.tsx` | **移除** — 输出方式在工作流配置中预定义 |
| 快捷操作卡片 (quick actions) | `AIAssistant/index.tsx` | **替换** — 转化为预置工作流卡片，受权限控制 |
| 今日统计 (stats panel) | `AIAssistant/index.tsx` | **增强** — 接入后端真实统计 API，支持点击查看明细 |

### 现有 API 端点（保留兼容）

| 端点 | 变更方式 |
|------|---------|
| `POST /chat` | 保留，新增可选 `workflow_id` 参数 |
| `POST /chat/stream` | 保留，新增可选 `workflow_id` 参数 |
| `GET /chat/openclaw-status` | 保留，向后兼容 |
| `GET /data-sources/available` | 保留，向后兼容 |
| `GET/POST /data-sources/config` | 保留，向后兼容 |
| `GET/POST /data-sources/role-permissions` | 保留，向后兼容 |
| `GET/POST /skills/role-permissions` | 保留，向后兼容 |
| `POST /skills/init-admin` | 保留，向后兼容 |
| `GET /access-logs` | 保留，向后兼容 |
| `GET /service-status` | 保留，向后兼容 |

### 新增模块

| 模块 | 说明 |
|------|------|
| Workflow 数据模型 | 新增 `ai_workflows` 表，JSONB 存储技能列表、数据源授权、输出方式、可见角色 |
| WorkflowService | 新增服务，负责 CRUD + 权限链路校验 + 执行调度 |
| Workflow API 端点 | 新增 `/workflows` CRUD + `/workflows/sync-permissions` + `/stats/today` |
| WorkflowSelector 组件 | 新增前端组件，替代模式切换 + 技能面板 + 配置弹窗 |
| 工作流管理页面 | 新增管理员界面，集成所有配置功能 |
| 数据迁移逻辑 | 基于现有权限配置自动生成默认工作流 |
| 客户 API 文档更新 | 更新 `文档/系统设计/智能服务引擎API接口文档.md`，补充工作流相关传参、示例、错误码 |

### 核心设计原则

1. **单一入口**：用户通过选择工作流来决定技能、数据源、输出方式，不再手动拼装参数
2. **权限层叠**：角色基础权限（旧表）→ 工作流授权范围 → API 传参权限（最终权威），三层取交集
3. **不重复不并行**：旧的散落配置 UI 全部移除，旧的后端服务作为内部依赖被工作流引擎调用，不暴露给用户直接操作
4. **向后兼容**：旧 API 端点保留，未携带 `workflow_id` 的请求按原有逻辑处理
5. **双通道共核心**：内部前端（JWT）和外部客户 API（API Key）共享同一个 WorkflowService，区别仅在认证方式和响应包装格式，禁止为两个通道维护两套工作流逻辑

---

## 需求

### 需求 1：工作流数据模型与 CRUD

**用户故事：** 作为管理员，我希望能够创建和管理工作流配置，以便将技能、数据源、输出方式统一编排到工作流中。

#### 验收标准

1. THE Workflow_Engine SHALL 提供工作流数据模型，包含以下字段：唯一 ID、名称、描述、状态（启用/禁用）、关联技能 ID 列表、数据源授权范围（总分结构，含数据源 ID 和数据表列表）、输出方式列表、可见角色列表、是否为预置工作流标记、创建时间、更新时间
2. WHEN 管理员提交创建工作流请求时，THE Workflow_Engine SHALL 校验名称非空且唯一，校验关联技能 ID 在已部署技能中存在，校验数据源 ID 在已注册数据源中存在，校验角色值在系统定义的角色列表中存在，校验通过后持久化工作流记录并返回完整工作流对象
3. WHEN 管理员提交更新工作流请求时，THE Workflow_Engine SHALL 对变更字段执行与创建相同的校验规则，校验通过后更新记录并返回更新后的工作流对象
4. WHEN 管理员提交删除工作流请求时，THE Workflow_Engine SHALL 软删除该工作流（标记为禁用状态），保留历史记录
5. THE Workflow_Engine SHALL 提供查询接口，支持按状态、角色过滤工作流列表
6. IF 工作流名称与已有工作流重复，THEN THE Workflow_Engine SHALL 返回 409 冲突错误，包含明确的错误信息

### 需求 2：工作流-角色权限链路

**用户故事：** 作为系统用户，我希望只能看到和执行我的角色有权限的工作流，以确保数据访问安全。

#### 验收标准

1. THE Workflow_Engine SHALL 在工作流配置中维护可见角色列表，仅列表中包含的角色可查看和执行该工作流
2. WHEN 非管理员用户请求工作流列表时，THE Workflow_Engine SHALL 仅返回该用户角色在可见角色列表中且状态为启用的工作流
3. WHEN 用户选择执行某工作流时，THE Workflow_Engine SHALL 校验该用户角色是否在工作流的可见角色列表中，校验不通过时返回 403 禁止访问错误
4. THE Workflow_Engine SHALL 确保管理员角色默认拥有所有工作流的查看和执行权限
5. WHEN 用户执行工作流时，THE Workflow_Engine SHALL 按照权限链路依次校验：用户角色对工作流的访问权限、工作流对技能的关联权限、工作流对数据源及数据表的授权范围，任一环节校验失败时拒绝执行并返回具体的权限不足信息
6. WHEN 客户 API 传参中携带权限列表与前端管理员配置的工作流权限发生冲突时，THE Workflow_Engine SHALL 以客户 API 传参权限为准（API 权限 > 前端配置权限），确保客户授权为最终权威来源

### 需求 3：数据源总分结构授权

**用户故事：** 作为管理员，我希望在工作流中精确控制数据源授权到数据表级别，以避免超范围授权或授权不足。

#### 验收标准

1. THE Workflow_Engine SHALL 支持数据源的总分结构授权，每个数据源下包含可访问的数据表列表
2. WHEN 管理员配置工作流的数据源授权时，THE Admin_Panel SHALL 展示数据源列表，每个数据源下展示其包含的数据表，支持逐表勾选授权
3. WHEN 工作流执行时请求数据源数据，THE Workflow_Engine SHALL 仅查询该工作流授权范围内的数据表，拒绝访问未授权的数据表
4. IF 工作流授权的数据表在数据源中不存在，THEN THE Workflow_Engine SHALL 跳过该数据表并在响应中记录警告信息
5. THE Workflow_Engine SHALL 确保数据源授权粒度与客户 API 传参授权一致，工作流中的数据表授权范围不超过数据源本身的访问权限配置
6. WHEN 客户通过 API 传参传入数据源和数据表的权限列表时，THE Workflow_Engine SHALL 以 API 传参为权威来源，覆盖更新工作流中对应的数据源授权配置，实现权限同步
7. THE Workflow_Engine SHALL 提供权限同步 API 端点，接受客户 API 传参的完整权限列表，批量更新所有相关工作流的数据源和数据表授权范围

### 需求 4：工作流选择与执行

**用户故事：** 作为系统用户，我希望在发送消息前选择一个工作流来执行，以便 AI 按照预定义的技能和数据范围处理我的请求。

#### 验收标准

1. THE Workflow_Selector SHALL 在对话输入区域上方以醒目的方式展示当前用户有权限的工作流列表，每个工作流卡片包含名称、简要描述和关联技能数量标签，支持搜索和选择，当前选中的工作流以高亮样式突出显示
2. WHEN 用户选择工作流并发送消息时，THE Chat_Page SHALL 将工作流 ID 附加到聊天请求中，并将该工作流 ID 持久化到 localStorage 作为用户的最近使用记录
3. WHEN 用户未主动选择工作流时，THE Workflow_Selector SHALL 自动选中用户上一次使用的工作流（从 localStorage 读取），若上一次的工作流已禁用或用户已无权限，则自动清除记录并提示用户重新选择
3. WHEN 后端收到带有工作流 ID 的聊天请求时，THE Workflow_Engine SHALL 从工作流配置中提取关联技能、数据源授权范围和输出方式，替代请求中的手动配置参数
4. WHILE 工作流执行中，THE Chat_Page SHALL 显示当前使用的工作流名称和执行状态
5. WHEN 工作流关联了多个技能时，THE Workflow_Engine SHALL 按工作流配置的技能列表顺序依次调用各技能
6. IF 工作流执行过程中某个技能调用失败，THEN THE Workflow_Engine SHALL 记录错误日志，在响应中标注失败的技能，并继续执行剩余技能

### 需求 5：自由对话工作流

**用户故事：** 作为系统用户，我希望保留自由对话能力，通过 LLM 直连工作流实现，同样受角色和数据授权控制。

#### 验收标准

1. THE Workflow_Engine SHALL 支持创建不关联任何技能的工作流，该类工作流执行时使用 LLM 直连模式
2. WHEN 用户选择不关联技能的工作流并发送消息时，THE Workflow_Engine SHALL 通过 LLMSwitcher 直连处理请求，同时应用工作流中配置的数据源授权范围和输出方式
3. THE Workflow_Engine SHALL 支持工作流的宽松配置（授权所有数据源、所有输出方式）和严格配置（仅授权特定数据源和数据表），由管理员根据业务需求决定
4. WHEN 用户未选择任何工作流且无上一次使用记录时，THE Chat_Page SHALL 在输入区域上方以醒目提示引导用户选择工作流，发送按钮保持可用但附带提示

### 需求 6：配置收敛与迁移

**用户故事：** 作为管理员，我希望现有的散落配置项（数据源配置、权限表、输出方式）统一收敛到工作流配置中，以简化管理。

#### 验收标准

1. THE Workflow_Engine SHALL 将现有 AIDataSourceConfigModel 的数据源启用/禁用配置作为工作流数据源授权的基础数据，工作流只能授权已启用的数据源
2. THE Workflow_Engine SHALL 将现有 AIDataSourceRolePermission 和 AISkillRolePermission 的角色权限数据作为工作流权限校验的补充约束，工作流授权范围不得超过角色基础权限
3. WHEN 系统首次启用工作流引擎时，THE Workflow_Engine SHALL 提供数据迁移逻辑，基于现有权限配置自动生成默认工作流（每个角色至少一个默认工作流），保持与迁移前相同的访问能力
4. THE Workflow_Engine SHALL 保留现有数据源配置和权限表的 API 端点，确保向后兼容，同时在管理面板中引导管理员通过工作流配置进行统一管理
5. THE Admin_Panel SHALL 在工作流配置界面中集成数据源选择、技能选择、输出方式选择和角色分配功能，替代现有分散的配置弹窗

### 需求 7：预置工作流（快捷操作替代）

**用户故事：** 作为系统用户，我希望现有的快捷操作转化为预置工作流，保持便捷操作的同时纳入权限管控。

#### 验收标准

1. THE Workflow_Engine SHALL 提供系统预置工作流，对应现有四个快捷操作：销售预测分析、数据质量检查、智能标注建议、任务进度追踪
2. THE Chat_Page SHALL 将预置工作流以快捷操作卡片形式展示，用户点击后自动选择对应工作流并填充预设提示词
3. WHEN 用户角色无权访问某预置工作流时，THE Chat_Page SHALL 隐藏该快捷操作卡片，确保无权限的工作流对该角色不可见
4. WHEN 预置工作流的权限配置与用户角色权限冲突时，THE Workflow_Engine SHALL 以角色权限为准，拒绝执行超出角色权限范围的操作
5. THE Workflow_Engine SHALL 允许管理员修改预置工作流的配置（技能、数据源、角色），但禁止删除系统预置工作流

### 需求 8：今日统计增强

**用户故事：** 作为系统用户，我希望今日统计显示与我角色相关的当日数据，并支持点击查看明细。

#### 验收标准

1. THE Stats_Panel SHALL 显示当前登录用户角色当日的统计数据，包括：对话次数、工作流执行次数、访问的数据源数量
2. WHEN 用户点击统计面板中的某项统计数据时，THE Stats_Panel SHALL 展开显示该统计项的明细列表（如对话时间列表、工作流执行记录列表、数据源访问记录列表）
3. THE Workflow_Engine SHALL 提供按角色和日期范围查询统计数据的 API 端点，返回当前用户角色的聚合统计和明细数据
4. THE Stats_Panel SHALL 仅展示当前用户角色有权限查看的统计数据，管理员可查看所有角色的汇总统计

### 需求 9：工作流管理界面

**用户故事：** 作为管理员，我希望有一个专门的工作流管理界面来创建、编辑和管理所有工作流。

#### 验收标准

1. THE Admin_Panel SHALL 提供工作流列表页面，展示所有工作流的名称、状态、关联技能数量、可见角色、创建时间，支持按状态筛选和按名称搜索
2. WHEN 管理员点击创建工作流按钮时，THE Admin_Panel SHALL 展示工作流配置表单，包含：名称输入、描述输入、技能多选（从已部署技能列表中选择）、数据源授权配置（总分结构树形选择）、输出方式选择、可见角色多选
3. WHEN 管理员点击编辑某工作流时，THE Admin_Panel SHALL 加载该工作流的完整配置到表单中，支持修改后保存
4. THE Admin_Panel SHALL 对工作流配置表单进行前端校验：名称必填、至少选择一个可见角色，校验不通过时显示具体的错误提示
5. THE Admin_Panel SHALL 所有可见文本使用 `t()` 国际化函数，同步维护中文和英文翻译文件

### 需求 10：全局国际化支持

**用户故事：** 作为系统用户，我希望所有前端页面的所有显示内容都支持国际化翻译，以便在不同语言环境下使用。

#### 验收标准

1. THE Chat_Page、Workflow_Selector、Stats_Panel、Admin_Panel 以及所有新增前端组件 SHALL 所有用户可见文本（包括标签、按钮、提示信息、错误信息、占位符、表头、状态文本等）均使用 `t()` 国际化函数
2. THE Workflow_Engine SHALL 在 `frontend/src/locales/zh/` 和 `frontend/src/locales/en/` 目录下同步维护中英文翻译文件，确保所有翻译键在两种语言文件中完全一致
3. WHEN 工作流名称和描述由管理员输入时，THE Admin_Panel SHALL 支持管理员分别输入中文和英文的名称与描述，前端根据当前语言环境显示对应语言版本
4. THE Workflow_Engine SHALL 确保后端 API 返回的错误信息使用错误码而非硬编码文本，由前端根据错误码映射到对应语言的翻译文本
5. THE Workflow_Engine SHALL 确保预置工作流的名称和描述在翻译文件中预定义，不依赖数据库中的硬编码文本

### 需求 11：API 端点设计

**用户故事：** 作为前端开发者，我希望有清晰的 API 端点来支持工作流的完整生命周期操作。

#### 验收标准

1. THE Workflow_Engine SHALL 提供以下 RESTful API 端点：`GET /api/v1/ai-assistant/workflows`（查询工作流列表，非管理员自动按角色过滤）、`POST /api/v1/ai-assistant/workflows`（创建工作流，仅管理员）、`PUT /api/v1/ai-assistant/workflows/{id}`（更新工作流，仅管理员）、`DELETE /api/v1/ai-assistant/workflows/{id}`（禁用工作流，仅管理员）
2. THE Workflow_Engine SHALL 扩展现有 `POST /api/v1/ai-assistant/chat` 和 `POST /api/v1/ai-assistant/chat/stream` 端点，新增可选参数 `workflow_id`，当提供 `workflow_id` 时从工作流配置中提取执行参数
3. THE Workflow_Engine SHALL 提供 `GET /api/v1/ai-assistant/workflows/{id}/stats` 端点，返回指定工作流的执行统计数据
4. THE Workflow_Engine SHALL 提供 `GET /api/v1/ai-assistant/stats/today` 端点，返回当前用户角色的当日统计数据和明细
5. IF 请求的 API 端点需要管理员权限而当前用户非管理员，THEN THE Workflow_Engine SHALL 返回 403 状态码和明确的权限不足错误信息
6. THE Workflow_Engine SHALL 对所有工作流相关 API 请求记录访问日志，包含用户 ID、角色、操作类型、工作流 ID、时间戳
7. THE Workflow_Engine SHALL 提供 `POST /api/v1/ai-assistant/workflows/sync-permissions` 端点，接受客户 API 传参的完整权限列表（包含角色、数据源、数据表授权范围），批量更新所有相关工作流的权限配置，以 API 传参为最终权威来源

### 需求 12：双通道架构（内部前端 + 外部客户 API）

**用户故事：** 作为平台运营方，我希望工作流引擎的后端 API 同时支持本项目前端交互和客户外部 APP 调用，共享同一套核心逻辑，避免维护两套代码。

#### 验收标准

1. THE Workflow_Engine SHALL 提供统一的 WorkflowService 核心服务层，包含工作流 CRUD、权限链路校验、执行调度逻辑，不依赖具体的认证方式或入口端点
2. THE Internal_Channel SHALL 通过现有 `POST /api/v1/ai-assistant/chat` 和 `POST /api/v1/ai-assistant/chat/stream` 端点（JWT 认证）接受 `workflow_id` 参数，调用 WorkflowService 执行工作流
3. THE External_Channel SHALL 通过现有 Service Engine（`POST /api/v1/service/request`，API Key 认证）扩展 chat 和 query 请求类型，新增可选 `workflow_id` 字段，调用同一个 WorkflowService 执行工作流
4. WHEN External_Channel 请求携带 `workflow_id` 时，THE Workflow_Engine SHALL 从 API Key 的 scope 和 skill_whitelist 中提取权限约束，与工作流配置的权限取交集后执行
5. WHEN External_Channel 请求同时携带 `workflow_id` 和显式权限参数（如 `data_source_ids`、`skill_ids`）时，THE Workflow_Engine SHALL 以显式参数为准覆盖工作流配置中的对应项（API 传参 > 工作流配置 > 管理员默认配置）
6. THE Workflow_Engine SHALL 确保两个通道的工作流执行结果格式一致，Internal_Channel 返回 ChatResponse/SSE 流，External_Channel 返回 ServiceResponse 包装格式
7. THE Workflow_Engine SHALL 对两个通道的工作流执行均记录 AIAccessLog，日志中通过 `request_type` 字段区分来源（`chat` = 内部前端，`api` = 外部客户）
8. THE External_Channel SHALL 支持客户通过 `GET /api/v1/service/workflows` 端点（API Key 认证）查询其 API Key 有权访问的工作流列表，返回格式与内部端点一致
9. WHEN 工作流引擎实现完成后，THE Workflow_Engine SHALL 同步更新客户 API 文档（`文档/系统设计/智能服务引擎API接口文档.md`），补充工作流相关的传参说明、请求示例、响应格式、错误码，确保客户可据此文档完成对接

### 需求 13：向后兼容

**用户故事：** 作为系统维护者，我希望工作流引擎的引入不破坏现有功能，确保平滑过渡。

#### 验收标准

1. THE Workflow_Engine SHALL 保持现有 API 端点（数据源配置、角色权限、技能权限、访问日志）的完整功能和响应格式不变
2. WHEN 聊天请求未携带 `workflow_id` 参数时，THE Workflow_Engine SHALL 按现有逻辑处理（使用请求中的 mode、skill_ids、data_source_ids 等参数），确保未迁移到工作流模式的客户端正常工作
3. THE Workflow_Engine SHALL 复用现有的 AISkill、AIDataSourceConfigModel、AIDataSourceRolePermission、AISkillRolePermission 数据模型，通过新增 Workflow 模型建立关联，避免重复定义
4. THE Workflow_Engine SHALL 复用现有的 OpenClawChatService 和 LLMSwitcher 服务进行实际的 AI 调用，工作流引擎仅负责参数编排和权限校验

### 需求 14：动态授权请求预留（高阶功能）

**用户故事：** 作为平台运营方，我希望当工作流执行遇到权限不足时，系统能向客户 API 发起动态授权请求，由客户系统决定是否授予所需权限，实现按需授权而非预先全量配置。

#### 验收标准

1. THE Workflow_Engine SHALL 在权限链路校验失败时，除返回 403 错误外，在响应的 `details` 中包含 `authorization_request` 字段，描述所需授权的具体内容（缺失的技能 ID 列表、缺失的数据源/数据表列表、所需的角色权限）
2. THE Workflow_Engine SHALL 预留 `POST /api/v1/ai-assistant/workflows/request-authorization` 端点接口定义（本期仅定义接口签名和请求/响应格式，返回 501 Not Implemented），用于向客户系统发起授权请求
3. THE Workflow_Engine SHALL 预留 `POST /api/v1/service/authorization-callback` 端点接口定义（本期仅定义接口签名和请求/响应格式，返回 501 Not Implemented），用于接收客户系统的授权回调响应
4. THE Workflow_Engine SHALL 在客户 API 文档（`文档/系统设计/智能服务引擎API接口文档.md`）中补充动态授权请求的完整协议说明，包括：授权请求格式（含所需权限内容和范围）、授权回调格式（含授权结果和有效期）、交互时序图、错误码，确保客户可据此文档预先规划对接方案
5. THE Workflow_Engine SHALL 在 `authorization_request` 响应结构中包含以下字段：`request_id`（唯一请求标识）、`workflow_id`、`missing_permissions`（缺失权限明细，含类型 skill/data_source/data_table 和具体 ID 列表）、`requested_scope`（请求的授权范围描述）、`callback_url`（授权回调地址模板）
