# Design Document: Admin Configuration (管理员配置)

## Overview

本设计文档描述 Admin Configuration 模块的架构设计，该模块实现平台管理员的可视化配置界面，包括仪表盘、LLM 配置、数据库连接、同步策略、SQL 构建器等功能。

设计原则：
- **统一入口**：通过管理员仪表盘提供所有配置功能的统一入口
- **实时验证**：配置修改时实时验证有效性，减少错误
- **安全优先**：敏感信息加密存储和脱敏显示
- **可追溯**：所有配置变更记录历史，支持回滚

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        Dashboard[Admin Dashboard]
        LLMConfig[LLM Config Panel]
        DBConfig[DB Config Panel]
        SyncConfig[Sync Strategy Panel]
        SQLBuilder[SQL Builder]
        History[Config History]
        ThirdParty[Third Party Config]
    end
    
    subgraph API["API 层"]
        AdminRouter[/api/v1/admin]
        ConfigAPI[Config API]
        HistoryAPI[History API]
        ValidationAPI[Validation API]
    end
    
    subgraph Core["核心层"]
        ConfigManager[Config Manager]
        Validator[Config Validator]
        HistoryTracker[History Tracker]
        Encryptor[Credential Encryptor]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
        Secrets[Secrets Store]
    end
    
    Dashboard --> AdminRouter
    LLMConfig --> AdminRouter
    DBConfig --> AdminRouter
    SyncConfig --> AdminRouter
    SQLBuilder --> AdminRouter
    History --> AdminRouter
    ThirdParty --> AdminRouter
    
    AdminRouter --> ConfigAPI
    AdminRouter --> HistoryAPI
    AdminRouter --> ValidationAPI
    
    ConfigAPI --> ConfigManager
    HistoryAPI --> HistoryTracker
    ValidationAPI --> Validator
    
    ConfigManager --> DB
    ConfigManager --> Cache
    ConfigManager --> Encryptor
    Encryptor --> Secrets
    HistoryTracker --> DB
```


## Components and Interfaces

### 1. Config Manager (配置管理器)

**文件**: `src/admin/config_manager.py`

**职责**: 统一管理所有配置的 CRUD 操作

```python
class ConfigManager:
    """配置管理器"""
    
    def __init__(self, db: AsyncSession, cache: Redis, encryptor: CredentialEncryptor):
        self.db = db
        self.cache = cache
        self.encryptor = encryptor
    
    async def get_config(self, config_type: ConfigType, tenant_id: str = None) -> Dict:
        """获取配置"""
        pass
    
    async def save_config(self, config_type: ConfigType, config: Dict, user_id: str) -> Dict:
        """保存配置（自动记录历史）"""
        pass
    
    async def validate_config(self, config_type: ConfigType, config: Dict) -> ValidationResult:
        """验证配置"""
        pass
    
    async def test_connection(self, config_type: ConfigType, config: Dict) -> ConnectionTestResult:
        """测试连接"""
        pass

class ConfigType(str, Enum):
    LLM = "llm"
    DATABASE = "database"
    SYNC_STRATEGY = "sync_strategy"
    THIRD_PARTY = "third_party"
```

### 2. Config Validator (配置验证器)

**文件**: `src/admin/config_validator.py`

**职责**: 验证各类配置的有效性

```python
class ConfigValidator:
    """配置验证器"""
    
    def validate_llm_config(self, config: LLMConfig) -> ValidationResult:
        """验证 LLM 配置"""
        pass
    
    def validate_db_config(self, config: DBConfig) -> ValidationResult:
        """验证数据库配置"""
        pass
    
    def validate_sync_config(self, config: SyncConfig) -> ValidationResult:
        """验证同步策略配置"""
        pass
    
    async def test_db_connection(self, config: DBConfig) -> ConnectionTestResult:
        """测试数据库连接"""
        pass
    
    async def verify_readonly_permission(self, config: DBConfig) -> bool:
        """验证只读权限"""
        pass

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationError] = []
    warnings: List[str] = []

class ConnectionTestResult(BaseModel):
    success: bool
    latency_ms: float
    error_message: Optional[str] = None
```

### 3. History Tracker (历史追踪器)

**文件**: `src/admin/history_tracker.py`

**职责**: 记录配置变更历史，支持回滚

```python
class HistoryTracker:
    """配置历史追踪器"""
    
    async def record_change(
        self,
        config_type: ConfigType,
        old_value: Dict,
        new_value: Dict,
        user_id: str,
        tenant_id: str = None
    ) -> ConfigHistory:
        """记录配置变更"""
        pass
    
    async def get_history(
        self,
        config_type: ConfigType = None,
        start_time: datetime = None,
        end_time: datetime = None,
        user_id: str = None
    ) -> List[ConfigHistory]:
        """获取变更历史"""
        pass
    
    async def get_diff(self, history_id: str) -> ConfigDiff:
        """获取配置差异"""
        pass
    
    async def rollback(self, history_id: str, user_id: str) -> Dict:
        """回滚到指定版本"""
        pass

class ConfigHistory(BaseModel):
    id: str
    config_type: ConfigType
    old_value: Dict
    new_value: Dict
    user_id: str
    user_name: str
    tenant_id: Optional[str]
    created_at: datetime

class ConfigDiff(BaseModel):
    added: Dict
    removed: Dict
    modified: Dict
```

### 4. Credential Encryptor (凭证加密器)

**文件**: `src/admin/credential_encryptor.py`

**职责**: 加密存储和脱敏显示敏感信息

```python
class CredentialEncryptor:
    """凭证加密器"""
    
    def __init__(self, encryption_key: str):
        self.fernet = Fernet(encryption_key)
    
    def encrypt(self, plaintext: str) -> str:
        """加密"""
        pass
    
    def decrypt(self, ciphertext: str) -> str:
        """解密"""
        pass
    
    def mask(self, value: str, visible_chars: int = 4) -> str:
        """脱敏显示（只显示前后 N 位）"""
        if len(value) <= visible_chars * 2:
            return '*' * len(value)
        return value[:visible_chars] + '*' * (len(value) - visible_chars * 2) + value[-visible_chars:]
    
    def is_encrypted(self, value: str) -> bool:
        """检查是否已加密"""
        pass
```

### 5. SQL Builder Service (SQL 构建服务)

**文件**: `src/admin/sql_builder.py`

**职责**: 可视化 SQL 构建

```python
class SQLBuilderService:
    """SQL 构建服务"""
    
    async def get_schema(self, db_config_id: str) -> DatabaseSchema:
        """获取数据库 Schema"""
        pass
    
    def build_sql(self, query_config: QueryConfig) -> str:
        """根据配置构建 SQL"""
        pass
    
    def validate_sql(self, sql: str, db_type: str) -> ValidationResult:
        """验证 SQL 语法"""
        pass
    
    async def execute_preview(self, db_config_id: str, sql: str, limit: int = 100) -> QueryResult:
        """执行查询预览"""
        pass
    
    async def save_template(self, template: QueryTemplate) -> QueryTemplate:
        """保存查询模板"""
        pass
    
    async def list_templates(self, tenant_id: str = None) -> List[QueryTemplate]:
        """列出查询模板"""
        pass

class QueryConfig(BaseModel):
    tables: List[str]
    columns: List[str]
    where_conditions: List[WhereCondition] = []
    order_by: List[OrderByClause] = []
    group_by: List[str] = []
    limit: Optional[int] = None

class QueryTemplate(BaseModel):
    id: str
    name: str
    description: str
    query_config: QueryConfig
    sql: str
    created_by: str
    created_at: datetime
```

### 6. Sync Strategy Service (同步策略服务)

**文件**: `src/admin/sync_strategy.py`

**职责**: 管理数据同步策略

```python
class SyncStrategyService:
    """同步策略服务"""
    
    async def get_strategy(self, db_config_id: str) -> SyncStrategy:
        """获取同步策略"""
        pass
    
    async def save_strategy(self, strategy: SyncStrategy) -> SyncStrategy:
        """保存同步策略"""
        pass
    
    async def validate_strategy(self, strategy: SyncStrategy) -> ValidationResult:
        """验证同步策略"""
        pass
    
    async def get_sync_history(self, db_config_id: str) -> List[SyncHistory]:
        """获取同步历史"""
        pass
    
    async def trigger_sync(self, db_config_id: str) -> SyncJob:
        """触发同步"""
        pass
    
    async def retry_sync(self, sync_job_id: str) -> SyncJob:
        """重试同步"""
        pass

class SyncStrategy(BaseModel):
    id: str
    db_config_id: str
    mode: SyncMode  # full/incremental/realtime
    incremental_field: Optional[str] = None
    schedule: Optional[str] = None  # Cron 表达式
    filter_conditions: List[FilterCondition] = []
    enabled: bool = True

class SyncMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    REALTIME = "realtime"
```

### 7. API Router (API 路由)

**文件**: `src/api/admin.py`

```python
router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

# 仪表盘
@router.get("/dashboard")
async def get_dashboard() -> DashboardData:
    """获取仪表盘数据"""
    pass

# LLM 配置
@router.get("/config/llm")
async def get_llm_config() -> LLMConfig:
    pass

@router.put("/config/llm")
async def update_llm_config(config: LLMConfig) -> LLMConfig:
    pass

# 数据库配置
@router.get("/config/databases")
async def list_db_configs() -> List[DBConfig]:
    pass

@router.post("/config/databases")
async def create_db_config(config: DBConfig) -> DBConfig:
    pass

@router.put("/config/databases/{id}")
async def update_db_config(id: str, config: DBConfig) -> DBConfig:
    pass

@router.delete("/config/databases/{id}")
async def delete_db_config(id: str) -> None:
    pass

@router.post("/config/databases/{id}/test")
async def test_db_connection(id: str) -> ConnectionTestResult:
    pass

# 同步策略
@router.get("/config/sync/{db_config_id}")
async def get_sync_strategy(db_config_id: str) -> SyncStrategy:
    pass

@router.put("/config/sync/{db_config_id}")
async def update_sync_strategy(db_config_id: str, strategy: SyncStrategy) -> SyncStrategy:
    pass

@router.post("/config/sync/{db_config_id}/trigger")
async def trigger_sync(db_config_id: str) -> SyncJob:
    pass

# SQL 构建器
@router.get("/sql-builder/schema/{db_config_id}")
async def get_db_schema(db_config_id: str) -> DatabaseSchema:
    pass

@router.post("/sql-builder/build")
async def build_sql(query_config: QueryConfig) -> str:
    pass

@router.post("/sql-builder/execute")
async def execute_sql(request: ExecuteSQLRequest) -> QueryResult:
    pass

# 配置历史
@router.get("/config/history")
async def get_config_history(
    config_type: ConfigType = None,
    start_time: datetime = None,
    end_time: datetime = None
) -> List[ConfigHistory]:
    pass

@router.post("/config/history/{id}/rollback")
async def rollback_config(id: str) -> Dict:
    pass

# 第三方工具
@router.get("/config/third-party")
async def list_third_party_configs() -> List[ThirdPartyConfig]:
    pass

@router.post("/config/third-party")
async def create_third_party_config(config: ThirdPartyConfig) -> ThirdPartyConfig:
    pass
```

## Data Models

### 数据库模型

```python
class AdminConfiguration(Base):
    """管理员配置表"""
    __tablename__ = "admin_configurations"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    config_type = Column(String(50), nullable=False)
    config_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseConnection(Base):
    """数据库连接配置表"""
    __tablename__ = "database_connections"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    name = Column(String(100), nullable=False)
    db_type = Column(String(50), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    is_readonly = Column(Boolean, default=True)
    extra_config = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ConfigChangeHistory(Base):
    """配置变更历史表"""
    __tablename__ = "config_change_history"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    config_type = Column(String(50), nullable=False)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class QueryTemplate(Base):
    """查询模板表"""
    __tablename__ = "query_templates"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    query_config = Column(JSONB, nullable=False)
    sql = Column(Text, nullable=False)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 敏感信息脱敏

*For any* 包含敏感信息（API Key、密码）的配置，在 API 响应和前端显示中，敏感信息应被脱敏处理（只显示前后 4 位）。

**Validates: Requirements 2.6, 3.6**

### Property 2: 数据库连接验证

*For any* 数据库连接配置，保存前应验证连接有效性，且只读连接应验证权限为只读。

**Validates: Requirements 3.4, 3.7**

### Property 3: SQL 构建正确性

*For any* 通过 SQL Builder 构建的查询配置，生成的 SQL 应通过语法验证，且执行结果应与配置一致。

**Validates: Requirements 5.4, 5.5**

### Property 4: 配置回滚一致性

*For any* 配置回滚操作，回滚后的配置应与历史记录中的旧值完全一致。

**Validates: Requirements 6.4**

### Property 5: 配置历史完整性

*For any* 配置变更，系统应记录完整的变更历史，包括变更时间、变更人、变更前后值。

**Validates: Requirements 6.2**

### Property 6: 第三方工具启用/禁用即时生效

*For any* 第三方工具的启用/禁用操作，应立即生效且不影响其他功能。

**Validates: Requirements 7.5**

## Error Handling

### 错误分类

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| 配置验证失败 | ADMIN_VALIDATION_ERROR | 返回详细验证错误 |
| 连接测试失败 | ADMIN_CONNECTION_ERROR | 返回连接错误详情 |
| 权限不足 | ADMIN_PERMISSION_DENIED | 返回权限错误 |
| 配置不存在 | ADMIN_CONFIG_NOT_FOUND | 返回 404 |
| 回滚失败 | ADMIN_ROLLBACK_ERROR | 返回回滚错误详情 |

## Testing Strategy

### 单元测试

- 测试配置验证逻辑
- 测试敏感信息加密/脱敏
- 测试 SQL 构建逻辑
- 测试历史记录和回滚

### 属性测试

```python
@given(st.text(min_size=8))
def test_credential_masking(credential: str):
    """Property 1: 敏感信息脱敏"""
    masked = encryptor.mask(credential)
    assert '*' in masked
    assert masked[:4] == credential[:4] if len(credential) > 8 else True

@given(query_config_strategy())
def test_sql_build_validity(query_config: QueryConfig):
    """Property 3: SQL 构建正确性"""
    sql = sql_builder.build_sql(query_config)
    assert sql_builder.validate_sql(sql, "postgresql").is_valid
```

### 集成测试

- 测试完整的配置保存和加载流程
- 测试数据库连接测试功能
- 测试配置历史和回滚
