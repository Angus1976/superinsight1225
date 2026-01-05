# 业务逻辑 API 参考文档

## 概述

本文档详细描述了 SuperInsight 业务逻辑提炼与智能化功能的所有 API 端点、请求参数、响应格式和使用示例。

## 基础信息

- **基础 URL**: `http://localhost:8000/api/business-logic`
- **认证方式**: JWT Bearer Token
- **内容类型**: `application/json`
- **API 版本**: v1.0

## 通用响应格式

### 成功响应
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2026-01-05T10:30:00Z"
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "请求参数无效",
    "details": "project_id 不能为空"
  },
  "timestamp": "2026-01-05T10:30:00Z"
}
```

## API 端点详情

### 1. 业务模式分析

#### POST /analyze

分析项目标注数据中的业务模式和规律。

**请求参数**:
```json
{
  "project_id": "string",           // 必需：项目ID
  "analysis_types": [               // 可选：分析类型数组
    "sentiment_correlation",        // 情感关联分析
    "keyword_cooccurrence",         // 关键词共现分析
    "temporal_trends",              // 时间趋势分析
    "user_behavior"                 // 用户行为分析
  ],
  "min_confidence": 0.7,            // 可选：最小置信度 (0.0-1.0)
  "min_support": 3,                 // 可选：最小支持度
  "time_range": {                   // 可选：时间范围
    "start_date": "2026-01-01",
    "end_date": "2026-01-31"
  },
  "filters": {                      // 可选：数据过滤条件
    "annotators": ["user1", "user2"],
    "sentiment": ["positive", "negative"]
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "patterns": [
      {
        "pattern_id": "pattern_001",
        "type": "sentiment_correlation",
        "description": "正面情感与产品质量关键词强关联",
        "confidence": 0.85,
        "support": 45,
        "details": {
          "sentiment": "positive",
          "keywords": ["quality", "excellent", "satisfied"],
          "correlation_strength": 0.78
        }
      }
    ],
    "analysis_summary": {
      "total_patterns": 12,
      "high_confidence_patterns": 8,
      "analysis_duration": "15.3s",
      "data_coverage": 0.92
    }
  }
}
```

**Python 示例**:
```python
import requests

url = "http://localhost:8000/api/business-logic/analyze"
headers = {
    "Authorization": "Bearer your_jwt_token",
    "Content-Type": "application/json"
}

data = {
    "project_id": "proj_123",
    "analysis_types": ["sentiment_correlation", "keyword_cooccurrence"],
    "min_confidence": 0.7
}

response = requests.post(url, json=data, headers=headers)
result = response.json()

if result["success"]:
    patterns = result["data"]["patterns"]
    print(f"发现 {len(patterns)} 个业务模式")
else:
    print(f"分析失败: {result['error']['message']}")
```

**JavaScript 示例**:
```javascript
const analyzePatterns = async (projectId) => {
  const response = await fetch('/api/business-logic/analyze', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      project_id: projectId,
      analysis_types: ['sentiment_correlation'],
      min_confidence: 0.7
    })
  });
  
  const result = await response.json();
  return result.data.patterns;
};
```

### 2. 获取业务规则

#### GET /rules/{project_id}

获取指定项目的业务规则列表。

**路径参数**:
- `project_id` (string): 项目ID

**查询参数**:
- `rule_type` (string, 可选): 规则类型 (`association`, `classification`, `temporal`, `pattern`)
- `active_only` (boolean, 可选): 仅返回激活的规则，默认 `true`
- `min_confidence` (float, 可选): 最小置信度过滤
- `limit` (int, 可选): 返回数量限制，默认 50
- `offset` (int, 可选): 分页偏移量，默认 0

**响应示例**:
```json
{
  "success": true,
  "data": {
    "rules": [
      {
        "id": "rule_001",
        "name": "高评分产品规则",
        "description": "评分大于4的产品通常获得正面情感",
        "rule_type": "classification",
        "conditions": [
          {
            "field": "rating",
            "operator": "greater_than",
            "value": 4.0,
            "confidence": 0.85
          }
        ],
        "consequent": {
          "field": "sentiment",
          "value": "positive",
          "confidence": 0.82,
          "probability": 0.78
        },
        "support": 156,
        "confidence": 0.82,
        "lift": 1.45,
        "created_at": "2026-01-05T08:30:00Z",
        "is_active": true
      }
    ],
    "pagination": {
      "total": 25,
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}
```

### 3. 提取业务规则

#### POST /rules/extract

从标注数据中提取新的业务规则。

**请求参数**:
```json
{
  "project_id": "string",           // 必需：项目ID
  "rule_types": [                   // 可选：要提取的规则类型
    "association",
    "classification",
    "temporal",
    "pattern"
  ],
  "min_support": 5,                 // 可选：最小支持度
  "min_confidence": 0.8,            // 可选：最小置信度
  "max_rules": 100,                 // 可选：最大规则数量
  "target_fields": [                // 可选：目标字段
    "sentiment",
    "rating",
    "category"
  ],
  "advanced_options": {             // 可选：高级选项
    "use_ml_algorithms": true,      // 使用机器学习算法
    "detect_anomalies": true,       // 检测异常模式
    "temporal_analysis": true       // 时间序列分析
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "extraction_id": "extract_001",
    "rules": [
      {
        "id": "rule_new_001",
        "name": "周末活跃用户规则",
        "description": "周末标注的用户活跃度更高",
        "rule_type": "temporal",
        "confidence": 0.76,
        "support": 23,
        "validation_score": 0.82
      }
    ],
    "extraction_summary": {
      "total_rules_extracted": 15,
      "high_confidence_rules": 8,
      "processing_time": "45.2s",
      "data_processed": 2847
    }
  }
}
```

### 4. 获取业务模式

#### GET /patterns/{project_id}

获取指定项目的业务模式列表。

**路径参数**:
- `project_id` (string): 项目ID

**查询参数**:
- `pattern_type` (string, 可选): 模式类型
- `min_strength` (float, 可选): 最小强度，默认 0.0
- `limit` (int, 可选): 返回数量限制
- `sort_by` (string, 可选): 排序字段 (`strength`, `detected_at`)

**响应示例**:
```json
{
  "success": true,
  "data": {
    "patterns": [
      {
        "id": "pattern_001",
        "project_id": "proj_123",
        "pattern_type": "sentiment_correlation",
        "description": "正面情感与高评分的强关联",
        "strength": 0.87,
        "evidence": [
          {
            "type": "correlation",
            "value": 0.85,
            "sample_size": 234
          }
        ],
        "detected_at": "2026-01-05T09:15:00Z",
        "last_seen": "2026-01-05T10:30:00Z"
      }
    ],
    "total_patterns": 8
  }
}
```

### 5. 生成可视化

#### POST /visualization

生成业务逻辑的可视化图表。

**请求参数**:
```json
{
  "project_id": "string",           // 必需：项目ID
  "visualization_type": "string",   // 必需：可视化类型
  "data_source": "string",          // 可选：数据源 (rules, patterns, insights)
  "chart_options": {                // 可选：图表选项
    "width": 800,
    "height": 600,
    "theme": "light",
    "interactive": true
  },
  "filters": {                      // 可选：数据过滤
    "confidence_range": [0.7, 1.0],
    "date_range": {
      "start": "2026-01-01",
      "end": "2026-01-31"
    }
  }
}
```

**可视化类型**:
- `rule_network`: 规则网络图
- `pattern_heatmap`: 模式热力图
- `trend_chart`: 趋势图表
- `correlation_matrix`: 关联矩阵
- `user_behavior_cluster`: 用户行为聚类图

**响应示例**:
```json
{
  "success": true,
  "data": {
    "visualization_id": "viz_001",
    "chart_data": {
      "nodes": [
        {
          "id": "sentiment_positive",
          "label": "正面情感",
          "size": 45,
          "color": "#4CAF50"
        }
      ],
      "edges": [
        {
          "source": "sentiment_positive",
          "target": "rating_high",
          "weight": 0.85,
          "label": "强关联"
        }
      ]
    },
    "chart_config": {
      "type": "network",
      "layout": "force",
      "interactive": true
    },
    "metadata": {
      "generated_at": "2026-01-05T10:45:00Z",
      "data_points": 156,
      "processing_time": "2.3s"
    }
  }
}
```

### 6. 导出业务逻辑

#### POST /export

导出业务逻辑数据到指定格式。

**请求参数**:
```json
{
  "project_id": "string",           // 必需：项目ID
  "export_format": "string",        // 必需：导出格式
  "export_types": [                 // 必需：导出类型
    "rules",
    "patterns",
    "insights"
  ],
  "filters": {                      // 可选：导出过滤条件
    "confidence_threshold": 0.7,
    "active_only": true,
    "date_range": {
      "start": "2026-01-01",
      "end": "2026-01-31"
    }
  },
  "options": {                      // 可选：导出选项
    "include_metadata": true,
    "include_statistics": true,
    "compress": false
  }
}
```

**支持的导出格式**:
- `json`: JSON 格式
- `csv`: CSV 格式
- `excel`: Excel 格式
- `xml`: XML 格式
- `yaml`: YAML 格式

**响应示例**:
```json
{
  "success": true,
  "data": {
    "export_id": "export_001",
    "download_url": "/api/business-logic/downloads/export_001.json",
    "file_size": 2048576,
    "expires_at": "2026-01-06T10:45:00Z",
    "export_summary": {
      "rules_exported": 25,
      "patterns_exported": 12,
      "insights_exported": 8,
      "total_records": 45
    }
  }
}
```

### 7. 应用业务规则

#### POST /apply

将业务规则应用到目标项目。

**请求参数**:
```json
{
  "source_project_id": "string",   // 必需：源项目ID
  "target_project_id": "string",   // 必需：目标项目ID
  "rule_ids": [                     // 可选：指定规则ID列表
    "rule_001",
    "rule_002"
  ],
  "application_mode": "string",     // 可选：应用模式
  "validation_options": {           // 可选：验证选项
    "validate_before_apply": true,
    "min_accuracy_threshold": 0.8,
    "test_sample_size": 100
  },
  "conflict_resolution": "string"   // 可选：冲突解决策略
}
```

**应用模式**:
- `preview`: 预览模式，不实际应用
- `apply`: 直接应用
- `test`: 测试模式，在测试集上验证

**冲突解决策略**:
- `skip`: 跳过冲突规则
- `override`: 覆盖现有规则
- `merge`: 合并规则

**响应示例**:
```json
{
  "success": true,
  "data": {
    "application_id": "app_001",
    "results": {
      "rules_applied": 15,
      "rules_skipped": 3,
      "rules_failed": 1,
      "success_rate": 0.88
    },
    "validation_results": {
      "accuracy": 0.85,
      "precision": 0.82,
      "recall": 0.79,
      "f1_score": 0.80
    },
    "conflicts_detected": [
      {
        "rule_id": "rule_003",
        "conflict_type": "duplicate",
        "resolution": "skipped"
      }
    ]
  }
}
```

### 8. 变化检测

#### POST /detect-changes

检测业务逻辑的变化趋势。

**请求参数**:
```json
{
  "project_id": "string",           // 必需：项目ID
  "time_window": {                  // 必需：时间窗口
    "start_date": "2026-01-01",
    "end_date": "2026-01-31"
  },
  "comparison_baseline": "string",  // 可选：比较基线
  "change_types": [                 // 可选：变化类型
    "pattern_emergence",
    "pattern_disappearance",
    "strength_change",
    "frequency_change"
  ],
  "sensitivity": 0.1                // 可选：变化敏感度
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "changes_detected": [
      {
        "change_id": "change_001",
        "change_type": "pattern_emergence",
        "description": "新出现的负面情感模式",
        "significance": 0.85,
        "detected_at": "2026-01-05T14:30:00Z",
        "affected_patterns": ["pattern_015"],
        "impact_assessment": "medium"
      }
    ],
    "change_summary": {
      "total_changes": 5,
      "significant_changes": 2,
      "trend_direction": "increasing_complexity",
      "stability_score": 0.72
    }
  }
}
```

### 9. 获取业务洞察

#### GET /insights/{project_id}

获取项目的业务洞察列表。

**路径参数**:
- `project_id` (string): 项目ID

**查询参数**:
- `insight_type` (string, 可选): 洞察类型
- `unacknowledged_only` (boolean, 可选): 仅未确认的洞察
- `priority` (string, 可选): 优先级过滤 (`high`, `medium`, `low`)

**响应示例**:
```json
{
  "success": true,
  "data": {
    "insights": [
      {
        "id": "insight_001",
        "project_id": "proj_123",
        "insight_type": "trend_alert",
        "title": "用户满意度下降趋势",
        "description": "过去一周用户满意度评分呈下降趋势",
        "impact_score": 0.78,
        "priority": "high",
        "recommendations": [
          "关注产品质量问题",
          "加强客户服务培训",
          "分析负面反馈根因"
        ],
        "data_points": [
          {
            "metric": "average_rating",
            "current_value": 3.2,
            "previous_value": 4.1,
            "change_percentage": -21.95
          }
        ],
        "created_at": "2026-01-05T11:20:00Z",
        "acknowledged_at": null
      }
    ],
    "summary": {
      "total_insights": 12,
      "unacknowledged": 5,
      "high_priority": 3
    }
  }
}
```

### 10. 确认洞察

#### POST /insights/{insight_id}/acknowledge

确认指定的业务洞察。

**路径参数**:
- `insight_id` (string): 洞察ID

**请求参数**:
```json
{
  "acknowledged_by": "string",      // 可选：确认人
  "notes": "string"                 // 可选：确认备注
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "message": "洞察已确认",
    "insight_id": "insight_001",
    "acknowledged_at": "2026-01-05T15:45:00Z",
    "acknowledged_by": "admin_user"
  }
}
```

## 错误代码

| 错误代码 | HTTP 状态码 | 描述 |
|----------|-------------|------|
| `INVALID_REQUEST` | 400 | 请求参数无效 |
| `UNAUTHORIZED` | 401 | 未授权访问 |
| `FORBIDDEN` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `CONFLICT` | 409 | 资源冲突 |
| `RATE_LIMITED` | 429 | 请求频率超限 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 使用限制

### 请求频率限制
- **分析请求**: 每分钟最多 10 次
- **查询请求**: 每分钟最多 100 次
- **导出请求**: 每小时最多 5 次

### 数据量限制
- **单次分析数据量**: 最多 50,000 条记录
- **规则数量**: 每个项目最多 1,000 个规则
- **导出文件大小**: 最大 100MB

### 并发限制
- **同时分析任务**: 每个用户最多 3 个
- **并发请求**: 每个用户最多 10 个

## SDK 和工具

### Python SDK
```bash
pip install superinsight-business-logic
```

```python
from superinsight_business_logic import BusinessLogicClient

client = BusinessLogicClient(
    base_url="http://localhost:8000",
    api_key="your_api_key"
)

# 分析业务模式
patterns = client.analyze_patterns(
    project_id="proj_123",
    analysis_types=["sentiment_correlation"]
)
```

### JavaScript SDK
```bash
npm install @superinsight/business-logic
```

```javascript
import { BusinessLogicClient } from '@superinsight/business-logic';

const client = new BusinessLogicClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your_api_key'
});

// 提取业务规则
const rules = await client.extractRules({
  projectId: 'proj_123',
  minConfidence: 0.8
});
```

## 更新日志

### v1.0.0 (2026-01-05)
- 🎉 初始版本发布
- ✅ 完整的业务逻辑分析 API
- ✅ 四大核心算法支持
- ✅ 可视化和导出功能
- ✅ 实时洞察和变化检测

---

如有疑问或需要技术支持，请联系开发团队或查看 [故障排查指南](troubleshooting.md)。