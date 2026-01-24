# 本体专家协作开发者文档

## 架构概述

本体专家协作模块采用分层架构：

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  - Components: Expert, Template, Collaboration, etc.    │
│  - State: Zustand                                        │
│  - API: TanStack Query                                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                   │
│  - REST Endpoints                                        │
│  - WebSocket Handlers                                    │
│  - Authentication/Authorization                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                          │
│  - ExpertService                                         │
│  - TemplateService                                       │
│  - CollaborationService                                  │
│  - ApprovalService                                       │
│  - ValidationService                                     │
│  - ImpactAnalysisService                                │
│  - I18nService                                           │
│  - ComplianceService                                     │
│  - BestPracticeService                                   │
│  - AuditService                                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                             │
│  - PostgreSQL (主数据)                                   │
│  - Neo4j (图数据)                                        │
│  - Redis (缓存/Pub-Sub)                                  │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
src/
├── api/
│   ├── ontology_expert_collaboration.py  # REST API
│   ├── ontology_collaboration_websocket.py  # WebSocket
│   └── ontology_health.py  # 健康检查
├── collaboration/
│   ├── expert_service.py  # 专家管理
│   ├── template_service.py  # 模板管理
│   ├── collaboration_service.py  # 协作会话
│   ├── approval_service.py  # 审批工作流
│   ├── validation_service.py  # 验证规则
│   ├── impact_analysis_service.py  # 影响分析
│   ├── ontology_i18n_service.py  # 国际化
│   ├── compliance_template_service.py  # 合规模板
│   ├── best_practice_service.py  # 最佳实践
│   ├── audit_service.py  # 审计日志
│   ├── knowledge_contribution_service.py  # 知识贡献
│   ├── performance_cache.py  # 缓存优化
│   ├── query_optimizer.py  # 查询优化
│   ├── graph_query_optimizer.py  # 图查询优化
│   ├── websocket_optimizer.py  # WebSocket优化
│   └── monitoring.py  # 监控
├── ontology/
│   └── expert_collaboration_integration.py  # 本体集成
├── knowledge_graph/
│   └── collaboration_integration.py  # 知识图谱集成
├── i18n/
│   └── ontology_collaboration_i18n.py  # 翻译
└── security/
    └── ontology_collaboration_security.py  # 安全
```

## 核心服务

### ExpertService

专家管理服务，提供：
- CRUD 操作
- 专家推荐算法
- 贡献指标计算

```python
from src.collaboration.expert_service import ExpertService

service = ExpertService()

# 创建专家
expert = await service.create_expert(
    name="张三",
    email="zhangsan@example.com",
    expertise_areas=["金融", "法律"],
)

# 推荐专家
recommendations = await service.recommend_experts(
    ontology_area="金融",
    limit=10,
)
```

### CollaborationService

实时协作服务，提供：
- 会话管理
- 元素锁定
- 冲突检测
- 版本历史

```python
from src.collaboration.collaboration_service import CollaborationService

service = CollaborationService()

# 创建会话
session = await service.create_session(
    ontology_id="ontology-uuid",
    created_by="user-uuid",
)

# 锁定元素
lock = await service.lock_element(
    session_id=session.id,
    element_id="entity-uuid",
    user_id="user-uuid",
)
```

### ApprovalService

审批工作流服务，提供：
- 审批链管理
- 变更请求路由
- 审批操作

```python
from src.collaboration.approval_service import ApprovalService

service = ApprovalService()

# 创建审批链
chain = await service.create_approval_chain(
    name="金融本体审批链",
    ontology_area="金融",
    levels=[...],
)

# 审批
await service.approve(
    change_request_id="request-uuid",
    approver_id="approver-uuid",
    reason="审批通过",
)
```

## 数据库设计

### PostgreSQL 表

```sql
-- 专家表
CREATE TABLE expert_profiles (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    expertise_areas JSONB,
    languages JSONB,
    certifications JSONB,
    quality_score FLOAT DEFAULT 0,
    contribution_count INT DEFAULT 0,
    is_available BOOLEAN DEFAULT TRUE,
    tenant_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 模板表
CREATE TABLE ontology_templates (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    version VARCHAR(50),
    entity_types JSONB,
    relation_types JSONB,
    validation_rules JSONB,
    metadata JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 变更请求表
CREATE TABLE change_requests (
    id UUID PRIMARY KEY,
    ontology_id UUID NOT NULL,
    requester_id UUID NOT NULL,
    ontology_area VARCHAR(100),
    change_type VARCHAR(50),
    before_state JSONB,
    after_state JSONB,
    status VARCHAR(50) DEFAULT 'draft',
    current_level INT DEFAULT 0,
    deadline TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 审批记录表
CREATE TABLE approval_records (
    id UUID PRIMARY KEY,
    change_request_id UUID REFERENCES change_requests(id),
    approver_id UUID NOT NULL,
    level INT NOT NULL,
    action VARCHAR(50),
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 审计日志表
CREATE TABLE ontology_audit_logs (
    id UUID PRIMARY KEY,
    ontology_id UUID NOT NULL,
    user_id UUID NOT NULL,
    change_type VARCHAR(50),
    affected_elements JSONB,
    before_state JSONB,
    after_state JSONB,
    description TEXT,
    signature VARCHAR(255),
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### Neo4j 图模式

```cypher
// 节点类型
(:EntityType {id, name, ontology_id, description})
(:RelationType {id, name, source_type, target_type})
(:Expert {id, name, expertise_area})
(:Template {id, name, industry})
(:Project {id, name})

// 关系类型
(e1:EntityType)-[:DEPENDS_ON]->(e2:EntityType)
(e1:EntityType)-[:USED_BY]->(p:Project)
(e:Expert)-[:CONTRIBUTED_TO]->(et:EntityType)
(t:Template)-[:DERIVED_FROM]->(t2:Template)
```

## WebSocket 协议

### 连接

```javascript
const ws = new WebSocket(
  `ws://host/api/v1/ontology/collaboration/sessions/${sessionId}/ws`
);

ws.onopen = () => {
  // 发送认证
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'jwt-token'
  }));
};
```

### 消息类型

| 类型 | 方向 | 描述 |
|------|------|------|
| auth | C→S | 认证 |
| lock_element | C→S | 锁定元素 |
| unlock_element | C→S | 解锁元素 |
| edit_element | C→S | 编辑元素 |
| element_locked | S→C | 元素已锁定 |
| element_unlocked | S→C | 元素已解锁 |
| element_edited | S→C | 元素已编辑 |
| presence_update | S→C | 在线状态更新 |
| conflict_detected | S→C | 检测到冲突 |

## 性能优化

### 缓存策略

```python
from src.collaboration.performance_cache import (
    get_collaboration_cache_service,
    CacheType,
)

cache = get_collaboration_cache_service(use_redis=True)

# 缓存模板
await cache.set_template(template_id, template_data)

# 获取缓存
template = await cache.get_template(template_id)

# 失效缓存
await cache.invalidate_template(template_id)
```

### 查询优化

```python
from src.collaboration.query_optimizer import (
    get_query_optimizer,
    PaginationParams,
)

optimizer = get_query_optimizer()

# 分页
params = PaginationParams(page=1, page_size=20)
result = optimizer.paginate(items, params)

# JSONB 查询
sql, params = optimizer.jsonb_contains_query(
    "metadata", "industry", "金融"
)
```

### 图查询优化

```python
from src.collaboration.graph_query_optimizer import (
    get_graph_query_optimizer,
)

optimizer = get_graph_query_optimizer()

# 依赖查询
cypher, params = optimizer.build_dependency_query(
    element_id="entity-uuid",
    max_depth=3,
)

# 影响分析查询
cypher, params = optimizer.build_impact_analysis_query(
    element_id="entity-uuid",
    change_type="delete",
)
```

## 监控

### Prometheus 指标

```python
from src.collaboration.monitoring import (
    get_metrics_collector,
    track_request,
)

# 使用装饰器
@track_request("/api/v1/experts", "POST")
async def create_expert(...):
    ...

# 手动记录
metrics = get_metrics_collector()
await metrics.inc_counter(
    "ontology_api_requests_total",
    labels={"endpoint": "/experts", "method": "POST"},
)
```

### 结构化日志

```python
from src.collaboration.monitoring import get_structured_logger

logger = get_structured_logger()

logger.info(
    "Expert created",
    user_id="user-uuid",
    extra={"expert_id": "expert-uuid"},
)
```

### 健康检查

```python
from src.collaboration.monitoring import get_health_checker

checker = get_health_checker()

# 注册自定义检查
checker.register_check("custom", custom_check_func)

# 执行检查
result = await checker.check_all()
```

## 安全

### 权限检查

```python
from src.security.ontology_collaboration_security import (
    get_ontology_security_service,
    OntologyPermission,
)

security = get_ontology_security_service()

# 检查权限
has_permission = await security.check_permission(
    user_id="user-uuid",
    permission=OntologyPermission.EXPERT_CREATE,
)

# 检查专业领域授权
has_expertise = await security.check_expertise_authorization(
    user_id="user-uuid",
    ontology_area="金融",
)
```

### 审计日志

```python
from src.collaboration.audit_service import AuditService

audit = AuditService()

# 记录变更
await audit.log_change(
    ontology_id="ontology-uuid",
    user_id="user-uuid",
    change_type="CREATE",
    affected_elements=["entity-uuid"],
    before_state=None,
    after_state={"name": "新实体"},
)

# 验证完整性
result = await audit.verify_integrity(ontology_id="ontology-uuid")
```

## 测试

### 单元测试

```bash
pytest tests/unit/test_expert_service.py -v
```

### 属性测试

```bash
pytest tests/property/test_expert_service_properties.py -v
```

### 集成测试

```bash
pytest tests/integration/test_ontology_expert_collaboration_api.py -v
```

## 部署

### 环境变量

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379
NEO4J_URI=bolt://host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 缓存
CACHE_USE_REDIS=true
CACHE_TTL_TEMPLATE=3600
CACHE_TTL_VALIDATION=1800

# WebSocket
WS_USE_REDIS_PUBSUB=true
WS_BATCH_SIZE=10
WS_BATCH_INTERVAL_MS=100
```

### Docker

```yaml
services:
  api:
    image: superinsight-api
    environment:
      - DATABASE_URL=...
      - REDIS_URL=...
    ports:
      - "8000:8000"
```

## 扩展

### 添加新服务

1. 在 `src/collaboration/` 创建服务文件
2. 实现服务类
3. 在 `__init__.py` 导出
4. 创建 API 端点
5. 编写测试

### 添加新验证规则

```python
from src.collaboration.validation_service import ValidationService

service = ValidationService()

await service.create_rule(
    name="自定义规则",
    entity_type="企业",
    region="CN",
    industry="金融",
    validation_logic="len(value) == 18",
    error_message_key="error.invalid_length",
)
```

### 添加新合规模板

```python
from src.collaboration.compliance_template_service import (
    ComplianceTemplateService,
)

service = ComplianceTemplateService()

await service.create_template(
    name="新法规模板",
    regulation="新法规名称",
    classification_rules=[...],
    validation_rules=[...],
)
```
