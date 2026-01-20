# SuperInsight 数据同步系统 - 用户指南

## 快速开始

### 1. 获取 API 凭证

首先，您需要获取 API 访问凭证。联系管理员获取以下信息：

- Client ID
- Client Secret
- API Base URL

### 2. 获取访问令牌

```bash
curl -X POST https://api.superinsight.com/v1/sync/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
  }'
```

响应示例：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 3600
}
```

### 3. 创建第一个同步作业

```bash
curl -X POST https://api.superinsight.com/v1/sync/jobs \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Sync",
    "connector": {
      "type": "rest_api",
      "config": {
        "base_url": "https://your-api.com",
        "endpoints": [{
          "path": "/data",
          "method": "GET"
        }]
      }
    }
  }'
```

---

## 同步作业配置指南

### REST API 连接器

从 REST API 拉取数据的配置示例：

```json
{
  "name": "REST API Sync",
  "connector": {
    "type": "rest_api",
    "config": {
      "base_url": "https://api.example.com",
      "auth": {
        "type": "bearer",
        "token": "your_api_token"
      },
      "headers": {
        "X-Custom-Header": "value"
      },
      "endpoints": [
        {
          "path": "/users",
          "method": "GET",
          "pagination": {
            "type": "cursor",
            "cursor_param": "cursor",
            "cursor_field": "next_cursor"
          }
        }
      ],
      "rate_limit": {
        "requests_per_second": 10
      }
    }
  }
}
```

**认证类型**:
- `bearer`: Bearer Token
- `basic`: HTTP Basic Auth
- `api_key`: API Key (header 或 query)
- `oauth2`: OAuth 2.0

**分页类型**:
- `offset`: 偏移量分页
- `cursor`: 游标分页
- `page`: 页码分页
- `link`: Link Header 分页

### 数据库连接器

从数据库同步数据的配置：

```json
{
  "name": "Database Sync",
  "connector": {
    "type": "database",
    "config": {
      "driver": "postgresql",
      "host": "db.example.com",
      "port": 5432,
      "database": "production",
      "username": "${DB_USER}",
      "password": "${DB_PASSWORD}",
      "ssl": true,
      "query": "SELECT * FROM orders WHERE updated_at > :last_sync",
      "incremental": {
        "column": "updated_at",
        "type": "timestamp"
      }
    }
  }
}
```

**支持的数据库**:
- PostgreSQL
- MySQL
- MariaDB
- SQL Server
- Oracle

### 文件连接器

从文件系统或对象存储同步：

```json
{
  "name": "S3 File Sync",
  "connector": {
    "type": "file",
    "config": {
      "source": "s3",
      "bucket": "my-data-bucket",
      "prefix": "exports/",
      "pattern": "*.csv",
      "credentials": {
        "access_key": "${AWS_ACCESS_KEY}",
        "secret_key": "${AWS_SECRET_KEY}",
        "region": "us-east-1"
      },
      "format": {
        "type": "csv",
        "delimiter": ",",
        "header": true,
        "encoding": "utf-8"
      }
    }
  }
}
```

---

## 数据转换配置

### 字段映射

将源字段映射到目标字段：

```json
{
  "transformations": [
    {
      "type": "field_mapping",
      "config": {
        "mappings": {
          "customer_id": "id",
          "customer_name": "full_name",
          "email_address": "email"
        },
        "drop_unmapped": false
      }
    }
  ]
}
```

### 类型转换

转换数据类型：

```json
{
  "transformations": [
    {
      "type": "type_conversion",
      "config": {
        "conversions": {
          "price": "float",
          "quantity": "integer",
          "is_active": "boolean",
          "created_at": "datetime"
        }
      }
    }
  ]
}
```

### 值转换

对字段值进行转换：

```json
{
  "transformations": [
    {
      "type": "value_transform",
      "config": {
        "transforms": {
          "email": "lowercase",
          "name": "trim",
          "phone": "normalize_phone",
          "ssn": "mask"
        }
      }
    }
  ]
}
```

**可用转换**:
- `uppercase`: 转大写
- `lowercase`: 转小写
- `trim`: 去除首尾空格
- `normalize_phone`: 规范化电话号码
- `normalize_email`: 规范化邮箱
- `mask`: 数据脱敏
- `hash`: 哈希处理

### 数据验证

配置数据验证规则：

```json
{
  "transformations": [
    {
      "type": "validation",
      "config": {
        "rules": {
          "email": {
            "type": "email",
            "required": true
          },
          "age": {
            "type": "range",
            "min": 0,
            "max": 150
          },
          "status": {
            "type": "enum",
            "values": ["active", "inactive", "pending"]
          }
        },
        "on_error": "skip"
      }
    }
  ]
}
```

**错误处理选项**:
- `skip`: 跳过无效记录
- `fail`: 整个批次失败
- `default`: 使用默认值

---

## 调度配置

### Cron 表达式

使用 Cron 表达式配置定时执行：

```json
{
  "schedule": {
    "type": "cron",
    "expression": "0 */6 * * *",
    "timezone": "Asia/Shanghai"
  }
}
```

常用表达式：
- `0 * * * *`: 每小时
- `0 */6 * * *`: 每6小时
- `0 0 * * *`: 每天午夜
- `0 0 * * 0`: 每周日
- `0 0 1 * *`: 每月1日

### 手动触发

禁用自动调度，仅手动触发：

```json
{
  "schedule": {
    "type": "manual"
  }
}
```

### 事件触发

基于 Webhook 事件触发：

```json
{
  "schedule": {
    "type": "webhook",
    "secret": "your_webhook_secret"
  }
}
```

---

## 冲突处理

### 配置冲突解决策略

```json
{
  "conflict_resolution": {
    "detection": {
      "enabled": true,
      "fields": ["id", "version"]
    },
    "strategy": "timestamp_wins",
    "options": {
      "timestamp_field": "updated_at",
      "fallback": "source_wins"
    }
  }
}
```

**可用策略**:
- `timestamp_wins`: 最后更新时间获胜
- `source_wins`: 源数据优先
- `target_wins`: 目标数据优先
- `field_merge`: 字段级合并
- `manual`: 手动解决

### 字段级合并

```json
{
  "conflict_resolution": {
    "strategy": "field_merge",
    "options": {
      "merge_rules": {
        "name": "source_wins",
        "email": "target_wins",
        "metadata": "merge_objects"
      }
    }
  }
}
```

---

## 实时同步

### WebSocket 连接

JavaScript 示例：

```javascript
const ws = new WebSocket('wss://api.superinsight.com/v1/sync/ws?token=' + token);

ws.onopen = () => {
  // 订阅同步更新
  ws.send(JSON.stringify({
    type: 'subscribe',
    payload: {
      channel: 'sync_updates',
      filters: {
        job_id: 'job_123'
      }
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Connection closed, reconnecting...');
  // 实现重连逻辑
};
```

### 处理背压

当消息处理速度跟不上接收速度时：

```javascript
let messageQueue = [];
let processing = false;

ws.onmessage = (event) => {
  messageQueue.push(JSON.parse(event.data));
  processQueue();
};

async function processQueue() {
  if (processing || messageQueue.length === 0) return;
  processing = true;

  while (messageQueue.length > 0) {
    const message = messageQueue.shift();
    await handleMessage(message);
  }

  processing = false;
}
```

---

## 数据推送

### Python 示例

```python
import requests
import json

API_URL = "https://api.superinsight.com/v1/sync"
TOKEN = "your_token"

def push_data(records):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "source": "my_system",
        "records": records,
        "options": {
            "upsert": True,
            "validate": True
        }
    }

    response = requests.post(
        f"{API_URL}/push/batch",
        headers=headers,
        json=payload
    )

    return response.json()

# 使用示例
records = [
    {"id": "1", "data": {"name": "Product A", "price": 99.99}},
    {"id": "2", "data": {"name": "Product B", "price": 149.99}}
]

result = push_data(records)
print(f"Accepted: {result['accepted']}, Rejected: {result['rejected']}")
```

### 流式推送

```python
import requests

def stream_push(records):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/x-ndjson"
    }

    def generate():
        for record in records:
            yield json.dumps(record) + "\n"

    response = requests.post(
        f"{API_URL}/push/stream",
        headers=headers,
        data=generate(),
        stream=True
    )

    return response.json()
```

---

## 故障排查

### 常见问题

#### 1. 认证失败 (401)

**问题**: 收到 `UNAUTHORIZED` 错误

**解决方案**:
- 检查 Token 是否过期
- 验证 Client ID 和 Secret 是否正确
- 确认 API 权限配置

```bash
# 刷新 Token
curl -X POST https://api.superinsight.com/v1/sync/auth/refresh \
  -d '{"refresh_token": "your_refresh_token"}'
```

#### 2. 速率限制 (429)

**问题**: 收到 `RATE_LIMITED` 错误

**解决方案**:
- 检查 `X-RateLimit-*` 响应头
- 实现请求重试和退避
- 考虑升级 API 配额

```python
import time

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait = 2 ** attempt
            time.sleep(wait)
    raise Exception("Max retries exceeded")
```

#### 3. 同步作业失败

**问题**: 作业状态变为 `failed`

**排查步骤**:
1. 查看作业日志
```bash
curl https://api.superinsight.com/v1/sync/jobs/{job_id}/logs
```

2. 检查数据源连接
3. 验证转换规则配置
4. 查看冲突记录

#### 4. 数据不一致

**问题**: 目标数据与源数据不匹配

**排查步骤**:
1. 检查转换规则是否正确
2. 查看冲突解决日志
3. 验证增量同步标记
4. 执行全量重新同步

### 日志分析

#### 查看详细日志

```bash
# 获取错误日志
curl "https://api.superinsight.com/v1/sync/jobs/{job_id}/logs?level=error"

# 获取指定时间范围日志
curl "https://api.superinsight.com/v1/sync/jobs/{job_id}/logs?since=2024-01-01T00:00:00Z"
```

#### 日志级别

- `debug`: 详细调试信息
- `info`: 一般操作信息
- `warning`: 警告信息
- `error`: 错误信息

---

## 性能优化

### 批量处理

推荐批次大小：
- 小记录 (<1KB): 1000-5000 条/批次
- 中等记录 (1-10KB): 100-500 条/批次
- 大记录 (>10KB): 10-50 条/批次

### 并行处理

配置并行连接数：

```json
{
  "connector": {
    "config": {
      "concurrency": 4,
      "connection_pool_size": 10
    }
  }
}
```

### 增量同步

优先使用增量同步而非全量：

```json
{
  "connector": {
    "config": {
      "incremental": {
        "enabled": true,
        "column": "updated_at",
        "type": "timestamp"
      }
    }
  }
}
```

### 监控指标

关注以下关键指标：
- 同步延迟 (sync_latency_seconds)
- 吞吐量 (sync_records_per_second)
- 错误率 (sync_error_rate)
- 队列深度 (sync_queue_depth)

---

## 最佳实践

### 1. 安全

- 使用环境变量存储敏感信息
- 定期轮换 API 凭证
- 启用 IP 白名单
- 使用最小权限原则

### 2. 可靠性

- 实现幂等性处理
- 配置合理的重试策略
- 监控告警及时响应
- 定期测试故障恢复

### 3. 可维护性

- 使用清晰的命名规范
- 添加详细的作业描述
- 定期清理历史数据
- 文档化配置变更

### 4. 性能

- 选择合适的批次大小
- 使用增量同步
- 优化转换规则
- 监控资源使用
