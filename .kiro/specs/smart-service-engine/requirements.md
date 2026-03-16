# 需求文档：智能服务引擎（Smart Service Engine）

## 简介

SuperInsight 平台的智能服务引擎是对现有外部 API 体系的重大升级。通过新增统一 API 入口 `POST /api/v1/service/request`，将平台的全量治理数据、对话式分析、辅助决策和 OpenClaw 技能调用能力以标准化方式对外输出。客户的 APP、微信小程序、H5 等终端通过该统一入口获取智能服务，同时保留现有 4 个只读数据端点作为简单直连通道。

## 术语表

- **Service_Engine**：智能服务引擎后端核心模块，负责请求路由、上下文组装、记忆管理和响应生成
- **Request_Router**：请求路由器，根据 `request_type` 将请求分发到对应的 Handler
- **Context_Builder**：上下文构建器，组装平台治理数据与客户业务上下文，为 LLM 提供分析素材
- **User_Memory**：用户记忆模块，按 `user_id` 跨请求累积对话历史，定期总结压缩
- **Skill_Whitelist**：技能白名单模块，管理每个 API Key 允许调用的 OpenClaw 技能列表
- **Webhook_Pusher**：Webhook 推送模块（MVP 预留），用于主动通知客户系统
- **API_Key**：外部 API 访问密钥，`sk_` 前缀，SHA-256 哈希存储，承载 scopes 和速率限制
- **Governed_Data**：平台治理数据，包括标注结果、增强数据、质量报告、AI 试验结果、数据流转统计、数据同步状态、样本库数据等全量数据资产
- **Business_Context**：客户可选传入的业务上下文信息，如用户画像、交易记录等
- **SSE**：Server-Sent Events，服务端推送事件流协议，用于 chat 类型的流式响应
- **Admin_UI**：前端管理界面，位于 `/data-sync/api-management`，用于配置 API Key、权限、白名单等

## 需求

### 需求 1：统一 API 入口

**用户故事：** 作为外部系统开发者，我希望通过一个统一的 API 入口访问平台的所有智能服务能力，以便简化集成工作并降低对接成本。

#### 验收标准

1. THE Service_Engine SHALL 提供 `POST /api/v1/service/request` 作为统一 API 入口
2. THE Service_Engine SHALL 在请求体中接受 `request_type` 参数，支持的值为 `query`、`chat`、`decision`、`skill`
3. WHEN `request_type` 为 `query` 时，THE Request_Router SHALL 将请求分发到结构化数据查询 Handler
4. WHEN `request_type` 为 `chat` 时，THE Request_Router SHALL 将请求分发到对话式分析 Handler
5. WHEN `request_type` 为 `decision` 时，THE Request_Router SHALL 将请求分发到辅助决策 Handler
6. WHEN `request_type` 为 `skill` 时，THE Request_Router SHALL 将请求分发到 OpenClaw 技能调用 Handler
7. IF `request_type` 的值不在支持列表中，THEN THE Service_Engine SHALL 返回 HTTP 400 错误，包含错误码 `INVALID_REQUEST_TYPE` 和支持的类型列表
8. THE Service_Engine SHALL 复用现有的 X-API-Key 认证中间件进行身份验证
9. THE Service_Engine SHALL 复用现有的速率限制机制进行流量控制
10. THE Service_Engine SHALL 在每次请求中记录调用审计日志，包含 `request_type`、响应状态码和响应时间

### 需求 2：结构化数据查询（query）

**用户故事：** 作为外部系统开发者，我希望通过统一入口查询平台的全量治理数据，以便在客户端应用中展示和使用这些数据。

#### 验收标准

1. WHEN `request_type` 为 `query` 时，THE Service_Engine SHALL 接受 `data_type` 参数指定查询的数据类型
2. THE Service_Engine SHALL 支持以下 `data_type` 值：`annotations`（标注结果）、`augmented_data`（增强数据）、`quality_reports`（质量报告）、`experiments`（AI 试验结果）、`data_lifecycle`（数据流转统计）、`data_sync`（数据同步状态）、`samples`（样本库数据）、`tasks`（标注任务）
3. THE Service_Engine SHALL 对每种 `data_type` 执行对应的 scope 权限校验
4. THE Service_Engine SHALL 支持分页参数 `page` 和 `page_size`，默认值分别为 1 和 50
5. THE Service_Engine SHALL 支持排序参数 `sort_by`，前缀 `-` 表示降序
6. THE Service_Engine SHALL 支持字段筛选参数 `fields`，以逗号分隔
7. THE Service_Engine SHALL 支持过滤条件参数 `filters`，以 JSON 对象形式传入
8. THE Service_Engine SHALL 对所有查询结果执行租户隔离
9. IF `data_type` 的值不在支持列表中，THEN THE Service_Engine SHALL 返回 HTTP 400 错误，包含错误码 `INVALID_DATA_TYPE`
10. IF API_Key 的 scopes 不包含所请求的 `data_type` 权限，THEN THE Service_Engine SHALL 返回 HTTP 403 错误，包含错误码 `INSUFFICIENT_SCOPE`

### 需求 3：对话式分析（chat）

**用户故事：** 作为外部系统开发者，我希望通过对话方式让终端用户与平台的 AI 进行数据分析交互，以便提供智能化的数据洞察体验。

#### 验收标准

1. WHEN `request_type` 为 `chat` 时，THE Service_Engine SHALL 接受 `messages` 参数（对话历史数组）和 `user_id` 参数
2. THE Service_Engine SHALL 通过 SSE（Server-Sent Events）流式返回 AI 生成的分析内容
3. THE Context_Builder SHALL 根据对话内容自动从平台治理数据中检索相关数据作为 LLM 上下文
4. THE Service_Engine SHALL 复用现有的 LLM 集成模块（LLMSwitcher）进行文本生成
5. THE Service_Engine SHALL 在 SSE 流中使用 `data: {"content": "...", "done": false}` 格式传输中间内容
6. THE Service_Engine SHALL 在 SSE 流结束时发送 `data: {"content": "", "done": true}` 标记
7. IF LLM 服务不可用，THEN THE Service_Engine SHALL 返回 HTTP 503 错误，包含错误码 `LLM_UNAVAILABLE`
8. IF 对话请求超过 60 秒未响应，THEN THE Service_Engine SHALL 返回 HTTP 504 错误，包含错误码 `REQUEST_TIMEOUT`
9. THE Service_Engine SHALL 对 chat 类型请求执行 `chat` scope 权限校验

### 需求 4：辅助决策（decision）

**用户故事：** 作为外部系统开发者，我希望向平台提交决策请求并获取结构化的分析建议，以便在业务场景中辅助决策（如库存管理、定价策略等）。

#### 验收标准

1. WHEN `request_type` 为 `decision` 时，THE Service_Engine SHALL 接受 `question` 参数（决策问题描述）和 `user_id` 参数
2. THE Service_Engine SHALL 接受可选的 `context_data` 参数，用于传入业务场景数据
3. THE Context_Builder SHALL 组装平台治理数据与客户传入的 `context_data` 作为 LLM 分析素材
4. THE Service_Engine SHALL 以结构化 JSON 格式返回决策建议，包含 `summary`（摘要）、`analysis`（分析过程）、`recommendations`（建议列表）和 `confidence`（置信度）字段
5. THE Service_Engine SHALL 在每条 recommendation 中包含 `action`（建议操作）、`reason`（理由）和 `priority`（优先级）字段
6. THE Service_Engine SHALL 对 decision 类型请求执行 `decision` scope 权限校验
7. IF 分析过程中 LLM 返回的内容无法解析为结构化格式，THEN THE Service_Engine SHALL 将原始内容放入 `analysis` 字段并将 `confidence` 设为 0

### 需求 5：OpenClaw 技能调用（skill）

**用户故事：** 作为外部系统开发者，我希望通过统一入口调用平台部署的 OpenClaw 技能，以便在客户端应用中使用 AI 技能处理数据。

#### 验收标准

1. WHEN `request_type` 为 `skill` 时，THE Service_Engine SHALL 接受 `skill_id` 参数和 `parameters` 参数
2. THE Skill_Whitelist SHALL 校验请求的 `skill_id` 是否在当前 API_Key 的白名单中
3. IF `skill_id` 不在白名单中，THEN THE Service_Engine SHALL 返回 HTTP 403 错误，包含错误码 `SKILL_NOT_ALLOWED`
4. THE Service_Engine SHALL 复用现有的 SkillManager 执行技能调用
5. THE Service_Engine SHALL 返回技能执行结果，包含 `success`（是否成功）、`result`（执行结果）和 `execution_time_ms`（执行耗时）字段
6. IF 指定的 `skill_id` 不存在或未部署，THEN THE Service_Engine SHALL 返回 HTTP 404 错误，包含错误码 `SKILL_NOT_FOUND`
7. THE Service_Engine SHALL 对 skill 类型请求执行 `skill` scope 权限校验

### 需求 6：业务上下文传入

**用户故事：** 作为外部系统开发者，我希望在请求中传入业务上下文（如用户画像），以便平台的 AI 分析能结合客户侧的业务数据提供更精准的响应。

#### 验收标准

1. THE Service_Engine SHALL 在所有请求类型中接受必传的 `user_id` 参数
2. THE Service_Engine SHALL 在所有请求类型中接受可选的 `business_context` 参数（JSON 对象）
3. WHEN `business_context` 被传入时，THE Context_Builder SHALL 将业务上下文与平台治理数据合并后注入 LLM 提示词
4. IF `user_id` 参数缺失，THEN THE Service_Engine SHALL 返回 HTTP 400 错误，包含错误码 `MISSING_USER_ID`
5. THE Service_Engine SHALL 对 `business_context` 的大小进行限制，单次请求的 `business_context` JSON 序列化后不超过 100KB

### 需求 7：用户全局记忆

**用户故事：** 作为外部系统开发者，我希望平台能记住终端用户的历史交互，以便在后续请求中提供更连贯和个性化的响应。

#### 验收标准

1. THE User_Memory SHALL 按 `user_id` 和 `tenant_id` 的组合存储用户交互历史
2. WHEN 收到请求时，THE User_Memory SHALL 加载该 `user_id` 的历史记忆并注入 LLM 上下文
3. WHEN 请求处理完成后，THE User_Memory SHALL 将本次交互的关键信息追加到用户记忆中
4. WHEN 用户记忆的条目数超过 50 条时，THE User_Memory SHALL 触发总结压缩，使用 LLM 将历史记忆压缩为摘要
5. THE User_Memory SHALL 为每条记忆记录创建时间戳，用于按时间排序和过期清理
6. THE Service_Engine SHALL 支持通过 API 参数 `include_memory` 控制是否启用记忆功能，默认为 `true`

### 需求 8：Webhook 推送（MVP 预留）

**用户故事：** 作为外部系统开发者，我希望平台能在特定事件发生时主动推送通知到我的系统，以便实现事件驱动的业务流程。

#### 验收标准

1. THE Service_Engine SHALL 在数据模型中预留 Webhook 配置字段，包含 `webhook_url`、`webhook_secret` 和 `webhook_events` 字段
2. THE Webhook_Pusher SHALL 提供 Webhook 配置的 CRUD 接口（仅数据存储，推送逻辑后续实现）
3. THE Admin_UI SHALL 在 API 管理页面中提供 Webhook 地址配置表单（标记为"即将推出"）
4. THE Service_Engine SHALL 在 API Key 模型中扩展 `webhook_config` 字段用于存储 Webhook 配置

### 需求 9：前端管理界面扩展

**用户故事：** 作为平台管理员，我希望在现有的 API 管理页面中统一管理智能服务引擎的所有配置，以便集中控制外部 API 的访问权限和行为。

#### 验收标准

1. THE Admin_UI SHALL 在现有 `/data-sync/api-management` 页面中扩展以下配置功能
2. THE Admin_UI SHALL 提供每个 API_Key 允许的 `request_type` 配置界面，支持多选 `query`、`chat`、`decision`、`skill`
3. THE Admin_UI SHALL 提供每个 API_Key 的 Skill 白名单配置界面，支持从已部署的 Skills 列表中选择
4. THE Admin_UI SHALL 提供 Webhook 地址配置界面（标记为"即将推出"状态）
5. THE Admin_UI SHALL 提供 API 指导文档的查看和下载功能
6. THE Admin_UI SHALL 所有用户可见文本使用 i18n 国际化，支持中文和英文双语切换
7. WHEN 管理员修改 API_Key 的 `request_type` 配置时，THE Admin_UI SHALL 立即将变更同步到后端
8. WHEN 管理员修改 Skill 白名单时，THE Admin_UI SHALL 展示每个 Skill 的名称、版本和状态信息

### 需求 10：统一请求/响应格式

**用户故事：** 作为外部系统开发者，我希望统一入口的请求和响应格式保持一致且可预测，以便降低客户端的解析复杂度。

#### 验收标准

1. THE Service_Engine SHALL 对所有请求类型使用统一的请求体结构，包含 `request_type`、`user_id`、`business_context`（可选）和类型特定的参数字段
2. THE Service_Engine SHALL 对所有成功响应使用统一的响应结构，包含 `success`（布尔值）、`request_type`（回显）、`data`（类型特定的响应数据）和 `metadata`（请求元信息）字段
3. THE Service_Engine SHALL 对所有错误响应使用统一的错误结构，包含 `success`（false）、`error`（错误描述）、`error_code`（机器可读错误码）和 `details`（附加信息）字段
4. THE Service_Engine SHALL 在 `metadata` 中包含 `request_id`（唯一请求标识）、`timestamp`（处理时间戳）和 `processing_time_ms`（处理耗时）字段
5. THE Service_Engine SHALL 对 chat 类型以外的所有请求类型使用 JSON 格式返回响应

### 需求 11：权限与安全扩展

**用户故事：** 作为平台管理员，我希望能精细控制每个 API Key 可以使用的服务类型和数据范围，以便确保外部访问的安全性。

#### 验收标准

1. THE Service_Engine SHALL 在 API_Key 的 scopes 中扩展以下权限项：`query`、`chat`、`decision`、`skill`
2. WHEN 收到请求时，THE Service_Engine SHALL 校验 API_Key 的 scopes 是否包含对应 `request_type` 的权限
3. IF API_Key 的 scopes 不包含所请求的 `request_type` 权限，THEN THE Service_Engine SHALL 返回 HTTP 403 错误
4. THE Service_Engine SHALL 在 API_Key 模型中扩展 `allowed_request_types` 字段（JSON 数组），用于存储允许的请求类型
5. THE Service_Engine SHALL 在 API_Key 模型中扩展 `skill_whitelist` 字段（JSON 数组），用于存储允许调用的 Skill ID 列表
6. THE Service_Engine SHALL 保持与现有 4 个只读数据端点的权限体系兼容，现有 scopes（`annotations`、`augmented_data`、`quality_reports`、`experiments`）继续生效

### 需求 12：灵活扩展性架构

**用户故事：** 作为平台开发者，我希望智能服务引擎采用插件化架构设计，以便未来能快速接入新的请求类型和处理能力，而无需修改核心路由和协议层。

#### 验收标准

1. THE Request_Router SHALL 采用 Handler 注册机制，每种 `request_type` 对应一个独立的 Handler 类，通过注册表动态映射
2. THE Service_Engine SHALL 定义统一的 Handler 接口（BaseHandler），包含 `validate()`（参数校验）、`build_context()`（上下文组装）和 `execute()`（执行处理）方法
3. WHEN 需要新增 `request_type` 时，开发者 SHALL 仅需实现 BaseHandler 接口并注册到 Request_Router，无需修改路由分发逻辑
4. THE Service_Engine SHALL 支持通过配置动态启用或禁用特定的 `request_type`，无需重启服务
5. THE Context_Builder SHALL 采用数据源注册表模式，每种数据源通过独立的 DataProvider 提供数据，新增数据源仅需实现 DataProvider 接口并注册
6. THE Service_Engine SHALL 在统一请求体中预留 `extensions` 字段（可选 JSON 对象），用于未来扩展类型传递自定义参数，不影响现有协议结构
