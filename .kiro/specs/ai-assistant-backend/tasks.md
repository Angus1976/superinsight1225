# 实施计划：AI 智能助手后端集成

## 概述

将 AI 助手从硬编码模拟升级为真实 LLM 后端对接。后端使用 FastAPI + LLMSwitcher，前端使用 fetch + ReadableStream 实现流式渲染。按照后端数据模型 → 路由实现 → 前端服务层 → 页面集成 → 路由注册的顺序递进实施。

## Tasks

- [x] 1. 实现后端数据模型与非流式聊天 API
  - [x] 1.1 创建 `src/api/ai_assistant.py`，定义 ChatMessage、ChatRequest、ChatResponse Pydantic 模型，实现 `POST /api/v1/ai-assistant/chat` 非流式端点
    - 定义 ChatMessage（role: Literal["user","assistant","system"], content: str）
    - 定义 ChatRequest（messages: list[ChatMessage], max_tokens: Optional[int], temperature: Optional[float]）含 Field 校验
    - 定义 ChatResponse（content: str, model: str, usage: Optional[dict]）
    - 实现 chat() 函数：认证 → 构建 prompt → 调用 LLMSwitcher.generate() → 返回 ChatResponse
    - 实现 format_chat_history() 辅助函数，将消息历史拼接为上下文字符串，保持原始顺序
    - 定义 SYSTEM_PROMPT 常量
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 5.1, 5.2, 5.3_

  - [ ]* 1.2 编写非流式 API 属性测试
    - **Property 1: 参数校验拒绝越界值**
    - **Validates: Requirements 1.3, 1.4**

  - [ ]* 1.3 编写非流式 API 单元测试
    - 测试有效请求返回 ChatResponse
    - 测试 messages 为空返回 422
    - 测试 temperature/max_tokens 越界返回 422
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. 实现流式聊天 API（SSE）与错误处理
  - [x] 2.1 在 `src/api/ai_assistant.py` 中添加 `POST /api/v1/ai-assistant/chat/stream` 流式端点
    - 实现 generate_stream() 异步生成器：调用 LLMSwitcher.stream_generate()，yield SSE 格式 chunk
    - 每个 chunk 格式：`data: {"content": "...", "done": false}\n\n`
    - 结束标记：`data: {"content": "", "done": true}\n\n`
    - 异常处理：`data: {"error": "...", "done": true}\n\n`
    - 返回 StreamingResponse，Content-Type 为 text/event-stream
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.2 实现 LLM 服务异常处理逻辑
    - LLMSwitcher 无可用 provider → HTTP 503
    - LLM 响应超时（60s）→ HTTP 504
    - 非流式未预期异常 → HTTP 500 + 错误日志
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 2.3 编写流式 API 属性测试
    - **Property 2: SSE 流格式一致性**
    - **Validates: Requirements 2.2, 2.3**

  - [ ]* 2.4 编写流式错误传播属性测试
    - **Property 3: 流式错误传播**
    - **Validates: Requirement 2.4**

  - [ ]* 2.5 编写认证强制性属性测试
    - **Property 4: 认证强制性**
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 2.6 编写 Prompt 构建属性测试
    - **Property 5: Prompt 上下文构建**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 3. 检查点 - 后端实现验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. 实现前端类型定义与 API 服务层
  - [x] 4.1 创建 `frontend/src/types/aiAssistant.ts`，定义前端类型
    - ChatMessage、ChatRequest、ChatResponse、StreamChunk 接口
    - _Requirements: 6.1, 6.2_

  - [x] 4.2 创建 `frontend/src/services/aiAssistantApi.ts`，实现 API 服务函数
    - sendMessage()：非流式调用，POST /api/v1/ai-assistant/chat，返回 ChatResponse
    - sendMessageStream()：流式调用，POST /api/v1/ai-assistant/chat/stream，使用 fetch + ReadableStream 解析 SSE
    - 实现 SSE 解析逻辑：buffer 拼接、按 `\n\n` 分割、解析 data: 前缀
    - 返回 AbortController 支持取消请求
    - onChunk / onDone / onError 回调处理
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 4.3 编写前端 SSE 解析属性测试
    - **Property 6: 前端 SSE 解析正确性**
    - **Validates: Requirements 6.3, 6.4, 6.5**

  - [ ]* 4.4 编写请求取消属性测试
    - **Property 7: 请求可取消**
    - **Validates: Requirements 7.3, 7.4**

- [x] 5. 改造前端 AI 助手页面
  - [x] 5.1 重构 `frontend/src/pages/AIAssistant/index.tsx`，替换硬编码 generateResponse() 为真实 API 调用
    - 导入 sendMessageStream 替换模拟函数
    - 发送消息时调用流式接口，实时追加 chunk 到当前助手消息
    - 添加 AbortController 引用，支持取消按钮调用 abort()
    - abort() 后停止接收 chunk，保留已显示内容
    - API 错误时显示用户友好提示（antd message）
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 6. 注册路由并集成
  - [x] 6.1 在 `src/app.py` 的 include_optional_routers() 中注册 AI Assistant Router
    - 按现有模式：try/except ImportError，成功日志 ✅，失败日志 ⚠️
    - 导入失败时记录警告并继续启动
    - _Requirements: 8.1, 8.2_

- [x] 7. 最终检查点 - 全功能验证
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- 标记 `*` 的任务为可选，可跳过以加速 MVP
- 后端使用 Python（FastAPI + Pydantic），前端使用 TypeScript
- 每个任务引用具体需求条款以确保可追溯性
- 属性测试验证设计文档中定义的 Correctness Properties
