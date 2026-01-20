# 质量计费闭环系统 - API 参考文档

## 概述

本文档描述质量计费闭环系统的 REST API 接口规范。所有 API 遵循 RESTful 设计原则，使用 JSON 格式进行数据交换。

### 基础 URL

```
生产环境: https://api.superinsight.com/v1
测试环境: https://api-staging.superinsight.com/v1
```

### 认证

所有 API 请求需要在 Header 中包含认证令牌：

```http
Authorization: Bearer <access_token>
```

### 响应格式

所有响应遵循统一格式：

```json
{
  "status": "success|error|warning",
  "data": { ... },
  "errors": [
    {
      "code": "ERROR_CODE",
      "message": "错误描述",
      "field": "字段名",
      "suggestion": "建议操作"
    }
  ],
  "meta": {
    "request_id": "req-xxx",
    "timestamp": "2025-01-01T00:00:00Z",
    "processing_time_ms": 50
  }
}
```

---

## 1. 工单管理 API

### 1.1 获取工单列表

```http
GET /tickets
```

**查询参数：**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页数量，默认 20，最大 100 |
| status | string | 否 | 状态筛选 |
| priority | string | 否 | 优先级筛选 |
| assigned_to | string | 否 | 分配人员筛选 |
| sort_by | string | 否 | 排序字段 |
| sort_order | string | 否 | 排序方向 (asc/desc) |

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "ticket_id": "TKT-001",
        "title": "数据标注质量问题",
        "type": "quality_issue",
        "priority": "high",
        "status": "open",
        "assigned_to": "user-123",
        "sla_deadline": "2025-01-02T12:00:00Z",
        "created_at": "2025-01-01T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8,
      "has_previous": false,
      "has_next": true
    }
  }
}
```

### 1.2 创建工单

```http
POST /tickets
```

**请求体：**

```json
{
  "title": "工单标题",
  "type": "quality_issue",
  "priority": "high",
  "description": "问题描述",
  "affected_items": ["item-1", "item-2"],
  "metadata": {
    "source": "auto_detection"
  }
}
```

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "ticket_id": "TKT-002",
    "title": "工单标题",
    "status": "open",
    "created_at": "2025-01-01T10:00:00Z"
  }
}
```

### 1.3 获取工单详情

```http
GET /tickets/{ticket_id}
```

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "ticket_id": "TKT-001",
    "title": "数据标注质量问题",
    "type": "quality_issue",
    "priority": "high",
    "status": "in_progress",
    "assigned_to": "user-123",
    "description": "详细描述...",
    "history": [
      {
        "action": "created",
        "timestamp": "2025-01-01T10:00:00Z",
        "user": "system"
      },
      {
        "action": "assigned",
        "timestamp": "2025-01-01T10:05:00Z",
        "user": "admin"
      }
    ]
  }
}
```

### 1.4 分配工单

```http
POST /tickets/{ticket_id}/assign
```

**请求体：**

```json
{
  "assigned_to": "user-456",
  "reason": "技能匹配"
}
```

### 1.5 解决工单

```http
POST /tickets/{ticket_id}/resolve
```

**请求体：**

```json
{
  "resolution": "问题已修复",
  "fixed_items": ["item-1", "item-2"],
  "quality_improvement": 0.15
}
```

---

## 2. 绩效评估 API

### 2.1 获取用户绩效

```http
GET /performance/{user_id}
```

**查询参数：**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| period | string | 否 | 评估周期 (daily/weekly/monthly) |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "user_id": "user-123",
    "period": "monthly",
    "scores": {
      "quality_score": 0.85,
      "efficiency_score": 0.90,
      "compliance_score": 0.95,
      "improvement_score": 0.80,
      "overall_score": 0.875
    },
    "performance_level": "A",
    "ranking": 5,
    "total_users": 50,
    "suggestions": [
      "提高处理速度可进一步提升效率分"
    ]
  }
}
```

### 2.2 获取绩效排名

```http
GET /performance/ranking
```

**查询参数：**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| period | string | 否 | 评估周期 |
| limit | integer | 否 | 返回数量，默认 10 |
| department | string | 否 | 部门筛选 |

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "rankings": [
      {
        "rank": 1,
        "user_id": "user-456",
        "user_name": "张三",
        "overall_score": 0.95,
        "performance_level": "A+"
      },
      {
        "rank": 2,
        "user_id": "user-789",
        "user_name": "李四",
        "overall_score": 0.92,
        "performance_level": "A"
      }
    ],
    "total_users": 50
  }
}
```

### 2.3 获取绩效趋势

```http
GET /performance/trends
```

**查询参数：**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| user_id | string | 否 | 用户 ID（可选） |
| metric | string | 是 | 指标名称 |
| period | string | 否 | 时间粒度 |
| duration | string | 否 | 时间范围 (7d/30d/90d) |

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "metric": "quality_score",
    "trend": [
      {"date": "2024-12-01", "value": 0.80},
      {"date": "2024-12-08", "value": 0.82},
      {"date": "2024-12-15", "value": 0.85},
      {"date": "2024-12-22", "value": 0.87}
    ],
    "trend_direction": "up",
    "change_percentage": 8.75
  }
}
```

---

## 3. 计费管理 API

### 3.1 获取账单列表

```http
GET /billing/invoices
```

**查询参数：**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| status | string | 否 | 账单状态 |
| billing_period | string | 否 | 计费周期 |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "invoice_id": "INV-2025-001",
        "billing_period": "2024-12",
        "total_amount": 12500.00,
        "currency": "CNY",
        "status": "pending",
        "due_date": "2025-01-31",
        "created_at": "2025-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "total_items": 12
    }
  }
}
```

### 3.2 生成账单

```http
POST /billing/invoices
```

**请求体：**

```json
{
  "billing_period": "2024-12",
  "include_details": true
}
```

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "invoice_id": "INV-2025-002",
    "billing_period": "2024-12",
    "line_items": [
      {
        "description": "Platinum 质量服务",
        "quantity": 50000,
        "unit": "tokens",
        "rate": 0.00015,
        "amount": 7500.00
      },
      {
        "description": "Gold 质量服务",
        "quantity": 30000,
        "unit": "tokens",
        "rate": 0.00012,
        "amount": 3600.00
      }
    ],
    "subtotal": 11100.00,
    "tax": 666.00,
    "total_amount": 11766.00
  }
}
```

### 3.3 获取账单详情

```http
GET /billing/invoices/{invoice_id}
```

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "invoice_id": "INV-2025-001",
    "billing_period": "2024-12",
    "total_amount": 12500.00,
    "currency": "CNY",
    "status": "paid",
    "line_items": [...],
    "quality_breakdown": {
      "platinum": {"count": 500, "amount": 7500.00},
      "gold": {"count": 300, "amount": 3600.00},
      "silver": {"count": 200, "amount": 1200.00},
      "bronze": {"count": 100, "amount": 200.00}
    },
    "quality_certificate": {
      "average_score": 0.85,
      "sla_compliance": 0.98,
      "issued_at": "2025-01-01T00:00:00Z"
    }
  }
}
```

### 3.4 处理支付

```http
POST /billing/payments
```

**请求体：**

```json
{
  "invoice_id": "INV-2025-001",
  "payment_method": "bank_transfer",
  "payment_reference": "TXN-123456"
}
```

---

## 4. 质量评估 API

### 4.1 执行质量评估

```http
POST /quality/evaluate
```

**请求体：**

```json
{
  "query": "用户问题",
  "response": "系统回答",
  "contexts": [
    "上下文信息 1",
    "上下文信息 2"
  ],
  "ground_truth": "标准答案（可选）"
}
```

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "evaluation_id": "EVAL-001",
    "scores": {
      "faithfulness": 0.92,
      "answer_relevancy": 0.88,
      "context_precision": 0.85,
      "context_recall": 0.90
    },
    "overall_score": 0.89,
    "quality_tier": "gold",
    "confidence": 0.95,
    "feedback": [
      "回答与上下文高度一致",
      "建议补充更多细节"
    ]
  }
}
```

### 4.2 获取质量指标

```http
GET /quality/metrics
```

**查询参数：**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| metric_type | string | 否 | 指标类型 |
| aggregation | string | 否 | 聚合方式 (avg/sum/count) |
| group_by | string | 否 | 分组字段 |

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "metrics": {
      "average_score": 0.85,
      "tier_distribution": {
        "platinum": 0.15,
        "gold": 0.35,
        "silver": 0.35,
        "bronze": 0.15
      },
      "total_evaluations": 10000,
      "trend": "improving"
    }
  }
}
```

### 4.3 获取质量趋势

```http
GET /quality/trends
```

**查询参数：**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| metric | string | 是 | 指标名称 |
| duration | string | 否 | 时间范围 |
| granularity | string | 否 | 时间粒度 |

---

## 5. 反馈管理 API

### 5.1 提交反馈

```http
POST /feedback
```

**请求体：**

```json
{
  "source": "customer_survey",
  "category": "quality",
  "content": "反馈内容",
  "rating": 4,
  "metadata": {
    "ticket_id": "TKT-001"
  }
}
```

### 5.2 获取反馈列表

```http
GET /feedback
```

### 5.3 处理反馈

```http
POST /feedback/{feedback_id}/process
```

---

## 6. 错误码参考

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| VALIDATION_FAILED | 400 | 请求数据验证失败 |
| MISSING_REQUIRED_FIELD | 400 | 缺少必需字段 |
| UNAUTHORIZED | 401 | 未授权访问 |
| TOKEN_EXPIRED | 401 | 认证令牌已过期 |
| PERMISSION_DENIED | 403 | 没有权限执行此操作 |
| RESOURCE_NOT_FOUND | 404 | 请求的资源不存在 |
| RATE_LIMIT_EXCEEDED | 429 | 请求频率超限 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 7. 速率限制

| 端点类型 | 限制 |
|----------|------|
| 读取操作 | 100 请求/分钟 |
| 写入操作 | 30 请求/分钟 |
| 评估操作 | 10 请求/分钟 |

超出限制时返回 429 状态码，响应头包含：

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704067200
```

---

*本文档最后更新: 2025-01-01*
