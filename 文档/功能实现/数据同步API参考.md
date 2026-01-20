# SuperInsight 数据同步系统 - API 参考文档

## 概述

本文档描述了 SuperInsight 数据同步系统的所有 API 端点。

**基础 URL**: `https://api.superinsight.com/v1/sync`

**认证方式**: 所有 API 请求需要在 Header 中携带认证信息

```
Authorization: Bearer <jwt_token>
# 或
X-API-Key: <api_key>
```

## 同步网关 API

### 认证端点

#### POST /auth/token

获取 JWT Token。

**请求体**:
```json
{
  "grant_type": "client_credentials",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "scope": "sync:read sync:write"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g...",
  "scope": "sync:read sync:write"
}
```

#### POST /auth/refresh

刷新 Token。

**请求体**:
```json
{
  "grant_type": "refresh_token",
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g..."
}
```

#### POST /auth/revoke

撤销 Token。

**请求体**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### API Key 管理

#### POST /api-keys

创建 API Key。

**请求体**:
```json
{
  "name": "production-key",
  "permissions": ["sync:read", "sync:write"],
  "expires_at": "2025-12-31T23:59:59Z",
  "rate_limit": 1000
}
```

**响应**:
```json
{
  "id": "key_abc123",
  "name": "production-key",
  "key": "sk_live_xxx...",
  "permissions": ["sync:read", "sync:write"],
  "expires_at": "2025-12-31T23:59:59Z",
  "rate_limit": 1000,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### DELETE /api-keys/{key_id}

撤销 API Key。

---

## 同步作业 API

### 作业管理

#### GET /jobs

列出所有同步作业。

**查询参数**:
- `status`: 过滤状态 (pending, running, completed, failed)
- `connector_type`: 过滤连接器类型
- `page`: 页码 (默认 1)
- `per_page`: 每页数量 (默认 20)

**响应**:
```json
{
  "items": [
    {
      "id": "job_123",
      "name": "Daily Sales Sync",
      "connector_type": "rest_api",
      "status": "running",
      "progress": 45.5,
      "records_processed": 10000,
      "records_total": 22000,
      "started_at": "2024-01-01T10:00:00Z",
      "eta": "2024-01-01T10:30:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20
}
```

#### POST /jobs

创建同步作业。

**请求体**:
```json
{
  "name": "Customer Data Sync",
  "connector": {
    "type": "rest_api",
    "config": {
      "base_url": "https://api.example.com",
      "auth": {
        "type": "bearer",
        "token": "xxx"
      },
      "endpoints": [
        {
          "path": "/customers",
          "method": "GET",
          "pagination": {
            "type": "offset",
            "page_param": "page",
            "limit_param": "limit",
            "limit": 100
          }
        }
      ]
    }
  },
  "schedule": {
    "type": "cron",
    "expression": "0 */6 * * *"
  },
  "transformations": [
    {
      "type": "field_mapping",
      "config": {
        "mappings": {
          "customer_id": "id",
          "customer_name": "name"
        }
      }
    }
  ],
  "destination": {
    "type": "database",
    "table": "customers",
    "mode": "upsert",
    "key_columns": ["id"]
  }
}
```

**响应**:
```json
{
  "id": "job_456",
  "name": "Customer Data Sync",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /jobs/{job_id}

获取作业详情。

#### PUT /jobs/{job_id}

更新作业配置。

#### DELETE /jobs/{job_id}

删除作业。

### 作业控制

#### POST /jobs/{job_id}/start

启动作业。

#### POST /jobs/{job_id}/pause

暂停作业。

#### POST /jobs/{job_id}/resume

恢复作业。

#### POST /jobs/{job_id}/cancel

取消作业。

#### GET /jobs/{job_id}/logs

获取作业日志。

**查询参数**:
- `level`: 日志级别 (debug, info, warning, error)
- `since`: 起始时间
- `until`: 结束时间
- `limit`: 最大条数

**响应**:
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T10:00:01Z",
      "level": "info",
      "message": "Starting sync job",
      "metadata": {}
    }
  ]
}
```

---

## 数据推送 API

### 批量推送

#### POST /push/batch

批量推送数据。

**请求体**:
```json
{
  "source": "erp_system",
  "records": [
    {
      "id": "rec_001",
      "data": {
        "name": "Product A",
        "price": 99.99
      },
      "metadata": {
        "updated_at": "2024-01-01T00:00:00Z"
      }
    }
  ],
  "options": {
    "upsert": true,
    "validate": true,
    "transform": true
  }
}
```

**响应**:
```json
{
  "request_id": "req_abc123",
  "accepted": 100,
  "rejected": 0,
  "errors": [],
  "processing_time_ms": 150
}
```

### 流式推送

#### POST /push/stream

流式推送数据（支持 NDJSON 格式）。

**请求头**:
```
Content-Type: application/x-ndjson
```

**请求体**:
```
{"id": "1", "data": {"name": "A"}}
{"id": "2", "data": {"name": "B"}}
{"id": "3", "data": {"name": "C"}}
```

### Webhook 接收

#### POST /push/webhook/{webhook_id}

Webhook 数据接收端点。

**请求体**: 根据 Webhook 配置的 schema 验证

**响应**:
```json
{
  "received": true,
  "webhook_id": "wh_123",
  "event_id": "evt_456"
}
```

### 文件上传

#### POST /push/file

上传文件进行同步。

**请求头**:
```
Content-Type: multipart/form-data
```

**表单字段**:
- `file`: 上传的文件
- `format`: 文件格式 (csv, json, parquet, excel)
- `options`: JSON 格式的处理选项

**响应**:
```json
{
  "file_id": "file_123",
  "filename": "data.csv",
  "size_bytes": 1024000,
  "records_count": 5000,
  "status": "processing"
}
```

---

## WebSocket API

### 连接

```
wss://api.superinsight.com/v1/sync/ws?token=<jwt_token>
```

### 消息格式

所有消息使用 JSON 格式：

```json
{
  "type": "message_type",
  "payload": {},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 订阅管理

#### 订阅数据变更

```json
{
  "type": "subscribe",
  "payload": {
    "channel": "sync_updates",
    "filters": {
      "job_id": "job_123",
      "event_types": ["record_created", "record_updated"]
    }
  }
}
```

#### 取消订阅

```json
{
  "type": "unsubscribe",
  "payload": {
    "channel": "sync_updates"
  }
}
```

### 事件类型

#### 同步进度更新

```json
{
  "type": "sync_progress",
  "payload": {
    "job_id": "job_123",
    "progress": 75.5,
    "records_processed": 15000,
    "records_total": 20000
  }
}
```

#### 记录变更

```json
{
  "type": "record_change",
  "payload": {
    "operation": "update",
    "table": "customers",
    "record_id": "cust_123",
    "changes": {
      "name": {"old": "John", "new": "John Doe"}
    }
  }
}
```

#### 冲突通知

```json
{
  "type": "conflict_detected",
  "payload": {
    "conflict_id": "conf_123",
    "record_id": "rec_456",
    "conflict_type": "version",
    "resolution_required": true
  }
}
```

---

## 数据集 API

### 数据集发现

#### GET /datasets

列出可用数据集。

**查询参数**:
- `category`: 数据集分类
- `quality_min`: 最低质量分数
- `search`: 搜索关键词

**响应**:
```json
{
  "datasets": [
    {
      "id": "ds_123",
      "name": "Industry Customer Data",
      "category": "customer",
      "quality_score": 0.95,
      "records_count": 100000,
      "last_updated": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 数据稀释

#### POST /datasets/dilute

用优质数据集稀释噪声数据。

**请求体**:
```json
{
  "source_dataset_id": "ds_source",
  "dilution_dataset_ids": ["ds_industry_1", "ds_industry_2"],
  "config": {
    "dilution_ratio": 0.3,
    "matching_fields": ["category", "region"],
    "quality_threshold": 0.8
  }
}
```

**响应**:
```json
{
  "output_dataset_id": "ds_output",
  "original_records": 10000,
  "diluted_records": 3000,
  "final_records": 13000,
  "quality_improvement": 0.15
}
```

### 数据增强

#### POST /datasets/augment

增强数据集。

**请求体**:
```json
{
  "dataset_id": "ds_123",
  "augmentation": {
    "strategies": ["synonym_replacement", "back_translation"],
    "multiplier": 3,
    "preserve_labels": true
  }
}
```

---

## 监控 API

### 指标

#### GET /metrics

获取 Prometheus 格式指标。

**响应**:
```
# HELP sync_operations_total Total sync operations
# TYPE sync_operations_total counter
sync_operations_total{connector="rest_api",status="success"} 12345

# HELP sync_latency_seconds Sync operation latency
# TYPE sync_latency_seconds histogram
sync_latency_seconds_bucket{le="0.1"} 1000
sync_latency_seconds_bucket{le="0.5"} 5000
...
```

### 健康检查

#### GET /health

健康检查端点。

**响应**:
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "connectors": "healthy"
  },
  "version": "1.0.0"
}
```

#### GET /health/live

存活探针（Kubernetes liveness probe）。

#### GET /health/ready

就绪探针（Kubernetes readiness probe）。

---

## 错误响应

所有 API 使用统一的错误响应格式：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "connector.type",
        "message": "Unsupported connector type"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

### 错误代码

| 代码 | HTTP 状态码 | 描述 |
|------|-------------|------|
| UNAUTHORIZED | 401 | 未认证或 Token 无效 |
| FORBIDDEN | 403 | 无权限访问 |
| NOT_FOUND | 404 | 资源不存在 |
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| RATE_LIMITED | 429 | 请求过于频繁 |
| CONFLICT | 409 | 资源冲突 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 速率限制

API 请求受到速率限制保护：

**默认限制**:
- 标准 API: 1000 请求/分钟
- 批量推送: 100 请求/分钟
- WebSocket 消息: 1000 消息/分钟

**响应头**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1704067260
```

超过限制时返回 429 状态码。
