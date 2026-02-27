# Requirements Document

## Introduction

本文档定义 OpenClaw 技能端到端集成的需求。当前管理控制台的"已部署技能"列表为空，因为它直连 Agent 服务而非读取数据库。本功能将管理控制台的技能数据源统一到后端 API，使管理员能查看、同步、管理 OpenClaw 网关上的技能，并支持端到端技能执行。

## Glossary

- **SkillAdminRouter**: 管理端技能 API 路由，提供技能列表、同步、执行、状态切换端点
- **SkillSyncService**: 技能同步服务，负责从 OpenClaw Agent 拉取技能并写入数据库
- **AISkill**: 数据库中的技能记录模型，存储在 `ai_skills` 表
- **AIGateway**: 数据库中的网关记录模型，存储在 `ai_gateways` 表
- **Agent**: OpenClaw Agent 服务，提供 `/api/skills` 和 `/api/skills/execute` HTTP 接口
- **AdminUI**: 管理控制台前端 AIIntegration 页面的技能管理 Tab
- **SkillAdminApi**: 前端 API 服务模块，封装对 SkillAdminRouter 的 HTTP 调用

## Requirements

### Requirement 1: 技能列表查询

**User Story:** As a 管理员, I want to 在管理控制台查看已部署的技能列表, so that 我能了解当前系统中可用的技能。

#### Acceptance Criteria

1. WHEN a 管理员 requests the skill list, THE SkillAdminRouter SHALL return all AISkill records associated with the tenant's active AIGateway
2. THE SkillAdminRouter SHALL return each AISkill with id, name, version, status, description, category, gateway_id, gateway_name, deployed_at, and created_at fields
3. THE SkillAdminRouter SHALL order the returned AISkill records by deployed_at in descending order
4. WHILE a tenant has no active AIGateway, THE SkillAdminRouter SHALL return an empty skill list with total count of zero

### Requirement 2: 租户隔离

**User Story:** As a 系统管理员, I want to 确保技能数据按租户隔离, so that 不同租户之间的技能数据互不可见。

#### Acceptance Criteria

1. THE SkillAdminRouter SHALL filter all AISkill queries by the authenticated tenant_id derived from the JWT token
2. WHEN a 管理员 queries skills, THE SkillAdminRouter SHALL return only AISkill records belonging to AIGateway entries where gateway.tenant_id matches the authenticated tenant_id

### Requirement 3: 技能同步

**User Story:** As a 管理员, I want to 将 OpenClaw Agent 上的技能同步到系统数据库, so that 管理控制台能展示最新的技能状态。

#### Acceptance Criteria

1. WHEN a 管理员 triggers a sync, THE SkillSyncService SHALL fetch the skill list from the Agent via GET {agent_url}/api/skills
2. WHEN the Agent returns skills not present in the database, THE SkillSyncService SHALL insert new AISkill records with status "deployed"
3. WHEN the Agent returns skills already present in the database, THE SkillSyncService SHALL update the existing AISkill records' version and status fields
4. WHEN the database contains AISkill records not present in the Agent response, THE SkillSyncService SHALL mark those records with status "removed"
5. WHEN sync completes, THE SkillSyncService SHALL return a SyncResult containing added, updated, and removed counts along with the full skill list
6. IF the Agent service is unreachable during sync, THEN THE SkillSyncService SHALL return HTTP 503 with an error message indicating Agent unavailability
7. IF the AIGateway configuration lacks a valid agent_url, THEN THE SkillSyncService SHALL return HTTP 400 with an error message indicating missing configuration

### Requirement 4: 技能执行

**User Story:** As a 管理员, I want to 在管理控制台执行技能, so that 我能验证技能是否正常工作。

#### Acceptance Criteria

1. WHEN a 管理员 submits an execution request with parameters, THE SkillAdminRouter SHALL forward the request to the Agent via POST {agent_url}/api/skills/execute
2. WHEN the Agent returns a successful result, THE SkillAdminRouter SHALL return an ExecuteResultResponse with success=true, the result payload, and execution_time_ms
3. IF the target AISkill status is not "deployed", THEN THE SkillAdminRouter SHALL reject the execution with HTTP 400
4. IF the Agent service is unreachable during execution, THEN THE SkillAdminRouter SHALL return HTTP 503 with an error message
5. IF the Agent execution exceeds 30 seconds, THEN THE SkillAdminRouter SHALL return HTTP 504 with a timeout error message
6. WHEN a skill execution completes (success or failure), THE SkillAdminRouter SHALL write an AIAuditLog record with event_type "skill_execution"

### Requirement 5: 技能状态管理

**User Story:** As a 管理员, I want to 启用或禁用技能, so that 我能控制哪些技能对 AI 助手可用。

#### Acceptance Criteria

1. WHEN a 管理员 toggles a skill status, THE SkillAdminRouter SHALL update the AISkill record's status to the specified value ("deployed" or "pending")
2. WHEN a skill status is changed to "pending", THE SkillAdminRouter SHALL exclude that skill from AI 助手页面的技能列表
3. THE SkillAdminRouter SHALL return the updated AISkill detail after a status toggle

### Requirement 6: 前端管理界面集成

**User Story:** As a 管理员, I want to 在管理控制台的技能管理 Tab 中操作技能, so that 我能通过统一界面管理所有技能。

#### Acceptance Criteria

1. WHEN the AdminUI loads the skill management tab, THE AdminUI SHALL call the SkillAdminApi to fetch the skill list from the backend
2. WHEN the 管理员 clicks the sync button, THE AdminUI SHALL call the SkillAdminApi sync endpoint and display the sync result (added, updated, removed counts)
3. WHEN the 管理员 clicks execute on a skill, THE AdminUI SHALL call the SkillAdminApi execute endpoint and display the result or error message
4. WHEN the 管理员 toggles a skill's status, THE AdminUI SHALL call the SkillAdminApi toggle endpoint and update the displayed skill status
5. WHILE the AdminUI is performing an async operation (sync, execute, toggle), THE AdminUI SHALL display a loading indicator

### Requirement 7: 数据源统一

**User Story:** As a 开发者, I want to AI 助手页面和管理控制台读取同一数据源, so that 两个页面展示的技能数据始终一致。

#### Acceptance Criteria

1. THE AdminUI SHALL read skill data exclusively from the SkillAdminRouter backend API, not directly from the Agent service
2. THE SkillAdminRouter SHALL query the same ai_skills database table used by the AI 助手页面's openclaw-status endpoint
