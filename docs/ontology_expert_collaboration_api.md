# 本体专家协作 API 文档

## 概述

本体专家协作模块提供完整的 RESTful API 和 WebSocket 接口，支持：
- 专家管理
- 模板管理
- 实时协作
- 审批工作流
- 验证规则
- 影响分析
- 国际化
- 合规检查
- 最佳实践
- 审计日志

## 认证

所有 API 端点需要 JWT 认证：

```
Authorization: Bearer <token>
```

## 基础 URL

```
/api/v1/ontology
```

---

## 专家管理 API

### 创建专家

```http
POST /api/v1/ontology/experts
```

**请求体：**
```json
{
  "name": "张三",
  "email": "zhangsan@example.com",
  "expertise_areas": ["金融", "法律"],
  "languages": ["zh-CN", "en-US"],
  "certifications": ["CFA", "律师资格证"]
}
```

**响应：**
```json
{
  "id": "expert-uuid",
  "name": "张三",
  "email": "zhangsan@example.com",
  "expertise_areas": ["金融", "法律"],
  "created_at": "2026-01-24T10:00:00Z"
}
```

### 获取专家

```http
GET /api/v1/ontology/experts/{expert_id}
```

### 更新专家

```http
PUT /api/v1/ontology/experts/{expert_id}
```

### 推荐专家

```http
GET /api/v1/ontology/experts/recommend?ontology_area=金融&limit=10
```

**响应：**
```json
{
  "recommendations": [
    {
      "expert_id": "expert-uuid",
      "name": "张三",
      "match_score": 0.95,
      "quality_score": 4.8,
      "availability": true
    }
  ]
}
```

### 获取专家指标

```http
GET /api/v1/ontology/experts/{expert_id}/metrics
```

---

## 模板管理 API

### 列出模板

```http
GET /api/v1/ontology/templates?industry=金融&page=1&page_size=20
```

### 获取模板

```http
GET /api/v1/ontology/templates/{template_id}
```

### 实例化模板

```http
POST /api/v1/ontology/templates/{template_id}/instantiate
```

**请求体：**
```json
{
  "name": "我的金融本体",
  "customizations": {
    "add_entities": [...],
    "remove_entities": [...]
  }
}
```

### 自定义模板

```http
POST /api/v1/ontology/templates/{template_id}/customize
```

### 导出模板

```http
GET /api/v1/ontology/templates/{template_id}/export?format=json
```

### 导入模板

```http
POST /api/v1/ontology/templates/import
Content-Type: multipart/form-data
```

---

## 协作 API

### 创建协作会话

```http
POST /api/v1/ontology/collaboration/sessions
```

**请求体：**
```json
{
  "ontology_id": "ontology-uuid",
  "name": "金融本体协作"
}
```

### 加入会话

```http
POST /api/v1/ontology/collaboration/sessions/{session_id}/join
```

### 锁定元素

```http
POST /api/v1/ontology/collaboration/sessions/{session_id}/lock
```

**请求体：**
```json
{
  "element_id": "entity-uuid",
  "element_type": "entity"
}
```

### 解锁元素

```http
DELETE /api/v1/ontology/collaboration/sessions/{session_id}/lock/{element_id}
```

### 创建变更请求

```http
POST /api/v1/ontology/collaboration/change-requests
```

### 解决冲突

```http
POST /api/v1/ontology/collaboration/conflicts/{conflict_id}/resolve
```

**请求体：**
```json
{
  "resolution": "accept_theirs",
  "reason": "对方的修改更准确"
}
```

---

## WebSocket API

### 连接

```
ws://host/api/v1/ontology/collaboration/sessions/{session_id}/ws
```

### 消息格式

**锁定元素：**
```json
{
  "type": "lock_element",
  "element_id": "entity-uuid"
}
```

**编辑元素：**
```json
{
  "type": "edit_element",
  "element_id": "entity-uuid",
  "changes": {
    "name": "新名称"
  }
}
```

**广播变更：**
```json
{
  "type": "broadcast_change",
  "change": {...}
}
```

---

## 审批工作流 API

### 创建审批链

```http
POST /api/v1/ontology/workflow/approval-chains
```

**请求体：**
```json
{
  "name": "金融本体审批链",
  "ontology_area": "金融",
  "levels": [
    {
      "level": 1,
      "approvers": ["expert-1", "expert-2"],
      "min_approvals": 1
    },
    {
      "level": 2,
      "approvers": ["admin-1"],
      "min_approvals": 1
    }
  ],
  "approval_type": "SEQUENTIAL"
}
```

### 列出审批链

```http
GET /api/v1/ontology/workflow/approval-chains?ontology_area=金融
```

### 审批

```http
POST /api/v1/ontology/workflow/change-requests/{id}/approve
```

**请求体：**
```json
{
  "reason": "审批通过，修改合理"
}
```

### 拒绝

```http
POST /api/v1/ontology/workflow/change-requests/{id}/reject
```

**请求体：**
```json
{
  "reason": "修改不符合规范"
}
```

### 请求修改

```http
POST /api/v1/ontology/workflow/change-requests/{id}/request-changes
```

### 获取待审批

```http
GET /api/v1/ontology/workflow/pending-approvals?ontology_area=金融
```

---

## 验证 API

### 列出验证规则

```http
GET /api/v1/ontology/validation/rules?region=CN&industry=金融
```

### 创建验证规则

```http
POST /api/v1/ontology/validation/rules
```

### 验证实体

```http
POST /api/v1/ontology/validation/validate
```

**请求体：**
```json
{
  "entity_type": "企业",
  "data": {
    "统一社会信用代码": "91110000MA001234X5"
  },
  "region": "CN"
}
```

### 中国业务标识符验证

```http
GET /api/v1/ontology/validation/chinese-business
POST /api/v1/ontology/validation/chinese-business/validate
```

---

## 影响分析 API

### 分析变更影响

```http
POST /api/v1/ontology/impact/analyze
```

**请求体：**
```json
{
  "element_id": "entity-uuid",
  "change_type": "delete"
}
```

**响应：**
```json
{
  "affected_count": 150,
  "impact_level": "HIGH",
  "requires_high_impact_approval": true,
  "affected_elements": [...],
  "migration_effort": {
    "complexity": "MEDIUM",
    "estimated_hours": 24
  },
  "recommendations": [...]
}
```

### 获取影响报告

```http
GET /api/v1/ontology/impact/reports/{change_request_id}
```

---

## 国际化 API

### 添加翻译

```http
POST /api/v1/ontology/i18n/{element_id}/translations
```

**请求体：**
```json
{
  "language": "en-US",
  "name": "Financial Entity",
  "description": "Entity representing financial concepts"
}
```

### 获取翻译

```http
GET /api/v1/ontology/i18n/{element_id}/translations/{lang}
```

### 获取缺失翻译

```http
GET /api/v1/ontology/i18n/{ontology_id}/missing/{lang}
```

### 导出翻译

```http
GET /api/v1/ontology/i18n/{ontology_id}/export/{lang}?format=json
```

### 导入翻译

```http
POST /api/v1/ontology/i18n/{ontology_id}/import/{lang}
```

---

## 合规 API

### 列出合规模板

```http
GET /api/v1/ontology/compliance/templates
```

### 应用合规模板

```http
POST /api/v1/ontology/compliance/templates/{template_id}/apply
```

### 生成合规报告

```http
POST /api/v1/ontology/compliance/reports
```

**响应：**
```json
{
  "compliance_score": 85,
  "violations": [...],
  "recommendations": [...],
  "citations": [...]
}
```

---

## 健康检查 API

### 基本健康检查

```http
GET /health
```

### 数据库健康检查

```http
GET /health/db
```

### Redis 健康检查

```http
GET /health/redis
```

### Neo4j 健康检查

```http
GET /health/neo4j
```

### 就绪检查

```http
GET /health/ready
```

### 存活检查

```http
GET /health/live
```

---

## 指标 API

### Prometheus 指标

```http
GET /metrics
```

### JSON 指标

```http
GET /metrics/json
```

---

## 错误响应

所有错误响应遵循统一格式：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "验证失败",
    "details": [...],
    "i18n_key": "error.validation_failed"
  }
}
```

### 错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| VALIDATION_ERROR | 400 | 请求验证失败 |
| UNAUTHORIZED | 401 | 未认证 |
| FORBIDDEN | 403 | 无权限 |
| NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 资源冲突 |
| INTERNAL_ERROR | 500 | 内部错误 |

---

## 分页

支持分页的端点使用以下参数：

- `page`: 页码（从 1 开始）
- `page_size`: 每页数量（默认 20，最大 100）

响应包含分页信息：

```json
{
  "items": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## 速率限制

API 实施速率限制：

- 默认：100 请求/分钟
- 认证用户：1000 请求/分钟

超出限制返回 429 状态码。

---

## 版本

当前 API 版本：v1

API 版本通过 URL 路径指定：`/api/v1/...`
