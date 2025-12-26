# 知识图谱系统实施计划

## 概述

根据 `tasks.md` 中的任务计划，为 SuperInsight 平台实现知识图谱集成系统。本计划将分阶段实施，每个阶段包含多个可独立开发和测试的模块。

## 项目现状分析

### 现有资源
- **知识模块** (`src/knowledge/`): 内存知识库、规则引擎、案例库（可作为参考和部分复用）
- **配置系统** (`src/config/settings.py`): 完善的配置管理框架
- **数据库层** (`src/database/`): SQLAlchemy ORM、连接池、迁移
- **API 框架** (`src/api/`): FastAPI 路由和中间件
- **AI 模块** (`src/ai/`): 多模型支持和批处理框架

### 技术栈
- Python 3.11+
- FastAPI + SQLAlchemy + PostgreSQL
- Redis 缓存
- Docker Compose 部署

## 实施架构

### 新增目录结构
```
src/knowledge_graph/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── graph_db.py           # 图数据库接口
│   ├── models.py             # 图数据模型
│   └── config.py             # 知识图谱配置
├── nlp/
│   ├── __init__.py
│   ├── entity_extractor.py   # 实体抽取
│   ├── relation_extractor.py # 关系抽取
│   └── text_processor.py     # 文本预处理
├── mining/
│   ├── __init__.py
│   ├── process_miner.py      # 流程挖掘
│   ├── pattern_detector.py   # 模式检测
│   └── behavior_analyzer.py  # 行为分析
├── visualization/
│   ├── __init__.py
│   ├── graph_renderer.py     # 图渲染数据
│   └── layout_engine.py      # 布局算法
├── query/
│   ├── __init__.py
│   ├── nl_query_engine.py    # 自然语言查询
│   ├── cypher_generator.py   # Cypher 查询生成
│   └── result_formatter.py   # 结果格式化
├── reasoning/
│   ├── __init__.py
│   ├── rule_engine.py        # 规则推理
│   └── ml_inference.py       # 机器学习推理
├── fusion/
│   ├── __init__.py
│   ├── entity_alignment.py   # 实体对齐
│   └── knowledge_merger.py   # 知识融合
├── algorithms/
│   ├── __init__.py
│   ├── centrality.py         # 中心性算法
│   ├── community.py          # 社区检测
│   ├── embedding.py          # 图嵌入
│   └── prediction.py         # 预测算法
└── api/
    ├── __init__.py
    └── knowledge_graph_api.py # REST API
```

## 分阶段实施计划

---

### Phase 1: 图数据库和基础架构

#### 1.1 Neo4j 配置和连接 (`core/graph_db.py`)
**任务内容**:
- 添加 Neo4j 配置到 `src/config/settings.py`
- 实现 Neo4j 连接管理器（连接池、事务、重试）
- 实现 PostgreSQL AGE 备用后端支持
- 添加图数据库健康检查

**关键代码**:
```python
class GraphDatabaseSettings:
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    use_age_backend: bool = False  # 使用 PostgreSQL AGE
```

#### 1.2 图数据模型 (`core/models.py`)
**任务内容**:
- 定义 `Entity` 节点模型（属性、类型、别名）
- 定义 `Relation` 边模型（类型、权重、置信度）
- 定义 `GraphSchema` 模式定义
- 添加版本控制和审计字段

**关键模型**:
```python
class Entity(BaseModel):
    id: UUID
    entity_type: EntityType
    name: str
    properties: Dict[str, Any]
    aliases: List[str]
    confidence: float
    source: str

class Relation(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    relation_type: RelationType
    properties: Dict[str, Any]
    weight: float
    confidence: float
```

#### 1.3 图操作服务 (`core/graph_service.py`)
**任务内容**:
- 实现节点 CRUD 操作
- 实现边 CRUD 操作
- 实现批量导入/导出
- 添加图遍历和查询接口

---

### Phase 2: NLP 处理和实体抽取

#### 2.1 文本预处理 (`nlp/text_processor.py`)
**任务内容**:
- 中文分词（jieba）
- 词性标注
- 命名实体预处理
- 文本清洗和规范化

#### 2.2 实体抽取 (`nlp/entity_extractor.py`)
**任务内容**:
- 集成 spaCy 中文模型
- 集成 BERT NER 模型（可选）
- 实现规则匹配实体抽取
- 实现多模型融合和投票
- 添加实体置信度评估

**关键接口**:
```python
class EntityExtractor:
    async def extract_entities(self, text: str) -> List[ExtractedEntity]
    async def extract_batch(self, texts: List[str]) -> List[List[ExtractedEntity]]
```

#### 2.3 关系抽取 (`nlp/relation_extractor.py`)
**任务内容**:
- 依存句法分析
- 基于模式的关系抽取
- 关系类型分类
- 关系验证和质量控制

---

### Phase 3: 流程挖掘和模式发现

#### 3.1 流程挖掘引擎 (`mining/process_miner.py`)
**任务内容**:
- 从标注数据构建事件日志
- 集成 PM4Py 流程发现算法
- 生成 Petri 网模型
- 计算流程符合度

#### 3.2 模式检测 (`mining/pattern_detector.py`)
**任务内容**:
- 时间序列异常检测
- 序列模式挖掘
- 质量问题模式识别

#### 3.3 行为分析 (`mining/behavior_analyzer.py`)
**任务内容**:
- 用户行为特征提取
- 用户能力画像
- 协作模式分析
- 质量影响因素分析

---

### Phase 4: 知识图谱可视化

#### 4.1 图渲染服务 (`visualization/graph_renderer.py`)
**任务内容**:
- 生成前端可用的图数据格式（JSON）
- 支持节点和边的样式配置
- 实现图数据分页和懒加载
- 支持大规模图的采样

#### 4.2 布局算法 (`visualization/layout_engine.py`)
**任务内容**:
- 力导向布局
- 层次布局
- 圆形布局
- 自定义布局参数

**输出格式**:
```python
class GraphVisualization(BaseModel):
    nodes: List[VisNode]
    edges: List[VisEdge]
    layout: LayoutConfig
    metadata: Dict[str, Any]
```

---

### Phase 5: 智能查询和推理

#### 5.1 自然语言查询 (`query/nl_query_engine.py`)
**任务内容**:
- 查询意图识别
- 实体和关系识别
- 查询参数提取

#### 5.2 Cypher 生成 (`query/cypher_generator.py`)
**任务内容**:
- 自然语言到 Cypher 转换
- 查询优化
- 查询模板管理

#### 5.3 推理引擎 (`reasoning/rule_engine.py`)
**任务内容**:
- 规则定义和管理
- 规则推理执行
- 推理链追踪
- 结果验证

#### 5.4 机器学习推理 (`reasoning/ml_inference.py`)
**任务内容**:
- 链接预测
- 实体分类
- 关系预测

---

### Phase 6: 知识融合和更新

#### 6.1 实体对齐 (`fusion/entity_alignment.py`)
**任务内容**:
- 基于名称的实体匹配
- 基于属性的实体对齐
- 对齐结果验证

#### 6.2 知识融合 (`fusion/knowledge_merger.py`)
**任务内容**:
- 多源知识合并
- 冲突检测和解决
- 知识质量评估

---

### Phase 7: 图算法和分析

#### 7.1 中心性算法 (`algorithms/centrality.py`)
**任务内容**:
- 度中心性
- 介数中心性
- PageRank
- 特征向量中心性

#### 7.2 社区检测 (`algorithms/community.py`)
**任务内容**:
- Louvain 算法
- 标签传播
- 层次聚类

#### 7.3 图嵌入 (`algorithms/embedding.py`)
**任务内容**:
- Node2Vec
- 图注意力网络（可选）

#### 7.4 预测算法 (`algorithms/prediction.py`)
**任务内容**:
- 链接预测
- 节点分类
- 推荐算法

---

### Phase 8: API 和系统集成

#### 8.1 REST API (`api/knowledge_graph_api.py`)
**任务内容**:
- 实体 CRUD API
- 关系 CRUD API
- 图查询 API
- 可视化数据 API
- 分析结果 API

**API 端点**:
```
POST   /api/v1/knowledge-graph/entities
GET    /api/v1/knowledge-graph/entities/{id}
PUT    /api/v1/knowledge-graph/entities/{id}
DELETE /api/v1/knowledge-graph/entities/{id}

POST   /api/v1/knowledge-graph/relations
GET    /api/v1/knowledge-graph/relations/{id}

POST   /api/v1/knowledge-graph/query
POST   /api/v1/knowledge-graph/query/natural-language
GET    /api/v1/knowledge-graph/visualize
POST   /api/v1/knowledge-graph/analyze/centrality
POST   /api/v1/knowledge-graph/analyze/community
```

#### 8.2 系统集成
**任务内容**:
- 注册到主应用路由
- 集成现有认证系统
- 添加多租户支持
- 实现权限控制

---

## 依赖更新

### requirements.txt 新增
```
# 图数据库
neo4j>=5.0.0
networkx>=3.0

# NLP
spacy>=3.5.0
jieba>=0.42.1
transformers>=4.30.0

# 流程挖掘
pm4py>=2.7.0

# 可选：图嵌入
# node2vec>=0.4.0
# torch-geometric>=2.3.0
```

### Docker 更新
```yaml
# docker-compose.yml 新增
neo4j:
  image: neo4j:5-community
  ports:
    - "7474:7474"
    - "7687:7687"
  environment:
    NEO4J_AUTH: neo4j/password
  volumes:
    - neo4j_data:/data
```

---

## 实施顺序建议

由于任务量较大，建议按以下优先级实施：

### 优先级 1（核心功能）
1. Phase 1: 图数据库基础架构
2. Phase 2.2: 实体抽取
3. Phase 8.1: 基础 REST API

### 优先级 2（增强功能）
4. Phase 2.3: 关系抽取
5. Phase 4: 可视化
6. Phase 5.1-5.2: 查询引擎

### 优先级 3（高级功能）
7. Phase 3: 流程挖掘
8. Phase 5.3-5.4: 推理引擎
9. Phase 6: 知识融合
10. Phase 7: 图算法

---

## 用户确认

已确认的技术选型：

1. **图数据库**: Neo4j (原生图数据库，性能最佳)
2. **NLP 模型**: spaCy + jieba (轻量级，适合生产环境)
3. **实施范围**: 优先级1核心功能 (图数据库 + 实体抽取 + 基础API)

## 当前实施任务

### 阶段 1: 核心功能实施 (已完成)

- [x] 1.1 添加 Neo4j 配置到 settings.py
- [x] 1.2 实现图数据库连接管理 (core/graph_db.py)
- [x] 1.3 定义图数据模型 (core/models.py)
- [x] 1.4 实现文本预处理器 (nlp/text_processor.py)
- [x] 1.5 实现实体抽取器 (nlp/entity_extractor.py)
- [x] 1.6 实现关系抽取器 (nlp/relation_extractor.py)
- [x] 1.7 创建知识图谱 REST API (api/knowledge_graph_api.py)
- [x] 1.8 注册到主应用路由
- [x] 1.9 更新 requirements.txt 和 docker-compose.yml

## 已创建的文件

```
src/knowledge_graph/
├── __init__.py                    # 模块入口
├── core/
│   ├── __init__.py
│   ├── models.py                  # 数据模型 (Entity, Relation, EntityType, RelationType等)
│   └── graph_db.py                # Neo4j 图数据库连接管理
├── nlp/
│   ├── __init__.py
│   ├── text_processor.py          # 中文文本预处理 (分词、词性标注)
│   ├── entity_extractor.py        # 实体抽取 (spaCy + 规则匹配)
│   └── relation_extractor.py      # 关系抽取 (模式匹配 + 依存分析)
├── api/
│   ├── __init__.py
│   └── knowledge_graph_api.py     # REST API 端点
└── (其他子模块目录已创建，待后续实施)
```

## API 端点

已实现的 REST API 端点 (`/api/v1/knowledge-graph`):

### 实体操作
- `POST /entities` - 创建实体
- `GET /entities/{id}` - 获取实体
- `PUT /entities/{id}` - 更新实体
- `DELETE /entities/{id}` - 删除实体
- `GET /entities` - 搜索实体

### 关系操作
- `POST /relations` - 创建关系
- `GET /relations/{id}` - 获取关系
- `GET /entities/{id}/relations` - 获取实体的关系
- `DELETE /relations/{id}` - 删除关系

### 文本抽取
- `POST /extract` - 从文本抽取实体和关系
- `POST /extract/entities` - 仅抽取实体

### 图查询
- `GET /neighbors/{id}` - 获取邻居节点
- `GET /path` - 查找最短路径
- `POST /query/cypher` - 执行 Cypher 查询

### 统计和健康
- `GET /statistics` - 获取图统计信息
- `GET /health` - 健康检查

### 批量操作
- `POST /bulk/entities` - 批量创建实体
- `POST /bulk/relations` - 批量创建关系
