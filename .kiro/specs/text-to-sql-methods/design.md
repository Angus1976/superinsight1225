# Design Document: Text-to-SQL Methods (Text-to-SQL 方法)

## Overview

本设计文档描述 Text-to-SQL Methods 模块的架构设计，该模块实现多种自然语言转 SQL 的方法，支持模板填充、LLM 生成、混合方法，以及第三方专业工具对接。

设计原则：
- **方法可插拔**：通过统一接口支持多种方法，便于扩展
- **第三方友好**：提供标准插件接口，支持对接外部专业工具
- **智能切换**：根据场景和数据库类型自动选择最优方法
- **Schema 感知**：自动分析数据库结构，为 LLM 提供准确上下文

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        ConfigUI[Text-to-SQL Config UI]
        TestUI[SQL 测试界面]
        PluginUI[第三方工具管理]
    end
    
    subgraph API["API 层"]
        Router[/api/v1/text-to-sql]
        GenerateAPI[Generate API]
        ConfigAPI[Config API]
        PluginAPI[Plugin API]
    end
    
    subgraph Core["核心层"]
        Switcher[Method Switcher]
        SchemaAnalyzer[Schema Analyzer]
        PluginManager[Plugin Manager]
    end
    
    subgraph Methods["方法层"]
        Template[Template Filler]
        LLM[LLM Generator]
        Hybrid[Hybrid Generator]
        ThirdParty[Third Party Adapter]
    end
    
    subgraph External["外部服务"]
        Ollama[Ollama/LLM]
        DIN[DIN-SQL]
        DAIL[DAIL-SQL]
        Vanna[Vanna.ai]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
        Templates[SQL Templates]
    end
    
    ConfigUI --> Router
    TestUI --> Router
    PluginUI --> Router
    
    Router --> GenerateAPI
    Router --> ConfigAPI
    Router --> PluginAPI
    
    GenerateAPI --> Switcher
    ConfigAPI --> PluginManager
    PluginAPI --> PluginManager
    
    Switcher --> Template
    Switcher --> LLM
    Switcher --> Hybrid
    Switcher --> ThirdParty
    
    LLM --> Ollama
    ThirdParty --> DIN
    ThirdParty --> DAIL
    ThirdParty --> Vanna
    
    SchemaAnalyzer --> DB
    Template --> Templates
    PluginManager --> Cache
```


## Components and Interfaces

### 1. Method Switcher (方法切换器)

**文件**: `src/text-to-sql/switcher.py`

**职责**: 根据配置和场景选择最优的 Text-to-SQL 方法

```python
class MethodSwitcher:
    """Text-to-SQL 方法切换器"""
    
    async def generate_sql(
        self,
        query: str,
        schema: DatabaseSchema,
        method: str = None,  # 可选，覆盖默认方法
        db_type: str = None  # 数据库类型
    ) -> SQLGenerationResult:
        """生成 SQL"""
        pass
    
    def switch_method(self, method: str) -> None:
        """切换默认方法"""
        pass
    
    def get_current_method(self) -> str:
        """获取当前方法"""
        pass
    
    def list_available_methods(self) -> List[MethodInfo]:
        """列出可用方法（包括第三方）"""
        pass
    
    def auto_select_method(self, query: str, db_type: str) -> str:
        """根据场景自动选择方法"""
        pass
```

**接口定义**:

```python
class SQLGenerationResult(BaseModel):
    """SQL 生成结果"""
    sql: str
    method_used: str  # template/llm/hybrid/third_party:{name}
    confidence: float
    execution_time_ms: float
    metadata: Dict[str, Any] = {}

class MethodInfo(BaseModel):
    """方法信息"""
    name: str
    type: str  # builtin/third_party
    description: str
    supported_db_types: List[str]
    is_available: bool
```

### 2. Template Filler (模板填充器)

**文件**: `src/text-to-sql/basic.py`

**职责**: 基于预定义模板进行槽位填充

```python
class TemplateFiller:
    """SQL 模板填充器"""
    
    def __init__(self, templates_path: str):
        self.templates = self._load_templates(templates_path)
    
    def match_template(self, query: str) -> Optional[TemplateMatch]:
        """匹配查询到模板"""
        pass
    
    def fill_template(self, template: SQLTemplate, params: Dict) -> str:
        """填充模板参数"""
        pass
    
    def validate_params(self, params: Dict, param_types: Dict) -> ValidationResult:
        """验证参数类型"""
        pass
    
    def generate(self, query: str, schema: DatabaseSchema) -> SQLGenerationResult:
        """生成 SQL"""
        pass

class SQLTemplate(BaseModel):
    """SQL 模板"""
    id: str
    name: str
    pattern: str  # 正则匹配模式
    template: str  # SQL 模板
    param_types: Dict[str, str]  # 参数类型定义
    category: str  # aggregate/filter/sort/group/join
```

**预定义模板示例**:

```yaml
templates:
  - id: aggregate_count
    name: "统计数量"
    pattern: "(?:统计|查询|获取)(.+)的(?:数量|总数|个数)"
    template: "SELECT COUNT(*) FROM {table} WHERE {condition}"
    param_types:
      table: string
      condition: string
    category: aggregate
    
  - id: filter_by_date
    name: "按日期筛选"
    pattern: "查询(.+)从(.+)到(.+)的(.+)"
    template: "SELECT * FROM {table} WHERE {date_column} BETWEEN '{start_date}' AND '{end_date}'"
    param_types:
      table: string
      date_column: string
      start_date: date
      end_date: date
    category: filter
```

### 3. LLM SQL Generator (LLM 生成器)

**文件**: `src/text-to-sql/llm-based.py`

**职责**: 使用 LLM 生成 SQL

```python
class LLMSQLGenerator:
    """LLM SQL 生成器"""
    
    def __init__(self, llm_switcher: LLMSwitcher):
        self.llm = llm_switcher
        self.max_retries = 3
    
    async def generate(
        self,
        query: str,
        schema: DatabaseSchema,
        framework: str = "langchain"  # langchain/sqlcoder/custom
    ) -> SQLGenerationResult:
        """生成 SQL"""
        pass
    
    def build_prompt(self, query: str, schema: DatabaseSchema) -> str:
        """构建 LLM prompt"""
        pass
    
    def validate_sql(self, sql: str, db_type: str) -> ValidationResult:
        """验证 SQL 语法"""
        pass
    
    async def retry_generate(self, query: str, schema: DatabaseSchema, error: str) -> str:
        """重试生成（带错误反馈）"""
        pass
```

### 4. Hybrid Generator (混合生成器)

**文件**: `src/text-to-sql/hybrid.py`

**职责**: 结合模板和 LLM 的优势

```python
class HybridGenerator:
    """混合 SQL 生成器"""
    
    def __init__(self, template_filler: TemplateFiller, llm_generator: LLMSQLGenerator):
        self.template = template_filler
        self.llm = llm_generator
        self.rules = SQLOptimizationRules()
    
    async def generate(self, query: str, schema: DatabaseSchema) -> SQLGenerationResult:
        """生成 SQL（模板优先，LLM 回退）"""
        # 1. 尝试模板匹配
        template_result = self.template.match_template(query)
        if template_result:
            sql = self.template.fill_template(template_result.template, template_result.params)
            return SQLGenerationResult(sql=sql, method_used="template", confidence=0.95)
        
        # 2. 回退到 LLM
        llm_result = await self.llm.generate(query, schema)
        
        # 3. 规则后处理
        optimized_sql = self.rules.optimize(llm_result.sql)
        
        return SQLGenerationResult(sql=optimized_sql, method_used="hybrid", confidence=llm_result.confidence)
    
    def log_method_usage(self, query: str, method: str) -> None:
        """记录方法使用"""
        pass
```

### 5. Third Party Adapter (第三方工具适配器)

**文件**: `src/text-to-sql/third_party_adapter.py`

**职责**: 对接第三方专业 Text-to-SQL 工具

```python
class ThirdPartyAdapter:
    """第三方工具适配器"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
    
    async def generate(
        self,
        query: str,
        schema: DatabaseSchema,
        tool_name: str
    ) -> SQLGenerationResult:
        """调用第三方工具生成 SQL"""
        plugin = self.plugin_manager.get_plugin(tool_name)
        if not plugin:
            raise PluginNotFoundError(tool_name)
        
        # 转换请求格式
        native_request = plugin.to_native_format(query, schema)
        
        # 调用工具
        native_response = await plugin.call(native_request)
        
        # 转换响应格式
        return plugin.from_native_format(native_response)
    
    async def fallback_to_builtin(self, query: str, schema: DatabaseSchema) -> SQLGenerationResult:
        """回退到内置方法"""
        pass

class PluginInterface(ABC):
    """第三方工具插件接口规范"""
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass
    
    @abstractmethod
    def to_native_format(self, query: str, schema: DatabaseSchema) -> Dict:
        """转换为工具特定格式"""
        pass
    
    @abstractmethod
    async def call(self, request: Dict) -> Dict:
        """调用工具"""
        pass
    
    @abstractmethod
    def from_native_format(self, response: Dict) -> SQLGenerationResult:
        """从工具格式转换为统一格式"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass

class PluginInfo(BaseModel):
    """插件信息"""
    name: str
    version: str
    description: str
    connection_type: str  # rest_api/grpc/local_sdk
    supported_db_types: List[str]
    config_schema: Dict[str, Any]  # JSON Schema
```

### 6. Plugin Manager (插件管理器)

**文件**: `src/text-to-sql/plugin_manager.py`

**职责**: 管理第三方工具插件的注册、配置和生命周期

```python
class PluginManager:
    """插件管理器"""
    
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache
        self.plugins: Dict[str, PluginInterface] = {}
    
    async def register_plugin(self, config: PluginConfig) -> PluginInfo:
        """注册插件"""
        # 验证插件实现了必要接口
        plugin = self._create_plugin(config)
        self._validate_interface(plugin)
        
        # 保存配置
        await self._save_config(config)
        
        # 注册到内存
        self.plugins[config.name] = plugin
        
        return plugin.get_info()
    
    async def unregister_plugin(self, name: str) -> None:
        """注销插件"""
        pass
    
    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """获取插件"""
        pass
    
    async def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件"""
        pass
    
    async def update_plugin_config(self, name: str, config: PluginConfig) -> None:
        """更新插件配置"""
        pass
    
    async def enable_plugin(self, name: str) -> None:
        """启用插件"""
        pass
    
    async def disable_plugin(self, name: str) -> None:
        """禁用插件"""
        pass
    
    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有插件健康状态"""
        pass

class PluginConfig(BaseModel):
    """插件配置"""
    name: str
    connection_type: str  # rest_api/grpc/local_sdk
    endpoint: Optional[str] = None  # REST API/gRPC 端点
    api_key: Optional[str] = None
    timeout: int = 30
    enabled: bool = True
    extra_config: Dict[str, Any] = {}
```


### 7. Schema Analyzer (Schema 分析器)

**文件**: `src/text-to-sql/schema_analyzer.py`

**职责**: 分析数据库 Schema，为 LLM 提供上下文

```python
class SchemaAnalyzer:
    """数据库 Schema 分析器"""
    
    async def analyze(self, connection: DatabaseConnection) -> DatabaseSchema:
        """分析数据库 Schema"""
        pass
    
    async def incremental_update(self, schema: DatabaseSchema, changes: List[SchemaChange]) -> DatabaseSchema:
        """增量更新 Schema"""
        pass
    
    def to_llm_context(self, schema: DatabaseSchema, max_tables: int = 50) -> str:
        """生成 LLM 友好的 Schema 描述"""
        pass
    
    def filter_relevant_tables(self, schema: DatabaseSchema, query: str, max_tables: int = 10) -> List[TableInfo]:
        """筛选相关表"""
        pass

class DatabaseSchema(BaseModel):
    """数据库 Schema"""
    tables: List[TableInfo]
    relationships: List[Relationship]
    updated_at: datetime

class TableInfo(BaseModel):
    """表信息"""
    name: str
    columns: List[ColumnInfo]
    primary_key: List[str]
    indexes: List[IndexInfo]
    row_count: Optional[int] = None

class ColumnInfo(BaseModel):
    """列信息"""
    name: str
    data_type: str
    nullable: bool
    default: Optional[str] = None
    is_foreign_key: bool = False
    references: Optional[str] = None  # table.column
```

### 8. API Router (API 路由)

**文件**: `src/api/text_to_sql.py`

```python
router = APIRouter(prefix="/api/v1/text-to-sql", tags=["Text-to-SQL"])

@router.post("/generate")
async def generate_sql(request: GenerateSQLRequest) -> SQLGenerationResult:
    """生成 SQL"""
    pass

@router.get("/methods")
async def list_methods() -> List[MethodInfo]:
    """列出可用方法"""
    pass

@router.get("/config")
async def get_config() -> TextToSQLConfig:
    """获取配置"""
    pass

@router.put("/config")
async def update_config(config: TextToSQLConfig) -> TextToSQLConfig:
    """更新配置"""
    pass

@router.post("/test")
async def test_generate(request: TestGenerateRequest) -> SQLGenerationResult:
    """测试生成 SQL"""
    pass

# 插件管理 API
@router.get("/plugins")
async def list_plugins() -> List[PluginInfo]:
    """列出所有插件"""
    pass

@router.post("/plugins")
async def register_plugin(config: PluginConfig) -> PluginInfo:
    """注册插件"""
    pass

@router.put("/plugins/{name}")
async def update_plugin(name: str, config: PluginConfig) -> PluginInfo:
    """更新插件配置"""
    pass

@router.delete("/plugins/{name}")
async def unregister_plugin(name: str) -> None:
    """注销插件"""
    pass

@router.post("/plugins/{name}/enable")
async def enable_plugin(name: str) -> None:
    """启用插件"""
    pass

@router.post("/plugins/{name}/disable")
async def disable_plugin(name: str) -> None:
    """禁用插件"""
    pass

@router.get("/plugins/health")
async def plugins_health() -> Dict[str, bool]:
    """检查插件健康状态"""
    pass
```

## Data Models

### 数据库模型

```python
class TextToSQLConfiguration(Base):
    """Text-to-SQL 配置表"""
    __tablename__ = "text_to_sql_configurations"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    default_method = Column(String(50), default="hybrid")
    config_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ThirdPartyPlugin(Base):
    """第三方插件表"""
    __tablename__ = "third_party_plugins"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    name = Column(String(100), nullable=False, unique=True)
    connection_type = Column(String(50), nullable=False)
    endpoint = Column(String(500), nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    timeout = Column(Integer, default=30)
    enabled = Column(Boolean, default=True)
    extra_config = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SQLGenerationLog(Base):
    """SQL 生成日志表"""
    __tablename__ = "sql_generation_logs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=False)
    method_used = Column(String(100), nullable=False)
    confidence = Column(Float, default=0)
    execution_time_ms = Column(Float, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do.*

### Property 1: SQL 语法正确性

*For any* 生成的 SQL 语句（无论使用哪种方法），都应通过 SQL 语法解析器验证，不包含语法错误。

**Validates: Requirements 1.2, 2.4**

### Property 2: 方法路由正确性

*For any* 配置的默认方法和调用时指定的方法，Method Switcher 应正确路由到对应的生成器，且指定方法优先于默认方法。

**Validates: Requirements 4.1, 4.2**

### Property 3: 混合方法优先级

*For any* 查询，Hybrid Generator 应首先尝试模板匹配，仅在模板匹配失败时才回退到 LLM 生成。

**Validates: Requirements 3.1, 3.2**

### Property 4: 第三方工具格式转换往返

*For any* 有效的查询和 Schema，经过 Third Party Adapter 转换为工具格式后，响应应能正确转换回统一格式，且不丢失关键信息（SQL、置信度）。

**Validates: Requirements 6.4, 6.5**

### Property 5: 参数类型验证

*For any* 模板参数，Template Filler 应正确验证参数类型（数字、字符串、日期），拒绝类型不匹配的参数。

**Validates: Requirements 1.5**

### Property 6: Schema 信息完整性

*For any* 数据库连接，Schema Analyzer 提取的信息应包含所有必要字段：表名、列名、数据类型、主键、外键、索引。

**Validates: Requirements 5.2**

### Property 7: 插件接口验证

*For any* 注册的第三方插件，Plugin Manager 应验证其实现了 PluginInterface 的所有必要方法，拒绝不完整的实现。

**Validates: Requirements 6.2**

### Property 8: 自动回退机制

*For any* 第三方工具调用失败（超时、错误、不可用），系统应自动回退到内置方法，不返回空结果。

**Validates: Requirements 6.7**

## Error Handling

### 错误分类

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| 模板匹配失败 | T2S_TEMPLATE_NOT_FOUND | 回退到 LLM 方法 |
| SQL 语法错误 | T2S_INVALID_SQL | 重试生成（最多 3 次） |
| LLM 调用失败 | T2S_LLM_ERROR | 返回错误，建议使用模板 |
| 插件不可用 | T2S_PLUGIN_UNAVAILABLE | 回退到内置方法 |
| Schema 分析失败 | T2S_SCHEMA_ERROR | 返回错误，提示检查连接 |
| 参数类型错误 | T2S_INVALID_PARAM | 返回验证错误详情 |

## Testing Strategy

### 单元测试

- 测试模板匹配逻辑
- 测试参数类型验证
- 测试 SQL 语法验证
- 测试方法路由逻辑
- 测试插件接口验证

### 属性测试

使用 Hypothesis 库：

```python
@given(st.text(min_size=1))
def test_sql_syntax_validity(query: str):
    """Property 1: SQL 语法正确性"""
    result = method_switcher.generate_sql(query, schema)
    assert is_valid_sql(result.sql)

@given(st.sampled_from(['template', 'llm', 'hybrid']))
def test_method_routing(method: str):
    """Property 2: 方法路由正确性"""
    result = method_switcher.generate_sql(query, schema, method=method)
    assert result.method_used.startswith(method) or result.method_used == "hybrid"
```

### 集成测试

- 测试完整的查询 → SQL 生成流程
- 测试第三方工具对接
- 测试回退机制
