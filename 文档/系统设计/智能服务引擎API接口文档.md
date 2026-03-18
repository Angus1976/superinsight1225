# 智能服务引擎（Smart Service Engine）API 接口文档

**最后更新**: 2026-03-18  
**版本**: 2.0  
**模块路径**: `src/service_engine/`  
**相关 Spec**: `.kiro/specs/smart-service-engine/`

---

## 概述

智能服务引擎通过统一 API 入口 `POST /api/v1/service/request`，将平台的结构化数据查询、对话式分析、辅助决策和 OpenClaw 技能调用能力以标准化方式对外输出。

认证方式：`X-API-Key` Header（复用现有 APIKeyAuthMiddleware）  
限流机制：复用现有 RateLimiter

---

## 统一入口

```
POST /api/v1/service/request
Content-Type: application/json
X-API-Key: sk_xxxxxxxx
```

---

## 请求体（ServiceRequest）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `request_type` | string | ✅ | — | 请求类型：`query` / `chat` / `decision` / `skill` |
| `user_id` | string | ✅ | — | 用户标识，不可为空 |
| `business_context` | object | — | `null` | 业务上下文（JSON 序列化后 ≤ 100KB） |
| `include_memory` | boolean | — | `true` | 是否启用用户记忆 |
| `workflow_id` | string | — | `null` | 工作流 ID，指定后从工作流配置中提取执行参数 |
| `extensions` | object | — | `null` | 扩展字段（预留），可传 `tenant_id` 等 |

### query 专用参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `data_type` | string | ✅ | — | 数据类型（见下方枚举） |
| `page` | int | — | `1` | 页码 |
| `page_size` | int | — | `50` | 每页条数 |
| `sort_by` | string | — | `null` | 排序字段，`-` 前缀表示降序 |
| `fields` | string | — | `null` | 字段筛选，逗号分隔 |
| `filters` | object | — | `null` | 过滤条件 JSON |

支持的 `data_type` 值：

| 值 | 说明 |
|----|------|
| `annotations` | 标注结果 |
| `augmented_data` | 增强数据 |
| `quality_reports` | 质量报告 |
| `experiments` | AI 试验结果 |
| `data_lifecycle` | 数据流转统计 |
| `data_sync` | 数据同步状态 |
| `samples` | 样本库数据 |
| `tasks` | 标注任务 |

### chat 专用参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `messages` | array | ✅ | 对话历史，每项含 `role` 和 `content` |

### decision 专用参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | ✅ | 决策问题描述 |
| `context_data` | object | — | 业务场景数据 |

### skill 专用参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `skill_id` | string | ✅ | 技能 ID（需在白名单内） |
| `parameters` | object | — | 技能执行参数 |

---

## 统一响应格式

### 成功响应（ServiceResponse）

```json
{
  "success": true,
  "request_type": "query",
  "data": { ... },
  "metadata": {
    "request_id": "uuid-string",
    "timestamp": "2026-03-16T08:00:00+00:00",
    "processing_time_ms": 123
  }
}
```

### 错误响应（ErrorResponse）

```json
{
  "success": false,
  "error": "错误描述",
  "error_code": "ERROR_CODE",
  "details": { ... }
}
```

---

## 各类型响应 data 结构

### query

```json
{
  "items": [ { ... }, { ... } ],
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 50,
    "total_pages": 2
  }
}
```

### chat（非流式）

```json
{
  "content": "AI 生成的分析内容"
}
```

### chat（SSE 流式）

中间帧：
```
data: {"content": "部分内容", "done": false}
```

结束帧：
```
data: {"content": "", "done": true}
```

### decision

```json
{
  "summary": "决策摘要",
  "analysis": "详细分析",
  "recommendations": [
    {
      "action": "建议操作",
      "reason": "理由",
      "priority": "high"
    }
  ],
  "confidence": 0.85
}
```

LLM 降级时 `confidence` 为 `0`，`recommendations` 为空数组。

### skill

```json
{
  "skill_id": "skill-001",
  "success": true,
  "result": { ... },
  "execution_time_ms": 456
}
```

---

## 工作流相关端点

### 查询可用工作流（外部通道）

```
GET /api/v1/service/workflows
X-API-Key: sk_xxxxxxxx
```

返回当前 API Key 有权访问的工作流列表。

**响应示例**：

```json
{
  "success": true,
  "data": [
    {
      "id": "wf-001",
      "name": "销售预测分析",
      "description": "基于历史数据进行销售趋势预测和分析",
      "skill_ids": ["skill-001"],
      "output_modes": ["merge"]
    }
  ]
}
```

### 带工作流的对话请求

当 `workflow_id` 存在时，系统从工作流配置中提取 `skill_ids`、`data_source_auth`、`output_modes`，替代手动配置。API Key 的 `scope` 和 `skill_whitelist` 与工作流配置取交集。

```json
{
  "request_type": "chat",
  "user_id": "user-001",
  "workflow_id": "wf-001",
  "messages": [
    { "role": "user", "content": "分析最近一个月的销售趋势" }
  ]
}
```

---

## 工作流管理端点（内部通道，需登录认证）

基础路径：`/api/v1/ai-assistant`

### 查询工作流列表

```
GET /api/v1/ai-assistant/workflows?status=enabled
Authorization: Bearer <token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 否 | 按状态过滤：`enabled` / `disabled`（仅管理员可用） |

- 管理员：返回所有工作流，支持 status 过滤
- 非管理员：仅返回 `status=enabled` 且 `visible_roles` 包含当前角色的工作流

**响应示例**：

```json
[
  {
    "id": "uuid-string",
    "name": "销售预测分析",
    "name_en": "Sales Forecast Analysis",
    "description": "基于历史数据进行销售趋势预测和分析",
    "description_en": "Predict and analyze sales trends based on historical data",
    "status": "enabled",
    "is_preset": true,
    "skill_ids": ["skill-001", "skill-002"],
    "data_source_auth": [
      { "source_id": "tasks", "tables": ["*"] },
      { "source_id": "annotation_efficiency", "tables": ["completion_rate", "quality_score"] }
    ],
    "output_modes": ["merge", "compare"],
    "visible_roles": ["admin", "business_expert"],
    "preset_prompt": "你是销售分析专家...",
    "created_at": "2026-03-18T08:00:00",
    "updated_at": "2026-03-18T08:00:00",
    "created_by": "user-uuid"
  }
]
```

### 创建工作流

```
POST /api/v1/ai-assistant/workflows
Authorization: Bearer <token>
Content-Type: application/json
```

仅管理员可用。

**请求体（WorkflowCreateRequest）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 工作流名称（1-255 字符，唯一） |
| `description` | string | 否 | 中文描述 |
| `name_en` | string | 否 | 英文名称 |
| `description_en` | string | 否 | 英文描述 |
| `skill_ids` | string[] | 否 | 关联技能 ID 列表 |
| `data_source_auth` | object[] | 否 | 数据源授权配置（见下方数据源授权结构） |
| `output_modes` | string[] | 否 | 输出方式：`merge`（合并）/ `compare`（对比） |
| `visible_roles` | string[] | ✅ | 可见角色（至少一个）：`admin` / `business_expert` / `annotator` / `viewer` |
| `preset_prompt` | string | 否 | 预设系统提示词 |

**请求示例**：

```json
{
  "name": "数据质量检查",
  "name_en": "Data Quality Check",
  "description": "自动检测数据质量问题并生成改进建议",
  "skill_ids": ["data-quality-check"],
  "data_source_auth": [
    { "source_id": "tasks", "tables": ["*"] },
    { "source_id": "quality", "tables": ["quality_scores", "quality_reports"] }
  ],
  "output_modes": ["merge"],
  "visible_roles": ["admin", "business_expert"]
}
```

**响应**：201 Created，返回完整工作流对象（同查询响应格式）。

**校验规则**：
- `name` 不可重复
- `skill_ids` 中的技能必须存在
- `data_source_auth` 中的数据源必须存在且启用
- `visible_roles` 中的角色必须合法

### 更新工作流

```
PUT /api/v1/ai-assistant/workflows/{workflow_id}
Authorization: Bearer <token>
Content-Type: application/json
```

仅管理员可用。所有字段均为可选，仅更新传入的字段。

**请求体（WorkflowUpdateRequest）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 否 | 工作流名称 |
| `description` | string | 否 | 中文描述 |
| `name_en` | string | 否 | 英文名称 |
| `description_en` | string | 否 | 英文描述 |
| `skill_ids` | string[] | 否 | 关联技能 ID 列表 |
| `data_source_auth` | object[] | 否 | 数据源授权配置 |
| `output_modes` | string[] | 否 | 输出方式 |
| `visible_roles` | string[] | 否 | 可见角色 |
| `status` | string | 否 | 状态：`enabled` / `disabled` |
| `preset_prompt` | string | 否 | 预设系统提示词 |

**启停示例**（仅切换状态）：

```json
{ "status": "disabled" }
```

**响应**：200 OK，返回更新后的完整工作流对象。

### 删除工作流

```
DELETE /api/v1/ai-assistant/workflows/{workflow_id}
Authorization: Bearer <token>
```

仅管理员可用。执行硬删除（从数据库中永久移除）。预置工作流（`is_preset=true`）不可删除。

**响应示例**：

```json
{ "success": true, "message": "Workflow wf-001 deleted" }
```

**错误响应**（预置工作流）：

```json
{
  "success": false,
  "error_code": "WORKFLOW_PRESET_DELETE_DENIED",
  "message": "Preset workflows cannot be deleted"
}
```

### 工作流执行统计

```
GET /api/v1/ai-assistant/workflows/{workflow_id}/stats
Authorization: Bearer <token>
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "total_executions": 42,
    "success_count": 40,
    "failure_count": 2,
    "avg_processing_time_ms": 1200
  }
}
```

### 当日统计

```
GET /api/v1/ai-assistant/stats/today
Authorization: Bearer <token>
```

非管理员仅返回自身数据，管理员可查看汇总。

**响应示例**：

```json
{
  "success": true,
  "data": {
    "chat_count": 15,
    "workflow_count": 8,
    "data_source_count": 3
  }
}
```

### 批量权限同步

```
POST /api/v1/ai-assistant/workflows/sync-permissions
Authorization: Bearer <token>
Content-Type: application/json
```

仅管理员可用。批量更新工作流的数据源授权配置。

**请求示例**：

```json
{
  "permissions": [
    {
      "workflow_id": "wf-001",
      "data_source_auth": [
        { "source_id": "tasks", "tables": ["*"] }
      ]
    }
  ]
}
```

---

## 数据源授权结构（data_source_auth）

工作流通过 `data_source_auth` 字段控制可访问的数据源和数据表。采用三级树形结构：数据源 → 数据表 → 字段。

### 授权格式

```json
[
  {
    "source_id": "tasks",
    "tables": ["*"]
  },
  {
    "source_id": "quality",
    "tables": ["quality_scores", "quality_reports"]
  }
]
```

- `tables: ["*"]` — 授权该数据源下所有数据表
- `tables: ["table_a", "table_b"]` — 仅授权指定数据表

### 可用数据源及数据表

| 数据源 ID | 名称 | 数据表 |
|-----------|------|--------|
| `tasks` | 标注任务 | `task_list`、`task_status`、`task_stats` |
| `annotation_efficiency` | 标注效率 | `completion_rate`、`quality_score`、`revision_rate` |
| `user_activity` | 用户活跃度 | `login_records`、`operations`、`online_duration` |
| `data_sync` | 数据同步 | `sync_sources`、`sync_jobs`、`sync_history` |
| `data_lifecycle` | 数据流转 | `temp_data`、`samples`、`annotation`、`enhancement`、`ai_trial` |
| `augmentation` | 数据增强 | `augmentation_tasks`、`augmentation_samples` |
| `quality` | 质量报表 | `quality_scores`、`quality_reports` |

每个数据表包含字段级元数据（用于前端树形选择展示），例如：

```json
{
  "id": "task_list",
  "label": "任务列表",
  "fields": ["task_id", "task_name", "project", "assignee", "deadline"]
}
```

---

## 动态授权请求（预留）

### 内部通道

```
POST /api/v1/ai-assistant/workflows/request-authorization
Authorization: Bearer <token>
```

**状态**: 501 Not Implemented

### 外部通道回调

```
POST /api/v1/service/authorization-callback
X-API-Key: sk_xxxxxxxx
Content-Type: application/json
```

**状态**: 501 Not Implemented（预留端点）

**请求体**：

```json
{
  "request_id": "auth-req-uuid",
  "granted": true,
  "granted_permissions": {
    "skills": ["skill-001"],
    "data_sources": ["tasks"]
  },
  "expires_at": "2026-04-01T00:00:00Z"
}
```

**说明**: 当工作流执行因权限不足返回 403 时，响应中包含 `authorization_request` 结构。客户系统可通过此回调端点授予临时权限。该功能当前为预留状态。

---

## 错误码一览

| HTTP 状态码 | error_code | 触发条件 |
|------------|------------|---------|
| 400 | `INVALID_REQUEST_TYPE` | `request_type` 不在支持列表 |
| 400 | `INVALID_DATA_TYPE` | `data_type` 不在支持列表 |
| 400 | `MISSING_MESSAGES` | chat 请求缺少 `messages` |
| 400 | `MISSING_QUESTION` | decision 请求缺少 `question` |
| 400 | `MISSING_SKILL_ID` | skill 请求缺少 `skill_id` |
| 400 | `VALIDATION_ERROR` | Pydantic 校验失败（user_id 为空、business_context 超限等） |
| 403 | `INSUFFICIENT_SCOPE` | API Key 无对应 request_type 权限 |
| 403 | `REQUEST_TYPE_DISABLED` | 该 request_type 已被禁用 |
| 403 | `SKILL_NOT_ALLOWED` | skill_id 不在白名单 |
| 404 | `SKILL_NOT_FOUND` | 技能不存在或未部署 |
| 500 | `INTERNAL_ERROR` | 服务器内部错误 |
| 500 | `SKILL_EXECUTION_ERROR` | 技能执行失败 |
| 503 | `LLM_UNAVAILABLE` | LLM 服务不可用 |
| 504 | `REQUEST_TIMEOUT` | 请求超时（60 秒） |
| 404 | `WORKFLOW_NOT_FOUND` | 指定的 workflow_id 不存在 |
| 403 | `WORKFLOW_DISABLED` | 工作流已禁用 |
| 403 | `WORKFLOW_PERMISSION_DENIED` | API Key 或用户无权访问该工作流 |
| 403 | `WORKFLOW_SKILL_DENIED` | 工作流技能超出权限范围 |
| 403 | `WORKFLOW_DATASOURCE_DENIED` | 工作流数据源超出权限范围 |
| 403 | `WORKFLOW_PRESET_DELETE_DENIED` | 预置工作流不可删除 |
| 409 | `WORKFLOW_NAME_CONFLICT` | 工作流名称已存在 |
| 501 | `AUTHORIZATION_NOT_IMPLEMENTED` | 动态授权请求功能尚未实现 |

---

## 请求示例

### 查询标注结果

```json
{
  "request_type": "query",
  "user_id": "user-001",
  "data_type": "annotations",
  "page": 1,
  "page_size": 20,
  "sort_by": "-created_at",
  "fields": "id,status,result",
  "filters": { "status": "completed" },
  "extensions": { "tenant_id": "tenant-001" }
}
```

### 对话式分析

```json
{
  "request_type": "chat",
  "user_id": "user-001",
  "messages": [
    { "role": "user", "content": "最近一周的标注质量趋势如何？" }
  ],
  "business_context": {
    "industry": "retail",
    "focus_area": "product_labeling"
  }
}
```

### 辅助决策

```json
{
  "request_type": "decision",
  "user_id": "user-001",
  "question": "基于当前数据质量，是否应该扩大标注团队规模？",
  "context_data": {
    "current_team_size": 10,
    "monthly_volume": 50000
  }
}
```

### 技能调用

```json
{
  "request_type": "skill",
  "user_id": "user-001",
  "skill_id": "text-classification-v2",
  "parameters": {
    "text": "这是一条待分类的文本",
    "categories": ["positive", "negative", "neutral"]
  }
}
```

---

## 权限模型

每个 API Key 通过以下字段控制访问：

| 字段 | 类型 | 说明 |
|------|------|------|
| `allowed_request_types` | JSON 数组 | 允许的请求类型，如 `["query", "chat"]` |
| `skill_whitelist` | JSON 数组 | 允许调用的技能 ID 列表 |
| `webhook_config` | JSON 对象 | Webhook 配置（MVP 预留） |

空 `allowed_request_types` 表示允许所有类型。空 `skill_whitelist` 表示允许所有技能。

---

## 架构要点

- 插件化 Handler 注册：`RequestRouter` 通过注册表映射 `request_type` → `BaseHandler`
- 处理管线：disabled 检查 → scope 校验 → validate → build_context → execute
- 新增类型只需实现 `BaseHandler`（validate / build_context / execute）并注册
- 支持运行时动态启用/禁用 request_type
- 数据源通过 `BaseDataProvider` 注册表扩展
- 用户记忆按 `user_id` + `tenant_id` 隔离，50 条阈值自动压缩
