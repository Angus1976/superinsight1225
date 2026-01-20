# 质量计费闭环系统 - 系统架构文档

## 1. 系统概述

质量计费闭环系统是 SuperInsight 平台的核心组件，实现从质量检测到计费结算的完整闭环管理。系统通过智能工单派发、修复效果考核、Ragas 质量评估和精准计费机制，确保标注质量的持续改进和公平计费。

### 1.1 设计目标

- **智能化**: AI 驱动的工单派发和质量评估
- **自动化**: 全流程自动化质量管理
- **数据驱动**: 基于数据的决策和优化
- **闭环管理**: 从检测到改进的完整闭环
- **公平透明**: 客观的评估和计费机制

### 1.2 核心功能

1. 智能工单派发系统
2. 修复效果考核机制
3. Ragas 质量评估集成
4. 精准计费系统
5. 质量趋势分析
6. 自动化质量监控
7. 多维度质量评估
8. 激励机制设计
9. 质量培训支持
10. 客户质量反馈

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Gateway (FastAPI)                          │
│                    /api/tickets  /api/billing  /api/quality              │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                           Service Layer                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Ticket    │  │ Evaluation  │  │   Billing   │  │  Feedback   │    │
│  │  Service    │  │   Service   │  │   Service   │  │   Service   │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
└─────────┼────────────────┼────────────────┼────────────────┼────────────┘
          │                │                │                │
┌─────────▼────────────────▼────────────────▼────────────────▼────────────┐
│                           Core Modules                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Dispatcher  │  │ Performance │  │  Pricing    │  │ Improvement │    │
│  │   Engine    │  │   Engine    │  │   Engine    │  │   Engine    │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │                │            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    SLA      │  │   Ragas     │  │  Invoice    │  │  Feedback   │    │
│  │  Monitor    │  │  Evaluator  │  │  Generator  │  │  Processor  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                           Data Layer                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ PostgreSQL  │  │    Redis    │  │   Celery    │  │ Prometheus  │    │
│  │  Database   │  │    Cache    │  │   Queue     │  │   Metrics   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

#### 2.2.1 工单管理模块 (src/ticket/)

| 组件 | 职责 |
|------|------|
| `dispatcher.py` | 智能工单派发，技能匹配和负载均衡 |
| `tracker.py` | 工单状态跟踪和生命周期管理 |
| `sla_monitor.py` | SLA 监控、超时检测和自动升级 |

#### 2.2.2 评估模块 (src/evaluation/)

| 组件 | 职责 |
|------|------|
| `performance.py` | 多维度绩效评估引擎 |
| `quality_scorer.py` | 质量评分算法 |
| `report_generator.py` | 绩效报告生成 |

#### 2.2.3 Ragas 集成模块 (src/ragas_integration/)

| 组件 | 职责 |
|------|------|
| `evaluator.py` | Ragas 评估框架集成 |
| `trend_analyzer.py` | 质量趋势分析 |
| `model_optimizer.py` | 模型优化建议 |

#### 2.2.4 计费模块 (src/billing/)

| 组件 | 职责 |
|------|------|
| `pricing_engine.py` | 质量驱动计费引擎 |
| `invoice_generator.py` | 账单生成和管理 |
| `incentive_manager.py` | 激励机制管理 |

#### 2.2.5 培训模块 (src/training/)

| 组件 | 职责 |
|------|------|
| `needs_analyzer.py` | 培训需求分析 |
| `content_recommender.py` | 培训内容推荐 |
| `effect_tracker.py` | 培训效果跟踪 |

#### 2.2.6 反馈模块 (src/feedback/)

| 组件 | 职责 |
|------|------|
| `collector.py` | 多渠道反馈收集 |
| `processor.py` | 反馈处理和分配 |
| `improvement_engine.py` | 改进引擎和客户关系 |

## 3. 数据流设计

### 3.1 工单处理流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  质量    │    │  工单    │    │  人员    │    │  修复    │
│  检测    │───▶│  创建    │───▶│  分配    │───▶│  处理    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  计费    │◀───│  绩效    │◀───│  质量    │◀────────┘
│  结算    │    │  评估    │    │  验证    │
└──────────┘    └──────────┘    └──────────┘
```

### 3.2 质量评估流程

```
Input Data ──▶ Ragas Evaluator ──▶ Quality Scores ──▶ Trend Analysis
                    │                    │                  │
                    ▼                    ▼                  ▼
              Faithfulness         Overall Score      Quality Alerts
              Relevancy            Quality Tier       Improvement
              Precision            Confidence         Suggestions
              Recall
```

### 3.3 计费流程

```
┌─────────────────────────────────────────────────────────────┐
│                     Billing Pipeline                         │
│                                                              │
│  Quality Score ──▶ Tier Mapping ──▶ Rate Calculation        │
│       │                 │                 │                  │
│       ▼                 ▼                 ▼                  │
│  [0.0-0.6]         [Bronze]          [0.05/1k]              │
│  [0.6-0.75]        [Silver]          [0.08/1k]              │
│  [0.75-0.9]        [Gold]            [0.12/1k]              │
│  [0.9-1.0]         [Platinum]        [0.15/1k]              │
│                                                              │
│  ──▶ Token Count ──▶ Amount ──▶ Invoice ──▶ Settlement      │
└─────────────────────────────────────────────────────────────┘
```

## 4. 核心模型设计

### 4.1 工单模型 (TicketModel)

```python
class TicketModel:
    ticket_id: str           # 工单唯一标识
    tenant_id: str           # 租户 ID
    ticket_type: TicketType  # 工单类型
    priority: TicketPriority # 优先级
    status: TicketStatus     # 状态
    assigned_to: str         # 分配人员
    sla_deadline: datetime   # SLA 截止时间
    created_at: datetime     # 创建时间
    resolved_at: datetime    # 解决时间
```

### 4.2 绩效模型 (PerformanceResult)

```python
class PerformanceResult:
    user_id: str
    period: PerformancePeriod
    quality_score: float      # 质量分 (0-1)
    efficiency_score: float   # 效率分 (0-1)
    compliance_score: float   # 合规分 (0-1)
    improvement_score: float  # 改进分 (0-1)
    overall_score: float      # 综合分
    performance_level: str    # 等级 (A/B/C/D/E)
```

### 4.3 计费模型 (BillingRecord)

```python
class BillingRecord:
    billing_id: str
    ticket_id: str
    quality_tier: str         # 质量等级
    token_count: int          # Token 数量
    rate: Decimal             # 费率
    amount: Decimal           # 金额
    created_at: datetime
```

### 4.4 反馈模型 (Feedback)

```python
class Feedback:
    feedback_id: str
    source: FeedbackSource    # 来源渠道
    category: FeedbackCategory # 分类
    sentiment: str            # 情感 (positive/neutral/negative)
    priority: Priority        # 优先级
    status: FeedbackStatus    # 状态
    resolution: str           # 解决方案
```

## 5. 接口设计

### 5.1 工单管理 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/tickets` | GET | 获取工单列表 |
| `/api/tickets` | POST | 创建工单 |
| `/api/tickets/{id}` | GET | 获取工单详情 |
| `/api/tickets/{id}` | PUT | 更新工单 |
| `/api/tickets/{id}/assign` | POST | 分配工单 |
| `/api/tickets/{id}/resolve` | POST | 解决工单 |

### 5.2 绩效评估 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/performance/{user_id}` | GET | 获取用户绩效 |
| `/api/performance/ranking` | GET | 获取绩效排名 |
| `/api/performance/trends` | GET | 获取绩效趋势 |

### 5.3 计费管理 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/billing/invoices` | GET | 获取账单列表 |
| `/api/billing/invoices` | POST | 生成账单 |
| `/api/billing/invoices/{id}` | GET | 获取账单详情 |
| `/api/billing/payments` | POST | 处理支付 |

### 5.4 质量评估 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/quality/evaluate` | POST | 执行质量评估 |
| `/api/quality/metrics` | GET | 获取质量指标 |
| `/api/quality/trends` | GET | 获取质量趋势 |

## 6. 安全设计

### 6.1 认证和授权

- JWT Token 认证
- 基于角色的访问控制 (RBAC)
- API 密钥管理

### 6.2 数据安全

- 传输加密 (TLS 1.3)
- 敏感数据加密存储
- 审计日志记录

### 6.3 多租户隔离

- 租户级数据隔离
- 资源配额管理
- 跨租户访问控制

## 7. 性能优化

### 7.1 缓存策略

```python
# 多级缓存架构
L1: 本地内存缓存 (LRU, 1000 条)
L2: Redis 分布式缓存 (TTL 5 分钟)
L3: 数据库查询缓存
```

### 7.2 批处理优化

- 批量评估任务
- 异步计费处理
- 任务队列优化

### 7.3 查询优化

- 数据库索引优化
- 慢查询检测
- 连接池管理

## 8. 监控和告警

### 8.1 监控指标

| 指标类型 | 指标名称 | 描述 |
|----------|----------|------|
| 性能 | api_latency | API 响应时间 |
| 性能 | query_time | 数据库查询时间 |
| 业务 | ticket_created | 工单创建数 |
| 业务 | quality_score | 平均质量分 |
| 系统 | cpu_usage | CPU 使用率 |
| 系统 | memory_usage | 内存使用率 |

### 8.2 告警规则

- API 响应时间 > 1s
- 错误率 > 1%
- 质量分下降 > 10%
- SLA 违规

## 9. 扩展性设计

### 9.1 水平扩展

- 无状态服务设计
- 负载均衡支持
- 数据库读写分离

### 9.2 模块化设计

- 松耦合架构
- 接口抽象
- 插件机制

## 10. 部署架构

### 10.1 生产环境

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │ App #1  │        │ App #2  │        │ App #3  │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
┌───▼───┐              ┌────▼────┐              ┌───▼───┐
│ Redis │              │PostgreSQL│              │Celery │
│Cluster│              │ Primary  │              │Workers│
└───────┘              │ Replica  │              └───────┘
                       └──────────┘
```

### 10.2 容器化部署

- Docker 容器化
- Kubernetes 编排
- CI/CD 流水线

## 11. 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| 1.0.0 | 2025-01 | 初始版本，核心功能完成 |
| 1.1.0 | 2025-02 | 添加培训模块和反馈系统 |
| 1.2.0 | 2025-03 | 性能优化和 UX 改进 |

---

*本文档最后更新: 2025-01-01*
