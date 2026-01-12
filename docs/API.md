# SuperInsight API 文档

## 概述

SuperInsight 提供完整的 RESTful API 和 WebSocket 接口，支持所有核心功能包括数据提取、AI 预标注、质量管理、安全审计、权限控制和合规报告。

## 基础信息

- **Base URL**: `http://localhost:8000` (开发环境)
- **API 版本**: v1
- **认证方式**: JWT Bearer Token
- **内容类型**: `application/json`
- **字符编码**: UTF-8

## 认证

### 获取访问令牌

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 使用访问令牌

```http
GET /api/users/me
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 核心 API 端点

### 1. 用户管理 API

#### 获取当前用户信息
```http
GET /api/users/me
Authorization: Bearer {token}
```

#### 更新用户信息
```http
PUT /api/users/me
Authorization: Bearer {token}
Content-Type: application/json

{
  "username": "newusername",
  "email": "newemail@example.com"
}
```

#### 用户列表 (管理员)
```http
GET /api/users?skip=0&limit=100&tenant_id={tenant_id}
Authorization: Bearer {token}
```

### 2. 审计系统 API

#### 查询审计事件
```http
POST /api/audit/events/query
Authorization: Bearer {token}
Content-Type: application/json

{
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "user_id": "optional_user_id",
  "action": "optional_action",
  "resource_type": "optional_resource_type",
  "skip": 0,
  "limit": 100
}
```

**响应**:
```json
{
  "total": 1250,
  "events": [
    {
      "id": "audit_event_123",
      "timestamp": "2024-01-15T10:30:00Z",
      "user_id": "user_456",
      "tenant_id": "tenant_789",
      "action": "READ",
      "resource_type": "document",
      "resource_id": "doc_123",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "details": {
        "request_path": "/api/documents/123",
        "response_status": 200
      }
    }
  ]
}
```

#### 导出审计日志
```http
POST /api/audit/export/excel
Authorization: Bearer {token}
Content-Type: application/json

{
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "filters": {
    "user_id": "optional_user_id",
    "action": "optional_action"
  }
}
```

#### 审计统计信息
```http
GET /api/audit/statistics?days=30&tenant_id={tenant_id}
Authorization: Bearer {token}
```

### 3. 数据脱敏 API

#### PII 检测
```http
POST /api/desensitization/detect
Authorization: Bearer {token}
Content-Type: application/json

{
  "text": "我的姓名是张三，电话号码是13812345678，邮箱是zhangsan@example.com",
  "language": "zh",
  "entities": ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS"]
}
```

**响应**:
```json
{
  "success": true,
  "entities": [
    {
      "entity_type": "PERSON",
      "start": 4,
      "end": 6,
      "score": 0.95,
      "text": "张三"
    },
    {
      "entity_type": "PHONE_NUMBER", 
      "start": 12,
      "end": 23,
      "score": 0.98,
      "text": "13812345678"
    },
    {
      "entity_type": "EMAIL_ADDRESS",
      "start": 27,
      "end": 46,
      "score": 0.99,
      "text": "zhangsan@example.com"
    }
  ]
}
```

#### 数据匿名化
```http
POST /api/desensitization/anonymize
Authorization: Bearer {token}
Content-Type: application/json

{
  "text": "我的姓名是张三，电话号码是13812345678",
  "anonymizers": [
    {
      "entity_type": "PERSON",
      "method": "replace",
      "replacement": "[姓名]"
    },
    {
      "entity_type": "PHONE_NUMBER",
      "method": "mask",
      "chars_to_mask": 4,
      "masking_char": "*"
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "anonymized_text": "我的姓名是[姓名]，电话号码是138****5678",
  "entities_anonymized": 2
}
```

#### 脱敏规则管理
```http
GET /api/desensitization/rules?tenant_id={tenant_id}
Authorization: Bearer {token}
```

```http
POST /api/desensitization/rules
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "手机号脱敏规则",
  "entity_type": "PHONE_NUMBER",
  "method": "mask",
  "config": {
    "chars_to_mask": 4,
    "masking_char": "*"
  },
  "enabled": true
}
```

### 4. RBAC 权限 API

#### 权限检查
```http
POST /api/rbac/check-permission
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_id": "user_123",
  "resource": "documents",
  "action": "READ",
  "tenant_id": "tenant_456"
}
```

**响应**:
```json
{
  "allowed": true,
  "reason": "User has READ permission on documents resource",
  "cache_hit": true,
  "check_time_ms": 2.5
}
```

#### 角色管理
```http
GET /api/rbac/roles?tenant_id={tenant_id}
Authorization: Bearer {token}
```

```http
POST /api/rbac/roles
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "数据分析师",
  "description": "可以查看和分析数据",
  "permissions": [
    {
      "resource": "documents",
      "actions": ["READ", "EXPORT"]
    },
    {
      "resource": "analytics",
      "actions": ["READ", "CREATE"]
    }
  ],
  "tenant_id": "tenant_456"
}
```

#### 用户角色分配
```http
POST /api/rbac/users/{user_id}/roles
Authorization: Bearer {token}
Content-Type: application/json

{
  "role_ids": ["role_123", "role_456"],
  "tenant_id": "tenant_789"
}
```

#### 权限缓存统计
```http
GET /api/rbac/cache/stats
Authorization: Bearer {token}
```

**响应**:
```json
{
  "cache_size": 1250,
  "hit_rate": 0.95,
  "miss_rate": 0.05,
  "eviction_count": 45,
  "average_response_time_ms": 1.2,
  "redis_connected": true
}
```

### 5. 安全监控 API

#### 安全事件查询
```http
GET /api/security/events?start_date=2024-01-01&end_date=2024-01-31&severity=high
Authorization: Bearer {token}
```

#### 威胁检测状态
```http
GET /api/security/threats
Authorization: Bearer {token}
```

**响应**:
```json
{
  "active_threats": 3,
  "threat_types": {
    "brute_force": 1,
    "privilege_escalation": 1,
    "unusual_activity": 1
  },
  "last_scan": "2024-01-15T10:30:00Z",
  "security_score": 85
}
```

#### 安全仪表盘数据
```http
GET /api/security/dashboard?time_range=24h
Authorization: Bearer {token}
```

#### 安全告警
```http
GET /api/security/alerts?status=active&limit=50
Authorization: Bearer {token}
```

```http
POST /api/security/alerts/{alert_id}/acknowledge
Authorization: Bearer {token}
Content-Type: application/json

{
  "acknowledged_by": "user_123",
  "notes": "已确认并处理此告警"
}
```

### 6. 合规报告 API

#### 生成合规报告
```http
POST /api/compliance/reports/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "standard": "GDPR",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "tenant_id": "tenant_123",
  "format": "json"
}
```

**响应**:
```json
{
  "report_id": "report_456",
  "status": "generating",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

#### 获取合规报告
```http
GET /api/compliance/reports/{report_id}
Authorization: Bearer {token}
```

#### 导出合规报告
```http
GET /api/compliance/reports/{report_id}/export?format=pdf
Authorization: Bearer {token}
```

#### 合规统计
```http
GET /api/compliance/statistics?standard=GDPR&tenant_id={tenant_id}
Authorization: Bearer {token}
```

### 7. 数据提取 API

#### 数据源连接测试
```http
POST /api/extractors/test-connection
Authorization: Bearer {token}
Content-Type: application/json

{
  "type": "postgresql",
  "config": {
    "host": "localhost",
    "port": 5432,
    "database": "testdb",
    "username": "user",
    "password": "password"
  }
}
```

#### 创建提取任务
```http
POST /api/extractors/tasks
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "用户数据提取",
  "source_type": "postgresql",
  "source_config": {
    "host": "localhost",
    "port": 5432,
    "database": "production",
    "username": "readonly_user",
    "password": "password"
  },
  "query": "SELECT id, name, email FROM users WHERE created_at >= '2024-01-01'",
  "schedule": "0 2 * * *"
}
```

#### 获取提取任务状态
```http
GET /api/extractors/tasks/{task_id}/status
Authorization: Bearer {token}
```

### 8. AI 预标注 API

#### 创建预标注任务
```http
POST /api/ai/preannotation/tasks
Authorization: Bearer {token}
Content-Type: application/json

{
  "project_id": "project_123",
  "model_name": "bert-base-chinese",
  "task_type": "text_classification",
  "config": {
    "labels": ["正面", "负面", "中性"],
    "confidence_threshold": 0.8
  }
}
```

#### 获取预标注结果
```http
GET /api/ai/preannotation/tasks/{task_id}/results
Authorization: Bearer {token}
```

### 9. 质量管理 API

#### 质量评估
```http
POST /api/quality/assess
Authorization: Bearer {token}
Content-Type: application/json

{
  "project_id": "project_123",
  "assessment_type": "semantic_similarity",
  "config": {
    "reference_dataset": "golden_standard",
    "metrics": ["bleu", "rouge", "semantic_similarity"]
  }
}
```

#### 质量报告
```http
GET /api/quality/reports/{project_id}?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}
```

### 10. 计费系统 API

#### 工时统计
```http
GET /api/billing/work-hours?user_id={user_id}&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}
```

#### 标注统计
```http
GET /api/billing/annotations?project_id={project_id}&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}
```

#### 生成账单
```http
POST /api/billing/invoices
Authorization: Bearer {token}
Content-Type: application/json

{
  "tenant_id": "tenant_123",
  "billing_period": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z"
  },
  "currency": "CNY"
}
```

## WebSocket API

### 1. 实时安全监控

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/security/dashboard');

ws.onopen = function(event) {
    console.log('Connected to security dashboard');
    
    // 发送认证信息
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'your_jwt_token_here'
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Security update:', data);
    
    // 处理不同类型的安全事件
    switch(data.type) {
        case 'threat_detected':
            handleThreatAlert(data.payload);
            break;
        case 'security_metrics':
            updateSecurityMetrics(data.payload);
            break;
        case 'dashboard_update':
            updateDashboard(data.payload);
            break;
    }
};
```

### 2. 实时审计事件

```javascript
const auditWs = new WebSocket('ws://localhost:8000/ws/audit/events');

auditWs.onmessage = function(event) {
    const auditEvent = JSON.parse(event.data);
    console.log('New audit event:', auditEvent);
    
    // 实时更新审计日志界面
    addAuditEventToUI(auditEvent);
};
```

### 3. 实时告警通知

```javascript
const alertWs = new WebSocket('ws://localhost:8000/ws/alerts');

alertWs.onmessage = function(event) {
    const alert = JSON.parse(event.data);
    
    // 显示告警通知
    showNotification({
        title: alert.title,
        message: alert.message,
        severity: alert.severity,
        timestamp: alert.timestamp
    });
};
```

## 错误处理

### HTTP 状态码

- `200 OK` - 请求成功
- `201 Created` - 资源创建成功
- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 未认证或认证失败
- `403 Forbidden` - 权限不足
- `404 Not Found` - 资源不存在
- `422 Unprocessable Entity` - 请求数据验证失败
- `429 Too Many Requests` - 请求频率限制
- `500 Internal Server Error` - 服务器内部错误

### 错误响应格式

```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "您没有权限访问此资源",
    "details": {
      "resource": "documents",
      "action": "DELETE",
      "user_id": "user_123"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_456789"
  }
}
```

### 常见错误码

- `INVALID_TOKEN` - JWT 令牌无效或过期
- `PERMISSION_DENIED` - 权限不足
- `RESOURCE_NOT_FOUND` - 资源不存在
- `VALIDATION_ERROR` - 数据验证失败
- `RATE_LIMIT_EXCEEDED` - 请求频率超限
- `TENANT_NOT_FOUND` - 租户不存在
- `USER_NOT_FOUND` - 用户不存在

## 分页和过滤

### 分页参数

```http
GET /api/users?skip=0&limit=20&sort=created_at&order=desc
```

- `skip` - 跳过的记录数 (默认: 0)
- `limit` - 返回的记录数 (默认: 100, 最大: 1000)
- `sort` - 排序字段
- `order` - 排序方向 (asc/desc)

### 过滤参数

```http
GET /api/audit/events?user_id=123&action=READ&start_date=2024-01-01&end_date=2024-01-31
```

### 分页响应格式

```json
{
  "total": 1250,
  "skip": 0,
  "limit": 20,
  "items": [...],
  "has_next": true,
  "has_prev": false
}
```

## 速率限制

### 限制规则

- **认证端点**: 5 次/分钟
- **查询端点**: 100 次/分钟
- **创建/更新端点**: 50 次/分钟
- **导出端点**: 10 次/分钟
- **WebSocket 连接**: 10 个/用户

### 限制响应头

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
```

## SDK 和客户端库

### Python SDK

```python
from superinsight_sdk import SuperInsightClient

client = SuperInsightClient(
    base_url="http://localhost:8000",
    token="your_jwt_token"
)

# 查询审计事件
events = client.audit.query_events(
    start_date="2024-01-01",
    end_date="2024-01-31",
    limit=100
)

# 检测 PII
result = client.desensitization.detect_pii(
    text="我的电话是13812345678",
    language="zh"
)

# 权限检查
allowed = client.rbac.check_permission(
    user_id="user_123",
    resource="documents",
    action="READ"
)
```

### JavaScript SDK

```javascript
import { SuperInsightClient } from '@superinsight/sdk';

const client = new SuperInsightClient({
  baseURL: 'http://localhost:8000',
  token: 'your_jwt_token'
});

// 查询审计事件
const events = await client.audit.queryEvents({
  startDate: '2024-01-01',
  endDate: '2024-01-31',
  limit: 100
});

// 检测 PII
const result = await client.desensitization.detectPII({
  text: '我的电话是13812345678',
  language: 'zh'
});
```

## 测试环境

### 测试数据

测试环境提供以下测试数据：

- **测试用户**: `test@example.com` / `password123`
- **测试租户**: `test_tenant`
- **测试项目**: `test_project`

### 测试端点

```http
GET /api/test/reset-data
Authorization: Bearer {admin_token}
```

重置测试环境数据。

```http
GET /api/test/generate-sample-data
Authorization: Bearer {admin_token}
```

生成示例数据用于测试。

## 版本控制

API 使用语义化版本控制：

- **主版本号**: 不兼容的 API 更改
- **次版本号**: 向后兼容的功能新增
- **修订号**: 向后兼容的问题修正

当前版本: `v2.3.0`

### 版本迁移

查看版本迁移指南：

```http
GET /api/version/migration-guide?from=2.2.0&to=2.3.0
```

## 支持和反馈

### 技术支持

- **API 文档**: https://docs.superinsight.ai/api
- **SDK 文档**: https://docs.superinsight.ai/sdk
- **示例代码**: https://github.com/superinsight/examples
- **技术支持**: api-support@superinsight.ai

### 问题报告

如发现 API 问题，请提供：

1. 请求 URL 和方法
2. 请求头和请求体
3. 响应状态码和响应体
4. 错误复现步骤
5. 预期行为描述

---

*文档最后更新: 2026-01-11*
*API 版本: v2.3.0*