# Requirements Document

## Introduction

本文档定义 AI 智能助手页面集成 OpenClaw 应用服务的功能需求。用户可在 LLM 直连模式和 OpenClaw 模式之间切换，OpenClaw 模式通过网关调用支持技能增强的对话能力。后端通过 `mode` 参数路由请求，前端提供模式切换器和技能面板。

## Glossary

- **Chat_Router**: 后端聊天请求路由模块，根据 mode 参数将请求分发到不同的 LLM 后端
- **OpenClaw_Chat_Service**: 封装 OpenClaw 网关聊天调用逻辑的后端服务
- **Mode_Switcher**: 前端模式切换 UI 组件（Segmented），用于在 direct 和 openclaw 模式间切换
- **Skill_Panel**: 前端技能面板组件，展示和选择 OpenClaw 可用技能
- **ChatRequest**: 聊天请求数据模型，包含 messages、mode、gateway_id、skill_ids 等字段
- **OpenClaw_Status_Endpoint**: 后端 `/chat/openclaw-status` 端点，返回网关可用性和技能列表
- **Gateway**: OpenClaw 网关实例，负责接收聊天请求并通过 Agent 处理
- **Skill**: OpenClaw 技能，部署在网关上的功能增强模块
- **SSE_Stream**: Server-Sent Events 流式响应，用于逐步返回聊天内容

## Requirements

### Requirement 1: 聊天请求模式路由

**User Story:** As a user, I want to choose between LLM direct mode and OpenClaw mode, so that I can use either basic LLM or skill-enhanced AI capabilities.

#### Acceptance Criteria

1. WHEN a ChatRequest with `mode="direct"` is received, THE Chat_Router SHALL forward the request to LLMSwitcher and return the LLM response
2. WHEN a ChatRequest with `mode="openclaw"` is received, THE Chat_Router SHALL forward the request to OpenClaw_Chat_Service and return the gateway response
3. WHEN a ChatRequest omits the `mode` field, THE Chat_Router SHALL default to `"direct"` mode
4. WHEN a ChatRequest with `mode="openclaw"` has an empty or missing `gateway_id`, THE Chat_Router SHALL reject the request with a validation error

### Requirement 2: OpenClaw 聊天服务

**User Story:** As a user, I want to chat through the OpenClaw gateway, so that I can leverage deployed skills for enhanced AI responses.

#### Acceptance Criteria

1. WHEN OpenClaw_Chat_Service receives a valid chat request, THE OpenClaw_Chat_Service SHALL call OpenClawLLMBridge to process the request and return an LLMResponse
2. WHEN OpenClaw_Chat_Service receives a stream chat request, THE OpenClaw_Chat_Service SHALL yield SSE-formatted JSON chunks where each chunk contains a `content` field and a `done` field
3. WHEN the stream chat completes, THE OpenClaw_Chat_Service SHALL yield a final chunk with `done: true`
4. WHEN `skill_ids` are provided in the request, THE OpenClaw_Chat_Service SHALL pass the selected skill identifiers to the gateway for skill-enhanced processing

### Requirement 3: OpenClaw 状态查询

**User Story:** As a user, I want to check OpenClaw gateway availability before switching modes, so that I know whether OpenClaw features are accessible.

#### Acceptance Criteria

1. WHEN the OpenClaw_Status_Endpoint is called, THE OpenClaw_Status_Endpoint SHALL query active OpenClaw gateways for the current tenant
2. WHEN an active OpenClaw gateway exists, THE OpenClaw_Status_Endpoint SHALL return `available: true` along with the gateway_id, gateway_name, and a list of deployed skills
3. WHEN no active OpenClaw gateway exists, THE OpenClaw_Status_Endpoint SHALL return `available: false` with an error message describing the reason
4. WHEN the status query encounters an internal error, THE OpenClaw_Status_Endpoint SHALL return `available: false` with an error description instead of raising an exception
5. THE OpenClaw_Status_Endpoint SHALL only return skills with status `"deployed"` in the skills list

### Requirement 4: 前端模式切换

**User Story:** As a user, I want a mode switcher in the AI assistant header, so that I can easily toggle between LLM direct and OpenClaw modes.

#### Acceptance Criteria

1. THE Mode_Switcher SHALL render a Segmented component with two options: "LLM 直连" and "OpenClaw"
2. WHEN the user selects OpenClaw mode, THE Mode_Switcher SHALL call the OpenClaw_Status_Endpoint to check gateway availability
3. WHEN the OpenClaw gateway is unavailable, THE Mode_Switcher SHALL display a warning message and prevent the mode from switching to OpenClaw
4. WHEN the user selects direct mode, THE Mode_Switcher SHALL clear the gateway_id and skills state and route subsequent requests to LLMSwitcher
5. WHEN the mode is set to OpenClaw, THE Mode_Switcher SHALL include the gateway_id and selected skill_ids in all subsequent chat requests

### Requirement 5: 前端技能面板

**User Story:** As a user, I want to see and select available skills when using OpenClaw mode, so that I can customize which skills enhance my AI interactions.

#### Acceptance Criteria

1. WHILE the chat mode is `"openclaw"`, THE Skill_Panel SHALL be visible and display the list of deployed skills from the current gateway
2. WHILE the chat mode is `"direct"`, THE Skill_Panel SHALL be hidden
3. WHEN a user toggles a skill in the Skill_Panel, THE Skill_Panel SHALL update the selected skill_ids list accordingly
4. THE Skill_Panel SHALL display each skill's name, version, status, and description

### Requirement 6: 错误处理 — 网关不可用

**User Story:** As a user, I want clear feedback when the OpenClaw gateway is unavailable, so that I can switch to an alternative mode without confusion.

#### Acceptance Criteria

1. WHEN the OpenClaw gateway is unreachable during a chat request, THE Chat_Router SHALL return an HTTP 503 error with a descriptive message
2. WHEN the frontend receives a gateway unavailable error, THE Mode_Switcher SHALL display an error notification and suggest switching to LLM direct mode

### Requirement 7: 错误处理 — 请求超时

**User Story:** As a user, I want to be informed when an OpenClaw request times out, so that I can retry or switch modes.

#### Acceptance Criteria

1. WHEN an OpenClaw gateway request exceeds 60 seconds, THE OpenClaw_Chat_Service SHALL terminate the request and yield an SSE error chunk with a timeout message and `done: true`
2. WHEN the frontend receives a timeout error chunk, THE Mode_Switcher SHALL stop the loading state and display the timeout error to the user

### Requirement 8: 错误处理 — 流式中途断开

**User Story:** As a user, I want to see partial responses and a clear error when the stream disconnects mid-conversation, so that I do not lose already received content.

#### Acceptance Criteria

1. WHEN the OpenClaw gateway connection drops during streaming, THE OpenClaw_Chat_Service SHALL catch the connection exception and yield an SSE error chunk with `done: true`
2. WHEN the frontend receives an error chunk during streaming, THE Mode_Switcher SHALL stop the loading indicator, preserve the partially received content, and display an error message

### Requirement 9: 错误处理 — 无效 gateway_id

**User Story:** As a user, I want the system to handle invalid gateway references gracefully, so that I can recover by refreshing gateway information.

#### Acceptance Criteria

1. WHEN a chat request references a gateway_id that does not exist or is inactive, THE Chat_Router SHALL return an HTTP 404 error with a descriptive message
2. WHEN the frontend receives a 404 gateway error, THE Mode_Switcher SHALL re-query the OpenClaw_Status_Endpoint to refresh gateway information

### Requirement 10: 请求数据验证

**User Story:** As a developer, I want strict validation on ChatRequest fields, so that invalid data is rejected before processing.

#### Acceptance Criteria

1. THE ChatRequest SHALL require `messages` to contain at least one ChatMessage
2. THE ChatRequest SHALL constrain `max_tokens` to a range of 1 to 4096 when provided
3. THE ChatRequest SHALL constrain `temperature` to a range of 0.0 to 2.0 when provided
4. WHEN `mode` is `"openclaw"`, THE ChatRequest SHALL require `gateway_id` to be non-empty
5. THE ChatRequest SHALL ignore `skill_ids` when `mode` is `"direct"`

### Requirement 11: 租户隔离与安全

**User Story:** As a system administrator, I want tenant-level isolation for gateway and skill data, so that users cannot access resources belonging to other tenants.

#### Acceptance Criteria

1. THE Chat_Router SHALL authenticate all requests using the existing JWT authentication mechanism
2. THE OpenClaw_Status_Endpoint SHALL only return gateways and skills belonging to the requesting user's tenant
3. WHEN a chat request references a gateway_id not belonging to the current tenant, THE Chat_Router SHALL reject the request with an authorization error
