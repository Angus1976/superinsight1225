# Implementation Plan: OpenClaw 技能端到端集成

## Overview

将管理控制台的技能数据源从直连 Agent 改为通过后端 API 读取数据库，实现技能列表、同步、执行、状态管理的端到端集成。后端新增 `SkillAdminRouter` + `SkillSyncService`，前端新增 `skillAdminApi` 并改造 `AIIntegration.tsx`。

## Tasks

- [x] 1. 后端 Pydantic Schemas 与 SkillSyncService
  - [x] 1.1 扩展 `src/ai_integration/schemas.py`，新增 SkillDetailResponse、SkillListResponse、SyncResultResponse、ExecuteRequest、ExecuteResultResponse、StatusToggle 模型
    - 复用已有 SkillInfoResponse，SkillDetailResponse 在其基础上增加 category、gateway_id、gateway_name、deployed_at、created_at 字段
    - _Requirements: 1.2, 3.5, 4.2_

  - [x] 1.2 创建 `src/ai_integration/skill_sync_service.py`，实现 SkillSyncService 类
    - `sync_from_agent(gateway)`: 调用 Agent GET /api/skills，执行 upsert 逻辑（新增→INSERT, 已有→UPDATE, 不存在→标记 removed），返回 SyncResult
    - `execute_skill(skill, gateway, params)`: 验证 skill.status=="deployed"，调用 Agent POST /api/skills/execute，写入 ai_audit_logs，返回执行结果
    - Agent 不可达返回 503，缺少 agent_url 返回 400，执行超时 30s 返回 504
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.3, 4.4, 4.5, 4.6_

  - [x] 1.3 编写 SkillSyncService 单元测试 `tests/test_skill_sync_service.py`
    - mock Agent HTTP 响应，验证 upsert 逻辑、错误处理、审计日志写入
    - _Requirements: 3.2, 3.3, 3.4, 3.6, 3.7, 4.6_

  - [x] 1.4 编写属性测试：同步后数据库与 Agent 一致
    - **Property 3: 同步后数据库与 Agent 一致**
    - **Validates: Requirements 3.2, 3.3, 3.4**

  - [x] 1.5 编写属性测试：同步计数准确性
    - **Property 4: 同步计数准确性**
    - **Validates: Requirement 3.5**

- [x] 2. 后端 SkillAdminRouter API
  - [x] 2.1 创建 `src/api/skill_admin.py`，实现 SkillAdminRouter
    - `GET /api/v1/admin/skills/` — 按 tenant_id 过滤，返回 active gateway 下的技能列表，按 deployed_at 降序
    - `POST /api/v1/admin/skills/sync` — 调用 SkillSyncService.sync_from_agent
    - `POST /api/v1/admin/skills/{skill_id}/execute` — 验证 deployed 状态后调用执行
    - `PATCH /api/v1/admin/skills/{skill_id}/status` — 切换 deployed/pending 状态
    - tenant_id 从 JWT token 中提取，所有查询强制 tenant 过滤
    - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.2, 4.3, 5.1, 5.2, 5.3_

  - [x] 2.2 在 FastAPI app 中注册 SkillAdminRouter（修改 `src/main.py` 或对应路由注册文件）
    - _Requirements: 1.1_

  - [x] 2.3 编写 SkillAdminRouter 单元测试 `tests/test_skill_admin.py`
    - mock service 层，验证权限校验、参数校验、租户隔离
    - _Requirements: 1.1, 2.1, 2.2, 4.3, 5.1_

  - [x] 2.4 编写属性测试：租户隔离
    - **Property 1: 租户隔离**
    - **Validates: Requirements 1.1, 2.1, 2.2**

  - [x] 2.5 编写属性测试：非 deployed 技能执行拒绝
    - **Property 5: 非 deployed 技能执行拒绝**
    - **Validates: Requirement 4.3**

- [x] 3. Checkpoint — 后端验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. 前端类型与 API 服务
  - [x] 4.1 扩展 `frontend/src/types/aiAssistant.ts`，新增 SkillDetail、SyncResult、ExecuteResult 接口
    - SkillDetail extends SkillInfo，增加 category、gateway_id、gateway_name、deployed_at、created_at
    - _Requirements: 1.2, 3.5, 4.2_

  - [x] 4.2 创建 `frontend/src/services/skillAdminApi.ts`，实现 listSkills、syncSkills、executeSkill、toggleSkillStatus 函数
    - 所有请求走后端 `/api/v1/admin/skills` 路径，不直连 Agent
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1_

- [x] 5. 前端 AIIntegration 页面改造
  - [x] 5.1 修改 `frontend/src/pages/Admin/AIIntegration.tsx` 技能管理 Tab
    - 替换直连 Agent 的调用为 skillAdminApi
    - 技能列表加载调用 listSkills，同步按钮调用 syncSkills 并显示 added/updated/removed 计数
    - 执行按钮调用 executeSkill 并展示结果或错误
    - 状态切换调用 toggleSkillStatus 并刷新列表
    - 异步操作期间显示 loading 状态
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2_

  - [x] 5.2 编写属性测试：技能列表排序不变量（前端 fast-check）
    - **Property 2: 技能列表排序不变量**
    - **Validates: Requirement 1.3**

  - [x] 5.3 编写属性测试：状态切换生效
    - **Property 7: 状态切换生效**
    - **Validates: Requirements 5.1, 5.2**

  - [x] 5.4 编写属性测试：技能执行审计日志
    - **Property 6: 技能执行审计日志**
    - **Validates: Requirement 4.6**

- [x] 6. Final Checkpoint — 全量验证
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 后端使用 Python (FastAPI + SQLAlchemy)，前端使用 TypeScript (React + Ant Design + React Query)
- 已有 AIGateway / AISkill 数据库模型无需修改，仅新增 API 层和服务层
- Property tests 使用 Hypothesis (Python) 或 fast-check (TypeScript)
