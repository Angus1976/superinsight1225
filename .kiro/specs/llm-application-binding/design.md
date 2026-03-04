# Design Document: LLM Application Binding System

**Version**: 1.0  
**Last Updated**: 2026-03-03  
**Status**: Draft

---

## Overview

The LLM Application Binding System implements a flexible many-to-many relationship between LLM configurations and applications, enabling priority-based failover, hot configuration reload, and multi-tenant isolation. This design upgrades the existing single-LLM-per-application architecture to support multiple LLM providers with automatic failover.

### Design Goals

- **Flexibility**: Each application can configure multiple LLM providers (primary + backups)
- **Reliability**: Automatic failover ensures service availability when LLMs fail
- **Maintainability**: Hot reload eliminates service restarts for configuration changes
- **Compatibility**: Zero code changes required for existing applications
- **Security**: AES-256 encryption for API keys with proper access control

### Key Features

1. Many-to-many LLM-application bindings with priority-based ordering
2. Automatic failover with configurable retry and timeout policies
3. Two-tier caching (local memory + optional Redis) with hot reload
4. Multi-tenant configuration hierarchy (global → tenant → application)
5. Backward compatible with environment variable configuration
6. Comprehensive REST API for configuration management
7. React-based admin UI with i18n support

---

## Architecture

### System Components


```
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │Structuring│ │Knowledge │  │AI Assistant│  ...       │
│  └─────┬────┘  └────┬─────┘  └────┬──────┘             │
└────────┼────────────┼─────────────┼────────────────────┘
         │            │             │
         └────────────┴─────────────┘
                      │
         ┌────────────▼────────────┐
         │ ApplicationLLMManager   │
         │  - get_llm_config()     │
         │  - execute_with_failover│
         │  - cache_manager        │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │     Cache Layer         │
         │  ┌──────┐  ┌─────────┐ │
         │  │Memory│  │Redis    │ │
         │  │Cache │  │(optional)│ │
         │  └──────┘  └─────────┘ │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │     Data Layer          │
         │  - llm_configs          │
         │  - llm_applications     │
         │  - llm_bindings         │
         └─────────────────────────┘
```

### Component Responsibilities

**ApplicationLLMManager**: Central service for LLM configuration retrieval and failover execution
- Loads configurations with priority ordering
- Implements retry logic with exponential backoff
- Manages cache invalidation and reload
- Handles multi-tenant configuration hierarchy

**Cache Layer**: Two-tier caching for performance optimization
- Local memory cache (TTL 300s, LRU eviction)
- Optional Redis cache for multi-instance synchronization
- Redis Pub/Sub for cache invalidation broadcasting

**Data Layer**: Three core tables for configuration storage
- `llm_configs`: LLM provider configurations with encrypted API keys
- `llm_applications`: Application registry with usage patterns
- `llm_application_bindings`: Many-to-many relationships with priority

---

## Components and Interfaces

### 1. Data Models

#### LLMConfig (Database Model)


```python
class LLMConfig(Base):
    __tablename__ = "llm_configs"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: str = Column(String(100), nullable=False)
    provider: str = Column(String(50), nullable=False)  # openai, azure, anthropic, ollama, custom
    api_key_encrypted: str = Column(Text, nullable=False)  # AES-256 encrypted
    base_url: str = Column(String(500), nullable=True)
    model_name: str = Column(String(100), nullable=False)
    parameters: dict = Column(JSON, nullable=True, default={})
    is_active: bool = Column(Boolean, default=True, nullable=False)
    tenant_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    bindings = relationship("LLMApplicationBinding", back_populates="llm_config", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_llm_configs_tenant_active", "tenant_id", "is_active"),
        Index("idx_llm_configs_provider", "provider"),
    )
```

#### LLMApplication (Database Model)

```python
class LLMApplication(Base):
    __tablename__ = "llm_applications"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: str = Column(String(50), unique=True, nullable=False)  # e.g., "structuring"
    name: str = Column(String(100), nullable=False)
    description: str = Column(Text, nullable=True)
    llm_usage_pattern: str = Column(Text, nullable=True)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    bindings = relationship("LLMApplicationBinding", back_populates="application", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_llm_applications_code", "code", unique=True),
    )
```

#### LLMApplicationBinding (Database Model)

```python
class LLMApplicationBinding(Base):
    __tablename__ = "llm_application_bindings"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    llm_config_id: UUID = Column(UUID(as_uuid=True), ForeignKey("llm_configs.id"), nullable=False)
    application_id: UUID = Column(UUID(as_uuid=True), ForeignKey("llm_applications.id"), nullable=False)
    priority: int = Column(Integer, nullable=False)  # 1-99, lower = higher priority
    max_retries: int = Column(Integer, default=3, nullable=False)
    timeout_seconds: int = Column(Integer, default=30, nullable=False)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    llm_config = relationship("LLMConfig", back_populates="bindings")
    application = relationship("LLMApplication", back_populates="bindings")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("application_id", "priority", name="uq_app_priority"),
        Index("idx_bindings_app_priority", "application_id", "priority"),
        Index("idx_bindings_active", "is_active"),
        CheckConstraint("priority >= 1 AND priority <= 99", name="ck_priority_range"),
        CheckConstraint("max_retries >= 0 AND max_retries <= 10", name="ck_max_retries_range"),
        CheckConstraint("timeout_seconds > 0", name="ck_timeout_positive"),
    )
```

### 2. Pydantic Schemas

#### Request/Response Models


```python
class LLMConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., pattern="^(openai|azure|anthropic|ollama|custom)$")
    api_key: str = Field(..., min_length=1)
    base_url: Optional[str] = Field(None, max_length=500)
    model_name: str = Field(..., min_length=1, max_length=100)
    parameters: Optional[dict] = Field(default_factory=dict)
    tenant_id: Optional[UUID] = None

class LLMConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[str] = Field(None, pattern="^(openai|azure|anthropic|ollama|custom)$")
    api_key: Optional[str] = Field(None, min_length=1)
    base_url: Optional[str] = Field(None, max_length=500)
    model_name: Optional[str] = Field(None, min_length=1, max_length=100)
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None

class LLMConfigResponse(BaseModel):
    id: UUID
    name: str
    provider: str
    base_url: Optional[str]
    model_name: str
    parameters: dict
    is_active: bool
    tenant_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    # Note: api_key is never returned in responses

class LLMBindingCreate(BaseModel):
    llm_config_id: UUID
    application_id: UUID
    priority: int = Field(..., ge=1, le=99)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=30, gt=0)

class LLMBindingUpdate(BaseModel):
    priority: Optional[int] = Field(None, ge=1, le=99)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None

class LLMBindingResponse(BaseModel):
    id: UUID
    llm_config: LLMConfigResponse
    application: ApplicationResponse
    priority: int
    max_retries: int
    timeout_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 3. ApplicationLLMManager Service

#### Core Interface

```python
class ApplicationLLMManager:
    """Central service for LLM configuration management and failover."""
    
    def __init__(
        self,
        db_session: AsyncSession,
        cache_manager: CacheManager,
        encryption_service: EncryptionService
    ):
        self.db = db_session
        self.cache = cache_manager
        self.encryption = encryption_service
    
    async def get_llm_config(
        self,
        application_code: str,
        tenant_id: Optional[str] = None
    ) -> List[CloudConfig]:
        """
        Retrieve LLM configurations for an application, ordered by priority.
        
        Priority order:
        1. Application-specific bindings (highest priority)
        2. Tenant-level configurations
        3. Global default configurations
        4. Environment variables (fallback)
        
        Returns:
            List of CloudConfig objects ordered by priority (ascending)
        """
        
    async def execute_with_failover(
        self,
        application_code: str,
        operation: Callable[[CloudConfig], Awaitable[T]],
        tenant_id: Optional[str] = None
    ) -> T:
        """
        Execute an operation with automatic failover across LLM configurations.
        
        Retry logic:
        - Retry each LLM up to max_retries times with exponential backoff
        - On timeout or failure, move to next LLM in priority order
        - Log all failover events
        - Raise exception if all LLMs fail
        """
    
    async def invalidate_cache(
        self,
        application_code: Optional[str] = None,
        broadcast: bool = True
    ) -> None:
        """
        Invalidate configuration cache.
        
        Args:
            application_code: If provided, invalidate only this application's cache
            broadcast: If True and Redis available, broadcast invalidation to other instances
        """
```

#### Configuration Loading Logic


```python
async def _load_from_database(
    self,
    application_code: str,
    tenant_id: Optional[str]
) -> List[CloudConfig]:
    """Load configurations from database with hierarchy resolution."""
    
    # Step 1: Get application
    app = await self.db.query(LLMApplication).filter_by(code=application_code).first()
    if not app:
        return []
    
    # Step 2: Get bindings ordered by priority
    query = (
        self.db.query(LLMApplicationBinding)
        .join(LLMConfig)
        .filter(
            LLMApplicationBinding.application_id == app.id,
            LLMApplicationBinding.is_active == True,
            LLMConfig.is_active == True
        )
        .order_by(LLMApplicationBinding.priority.asc())
    )
    
    # Step 3: Apply tenant filter with fallback to global
    if tenant_id:
        # Try tenant-specific first
        tenant_bindings = query.filter(LLMConfig.tenant_id == tenant_id).all()
        if tenant_bindings:
            return [self._to_cloud_config(b.llm_config) for b in tenant_bindings]
    
    # Step 4: Fallback to global configurations
    global_bindings = query.filter(LLMConfig.tenant_id == None).all()
    return [self._to_cloud_config(b.llm_config) for b in global_bindings]

def _to_cloud_config(self, llm_config: LLMConfig) -> CloudConfig:
    """Convert LLMConfig to CloudConfig with decryption."""
    api_key = self.encryption.decrypt(llm_config.api_key_encrypted)
    return CloudConfig(
        provider=llm_config.provider,
        api_key=api_key,
        base_url=llm_config.base_url,
        model_name=llm_config.model_name,
        parameters=llm_config.parameters
    )

def _load_from_env(self) -> Optional[CloudConfig]:
    """Fallback to environment variables for backward compatibility."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    
    return CloudConfig(
        provider="openai",
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        parameters={}
    )
```

#### Failover Implementation

```python
async def _execute_with_retry(
    self,
    config: CloudConfig,
    operation: Callable,
    max_retries: int,
    timeout_seconds: int
) -> T:
    """Execute operation with retry and timeout."""
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                operation(config),
                timeout=timeout_seconds
            )
            return result
            
        except asyncio.TimeoutError as e:
            last_error = e
            logger.warning(
                f"LLM request timeout (attempt {attempt + 1}/{max_retries + 1})",
                extra={"config": config.model_name, "timeout": timeout_seconds}
            )
            
        except Exception as e:
            last_error = e
            logger.warning(
                f"LLM request failed (attempt {attempt + 1}/{max_retries + 1}): {e}",
                extra={"config": config.model_name}
            )
        
        # Exponential backoff
        if attempt < max_retries:
            await asyncio.sleep(2 ** attempt)
    
    raise last_error
```

### 4. Cache Management

#### CacheManager Interface

```python
class CacheManager:
    """Two-tier cache with local memory and optional Redis."""
    
    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        local_ttl: int = 300,
        max_memory_mb: int = 100
    ):
        self.local_cache: Dict[str, CacheEntry] = {}
        self.redis = redis_client
        self.local_ttl = local_ttl
        self.max_memory_mb = max_memory_mb
        
        if redis_client:
            self._subscribe_to_invalidations()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache with TTL validation."""
        # Try local cache first
        if key in self.local_cache:
            entry = self.local_cache[key]
            if not entry.is_expired():
                return entry.value
            else:
                del self.local_cache[key]
        
        # Try Redis if available
        if self.redis:
            value = await self.redis.get(key)
            if value:
                # Populate local cache
                self.local_cache[key] = CacheEntry(value, self.local_ttl)
                return value
        
        return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set in both cache tiers."""
        # Set in local cache
        self.local_cache[key] = CacheEntry(value, self.local_ttl)
        
        # Set in Redis if available
        if self.redis:
            await self.redis.setex(key, self.local_ttl, value)
        
        # Evict if memory limit exceeded
        self._evict_if_needed()
    
    async def invalidate(self, pattern: str, broadcast: bool = True) -> None:
        """Invalidate cache entries matching pattern."""
        # Invalidate local cache
        keys_to_delete = [k for k in self.local_cache.keys() if fnmatch(k, pattern)]
        for key in keys_to_delete:
            del self.local_cache[key]
        
        # Invalidate Redis and broadcast
        if self.redis:
            await self.redis.delete(*keys_to_delete)
            
            if broadcast:
                await self.redis.publish(
                    "llm:config:invalidate",
                    json.dumps({"pattern": pattern})
                )
```

---

## Data Models

### Database Schema

#### Table: llm_configs


| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| name | VARCHAR(100) | NOT NULL | Display name |
| provider | VARCHAR(50) | NOT NULL | Provider type (openai, azure, anthropic, ollama, custom) |
| api_key_encrypted | TEXT | NOT NULL | AES-256 encrypted API key |
| base_url | VARCHAR(500) | NULL | API base URL |
| model_name | VARCHAR(100) | NOT NULL | Model identifier |
| parameters | JSON | NULL | Additional parameters |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Active status |
| tenant_id | UUID | NULL, FK(tenants.id) | Tenant scope (NULL = global) |
| created_at | TIMESTAMP | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL | Last update timestamp |

**Indexes:**
- `idx_llm_configs_tenant_active` ON (tenant_id, is_active)
- `idx_llm_configs_provider` ON (provider)

#### Table: llm_applications

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| code | VARCHAR(50) | NOT NULL, UNIQUE | Application code (e.g., "structuring") |
| name | VARCHAR(100) | NOT NULL | Display name |
| description | TEXT | NULL | Application description |
| llm_usage_pattern | TEXT | NULL | Usage pattern description |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Active status |
| created_at | TIMESTAMP | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL | Last update timestamp |

**Indexes:**
- `idx_llm_applications_code` ON (code) UNIQUE

**Initial Data:**
```sql
INSERT INTO llm_applications (code, name, description, llm_usage_pattern) VALUES
('structuring', 'Data Structuring', 'Schema inference and entity extraction', 'High-frequency, low-latency'),
('knowledge_graph', 'Knowledge Graph', 'Knowledge graph construction', 'Medium-frequency, high-quality'),
('ai_assistant', 'AI Assistant', 'Intelligent assistant services', 'High-frequency, conversational'),
('semantic_analysis', 'Semantic Analysis', 'Semantic analysis services', 'Medium-frequency, analytical'),
('rag_agent', 'RAG Agent', 'Retrieval-augmented generation', 'High-frequency, context-aware'),
('text_to_sql', 'Text to SQL', 'Natural language to SQL conversion', 'Medium-frequency, precise');
```

#### Table: llm_application_bindings

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| llm_config_id | UUID | NOT NULL, FK(llm_configs.id) | LLM configuration reference |
| application_id | UUID | NOT NULL, FK(llm_applications.id) | Application reference |
| priority | INTEGER | NOT NULL, CHECK(1-99) | Priority (1=highest) |
| max_retries | INTEGER | NOT NULL, DEFAULT 3, CHECK(0-10) | Maximum retry attempts |
| timeout_seconds | INTEGER | NOT NULL, DEFAULT 30, CHECK(>0) | Request timeout |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Active status |
| created_at | TIMESTAMP | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL | Last update timestamp |

**Constraints:**
- `uq_app_priority` UNIQUE (application_id, priority)
- `ck_priority_range` CHECK (priority >= 1 AND priority <= 99)
- `ck_max_retries_range` CHECK (max_retries >= 0 AND max_retries <= 10)
- `ck_timeout_positive` CHECK (timeout_seconds > 0)

**Indexes:**
- `idx_bindings_app_priority` ON (application_id, priority)
- `idx_bindings_active` ON (is_active)

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Provider Validation

*For any* LLM configuration creation or update request, the provider field should only accept values from the set {openai, azure, anthropic, ollama, custom}, and reject all other values.

**Validates: Requirements 1.2**

### Property 2: API Key Encryption Round-Trip

*For any* API key string, encrypting then decrypting should produce the original value, and the encrypted value should differ from the original.

**Validates: Requirements 1.3, 4.3, 12.1**

### Property 3: Binding Prevents Config Deletion

*For any* LLM configuration with active bindings, attempting to delete the configuration should fail with an error indicating existing bindings.

**Validates: Requirements 1.5**

### Property 4: Application Code Uniqueness

*For any* two application registration attempts with the same code, the second attempt should fail with a uniqueness constraint error.

**Validates: Requirements 2.3**

### Property 5: Binding Referential Integrity

*For any* binding creation attempt, if either the LLM configuration ID or application ID does not exist in the database, the creation should fail with a referential integrity error.

**Validates: Requirements 3.2**

### Property 6: Priority Uniqueness Per Application

*For any* application, attempting to create two bindings with the same priority value should fail with a uniqueness constraint error.

**Validates: Requirements 3.3**

### Property 7: Priority Range Validation

*For any* binding creation or update, the priority value should be accepted if and only if it is between 1 and 99 (inclusive).

**Validates: Requirements 3.4, 14.3**

### Property 8: Bindings Ordered By Priority

*For any* application with multiple active bindings, retrieving the bindings should return them in ascending priority order (1, 2, 3, ...).

**Validates: Requirements 3.5, 4.1**

### Property 9: Configuration Loading Hierarchy

*For any* application and tenant, when loading LLM configuration, the system should return application-specific bindings if they exist, otherwise tenant-level configurations if they exist, otherwise global configurations, otherwise environment variable configuration.

**Validates: Requirements 4.2, 7.1, 7.3, 7.5, 17.1, 18.4**

### Property 10: Cache TTL Expiration

*For any* cached configuration entry, if the current time exceeds the entry's creation time plus TTL, the entry should be considered expired and not returned from cache.

**Validates: Requirements 4.4, 4.5**

### Property 11: Retry With Exponential Backoff

*For any* failed LLM request, the system should retry up to max_retries times, with wait times following exponential backoff pattern (2^0, 2^1, 2^2, ... seconds).

**Validates: Requirements 5.1**

### Property 12: Failover On Exhausted Retries

*For any* LLM configuration that fails all retry attempts, if additional LLM configurations exist with higher priority values, the system should attempt the next configuration in priority order.

**Validates: Requirements 5.2**

### Property 13: Timeout Triggers Failover

*For any* LLM request that exceeds the configured timeout_seconds, the system should treat it as a failure and trigger the retry/failover logic.

**Validates: Requirements 5.3**

### Property 14: Failover Logging

*For any* failover event, the system should create a log entry containing timestamp, application code, failed LLM identifier, target LLM identifier, and failure reason.

**Validates: Requirements 5.5, 13.4**

### Property 15: Cache Invalidation On Configuration Change

*For any* LLM configuration or binding creation, update, or deletion, the system should invalidate all related cache entries immediately.

**Validates: Requirements 6.1, 6.2, 17.3, 17.4**

### Property 16: Cache Reload After Invalidation

*For any* cache invalidation event, the next configuration retrieval request should fetch data from the database rather than cache.

**Validates: Requirements 6.3, 17.5**

### Property 17: Input Validation Completeness

*For any* LLM configuration or binding creation/update request, the system should validate all required fields are present, URLs are valid format, numeric fields are within allowed ranges, and reject invalid requests with descriptive error messages.

**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**

### Property 18: Configuration Override Priority

*For any* application with configurations at multiple levels (global, tenant, application), the system should apply the most specific configuration available, following the priority: application binding > tenant configuration > global configuration > environment variables.

**Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8**

---

## Error Handling

### Error Categories


**Validation Errors** (HTTP 400):
- Invalid provider type
- Missing required fields
- Invalid URL format
- Priority out of range (1-99)
- Timeout or retry values out of bounds

**Business Logic Errors** (HTTP 409):
- Duplicate application code
- Duplicate priority within application
- Cannot delete LLM config with active bindings
- LLM config or application not found for binding

**Authentication/Authorization Errors** (HTTP 401/403):
- Missing or invalid authentication token
- Insufficient permissions for operation

**System Errors** (HTTP 500):
- Database connection failure
- Encryption/decryption failure
- Cache service unavailable

**LLM Execution Errors**:
- All LLMs failed after exhausting retries
- Timeout on all configured LLMs
- Invalid LLM response format

### Error Response Format

```python
class ErrorResponse(BaseModel):
    error_code: str  # Machine-readable error code
    message: str  # Human-readable error message
    details: Optional[dict] = None  # Additional context
    timestamp: datetime
    request_id: str  # For tracing

# Example
{
    "error_code": "BINDING_PRIORITY_DUPLICATE",
    "message": "Priority 1 is already assigned to another LLM for this application",
    "details": {
        "application_code": "structuring",
        "priority": 1,
        "existing_binding_id": "uuid"
    },
    "timestamp": "2026-03-03T10:00:00Z",
    "request_id": "req_abc123"
}
```

### Retry and Timeout Strategy

**Exponential Backoff**:
- Base delay: 1 second
- Backoff multiplier: 2
- Max delay: 32 seconds
- Formula: `min(2^attempt, 32)` seconds

**Timeout Handling**:
- Per-request timeout: Configurable per binding (default 30s)
- Total operation timeout: Sum of all LLM timeouts + retry delays
- Graceful degradation: Return partial results if possible

---

## Testing Strategy

### Dual Testing Approach

The system requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests**: Verify specific examples, edge cases, and integration points
- Database schema creation and constraints
- API endpoint functionality
- Redis pub/sub integration
- Environment variable fallback
- Specific error conditions

**Property-Based Tests**: Verify universal properties across all inputs
- Minimum 100 iterations per property test
- Each test references its design document property
- Tag format: `Feature: llm-application-binding, Property {number}: {property_text}`

### Property-Based Testing Library

**Python Backend**: Use `hypothesis` library
```python
from hypothesis import given, strategies as st

@given(
    provider=st.sampled_from(['openai', 'azure', 'anthropic', 'ollama', 'custom']),
    api_key=st.text(min_size=1)
)
def test_property_2_encryption_round_trip(provider, api_key):
    """Feature: llm-application-binding, Property 2: API Key Encryption Round-Trip"""
    encrypted = encryption_service.encrypt(api_key)
    decrypted = encryption_service.decrypt(encrypted)
    
    assert decrypted == api_key
    assert encrypted != api_key
```

**TypeScript Frontend**: Use `fast-check` library
```typescript
import fc from 'fast-check';

test('Property 17: Input Validation Completeness', () => {
  fc.assert(
    fc.property(
      fc.record({
        name: fc.string(),
        provider: fc.constantFrom('openai', 'azure', 'anthropic', 'ollama', 'custom'),
        api_key: fc.string({ minLength: 1 }),
        model_name: fc.string({ minLength: 1 })
      }),
      (config) => {
        const result = validateLLMConfig(config);
        expect(result.isValid).toBe(true);
      }
    ),
    { numRuns: 100 }
  );
});
```

### Test Coverage Requirements

**Backend**:
- Unit test coverage: > 80%
- Property test coverage: All 18 correctness properties
- Integration tests: All API endpoints
- Database migration tests: Up and down migrations

**Frontend**:
- Component test coverage: > 70%
- Integration tests: User workflows (create, edit, delete, reorder)
- i18n tests: All translation keys exist in both languages

### Key Test Scenarios

**Configuration Loading**:
- Application with database bindings
- Application without bindings (environment fallback)
- Multi-tenant configuration hierarchy
- Cache hit and miss scenarios

**Failover Logic**:
- Single LLM failure with retry
- Multiple LLM failover
- All LLMs fail scenario
- Timeout handling

**Cache Management**:
- Cache invalidation on config change
- Cache expiration after TTL
- Redis pub/sub synchronization
- Memory limit enforcement

**Security**:
- API key encryption/decryption
- Access control enforcement
- Audit log creation

---

## API Endpoints

### LLM Configuration Management

**POST /api/llm-configs**
- Create new LLM configuration
- Request: `LLMConfigCreate`
- Response: `LLMConfigResponse`
- Auth: ADMIN role required

**GET /api/llm-configs**
- List all LLM configurations
- Query params: `tenant_id`, `provider`, `is_active`
- Response: `List[LLMConfigResponse]`
- Auth: ADMIN or TECHNICAL_EXPERT role

**GET /api/llm-configs/{id}**
- Get single LLM configuration
- Response: `LLMConfigResponse`
- Auth: ADMIN or TECHNICAL_EXPERT role

**PUT /api/llm-configs/{id}**
- Update LLM configuration
- Request: `LLMConfigUpdate`
- Response: `LLMConfigResponse`
- Auth: ADMIN role required

**DELETE /api/llm-configs/{id}**
- Delete LLM configuration (fails if bindings exist)
- Response: 204 No Content
- Auth: ADMIN role required

**POST /api/llm-configs/{id}/test**
- Test LLM connectivity
- Response: `{"status": "success", "latency_ms": 123}`
- Auth: ADMIN or TECHNICAL_EXPERT role

### Application Management

**GET /api/applications**
- List all applications
- Response: `List[ApplicationResponse]`
- Auth: Authenticated users

**GET /api/applications/{code}**
- Get single application by code
- Response: `ApplicationResponse`
- Auth: Authenticated users

### Binding Management

**POST /api/llm-bindings**
- Create new binding
- Request: `LLMBindingCreate`
- Response: `LLMBindingResponse`
- Auth: ADMIN role required

**GET /api/llm-bindings**
- List bindings with optional filters
- Query params: `application_id`, `llm_config_id`, `is_active`
- Response: `List[LLMBindingResponse]`
- Auth: ADMIN or TECHNICAL_EXPERT role

**GET /api/llm-bindings/{id}**
- Get single binding
- Response: `LLMBindingResponse`
- Auth: ADMIN or TECHNICAL_EXPERT role

**PUT /api/llm-bindings/{id}**
- Update binding
- Request: `LLMBindingUpdate`
- Response: `LLMBindingResponse`
- Auth: ADMIN role required

**DELETE /api/llm-bindings/{id}**
- Delete binding
- Response: 204 No Content
- Auth: ADMIN role required

---

## Frontend Design

### Component Structure

```
src/pages/admin/LLMConfig/
├── index.tsx                    # Main page component
├── LLMConfigList.tsx           # Configuration list with cards
├── LLMConfigForm.tsx           # Create/edit form
├── ApplicationBindings.tsx     # Application binding management
├── BindingForm.tsx             # Binding create/edit form
├── TestConnectionButton.tsx    # Test LLM connectivity
└── styles.module.css           # Component styles
```

### State Management (Zustand)

```typescript
interface LLMConfigStore {
  configs: LLMConfig[];
  applications: Application[];
  bindings: LLMBinding[];
  
  // Actions
  fetchConfigs: () => Promise<void>;
  createConfig: (data: LLMConfigCreate) => Promise<void>;
  updateConfig: (id: string, data: LLMConfigUpdate) => Promise<void>;
  deleteConfig: (id: string) => Promise<void>;
  testConnection: (id: string) => Promise<TestResult>;
  
  fetchApplications: () => Promise<void>;
  fetchBindings: (applicationId?: string) => Promise<void>;
  createBinding: (data: LLMBindingCreate) => Promise<void>;
  updateBinding: (id: string, data: LLMBindingUpdate) => Promise<void>;
  deleteBinding: (id: string) => Promise<void>;
  reorderBindings: (applicationId: string, newOrder: string[]) => Promise<void>;
}
```

### Internationalization

**Translation Namespace**: `llmConfig`

**Translation Files**:
- `frontend/src/locales/zh/llmConfig.json`
- `frontend/src/locales/en/llmConfig.json`

**Translation Keys Structure**:
```json
{
  "title": "LLM Configuration",
  "providers": {
    "openai": "OpenAI",
    "azure": "Azure OpenAI Service",
    "anthropic": "Anthropic Claude",
    "ollama": "Ollama (Local)",
    "custom": "Custom Provider"
  },
  "applications": {
    "structuring": "Data Structuring",
    "knowledge_graph": "Knowledge Graph",
    "ai_assistant": "AI Assistant"
  },
  "form": {
    "name": "Configuration Name",
    "provider": "Provider",
    "apiKey": "API Key",
    "baseUrl": "Base URL",
    "modelName": "Model Name",
    "parameters": "Parameters (JSON)"
  },
  "actions": {
    "create": "Create Configuration",
    "edit": "Edit",
    "delete": "Delete",
    "test": "Test Connection",
    "save": "Save",
    "cancel": "Cancel"
  },
  "messages": {
    "createSuccess": "Configuration created successfully",
    "updateSuccess": "Configuration updated successfully",
    "deleteSuccess": "Configuration deleted successfully",
    "testSuccess": "Connection test successful",
    "testFailed": "Connection test failed"
  }
}
```

### UI Components

**LLM Configuration Card**:
- Display: Name, provider icon, model name, status badge
- Actions: Edit, Delete, Test Connection buttons
- Status indicators: Active (green), Inactive (gray), Testing (blue)

**Binding Management**:
- Drag-and-drop list for priority reordering
- Visual priority indicators (1st, 2nd, 3rd)
- Inline editing for retry and timeout settings
- Add binding button with modal form

---

## Security Design

### API Key Encryption

**Algorithm**: AES-256-GCM
**Key Management**: Environment variable `LLM_ENCRYPTION_KEY` (32 bytes)
**Implementation**:

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64

class EncryptionService:
    def __init__(self):
        key = os.getenv("LLM_ENCRYPTION_KEY")
        if not key:
            raise ValueError("LLM_ENCRYPTION_KEY not set")
        self.key = base64.b64decode(key)
        self.aesgcm = AESGCM(self.key)
    
    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()
    
    def decrypt(self, encrypted: str) -> str:
        data = base64.b64decode(encrypted)
        nonce, ciphertext = data[:12], data[12:]
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()
```

### Access Control

**Role-Based Permissions**:
- `ADMIN`: Full CRUD access to configurations and bindings
- `TECHNICAL_EXPERT`: Read-only access to configurations
- `USER`: Can use LLMs through applications (no direct config access)

**Audit Logging**:
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: UUID
    user_id: UUID
    action: str  # CREATE, UPDATE, DELETE, ACCESS
    resource_type: str  # LLM_CONFIG, BINDING
    resource_id: UUID
    changes: dict  # JSON of what changed
    timestamp: datetime
```

---

## Cache Strategy

### Two-Tier Architecture

**Tier 1: Local Memory Cache**
- TTL: 300 seconds (5 minutes)
- Max memory: 100 MB
- Eviction: LRU (Least Recently Used)
- Scope: Per application instance

**Tier 2: Redis Cache (Optional)**
- TTL: 300 seconds (synchronized with local)
- Scope: Shared across all instances
- Pub/Sub channel: `llm:config:invalidate`

### Cache Key Format

```
llm:config:{application_code}:{tenant_id}
llm:config:{application_code}:global
```

### Invalidation Strategy

**Trigger Events**:
- LLM config created/updated/deleted
- Binding created/updated/deleted
- Application deactivated

**Invalidation Flow**:
1. Update database
2. Invalidate local cache
3. If Redis available, publish invalidation event
4. Other instances receive event and invalidate their local cache

### Cache Warming

**Startup Preload**:
- Load configurations for high-frequency applications
- Applications: `structuring`, `ai_assistant`, `rag_agent`

---

## Migration Strategy

### Alembic Migration Script

**File**: `alembic/versions/009_add_llm_application_binding.py`

**Upgrade Steps**:
1. Create `llm_applications` table
2. Insert initial application data
3. Create `llm_application_bindings` table
4. Create indexes and constraints
5. Add `tenant_id` column to `llm_configs` (if not exists)

**Downgrade Steps**:
1. Drop `llm_application_bindings` table
2. Drop `llm_applications` table
3. Remove `tenant_id` column from `llm_configs` (if added)

### Data Migration

**Existing LLM Configs**:
- No migration needed, existing configs remain as global defaults
- Applications can be bound to existing configs

**Environment Variables**:
- Continue to work as fallback
- No action required from users

---

## Backward Compatibility

### _load_cloud_config() Upgrade

**Old Implementation**:
```python
def _load_cloud_config(tenant_id: Optional[str] = None) -> CloudConfig:
    return CloudConfig(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model_name=os.getenv("OPENAI_MODEL")
    )
```

**New Implementation**:
```python
async def _load_cloud_config(
    tenant_id: Optional[str] = None,
    application_code: str = "structuring"
) -> CloudConfig:
    # Try database first
    configs = await app_llm_manager.get_llm_config(application_code, tenant_id)
    if configs:
        return configs[0]  # Return highest priority
    
    # Fallback to environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No LLM configuration found")
    
    return CloudConfig(
        provider="openai",
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    )
```

### Migration Path

**Phase 1: Deploy with backward compatibility**
- All existing code continues to work
- Environment variables still functional

**Phase 2: Configure database bindings**
- Admin creates LLM configs in database
- Admin creates bindings for applications

**Phase 3: Gradual cutover**
- Applications automatically use database configs
- Environment variables serve as fallback

**Phase 4: Remove environment variables (optional)**
- Once all configs in database, can remove env vars
- System fully managed through UI

---

## Performance Considerations

### Database Query Optimization

**Indexes**:
- Composite index on `(application_id, priority)` for binding queries
- Index on `(tenant_id, is_active)` for config queries
- Index on `is_active` for filtering

**Query Patterns**:
- Use eager loading for relationships to avoid N+1 queries
- Batch queries when loading multiple applications

### Cache Performance

**Target Metrics**:
- Cache hit rate: > 95%
- Cache retrieval latency: < 1ms
- Database retrieval latency: < 50ms

**Memory Management**:
- Monitor cache size with metrics
- Implement LRU eviction when approaching limit
- Alert if cache hit rate drops below 90%

### Failover Performance

**Retry Timing**:
- First retry: Immediate (0s delay)
- Second retry: 2s delay
- Third retry: 4s delay
- Total max time per LLM: timeout + 6s

**Optimization**:
- Parallel health checks for LLMs (future enhancement)
- Circuit breaker pattern to skip known-failing LLMs

---

## Deployment Checklist

- [ ] Set `LLM_ENCRYPTION_KEY` environment variable (32 bytes, base64)
- [ ] Run Alembic migration: `alembic upgrade head`
- [ ] Verify initial applications are registered
- [ ] Configure Redis connection (optional but recommended)
- [ ] Set up monitoring for cache hit rate and failover events
- [ ] Test environment variable fallback
- [ ] Create initial LLM configurations via API or UI
- [ ] Create bindings for critical applications
- [ ] Verify hot reload works (update config, check next request)
- [ ] Load test with expected concurrent request volume

---

**Document Status**: Complete  
**Ready for**: Task breakdown and implementation

