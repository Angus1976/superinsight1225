# Design Document: Data Sync Pipeline (数据同步全流程)

## Overview

本设计文档描述 Data Sync Pipeline 模块的架构设计，该模块优化现有 `src/extractors/` 和 `src/sync/`，实现客户数据库读取/拉取/接收的完整同步流程，支持保存/不保存策略、业务逻辑提炼（AI 语义增强）和 AI 友好数据输出。

设计原则：
- **扩展现有**：基于现有 extractors 和 sync 模块扩展
- **多模式支持**：读取/拉取/接收三种数据获取方式
- **策略灵活**：支持持久化/内存/混合保存策略
- **AI 增强**：语义提炼提升数据可读性和 AI 处理效果
- **安全优先**：只读连接、数据脱敏、签名验证

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        SyncConfigUI[Sync Config UI]
        DataSourceUI[Data Source UI]
        SchedulerUI[Scheduler UI]
        ExportUI[Export UI]
    end

    subgraph API["API 层"]
        SyncRouter[/api/v1/sync]
        DataSourceAPI[Data Source API]
        SchedulerAPI[Scheduler API]
        ExportAPI[Export API]
    end
    
    subgraph Core["核心层"]
        DataReader[Data Reader]
        DataPuller[Data Puller]
        DataReceiver[Data Receiver]
        SaveStrategyManager[Save Strategy Manager]
        SemanticRefiner[Semantic Refiner]
        AIFriendlyExporter[AI Friendly Exporter]
        SyncScheduler[Sync Scheduler]
    end
    
    subgraph Connectors["连接器层"]
        PostgreSQLConn[PostgreSQL Connector]
        MySQLConn[MySQL Connector]
        SQLiteConn[SQLite Connector]
        OracleConn[Oracle Connector]
        SQLServerConn[SQL Server Connector]
    end
    
    subgraph External["外部服务"]
        LLMService[LLM Service]
        CustomerDB[(Customer DB)]
        Webhook[Webhook Source]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
    end
    
    SyncConfigUI --> SyncRouter
    DataSourceUI --> SyncRouter
    SchedulerUI --> SyncRouter
    ExportUI --> SyncRouter
    
    SyncRouter --> DataSourceAPI
    SyncRouter --> SchedulerAPI
    SyncRouter --> ExportAPI
    
    DataSourceAPI --> DataReader
    DataSourceAPI --> DataPuller
    DataSourceAPI --> DataReceiver
    
    DataReader --> PostgreSQLConn
    DataReader --> MySQLConn
    DataReader --> SQLiteConn
    DataReader --> OracleConn
    DataReader --> SQLServerConn
    
    PostgreSQLConn --> CustomerDB
    MySQLConn --> CustomerDB
    SQLiteConn --> CustomerDB
    OracleConn --> CustomerDB
    SQLServerConn --> CustomerDB
    
    DataPuller --> DataReader
    DataReceiver --> Webhook
    
    DataReader --> SaveStrategyManager
    DataPuller --> SaveStrategyManager
    DataReceiver --> SaveStrategyManager
    
    SaveStrategyManager --> DB
    SaveStrategyManager --> Cache
    
    SemanticRefiner --> LLMService
    SemanticRefiner --> Cache
    
    AIFriendlyExporter --> SemanticRefiner
    AIFriendlyExporter --> DB
    
    SchedulerAPI --> SyncScheduler
    SyncScheduler --> DataPuller
```

## Components and Interfaces

### 1. Data Reader (数据读取器)

**文件**: `src/sync/data_reader.py`

**职责**: 支持 JDBC/ODBC 方式读取客户数据库，只读权限连接

```python
class DataReader:
    """数据读取器"""
    
    def __init__(self, connector_factory: ConnectorFactory):
        self.connector_factory = connector_factory
    
    async def connect(
        self,
        config: DataSourceConfig,
        connection_method: ConnectionMethod = ConnectionMethod.JDBC
    ) -> Connection:
        """建立只读连接"""
        pass
    
    async def read_by_query(
        self,
        connection: Connection,
        query: str,
        page_size: int = 1000
    ) -> AsyncIterator[DataPage]:
        """通过 SQL 查询读取数据（分页）"""
        pass
    
    async def read_by_table(
        self,
        connection: Connection,
        table_name: str,
        columns: List[str] = None,
        page_size: int = 1000
    ) -> AsyncIterator[DataPage]:
        """通过表名读取数据（分页）"""
        pass
    
    def get_statistics(self, pages: List[DataPage]) -> ReadStatistics:
        """获取读取统计"""
        pass

class ConnectionMethod(str, Enum):
    JDBC = "jdbc"
    ODBC = "odbc"

class DataSourceConfig(BaseModel):
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str  # 加密存储
    connection_method: ConnectionMethod = ConnectionMethod.JDBC
    extra_params: Dict[str, Any] = {}

class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"

class DataPage(BaseModel):
    page_number: int
    rows: List[Dict[str, Any]]
    row_count: int
    has_more: bool

class ReadStatistics(BaseModel):
    total_rows: int
    total_columns: int
    total_size_bytes: int
    read_duration_ms: float
```

### 2. Data Puller (数据拉取器)

**文件**: `src/sync/data_puller.py`

**职责**: 支持定时轮询拉取，增量拉取，断点续传

```python
class DataPuller:
    """数据拉取器"""
    
    def __init__(self, data_reader: DataReader, checkpoint_store: CheckpointStore):
        self.data_reader = data_reader
        self.checkpoint_store = checkpoint_store
    
    async def pull(
        self,
        source_id: str,
        config: PullConfig
    ) -> PullResult:
        """执行拉取"""
        pass
    
    async def pull_incremental(
        self,
        source_id: str,
        config: PullConfig,
        checkpoint_field: str
    ) -> PullResult:
        """增量拉取"""
        checkpoint = await self.checkpoint_store.get(source_id)
        # 基于 checkpoint 构建增量查询
        pass
    
    async def save_checkpoint(self, source_id: str, checkpoint: Checkpoint) -> None:
        """保存检查点"""
        pass
    
    async def resume_from_checkpoint(self, source_id: str) -> PullResult:
        """从检查点恢复"""
        pass
    
    async def pull_with_retry(
        self,
        source_id: str,
        config: PullConfig,
        max_retries: int = 3
    ) -> PullResult:
        """带重试的拉取"""
        pass
    
    async def pull_parallel(
        self,
        source_configs: List[Tuple[str, PullConfig]]
    ) -> List[PullResult]:
        """并行拉取多个数据源"""
        pass

class PullConfig(BaseModel):
    cron_expression: str
    incremental: bool = True
    checkpoint_field: str = "updated_at"
    min_interval_minutes: int = 1  # 最小 1 分钟
    query: Optional[str] = None
    table_name: Optional[str] = None

class Checkpoint(BaseModel):
    source_id: str
    last_value: Any
    last_pull_at: datetime
    rows_pulled: int

class PullResult(BaseModel):
    source_id: str
    success: bool
    rows_pulled: int
    checkpoint: Checkpoint
    error_message: Optional[str] = None
    retries_used: int = 0
```

### 3. Data Receiver (数据接收器)

**文件**: `src/sync/data_receiver.py`

**职责**: 提供 Webhook 端点接收推送数据，支持签名验证和幂等处理

```python
class DataReceiver:
    """数据接收器"""
    
    def __init__(self, idempotency_store: IdempotencyStore):
        self.idempotency_store = idempotency_store
    
    async def receive(
        self,
        data: Union[str, bytes],
        format: DataFormat,
        signature: str,
        idempotency_key: str
    ) -> ReceiveResult:
        """接收数据"""
        # 验证签名
        if not self.verify_signature(data, signature):
            raise InvalidSignatureError()
        
        # 幂等检查
        if await self.idempotency_store.exists(idempotency_key):
            return ReceiveResult(success=True, duplicate=True, rows_received=0)
        
        # 解析数据
        parsed = self.parse_data(data, format)
        
        # 验证批量大小
        if len(parsed) > 10000:
            raise BatchSizeLimitExceededError()
        
        # 保存幂等键
        await self.idempotency_store.save(idempotency_key)
        
        return ReceiveResult(success=True, duplicate=False, rows_received=len(parsed))
    
    def verify_signature(self, data: Union[str, bytes], signature: str) -> bool:
        """验证签名"""
        pass
    
    def parse_data(self, data: Union[str, bytes], format: DataFormat) -> List[Dict]:
        """解析数据"""
        pass

class DataFormat(str, Enum):
    JSON = "json"
    CSV = "csv"

class ReceiveResult(BaseModel):
    success: bool
    duplicate: bool
    rows_received: int
    error_message: Optional[str] = None
```

### 4. Save Strategy Manager (保存策略管理器)

**文件**: `src/sync/save_strategy.py`

**职责**: 管理数据保存策略（持久化/内存/混合）

```python
class SaveStrategyManager:
    """保存策略管理器"""
    
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache
    
    async def save(
        self,
        data: List[Dict],
        strategy: SaveStrategy,
        config: SaveConfig
    ) -> SaveResult:
        """根据策略保存数据"""
        if strategy == SaveStrategy.PERSISTENT:
            return await self.save_to_db(data, config)
        elif strategy == SaveStrategy.MEMORY:
            return await self.save_to_memory(data, config)
        else:  # HYBRID
            return await self.save_hybrid(data, config)
    
    async def save_to_db(self, data: List[Dict], config: SaveConfig) -> SaveResult:
        """持久化保存到 PostgreSQL"""
        pass
    
    async def save_to_memory(self, data: List[Dict], config: SaveConfig) -> SaveResult:
        """仅内存处理"""
        # 处理完成后自动释放
        pass
    
    async def save_hybrid(self, data: List[Dict], config: SaveConfig) -> SaveResult:
        """混合模式：根据数据大小自动选择"""
        threshold = config.hybrid_threshold_bytes or 1024 * 1024  # 1MB
        data_size = self.calculate_size(data)
        
        if data_size > threshold:
            return await self.save_to_db(data, config)
        else:
            return await self.save_to_memory(data, config)
    
    async def cleanup_expired(self, retention_days: int) -> int:
        """清理过期数据"""
        pass
    
    def calculate_size(self, data: List[Dict]) -> int:
        """计算数据大小"""
        pass

class SaveStrategy(str, Enum):
    PERSISTENT = "persistent"
    MEMORY = "memory"
    HYBRID = "hybrid"

class SaveConfig(BaseModel):
    strategy: SaveStrategy = SaveStrategy.PERSISTENT
    retention_days: int = 30
    hybrid_threshold_bytes: int = 1024 * 1024  # 1MB
    table_name: Optional[str] = None

class SaveResult(BaseModel):
    success: bool
    strategy_used: SaveStrategy
    rows_saved: int
    storage_location: str  # "database" or "memory"
```

### 5. Semantic Refiner (语义提炼器)

**文件**: `src/sync/semantic_refiner.py`

**职责**: 使用 LLM 分析数据业务含义，生成语义增强描述

```python
class SemanticRefiner:
    """语义提炼器"""
    
    def __init__(self, llm_service: LLMService, cache: Redis):
        self.llm = llm_service
        self.cache = cache
    
    async def refine(
        self,
        data: List[Dict],
        config: RefineConfig
    ) -> RefinementResult:
        """执行语义提炼"""
        # 检查缓存
        cache_key = self.generate_cache_key(data, config)
        cached = await self.cache.get(cache_key)
        if cached:
            return RefinementResult.parse_raw(cached)
        
        # 执行提炼
        result = await self._do_refine(data, config)
        
        # 缓存结果
        await self.cache.set(cache_key, result.json(), ex=config.cache_ttl)
        
        return result
    
    async def generate_field_descriptions(self, data: List[Dict]) -> Dict[str, str]:
        """生成字段描述"""
        pass
    
    async def generate_data_dictionary(self, data: List[Dict]) -> DataDictionary:
        """生成数据字典"""
        pass
    
    async def extract_entities(self, data: List[Dict]) -> List[Entity]:
        """识别实体"""
        pass
    
    async def extract_relations(self, entities: List[Entity]) -> List[Relation]:
        """识别关系"""
        pass
    
    async def apply_custom_rules(
        self,
        data: List[Dict],
        rules: List[RefineRule]
    ) -> List[Dict]:
        """应用自定义提炼规则"""
        pass

class RefineConfig(BaseModel):
    generate_descriptions: bool = True
    generate_dictionary: bool = True
    extract_entities: bool = True
    extract_relations: bool = True
    custom_rules: List[RefineRule] = []
    cache_ttl: int = 3600  # 1 hour

class RefinementResult(BaseModel):
    field_descriptions: Dict[str, str]
    data_dictionary: DataDictionary
    entities: List[Entity]
    relations: List[Relation]
    enhanced_description: str

class DataDictionary(BaseModel):
    fields: List[FieldDefinition]
    table_description: str
    business_context: str

class Entity(BaseModel):
    name: str
    type: str
    source_field: str
    confidence: float

class Relation(BaseModel):
    source_entity: str
    target_entity: str
    relation_type: str
    confidence: float
```

### 6. AI Friendly Exporter (AI 友好导出器)

**文件**: `src/sync/ai_exporter.py`

**职责**: 导出适合 AI 处理的数据格式

```python
class AIFriendlyExporter:
    """AI 友好导出器"""
    
    def __init__(self, semantic_refiner: SemanticRefiner, desensitizer: Desensitizer):
        self.semantic_refiner = semantic_refiner
        self.desensitizer = desensitizer
    
    async def export(
        self,
        data: List[Dict],
        format: ExportFormat,
        config: ExportConfig
    ) -> ExportResult:
        """导出数据"""
        # 语义增强
        if config.include_semantics:
            refinement = await self.semantic_refiner.refine(data, RefineConfig())
            data = self.enrich_with_semantics(data, refinement)
        
        # 数据脱敏
        if config.desensitize:
            data = await self.desensitizer.desensitize(data)
        
        # 数据分割
        if config.split_config:
            splits = self.split_data(data, config.split_config)
        else:
            splits = {"all": data}
        
        # 导出
        exported_files = await self.export_splits(splits, format)
        
        # 生成统计报告
        report = self.generate_statistics_report(data, exported_files)
        
        return ExportResult(files=exported_files, statistics=report)
    
    async def export_incremental(
        self,
        source_id: str,
        format: ExportFormat,
        config: ExportConfig
    ) -> ExportResult:
        """增量导出"""
        pass
    
    def split_data(
        self,
        data: List[Dict],
        split_config: SplitConfig
    ) -> Dict[str, List[Dict]]:
        """分割数据集"""
        pass
    
    def generate_statistics_report(
        self,
        data: List[Dict],
        files: List[ExportedFile]
    ) -> StatisticsReport:
        """生成统计报告"""
        pass

class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"
    COCO = "coco"
    PASCAL_VOC = "pascal_voc"

class ExportConfig(BaseModel):
    include_semantics: bool = True
    desensitize: bool = False
    split_config: Optional[SplitConfig] = None
    incremental: bool = False
    last_export_id: Optional[str] = None

class SplitConfig(BaseModel):
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1
    shuffle: bool = True
    seed: int = 42

class ExportResult(BaseModel):
    files: List[ExportedFile]
    statistics: StatisticsReport

class StatisticsReport(BaseModel):
    total_rows: int
    total_size_bytes: int
    split_counts: Dict[str, int]
    field_statistics: Dict[str, FieldStats]
    export_duration_ms: float
```

### 7. Sync Scheduler (同步调度器)

**文件**: `src/sync/scheduler.py`

**职责**: 管理同步任务调度

```python
class SyncScheduler:
    """同步调度器"""
    
    def __init__(self, data_puller: DataPuller, notification_service: NotificationService):
        self.data_puller = data_puller
        self.notification_service = notification_service
        self.jobs: Dict[str, ScheduledJob] = {}
    
    async def schedule(
        self,
        job_id: str,
        source_id: str,
        config: ScheduleConfig
    ) -> ScheduledJob:
        """创建调度任务"""
        pass
    
    async def trigger_manual(self, job_id: str) -> SyncResult:
        """手动触发同步"""
        pass
    
    async def get_status(self, job_id: str) -> JobStatus:
        """获取任务状态"""
        pass
    
    async def update_status(self, job_id: str, status: JobStatus) -> None:
        """更新任务状态"""
        pass
    
    async def on_failure(self, job_id: str, error: Exception) -> None:
        """同步失败处理"""
        await self.notification_service.send_alert(
            AlertType.SYNC_FAILURE,
            {"job_id": job_id, "error": str(error)}
        )
    
    async def set_priority(self, job_id: str, priority: int) -> None:
        """设置任务优先级"""
        pass
    
    async def get_history(self, job_id: str, limit: int = 100) -> List[SyncHistoryRecord]:
        """获取同步历史"""
        pass
    
    async def list_jobs(self, status: JobStatus = None) -> List[ScheduledJob]:
        """列出所有任务"""
        pass

class ScheduleConfig(BaseModel):
    cron_expression: str
    priority: int = 0
    enabled: bool = True
    pull_config: PullConfig

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ScheduledJob(BaseModel):
    job_id: str
    source_id: str
    config: ScheduleConfig
    status: JobStatus
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime

class SyncHistoryRecord(BaseModel):
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: JobStatus
    rows_synced: int
    error_message: Optional[str]
```

### 8. API Router (API 路由)

**文件**: `src/api/sync_pipeline.py`

```python
router = APIRouter(prefix="/api/v1/sync", tags=["Data Sync"])

# 数据源管理
@router.post("/sources")
async def create_data_source(request: CreateDataSourceRequest) -> DataSource:
    """创建数据源"""
    pass

@router.get("/sources")
async def list_data_sources() -> List[DataSource]:
    """列出数据源"""
    pass

@router.get("/sources/{source_id}")
async def get_data_source(source_id: str) -> DataSource:
    """获取数据源详情"""
    pass

@router.delete("/sources/{source_id}")
async def delete_data_source(source_id: str) -> None:
    """删除数据源"""
    pass

# 数据读取
@router.post("/sources/{source_id}/read")
async def read_data(source_id: str, request: ReadRequest) -> ReadResult:
    """读取数据"""
    pass

@router.post("/sources/{source_id}/test-connection")
async def test_connection(source_id: str) -> ConnectionTestResult:
    """测试连接"""
    pass

# 数据拉取
@router.post("/sources/{source_id}/pull")
async def pull_data(source_id: str, request: PullRequest) -> PullResult:
    """拉取数据"""
    pass

@router.get("/sources/{source_id}/checkpoint")
async def get_checkpoint(source_id: str) -> Checkpoint:
    """获取检查点"""
    pass

# Webhook 接收
@router.post("/webhook/{source_id}")
async def receive_webhook(
    source_id: str,
    request: Request,
    x_signature: str = Header(...),
    x_idempotency_key: str = Header(...)
) -> ReceiveResult:
    """接收 Webhook 数据"""
    pass

# 保存策略
@router.put("/sources/{source_id}/save-strategy")
async def set_save_strategy(source_id: str, request: SaveStrategyRequest) -> None:
    """设置保存策略"""
    pass

# 语义提炼
@router.post("/sources/{source_id}/refine")
async def refine_semantics(source_id: str, request: RefineRequest) -> RefinementResult:
    """执行语义提炼"""
    pass

# 导出
@router.post("/export")
async def export_data(request: ExportRequest) -> ExportResult:
    """导出数据"""
    pass

@router.get("/export/{export_id}/status")
async def get_export_status(export_id: str) -> ExportStatus:
    """获取导出状态"""
    pass

@router.get("/export/{export_id}/download")
async def download_export(export_id: str) -> FileResponse:
    """下载导出文件"""
    pass

# 调度管理
@router.post("/schedules")
async def create_schedule(request: CreateScheduleRequest) -> ScheduledJob:
    """创建调度任务"""
    pass

@router.get("/schedules")
async def list_schedules(status: JobStatus = None) -> List[ScheduledJob]:
    """列出调度任务"""
    pass

@router.post("/schedules/{job_id}/trigger")
async def trigger_schedule(job_id: str) -> SyncResult:
    """手动触发同步"""
    pass

@router.get("/schedules/{job_id}/history")
async def get_schedule_history(job_id: str, limit: int = 100) -> List[SyncHistoryRecord]:
    """获取同步历史"""
    pass

@router.put("/schedules/{job_id}/priority")
async def set_schedule_priority(job_id: str, priority: int) -> None:
    """设置任务优先级"""
    pass
```

## Data Models

### 数据库模型

```python
class DataSource(Base):
    """数据源表"""
    __tablename__ = "data_sources"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    name = Column(String(200), nullable=False)
    db_type = Column(String(50), nullable=False)
    host = Column(String(500), nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String(200), nullable=False)
    username = Column(String(200), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    connection_method = Column(String(20), default="jdbc")
    extra_params = Column(JSONB, default={})
    save_strategy = Column(String(20), default="persistent")
    save_config = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SyncCheckpoint(Base):
    """同步检查点表"""
    __tablename__ = "sync_checkpoints"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    source_id = Column(UUID, ForeignKey("data_sources.id"), nullable=False)
    checkpoint_field = Column(String(200), nullable=False)
    last_value = Column(Text, nullable=True)
    last_pull_at = Column(DateTime, nullable=True)
    rows_pulled = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SyncJob(Base):
    """同步任务表"""
    __tablename__ = "sync_jobs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    source_id = Column(UUID, ForeignKey("data_sources.id"), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    status = Column(String(20), default="pending")
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    pull_config = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SyncHistory(Base):
    """同步历史表"""
    __tablename__ = "sync_history"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    job_id = Column(UUID, ForeignKey("sync_jobs.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)
    rows_synced = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

class SemanticCache(Base):
    """语义缓存表"""
    __tablename__ = "semantic_cache"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    cache_key = Column(String(64), nullable=False, unique=True)
    refinement_result = Column(JSONB, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExportRecord(Base):
    """导出记录表"""
    __tablename__ = "export_records"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    source_id = Column(UUID, ForeignKey("data_sources.id"), nullable=True)
    format = Column(String(20), nullable=False)
    config = Column(JSONB, default={})
    status = Column(String(20), default="pending")
    file_paths = Column(JSONB, default=[])
    statistics = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 只读连接验证

*For any* 数据库连接，Data Reader 应使用只读权限连接，任何写操作尝试应被拒绝。

**Validates: Requirements 1.2**

### Property 2: 分页读取内存安全

*For any* 数据读取操作，当数据量超过页大小时，Data Reader 应返回分页迭代器，单次内存占用不超过页大小限制。

**Validates: Requirements 1.5**

### Property 3: 读取统计完整性

*For any* 完成的读取操作，返回的统计信息应包含准确的行数、列数和数据大小。

**Validates: Requirements 1.6**

### Property 4: 增量拉取检查点持久化

*For any* 增量拉取操作，完成后应保存检查点，下次拉取应从检查点位置继续，不重复拉取已处理数据。

**Validates: Requirements 2.2, 2.3**

### Property 5: 拉取重试机制

*For any* 失败的拉取操作，系统应自动重试最多 3 次，重试次数应记录在结果中。

**Validates: Requirements 2.5**

### Property 6: Webhook 幂等处理

*For any* 相同幂等键的 Webhook 请求，系统应识别为重复请求并返回成功，不创建重复数据。

**Validates: Requirements 3.6**

### Property 7: 批量大小限制

*For any* Webhook 接收请求，当数据条数超过 10000 时，系统应拒绝请求并返回错误。

**Validates: Requirements 3.4**

### Property 8: 保存策略正确性

*For any* 持久化保存操作，数据应可从数据库检索；对于内存处理操作，处理完成后数据应不可检索。

**Validates: Requirements 4.2, 4.3**

### Property 9: 混合模式自动选择

*For any* 混合模式保存操作，数据大小超过阈值时应使用持久化，否则使用内存处理。

**Validates: Requirements 4.4**

### Property 10: 语义提炼缓存命中

*For any* 相同输入的语义提炼请求，第二次请求应返回缓存结果，不重复调用 LLM。

**Validates: Requirements 5.6**

### Property 11: 导出格式正确性

*For any* 导出操作，输出文件应符合指定格式规范（JSON/CSV/JSONL/COCO/Pascal VOC）。

**Validates: Requirements 6.1**

### Property 12: 数据分割比例准确性

*For any* 带分割配置的导出操作，训练集/验证集/测试集的实际比例应与配置比例一致（允许 1% 误差）。

**Validates: Requirements 6.3**

### Property 13: 调度任务状态追踪

*For any* 同步任务，其状态应准确反映实际执行状态（等待/运行/完成/失败）。

**Validates: Requirements 7.3**

### Property 14: 同步历史完整性

*For any* 执行的同步操作，应在历史记录中保存完整信息（开始时间、结束时间、状态、同步行数）。

**Validates: Requirements 7.6**

## Error Handling

### 错误分类

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| 连接失败 | SYNC_CONNECTION_ERROR | 返回连接错误详情 |
| 只读违规 | SYNC_READONLY_VIOLATION | 拒绝操作，记录日志 |
| 签名无效 | SYNC_INVALID_SIGNATURE | 拒绝请求，返回 401 |
| 批量超限 | SYNC_BATCH_LIMIT_EXCEEDED | 拒绝请求，返回 413 |
| 拉取失败 | SYNC_PULL_ERROR | 重试最多 3 次 |
| 导出失败 | SYNC_EXPORT_ERROR | 记录错误，通知用户 |
| 调度失败 | SYNC_SCHEDULE_ERROR | 发送告警通知 |
| LLM 调用失败 | SYNC_LLM_ERROR | 返回未增强数据 |

## Testing Strategy

### 单元测试

- 测试各数据库连接器
- 测试分页读取逻辑
- 测试检查点保存/恢复
- 测试签名验证
- 测试幂等处理
- 测试保存策略选择
- 测试数据分割算法

### 属性测试

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=100000))
def test_pagination_memory_safety(total_rows: int):
    """Property 2: 分页读取内存安全"""
    page_size = 1000
    reader = DataReader(connector_factory)
    pages = list(reader.read_by_query(conn, query, page_size))
    for page in pages:
        assert len(page.rows) <= page_size

@given(st.text(min_size=1), st.text(min_size=1))
def test_idempotency_handling(data: str, idempotency_key: str):
    """Property 6: Webhook 幂等处理"""
    receiver = DataReceiver(idempotency_store)
    result1 = await receiver.receive(data, DataFormat.JSON, sig, idempotency_key)
    result2 = await receiver.receive(data, DataFormat.JSON, sig, idempotency_key)
    assert result1.success == True
    assert result2.success == True
    assert result2.duplicate == True

@given(st.floats(min_value=0, max_value=1), st.floats(min_value=0, max_value=1), st.floats(min_value=0, max_value=1))
def test_split_ratio_accuracy(train: float, val: float, test: float):
    """Property 12: 数据分割比例准确性"""
    # 归一化比例
    total = train + val + test
    if total == 0:
        return
    train, val, test = train/total, val/total, test/total
    
    config = SplitConfig(train_ratio=train, val_ratio=val, test_ratio=test)
    data = [{"id": i} for i in range(1000)]
    splits = exporter.split_data(data, config)
    
    actual_train = len(splits.get("train", [])) / 1000
    actual_val = len(splits.get("val", [])) / 1000
    actual_test = len(splits.get("test", [])) / 1000
    
    assert abs(actual_train - train) < 0.01
    assert abs(actual_val - val) < 0.01
    assert abs(actual_test - test) < 0.01
```

### 集成测试

- 测试完整的读取 → 保存 → 导出流程
- 测试定时拉取调度
- 测试 Webhook 接收流程
- 测试语义提炼与缓存
- 测试多数据源并行拉取
