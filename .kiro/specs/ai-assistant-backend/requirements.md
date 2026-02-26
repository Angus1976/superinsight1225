# 需求文档：AI 智能助手后端集成

## 简介

将现有 AI 助手前端页面从硬编码模拟响应升级为真实 LLM 后端对接。通过新增 FastAPI 路由连接现有 LLMSwitcher 基础设施，支持流式（SSE）和非流式两种对话模式，并在前端实现流式文本渲染。

## 术语表

- **AI_Assistant_Router**：FastAPI 路由模块，提供 AI 助手聊天 API 端点
- **LLMSwitcher**：现有的 LLM 提供商切换器，管理 Ollama/Cloud 等多个 LLM 后端
- **SSE**：Server-Sent Events，服务器推送事件协议，用于流式响应
- **StreamChunk**：流式响应中的单个数据块，包含 content 和 done 字段
- **ChatRequest**：聊天请求数据模型，包含消息历史和可选参数
- **ChatResponse**：非流式聊天响应数据模型，包含生成内容、模型名和用量信息
- **Frontend_Service**：前端 API 服务层，封装对后端的 HTTP 调用
- **AIAssistant_Page**：前端 AI 助手页面组件

## 需求

### 需求 1：非流式聊天 API

**用户故事：** 作为前端开发者，我希望有一个非流式聊天 API 端点，以便在不需要实时渲染的场景下获取完整的 AI 回复。

#### 验收标准

1. WHEN 已认证用户发送包含有效消息历史的 ChatRequest，THE AI_Assistant_Router SHALL 调用 LLMSwitcher 生成回复并返回包含 content、model、usage 字段的 ChatResponse
2. WHEN ChatRequest 中 messages 为空数组，THE AI_Assistant_Router SHALL 返回 HTTP 422 并附带参数校验错误信息
3. WHEN ChatRequest 中 temperature 超出 [0.0, 2.0] 范围，THE AI_Assistant_Router SHALL 返回 HTTP 422 并附带参数校验错误信息
4. WHEN ChatRequest 中 max_tokens 超出 [1, 4096] 范围，THE AI_Assistant_Router SHALL 返回 HTTP 422 并附带参数校验错误信息

### 需求 2：流式聊天 API（SSE）

**用户故事：** 作为用户，我希望 AI 回复能逐字流式显示，以便获得更好的交互体验而不必等待完整回复。

#### 验收标准

1. WHEN 已认证用户发送流式 ChatRequest，THE AI_Assistant_Router SHALL 返回 Content-Type 为 text/event-stream 的 StreamingResponse
2. WHILE 流式响应进行中，THE AI_Assistant_Router SHALL 以 `data: {"content": "...", "done": false}\n\n` 格式发送每个文本块
3. WHEN LLM 生成完毕，THE AI_Assistant_Router SHALL 发送 `data: {"content": "", "done": true}\n\n` 作为结束标记
4. IF 流式生成过程中 LLM 抛出异常，THEN THE AI_Assistant_Router SHALL 发送 `data: {"error": "...", "done": true}\n\n` 并关闭流

### 需求 3：用户认证

**用户故事：** 作为系统管理员，我希望 AI 助手 API 受 JWT 认证保护，以便只有已登录用户才能使用 AI 功能。

#### 验收标准

1. THE AI_Assistant_Router SHALL 对所有端点使用 get_current_user 依赖进行 JWT 认证
2. WHEN 请求未携带 Bearer token 或 token 无效，THE AI_Assistant_Router SHALL 返回 HTTP 401 并附带 "Invalid or expired token" 错误信息
3. WHEN 请求携带的 token 对应的用户已被禁用，THE AI_Assistant_Router SHALL 返回 HTTP 401 并附带 "User not found or inactive" 错误信息

### 需求 4：LLM 服务异常处理

**用户故事：** 作为用户，我希望在 LLM 服务不可用时获得清晰的错误提示，以便了解问题并决定是否重试。

#### 验收标准

1. IF LLMSwitcher 无可用 provider，THEN THE AI_Assistant_Router SHALL 返回 HTTP 503 并附带 "AI 服务暂不可用" 错误信息
2. IF LLM 响应超过 60 秒未完成，THEN THE AI_Assistant_Router SHALL 返回 HTTP 504 超时错误
3. IF 非流式调用中 LLM 抛出未预期异常，THEN THE AI_Assistant_Router SHALL 返回 HTTP 500 并记录错误日志

### 需求 5：Prompt 构建与上下文管理

**用户故事：** 作为用户，我希望 AI 助手能理解多轮对话上下文，以便进行连贯的对话。

#### 验收标准

1. WHEN 构建 LLM 请求时，THE AI_Assistant_Router SHALL 将 ChatRequest 中的历史消息拼接为上下文传递给 LLMSwitcher
2. THE AI_Assistant_Router SHALL 在每次请求中附带预定义的 system_prompt 以约束 AI 助手行为
3. WHEN ChatRequest 包含多条消息，THE AI_Assistant_Router SHALL 保持消息的原始顺序传递给 LLM

### 需求 6：前端 API 服务层

**用户故事：** 作为前端开发者，我希望有封装好的 API 服务函数，以便在页面组件中方便地调用 AI 助手后端。

#### 验收标准

1. THE Frontend_Service SHALL 提供 sendMessage 函数用于非流式调用，返回 ChatResponse
2. THE Frontend_Service SHALL 提供 sendMessageStream 函数用于流式调用，返回 AbortController 以支持取消
3. WHEN 流式响应中收到 StreamChunk，THE Frontend_Service SHALL 通过 onChunk 回调将 content 传递给调用方
4. WHEN 流式响应结束（done=true），THE Frontend_Service SHALL 调用 onDone 回调通知调用方
5. IF 流式响应中收到 error 字段，THEN THE Frontend_Service SHALL 调用 onError 回调并传递错误信息

### 需求 7：前端页面集成

**用户故事：** 作为用户，我希望 AI 助手页面能实时显示 AI 回复，以便获得流畅的对话体验。

#### 验收标准

1. WHEN 用户发送消息，THE AIAssistant_Page SHALL 调用 Frontend_Service 的流式接口发起请求
2. WHILE 流式响应进行中，THE AIAssistant_Page SHALL 将收到的文本块实时追加到当前助手消息中
3. WHEN 用户点击取消按钮，THE AIAssistant_Page SHALL 调用 AbortController.abort() 终止流式请求
4. WHEN 调用 abort() 后，THE AIAssistant_Page SHALL 停止接收后续 chunk 并保留已显示的内容
5. IF API 调用返回错误，THEN THE AIAssistant_Page SHALL 显示用户友好的错误提示信息

### 需求 8：路由注册

**用户故事：** 作为后端开发者，我希望 AI 助手路由能通过现有的可选路由机制注册，以便保持系统架构一致性。

#### 验收标准

1. THE AI_Assistant_Router SHALL 在 app.py 的 include_optional_routers() 中注册
2. IF AI_Assistant_Router 模块导入失败，THEN app.py SHALL 记录警告日志并继续启动，不影响其他功能
