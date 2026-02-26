# Implementation Plan: AI Assistant OpenClaw Integration

## Overview

在现有 AI 智能助手页面中集成 OpenClaw 模式切换。后端新增 mode 路由和 openclaw-status 端点，前端新增模式切换器和技能面板。复用已有的 OpenClawLLMBridge、GatewayManager、SkillManager 基础设施。

## Tasks

- [x] 1. Define types and extend data models
  - [x] 1.1 Add frontend type definitions in `frontend/src/types/aiAssistant.ts`
    - Add `ChatMode`, `SkillInfo`, `OpenClawStatus` types
    - Extend `ChatRequest` with `mode`, `gateway_id`, `skill_ids` fields
    - _Requirements: 10.1, 10.4, 10.5_
  - [x] 1.2 Extend backend `ChatRequest` model in `src/api/ai_assistant.py`
    - Add `mode`, `gateway_id`, `skill_ids` fields with Pydantic validators
    - Add `OpenClawStatusResponse` and `SkillInfoResponse` models
    - Add `model_validator` for openclaw mode requiring gateway_id
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [ ]* 1.3 Write property test for ChatRequest validation
    - **Property 1: OpenClaw mode requires gateway_id**
    - **Property 2: Direct mode ignores skill_ids**
    - **Validates: Requirements 10.4, 10.5**

- [x] 2. Implement OpenClaw Chat Service
  - [x] 2.1 Create `src/ai_integration/openclaw_chat_service.py`
    - Implement `OpenClawChatService` class with `chat()`, `stream_chat()`, `get_status()` methods
    - Use `OpenClawLLMBridge.handle_llm_request` for non-streaming
    - Implement SSE streaming via OpenClaw Gateway HTTP API
    - Query active gateways and deployed skills for status
    - Handle timeout (60s), connection drops, and gateway unavailable errors
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5_
  - [ ]* 2.2 Write property test for get_status returns only deployed skills
    - **Property 3: Status endpoint returns only deployed skills**
    - **Validates: Requirements 3.5**
  - [ ]* 2.3 Write property test for stream_chat yields valid JSON chunks
    - **Property 4: Stream chunks are valid JSON with content and done fields**
    - **Validates: Requirements 2.2, 2.3**
  - [ ]* 2.4 Write unit tests for OpenClawChatService error handling
    - Test timeout yields error chunk with done=true
    - Test connection drop yields error chunk
    - Test gateway unavailable raises OpenClawUnavailableError
    - _Requirements: 6.1, 7.1, 8.1_

- [x] 3. Checkpoint - Ensure backend service tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Extend backend API with mode routing
  - [x] 4.1 Add mode routing to chat endpoints in `src/api/ai_assistant.py`
    - Modify `chat()` and `chat_stream()` to route based on `request.mode`
    - Direct mode: use existing LLMSwitcher flow (unchanged)
    - OpenClaw mode: delegate to OpenClawChatService
    - Validate gateway_id belongs to current tenant
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 11.1, 11.2, 11.3_
  - [x] 4.2 Add `/chat/openclaw-status` GET endpoint
    - Return `OpenClawStatusResponse` with gateway availability and skills
    - Filter by current tenant, catch all internal errors
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [ ]* 4.3 Write property test for mode routing isolation
    - **Property 5: Direct mode never accesses OpenClaw infrastructure**
    - **Validates: Requirements 1.1, 1.3**
  - [ ]* 4.4 Write unit tests for API endpoints
    - Test direct mode routing, openclaw mode routing
    - Test openclaw-status with/without active gateway
    - Test tenant isolation on gateway_id
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 9.1, 11.2, 11.3_

- [x] 5. Checkpoint - Ensure backend API tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement frontend API and mode switcher
  - [x] 6.1 Add `getOpenClawStatus()` to `frontend/src/services/aiAssistantApi.ts`
    - Call GET `/api/v1/ai-assistant/chat/openclaw-status`
    - Update `sendMessage` and `sendMessageStream` to pass mode/gateway_id/skill_ids
    - _Requirements: 3.1, 4.2, 4.5_
  - [x] 6.2 Add Mode Switcher UI in `frontend/src/pages/AIAssistant/index.tsx`
    - Render Ant Design `Segmented` with "LLM 直连" / "OpenClaw" options
    - On OpenClaw select: call `getOpenClawStatus()`, block switch if unavailable
    - On direct select: clear gateway state
    - Pass mode, gateway_id, skill_ids to chat API calls
    - Add i18n keys for mode labels and error messages
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.2_
  - [ ]* 6.3 Write unit tests for Mode Switcher
    - Test mode toggle renders correctly
    - Test gateway unavailable blocks OpenClaw switch
    - Test mode state passed to API calls
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 7. Implement frontend Skill Panel
  - [x] 7.1 Add Skill Panel component in `frontend/src/pages/AIAssistant/index.tsx`
    - Show skill list when mode is openclaw, hide when direct
    - Display skill name, version, status, description
    - Support skill toggle (checkbox) to select/deselect skills
    - Pass selected skill_ids with chat requests
    - Add i18n keys for skill panel labels
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [ ]* 7.2 Write unit tests for Skill Panel
    - Test panel visibility based on mode
    - Test skill toggle updates selected list
    - Test skill info display
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 8. Implement frontend error handling
  - [x] 8.1 Handle error scenarios in AI Assistant page
    - Gateway unavailable (503): show error notification, suggest direct mode
    - Request timeout: stop loading, display timeout message
    - Stream disconnect: preserve partial content, show error
    - Invalid gateway (404): re-query openclaw-status to refresh
    - _Requirements: 6.1, 6.2, 7.1, 7.2, 8.1, 8.2, 9.1, 9.2_
  - [ ]* 8.2 Write property test for frontend ChatRequest mode validation (fast-check)
    - **Property 6: OpenClaw mode ChatRequest always includes gateway_id**
    - **Validates: Requirements 10.4, 4.5**

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Reuse existing infrastructure: OpenClawLLMBridge, GatewayManager, SkillManager, LLMSwitcher
- Do NOT modify existing `src/ai_integration/` files or `src/ai/llm_switcher.py`
- Property tests use hypothesis (Python) and fast-check (TypeScript)
- All backend async operations follow existing patterns in ai_assistant.py
- Frontend uses Ant Design components and react-i18next for i18n
