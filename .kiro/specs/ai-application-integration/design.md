# Design Document: AI Application Integration System

## Overview

The AI Application Integration System provides a comprehensive framework for integrating AI assistant gateways (starting with OpenClaw) into the SuperInsight platform. The system enables conversational access to governed data through custom skills, while maintaining strict security, multi-tenancy, and auditability.

### Key Design Principles

1. **Gateway-Agnostic Architecture**: Plugin-based design supports multiple AI gateway types
2. **Security First**: Multi-tenant isolation, credential management, and comprehensive auditing
3. **Skill-Based Integration**: Custom skills provide natural language interfaces to governed data
4. **Docker-Native**: Seamless integration with existing Docker Compose infrastructure
5. **Observability**: Full monitoring, health checks, and metrics integration with Prometheus

### Technology Choices

- **Backend**: Python 3.11+ with FastAPI (consistent with existing platform)
- **Database**: PostgreSQL for gateway registry, Redis for rate limiting
- **Container Orchestration**: Docker Compose (extends existing `docker-compose.yml`)
- **Skill Development**: Node.js (OpenClaw native runtime)
- **Authentication**: JWT tokens with API key authentication
- **Monitoring**: Prometheus metrics, integrated with existing Grafana dashboards

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    SuperInsight Platform                     │
│                                                              │
│  ┌──────────────┐      ┌─────────────────────────────────┐ │
│  │   Governed   │      │  AI Application Integration     │ │
│  │     Data     │◄─────┤         Service                 │ │
│  │  (Postgres,  │      │                                 │ │
│  │   Neo4j)     │      │  - Gateway Registry             │ │
│  └──────────────┘      │  - Data Access API              │ │
│                        │  - Skill Manager                │ │
│                        │  - Auth & Audit                 │ │
│                        └─────────────┬───────────────────┘ │
│                                      │                      │
└──────────────────────────────────────┼──────────────────────┘
                                       │
                                       │ Docker Network
                                       │
                        ┌──────────────▼──────────────┐
                        │      OpenClaw Gateway       │
                        │                             │
                        │  ┌──────────────────────┐   │
                        │  │  OpenClaw Agent (Pi) │   │
                        │  │                      │   │
                        │  │  ┌────────────────┐ │   │
                        │  │  │ SuperInsight   │ │   │
                        │  │  │     Skill      │ │   │
                        │  │  └────────────────┘ │   │
                        │  └──────────────────────┘   │
                        └─────────────┬───────────────┘
                                      │
                        ┌─────────────▼───────────────┐
                        │   Communication Channels    │
                        │  (WhatsApp, Telegram, etc.) │
                        └─────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              AI Application Integration Service              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Gateway Manager │  │  Skill Manager   │                │
│  │                  │  │                  │                │
│  │  - Registration  │  │  - Deployment    │                │
│  │  - Configuration │  │  - Versioning    │                │
│  │  - Health Check  │  │  - Hot Reload    │                │
│  └────────┬─────────┘  └────────┬─────────┘                │
│           │                     │                           │
│  ┌────────▼─────────────────────▼─────────┐                │
│  │        Data Access API Layer           │                │
│  │                                         │                │
│  │  - Authentication & Authorization       │                │
│  │  - Multi-Tenant Filtering              │                │
│  │  - Format Transformation               │                │
│  │  - Rate Limiting & Quotas              │                │
│  └────────┬────────────────────────────────┘                │
│           │                                                 │
│  ┌────────▼─────────────────────────────────┐              │
│  │         Security & Audit Layer           │              │
│  │                                           │              │
│  │  - Credential Management                 │              │
│  │  - Audit Logging                         │              │
│  │  - Security Event Detection              │              │
│  └───────────────────────────────────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Gateway Manager

**Responsibility**: Manages AI gateway lifecycle, registration, and configuration.

**Key Classes**:

```python
class GatewayManager:
    """Manages AI gateway registration and lifecycle."""
    
    def register_gateway(
        self,
        name: str,
        gateway_type: GatewayType,
        tenant_id: str,
        config: GatewayConfig
    ) -> Gateway:
        """Register a new AI gateway."""
        
    def deploy_gateway(self, gateway_id: str) -> DeploymentResult:
        """Deploy gateway using Docker Compose."""
        
    def update_configuration(
        self,
        gateway_id: str,
        config: GatewayConfig
    ) -> Gateway:
        """Update gateway configuration."""
        
    def health_check(self, gateway_id: str) -> HealthStatus:
        """Perform health check on gateway."""
        
    def deactivate_gateway(self, gateway_id: str) -> None:
        """Deactivate gateway and revoke credentials."""
```

**API Endpoints**:

- `POST /api/v1/ai-integration/gateways` - Register new gateway
- `GET /api/v1/ai-integration/gateways` - List gateways
- `GET /api/v1/ai-integration/gateways/{id}` - Get gateway details
- `PUT /api/v1/ai-integration/gateways/{id}` - Update gateway
- `DELETE /api/v1/ai-integration/gateways/{id}` - Deactivate gateway
- `POST /api/v1/ai-integration/gateways/{id}/deploy` - Deploy gateway
- `GET /api/v1/ai-integration/gateways/{id}/health` - Health check

### 2. Skill Manager

**Responsibility**: Manages skill deployment, versioning, and hot-reloading.

**Key Classes**:

```python
class SkillManager:
    """Manages skill packages and deployment."""
    
    def package_skill(
        self,
        skill_code: str,
        dependencies: List[str],
        config: SkillConfig
    ) -> SkillPackage:
        """Package skill for deployment."""
        
    def deploy_skill(
        self,
        gateway_id: str,
        skill_package: SkillPackage
    ) -> DeploymentResult:
        """Deploy skill to gateway."""
        
    def hot_reload_skill(
        self,
        gateway_id: str,
        skill_id: str
    ) -> None:
        """Hot reload skill without restarting gateway."""
        
    def list_skills(self, gateway_id: str) -> List[Skill]:
        """List deployed skills for gateway."""
```

**API Endpoints**:

- `POST /api/v1/ai-integration/skills` - Create skill package
- `GET /api/v1/ai-integration/skills` - List skills
- `POST /api/v1/ai-integration/skills/{id}/deploy` - Deploy skill
- `POST /api/v1/ai-integration/skills/{id}/reload` - Hot reload skill

### 3. Data Access API (Reuses Existing System)

**Responsibility**: Provides authenticated, authorized access to governed data.

**Existing APIs to Reuse**:

```python
# From src/api/export.py - EXISTING
@router.post("/api/v1/export/start")
async def start_export(request: ExportRequest) -> ExportJobResponse:
    """Export annotation data in AI-friendly formats (JSON, CSV, JSONL, COCO, Pascal VOC)"""

@router.get("/api/v1/export/status/{export_id}")
async def get_export_status(export_id: str) -> ExportStatusResponse:
    """Get export job status and progress"""

@router.get("/api/v1/export/download/{export_id}")
async def download_export(export_id: str) -> FileResponse:
    """Download exported AI-friendly data file"""

# From src/api/sync_pipeline.py - EXISTING
@router.post("/api/v1/sync/export")
async def export_data(request: ExportRequest) -> ExportResult:
    """Export synced data with semantic enrichment and data splitting"""

# From src/api/sync_datasets.py - EXISTING
@router.get("/api/v1/sync/datasets")
async def list_datasets(...) -> DatasetListResponse:
    """List available AI-friendly datasets"""

@router.get("/api/v1/sync/datasets/{dataset_id}/quality")
async def get_dataset_quality(dataset_id: UUID) -> DatasetQualityResponse:
    """Get quality metrics for AI-friendly dataset"""

@router.post("/api/v1/sync/datasets/generate")
async def generate_ai_dataset(request: AIDatasetGenerateRequest) -> DatasetResponse:
    """Generate AI-friendly dataset with quality optimization"""
```

**Existing Components to Reuse**:

```python
# From src/sync/pipeline/ai_exporter.py - EXISTING
class AIFriendlyExporter:
    """AI Friendly Exporter for data export - REUSE"""
    async def export(data, format, config) -> ExportResult
    def split_data(data, split_config) -> Dict[str, List]
    def generate_statistics_report(...) -> StatisticsReport
    
# From src/export/ - EXISTING
class ExportService:
    """Export service for annotation data - REUSE"""
    def export_data(export_id, request) -> ExportResult
    def get_export_status(export_id) -> ExportResult
```

**New Integration Layer**:

```python
class OpenClawDataBridge:
    """Bridges OpenClaw with existing data export APIs."""
    
    def __init__(
        self,
        export_service: ExportService,
        ai_exporter: AIFriendlyExporter
    ):
        self.export_service = export_service
        self.ai_exporter = ai_exporter
        
    async def query_governed_data(
        self,
        gateway_id: str,
        tenant_id: str,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query governed data using existing export APIs."""
        # Use existing ExportService
        export_request = ExportRequest(
            format=ExportFormat.JSON,
            filters=filters,
            include_semantics=True,
            desensitize=False
        )
        
        export_id = self.export_service.start_export(export_request)
        result = await self._wait_for_export(export_id)
        
        return self._format_for_openclaw(result)
        
    async def export_for_skill(
        self,
        gateway_id: str,
        data_query: Dict[str, Any],
        format: str = "json"
    ) -> bytes:
        """Export data in format suitable for OpenClaw skill."""
        # Use existing AIFriendlyExporter
        export_format = ExportFormat(format)
        config = ExportConfig(
            include_semantics=True,
            desensitize=False,
            split_config=None
        )
        
        result = await self.ai_exporter.export(
            data=data_query["results"],
            format=export_format,
            config=config
        )
        
        return result.exported_files[0].content
```

**New API Endpoints** (Thin wrappers around existing APIs):

- `GET /api/v1/ai-integration/data/query` - NEW: Query governed data (wraps existing export API)
- `POST /api/v1/ai-integration/data/export-for-skill` - NEW: Export for OpenClaw skill (wraps AIFriendlyExporter)
- `GET /api/v1/ai-integration/data/quality-metrics` - NEW: Get quality metrics (wraps dataset quality API)

**Integration Approach**:
1. Use existing `ExportService` for all data export operations
2. Use existing `AIFriendlyExporter` for format transformation
3. Use existing dataset quality APIs for quality metrics
4. Add thin wrapper layer (`OpenClawDataBridge`) to adapt existing APIs for OpenClaw
5. Maintain all existing authentication, authorization, and audit logging

### 4. Authentication Service

**Responsibility**: Manages API credentials and JWT token issuance.

**Key Classes**:

```python
class AuthenticationService:
    """Handles authentication for AI gateways."""
    
    def generate_credentials(
        self,
        gateway_id: str
    ) -> APICredentials:
        """Generate API key and secret."""
        
    def authenticate(
        self,
        api_key: str,
        api_secret: str
    ) -> AuthResult:
        """Authenticate gateway and issue JWT."""
        
    def validate_token(self, token: str) -> TokenClaims:
        """Validate JWT token."""
        
    def rotate_credentials(
        self,
        gateway_id: str
    ) -> APICredentials:
        """Rotate API credentials."""
```

### 5. Authorization Service

**Responsibility**: Enforces multi-tenant isolation and permission checks.

**Key Classes**:

```python
class AuthorizationService:
    """Enforces authorization and tenant isolation."""
    
    def check_permission(
        self,
        gateway_id: str,
        resource: str,
        action: str
    ) -> bool:
        """Check if gateway has permission."""
        
    def apply_tenant_filter(
        self,
        query: Query,
        tenant_id: str
    ) -> Query:
        """Apply tenant filter to database query."""
        
    def validate_cross_tenant_access(
        self,
        gateway_id: str,
        resource_tenant_id: str
    ) -> None:
        """Validate no cross-tenant access."""
```

### 6. Audit Service

**Responsibility**: Records all gateway activities for compliance and security.

**Key Classes**:

```python
class AuditService:
    """Records audit logs for all gateway activities."""
    
    def log_data_access(
        self,
        gateway_id: str,
        resource: str,
        action: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Log data access event."""
        
    def log_security_event(
        self,
        gateway_id: str,
        event_type: SecurityEventType,
        details: Dict[str, Any]
    ) -> None:
        """Log security event."""
        
    def query_audit_logs(
        self,
        filters: AuditFilters
    ) -> List[AuditLog]:
        """Query audit logs."""
```

### 7. Rate Limiter

**Responsibility**: Enforces rate limits and quotas.

**Key Classes**:

```python
class RateLimiter:
    """Enforces rate limits and quotas."""
    
    def check_rate_limit(
        self,
        gateway_id: str
    ) -> RateLimitResult:
        """Check if request is within rate limit."""
        
    def check_quota(
        self,
        gateway_id: str
    ) -> QuotaResult:
        """Check if request is within quota."""
        
    def record_request(
        self,
        gateway_id: str
    ) -> None:
        """Record request for rate limiting."""
```

### 8. Monitoring Service

**Responsibility**: Collects metrics and performs health checks.

**Key Classes**:

```python
class MonitoringService:
    """Collects metrics and performs health checks."""
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str]
    ) -> None:
        """Record Prometheus metric."""
        
    def health_check_gateway(
        self,
        gateway_id: str
    ) -> HealthStatus:
        """Perform health check."""
        
    def get_gateway_metrics(
        self,
        gateway_id: str,
        time_range: TimeRange
    ) -> Metrics:
        """Get gateway metrics."""
```

## Data Models

### Gateway Registry Schema

```python
class Gateway(Base):
    """AI Gateway registration."""
    __tablename__ = "ai_gateways"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gateway_type: Mapped[str] = mapped_column(String(50), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Configuration stored as JSONB
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Credentials (hashed)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Limits
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    quota_per_day: Mapped[int] = mapped_column(Integer, default=10000)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.utcnow)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    skills: Mapped[List["Skill"]] = relationship(back_populates="gateway")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="gateway")


class Skill(Base):
    """Skill package deployed to gateway."""
    __tablename__ = "ai_skills"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    gateway_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_gateways.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Skill code and configuration
    code_path: Mapped[str] = mapped_column(String(500), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dependencies: Mapped[list] = mapped_column(JSONB, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    gateway: Mapped["Gateway"] = relationship(back_populates="skills")


class AuditLog(Base):
    """Audit log for gateway activities."""
    __tablename__ = "ai_audit_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    gateway_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_gateways.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # User/channel information
    user_identifier: Mapped[Optional[str]] = mapped_column(String(255))
    channel: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Cryptographic signature for tamper detection
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Relationships
    gateway: Mapped["Gateway"] = relationship(back_populates="audit_logs")
```

### Configuration Schemas

```python
class GatewayConfig(BaseModel):
    """Gateway configuration schema."""
    channels: List[ChannelConfig]
    ai_models: List[AIModelConfig]
    network_settings: NetworkSettings
    custom_settings: Dict[str, Any] = {}


class ChannelConfig(BaseModel):
    """Channel configuration for OpenClaw."""
    channel_type: str  # whatsapp, telegram, slack, etc.
    enabled: bool
    credentials: Dict[str, str]
    settings: Dict[str, Any] = {}


class SkillConfig(BaseModel):
    """Skill configuration schema."""
    name: str
    description: str
    entry_point: str
    environment_variables: Dict[str, str] = {}
    permissions: List[str]
    timeout_seconds: int = 30
```

### Docker Compose Integration

```yaml
# Addition to existing docker-compose.yml
services:
  openclaw-gateway:
    image: openclaw/gateway:latest
    container_name: superinsight-openclaw-gateway
    environment:
      - SUPERINSIGHT_API_URL=http://backend:8000
      - SUPERINSIGHT_API_KEY=${OPENCLAW_API_KEY}
      - SUPERINSIGHT_TENANT_ID=${TENANT_ID}
    networks:
      - superinsight-network
    ports:
      - "3000:3000"
    volumes:
      - openclaw-config:/app/config
      - openclaw-memory:/app/memory
    depends_on:
      - backend
      - postgres
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  openclaw-agent:
    image: openclaw/agent:latest
    container_name: superinsight-openclaw-agent
    environment:
      - GATEWAY_URL=http://openclaw-gateway:3000
      - SUPERINSIGHT_API_URL=http://backend:8000
      - SUPERINSIGHT_API_KEY=${OPENCLAW_API_KEY}
    networks:
      - superinsight-network
    volumes:
      - openclaw-skills:/app/skills
      - openclaw-memory:/app/memory
    depends_on:
      - openclaw-gateway
      - backend
    restart: unless-stopped

volumes:
  openclaw-config:
  openclaw-skills:
  openclaw-memory:
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Gateway Registration Completeness
*For any* gateway registration request with valid parameters, all required metadata fields (name, type, version, channels, configuration, tenant_id) should be stored in the Gateway_Registry and retrievable.
**Validates: Requirements 2.1**

### Property 2: API Credential Uniqueness
*For any* set of registered gateways, all API credentials (api_key, api_secret) should be unique across the system.
**Validates: Requirements 2.2**

### Property 3: Configuration Validation
*For any* gateway configuration update, invalid configurations (missing required fields, invalid types, or schema violations) should be rejected before persistence.
**Validates: Requirements 2.3, 9.1, 10.2**

### Property 4: Configuration Versioning
*For any* gateway configuration update, the Gateway_Registry should create a new version entry with timestamp and change author, and all previous versions should remain accessible.
**Validates: Requirements 2.4, 9.5**

### Property 5: Gateway Deactivation Completeness
*For any* gateway deactivation, the gateway's API credentials should be revoked, all associated skills should be disabled, and subsequent authentication attempts should fail.
**Validates: Requirements 2.5**

### Property 6: Authenticated and Authorized Data Access
*For any* data access request, if authentication succeeds and the gateway has permission for the requested resource within its tenant, then data should be returned; otherwise, the request should be rejected with appropriate error code.
**Validates: Requirements 3.1, 3.2**

### Property 7: JSON Response Format
*For any* successful data access request, the response should be valid JSON that can be parsed without errors.
**Validates: Requirements 3.3**

### Property 8: Data Filtering Functionality
*For any* data access request with filters (dataset, annotation status, quality score, metadata tags), only data matching all specified filters should be returned.
**Validates: Requirements 3.4**

### Property 9: Pagination Consistency
*For any* large dataset request with pagination, the union of all pages should equal the complete dataset, with no duplicates or missing records.
**Validates: Requirements 3.5**

### Property 10: Error Response Completeness
*For any* failed API request, the response should include an appropriate HTTP status code (4xx or 5xx) and a descriptive error message.
**Validates: Requirements 3.6**

### Property 11: Single Tenant Association
*For any* registered gateway, it should be associated with exactly one tenant_id, and this association should be immutable unless explicitly changed through tenant reassignment.
**Validates: Requirements 4.1**

### Property 12: Multi-Tenant Data Isolation
*For any* data access request from a gateway, all returned data should belong exclusively to the gateway's assigned tenant, with no cross-tenant data leakage.
**Validates: Requirements 4.2, 4.4**

### Property 13: Cross-Tenant Access Rejection
*For any* attempt to access data from a different tenant, the request should be rejected with a security error, and a security event should be logged in the Audit_Log.
**Validates: Requirements 4.3**

### Property 14: Tenant Reassignment Session Invalidation
*For any* gateway tenant reassignment, all existing JWT tokens and sessions for that gateway should be invalidated, and new credentials should be generated.
**Validates: Requirements 4.5**

### Property 15: Skill Authentication
*For any* skill invocation, the skill should authenticate with SuperInsight using the gateway's API credentials before accessing data.
**Validates: Requirements 5.2**

### Property 16: Natural Language Query Translation
*For any* natural language query through OpenClaw, the SuperInsight_Skill should translate it into one or more Data_Access_API calls with appropriate parameters.
**Validates: Requirements 5.3**

### Property 17: Channel-Appropriate Formatting
*For any* data retrieval through a skill, the results should be formatted appropriately for the channel (WhatsApp, Telegram, etc.) with proper text length and structure constraints.
**Validates: Requirements 5.4**

### Property 18: User-Friendly Error Messages
*For any* skill execution failure, the error message returned to the user should be in natural language, avoid technical jargon, and suggest corrective actions when possible.
**Validates: Requirements 5.5**

### Property 19: Metrics Recording Completeness
*For any* gateway data access, metrics including request count, latency, error rate, and skill execution time should be recorded and available for querying.
**Validates: Requirements 6.3**

### Property 20: JWT Token Issuance
*For any* successful authentication, a JWT token should be issued with tenant_id and permissions in the claims, and the token should be valid for the configured duration.
**Validates: Requirements 7.2**

### Property 21: Expired Token Rejection
*For any* API request with an expired JWT token, the request should be rejected with HTTP 401 status, and the client should be required to re-authenticate.
**Validates: Requirements 7.3**

### Property 22: Authentication Failure Rate Limiting
*For any* gateway with multiple consecutive authentication failures (exceeding threshold), subsequent authentication attempts should be rate-limited with exponential backoff, and temporary lockout should be applied.
**Validates: Requirements 7.5**

### Property 23: Comprehensive Audit Logging
*For any* gateway data access or operation, an audit log entry should be created containing gateway_id, skill_name, timestamp, user/channel, resource, action, operation_type, parameters, result_status, and cryptographic signature.
**Validates: Requirements 8.1, 8.2**

### Property 24: Audit Log Immutability
*For any* audit log entry, once written, it should not be modifiable, and any tampering should be detectable through signature verification.
**Validates: Requirements 8.3**

### Property 25: Audit Log Query Filtering
*For any* audit log query with filters (gateway, tenant, skill, time range, operation type), only logs matching all specified filters should be returned.
**Validates: Requirements 8.4**

### Property 26: Configuration Change Notification
*For any* gateway configuration update, all affected gateways should be notified of the change within a reasonable time window (e.g., 30 seconds).
**Validates: Requirements 9.2**

### Property 27: Latest Configuration Retrieval
*For any* gateway restart or configuration request, the gateway should receive the most recent configuration version from the Gateway_Configuration.
**Validates: Requirements 9.3**

### Property 28: Secret Encryption
*For any* configuration containing secrets (API keys, passwords, tokens), the sensitive values should be encrypted using AES-256 before storage, and decrypted only when needed.
**Validates: Requirements 9.4**

### Property 29: Data Format Transformation with Preservation
*For any* data format conversion request, the transformed data should preserve all annotations, metadata, and lineage information from the original format.
**Validates: Requirements 11.2**

### Property 30: Format-Specific Structure Handling
*For any* data with nested structures, the conversion should flatten or preserve structure based on the target format's capabilities (flatten for CSV, preserve for JSON/Parquet).
**Validates: Requirements 11.3**

### Property 31: Binary Content Encoding
*For any* data containing binary content, the encoding should be appropriate for the target format (Base64 for JSON/CSV, raw bytes for Parquet/MessagePack).
**Validates: Requirements 11.4**

### Property 32: Format Conversion Fallback
*For any* format conversion failure, the API should return the data in its original format with a warning header and error details explaining the conversion failure.
**Validates: Requirements 11.5**

### Property 33: Rate Limit Enforcement
*For any* gateway, when the number of requests in the current time window exceeds the configured rate limit, subsequent requests should be rejected with HTTP 429 status and Retry-After header.
**Validates: Requirements 12.2**

### Property 34: Immediate Limit Updates
*For any* rate limit or quota adjustment by an administrator, the new limits should be applied to the gateway immediately without requiring restart, and the next request should use the new limits.
**Validates: Requirements 12.4**

### Property 35: Usage Counter Management
*For any* gateway, usage counters should reset based on the configured time window (sliding or fixed), and historical usage data should be persisted for reporting.
**Validates: Requirements 12.5**

### Property 36: Language Preference Persistence
*For any* user language preference change, the preference should be persisted to the user's profile and applied to all subsequent sessions until changed again.
**Validates: Requirements 13.2**

### Property 37: UI Language Switching
*For any* language switch request between Chinese (zh-CN) and English (en-US), all UI text elements should update to the selected language.
**Validates: Requirements 13.3**

### Property 38: Localized Error Messages
*For any* error response from the Data_Access_API, the error message should be localized based on the Accept-Language header (zh-CN or en-US).
**Validates: Requirements 13.4**

### Property 39: Localized Audit Log Display
*For any* audit log display request, timestamps should be formatted according to the user's locale, and operation names should be translated to the user's selected language.
**Validates: Requirements 13.5**

## Error Handling

### Error Categories

1. **Authentication Errors**
   - Invalid API credentials → HTTP 401
   - Expired JWT token → HTTP 401
   - Rate limit exceeded → HTTP 429

2. **Authorization Errors**
   - Insufficient permissions → HTTP 403
   - Cross-tenant access attempt → HTTP 403 + security log

3. **Validation Errors**
   - Invalid configuration → HTTP 400 with field-specific errors
   - Missing required parameters → HTTP 400
   - Invalid data format → HTTP 400

4. **Resource Errors**
   - Gateway not found → HTTP 404
   - Skill not found → HTTP 404
   - Dataset not found → HTTP 404

5. **System Errors**
   - Database connection failure → HTTP 503
   - Docker deployment failure → HTTP 500
   - External service unavailable → HTTP 503

### Error Response Format

```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid API credentials",
    "message_zh": "API 凭证无效",
    "details": {
      "field": "api_key",
      "reason": "Key not found in registry"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Retry Strategy

- **Transient Errors (503)**: Exponential backoff with jitter
- **Rate Limit (429)**: Respect Retry-After header
- **Authentication (401)**: Re-authenticate once, then fail
- **Client Errors (4xx)**: Do not retry

## Testing Strategy

### Unit Testing

Unit tests focus on individual components and specific scenarios:

1. **Gateway Manager Tests**
   - Test gateway registration with valid/invalid data
   - Test configuration validation logic
   - Test credential generation uniqueness
   - Test deactivation workflow

2. **Authentication Service Tests**
   - Test API key hashing and validation
   - Test JWT token generation and validation
   - Test token expiration handling
   - Test credential rotation

3. **Authorization Service Tests**
   - Test tenant filter injection
   - Test permission checking logic
   - Test cross-tenant access detection

4. **Data Access API Tests**
   - Test data filtering logic
   - Test pagination implementation
   - Test format transformation
   - Test error response formatting

5. **Audit Service Tests**
   - Test log entry creation
   - Test signature generation and verification
   - Test log query filtering

6. **Rate Limiter Tests**
   - Test rate limit enforcement
   - Test quota tracking
   - Test counter reset logic

### Property-Based Testing

Property-based tests validate universal properties across randomized inputs. Each test should run minimum 100 iterations.

**Configuration**:
- Use `pytest` with `hypothesis` library for Python
- Minimum 100 iterations per property test
- Tag format: `# Feature: ai-application-integration, Property {N}: {property_text}`

**Key Property Tests**:

1. **Property 2: API Credential Uniqueness**
   - Generate N random gateway registrations
   - Verify all API keys are unique
   - Verify all API secrets are unique

2. **Property 12: Multi-Tenant Data Isolation**
   - Generate random gateways with different tenants
   - Generate random data access requests
   - Verify returned data only belongs to gateway's tenant

3. **Property 23: Comprehensive Audit Logging**
   - Generate random gateway operations
   - Verify audit log contains all required fields
   - Verify signature is valid

4. **Property 29: Data Format Transformation with Preservation**
   - Generate random data with annotations and metadata
   - Convert to different formats
   - Verify annotations and metadata are preserved

5. **Property 33: Rate Limit Enforcement**
   - Generate requests exceeding rate limit
   - Verify requests are rejected with HTTP 429
   - Verify Retry-After header is present

### Integration Testing

Integration tests verify component interactions:

1. **End-to-End Gateway Registration**
   - Register gateway → Deploy Docker containers → Verify health check

2. **End-to-End Data Access**
   - Authenticate → Request data → Verify response → Check audit log

3. **End-to-End Skill Execution**
   - Deploy skill → Invoke through OpenClaw → Verify data access → Check metrics

4. **Multi-Tenant Isolation**
   - Create gateways for different tenants → Attempt cross-tenant access → Verify rejection

5. **Configuration Hot Reload**
   - Update configuration → Verify gateway receives update → Verify no restart

### Docker Integration Testing

Test Docker Compose integration:

1. **Container Startup**
   - Verify OpenClaw containers start successfully
   - Verify network connectivity
   - Verify environment variables are injected

2. **Health Checks**
   - Verify health check endpoints respond
   - Verify unhealthy containers trigger alerts

3. **Volume Persistence**
   - Stop containers → Restart → Verify state is preserved

## Implementation Notes

### Security Considerations

1. **Credential Storage**: Use bcrypt or Argon2 for API key hashing
2. **JWT Signing**: Use RS256 with key rotation
3. **Audit Log Signatures**: Use HMAC-SHA256 with secret key
4. **Secret Encryption**: Use AES-256-GCM for configuration secrets
5. **Network Security**: Use TLS for all external communications

### Performance Considerations

1. **Rate Limiting**: Use Redis for distributed rate limiting
2. **Caching**: Cache gateway configurations in Redis (TTL: 5 minutes)
3. **Database Indexing**: Index tenant_id, gateway_id, timestamp fields
4. **Connection Pooling**: Use connection pools for PostgreSQL and Redis
5. **Async Operations**: Use async/await for I/O-bound operations

### Scalability Considerations

1. **Horizontal Scaling**: Stateless API design supports multiple instances
2. **Database Sharding**: Partition audit logs by time range
3. **Load Balancing**: Use round-robin for gateway requests
4. **Queue-Based Processing**: Use Celery for async skill deployment

### Internationalization Implementation (Reuses Existing System)

**Existing i18n Infrastructure to Reuse**:

```python
# From src/i18n/ - EXISTING
from src.i18n import TranslationManager, get_manager

# Backend usage
i18n = get_manager()
message = i18n.t('aiIntegration.error.gatewayNotFound', language='zh')

# Existing features:
# - TranslationManager: Unified translation interface
# - Hot reload: Dynamic translation updates without restart
# - Performance optimization: Caching and precomputation
# - Thread safety: Context-aware language switching
# - Validation: Translation completeness and consistency checks
# - Formatters: Date, time, number, currency formatting
```

**Frontend i18n** (react-i18next):

```typescript
// From frontend/src/locales/ - EXISTING
import { useTranslation } from 'react-i18next';

const { t } = useTranslation('aiIntegration');
const title = t('gateway.title');

// Existing structure:
// - frontend/src/locales/zh/*.json - Chinese translations
// - frontend/src/locales/en/*.json - English translations
// - 27 existing translation namespaces
```

**New Translation Files** (Following existing structure):

1. **Backend Translation Files**:
   - Add to existing `src/i18n/translations.py` TRANSLATIONS dict
   - Follow existing key structure: `'aiIntegration.gateway.title'`
   - Use existing `TranslationManager` for all translations

2. **Frontend Translation Files**:
   - Create `frontend/src/locales/zh/aiIntegration.json`
   - Create `frontend/src/locales/en/aiIntegration.json`
   - Follow existing naming convention (camelCase namespace)

**Translation Key Structure** (Following existing conventions):

```json
{
  "aiIntegration": {
    "title": "AI 应用集成",
    "gateway": {
      "title": "网关管理",
      "register": "注册网关",
      "deploy": "部署网关",
      "status": "状态",
      "health": "健康检查"
    },
    "skill": {
      "title": "技能管理",
      "deploy": "部署技能",
      "reload": "重新加载",
      "status": "状态"
    },
    "dataAccess": {
      "title": "数据访问",
      "query": "查询数据",
      "export": "导出数据",
      "format": "数据格式"
    },
    "workflow": {
      "title": "工作流设计",
      "playground": "工作流游乐场",
      "library": "工作流库",
      "execute": "执行",
      "compare": "比较结果"
    },
    "quality": {
      "title": "质量对比",
      "governed": "AI友好型数据（已治理）",
      "raw": "原始数据（未治理）",
      "metrics": "质量指标",
      "improvement": "改进百分比"
    },
    "audit": {
      "title": "审计日志",
      "event": "事件",
      "timestamp": "时间戳",
      "user": "用户",
      "action": "操作"
    },
    "error": {
      "gatewayNotFound": "网关未找到",
      "skillDeployFailed": "技能部署失败",
      "authenticationFailed": "认证失败",
      "rateLimitExceeded": "请求频率超限",
      "crossTenantAccess": "跨租户访问被拒绝"
    },
    "success": {
      "gatewayRegistered": "网关注册成功",
      "gatewayDeployed": "网关部署成功",
      "skillDeployed": "技能部署成功",
      "configurationUpdated": "配置更新成功"
    }
  }
}
```

**Backend i18n Usage** (Using existing TranslationManager):

```python
from src.i18n import get_manager

i18n = get_manager()

# In API endpoints
@router.post("/api/v1/ai-integration/gateways")
async def register_gateway(...):
    # Use existing TranslationManager
    message = i18n.t('aiIntegration.success.gatewayRegistered', language='zh')
    return {"message": message}

# In error responses
@router.exception_handler(GatewayNotFoundError)
async def gateway_not_found_handler(request, exc):
    language = request.headers.get('Accept-Language', 'zh')
    message = i18n.t('aiIntegration.error.gatewayNotFound', language=language)
    return JSONResponse({"error": message}, status_code=404)
```

**Frontend i18n Usage** (Using existing react-i18next):

```typescript
import { useTranslation } from 'react-i18next';

const GatewayManagement: React.FC = () => {
  const { t } = useTranslation('aiIntegration');
  
  return (
    <div>
      <h1>{t('gateway.title')}</h1>
      <Button>{t('gateway.register')}</Button>
    </div>
  );
};
```

### OpenClaw Language Integration (Using SuperInsight i18n)

**Current State**: OpenClaw does not have built-in internationalization support. It primarily operates in English with no system-level language switching mechanism.

**Integration Strategy**: Use SuperInsight's i18n system to provide multilingual support for OpenClaw interactions.

**Implementation Approach**:

1. **System Prompt Injection** (Primary Method):
   ```python
   class OpenClawLanguageAdapter:
       """Adapts OpenClaw responses to user's language preference."""
       
       def __init__(self, i18n_manager: TranslationManager):
           self.i18n = i18n_manager
           
       def get_system_prompt_for_language(self, language: str) -> str:
           """Generate language-specific system prompt for OpenClaw."""
           if language == 'zh':
               return """You are an AI assistant integrated with SuperInsight platform.
   IMPORTANT: Always respond in Simplified Chinese (简体中文).
   When describing data, use Chinese terms:
   - "数据集" for dataset
   - "标注" for annotation
   - "质量" for quality
   - "已治理数据" for governed data
   - "原始数据" for raw data
   
   Format all dates, numbers, and currencies according to Chinese conventions."""
           else:
               return """You are an AI assistant integrated with SuperInsight platform.
   Respond in English and format data according to international conventions."""
       
       def inject_language_context(
           self,
           gateway_id: str,
           user_language: str
       ) -> Dict[str, str]:
           """Inject language context into OpenClaw environment."""
           system_prompt = self.get_system_prompt_for_language(user_language)
           
           return {
               'OPENCLAW_SYSTEM_PROMPT': system_prompt,
               'OPENCLAW_USER_LANGUAGE': user_language,
               'OPENCLAW_LOCALE': 'zh-CN' if user_language == 'zh' else 'en-US'
           }
   ```

2. **Response Translation** (Fallback Method):
   ```python
   class OpenClawResponseTranslator:
       """Translates OpenClaw responses if needed."""
       
       def __init__(self, i18n_manager: TranslationManager):
           self.i18n = i18n_manager
           
       async def translate_response(
           self,
           response: str,
           target_language: str
       ) -> str:
           """Translate OpenClaw response to target language."""
           if target_language == 'zh':
               # Use LLM to translate technical responses
               # Preserve code blocks, file paths, and technical terms
               return await self._llm_translate(response, 'zh')
           return response
       
       def localize_data_format(
           self,
           data: Dict[str, Any],
           language: str
       ) -> Dict[str, Any]:
           """Localize data formatting (dates, numbers, etc.)."""
           # Use existing formatters from src/i18n/formatters.py
           from src.i18n.formatters import (
               format_date,
               format_number,
               format_currency
           )
           
           # Apply locale-specific formatting
           return self._apply_formatters(data, language)
   ```

3. **Skill-Level Language Support**:
   ```javascript
   // In SuperInsight OpenClaw Skill (Node.js)
   class SuperInsightSkill {
       constructor(config) {
           this.apiUrl = config.SUPERINSIGHT_API_URL;
           this.userLanguage = config.OPENCLAW_USER_LANGUAGE || 'zh';
       }
       
       async handleMessage(message) {
           // Get user's language preference from SuperInsight
           const userProfile = await this.getUserProfile(message.userId);
           const language = userProfile.language || 'zh';
           
           // Include language in all API requests
           const headers = {
               'Accept-Language': language,
               'Authorization': `Bearer ${this.apiToken}`
           };
           
           // Fetch data with language preference
           const data = await this.fetchGovernedData(message.query, headers);
           
           // Format response in user's language
           return this.formatResponse(data, language);
       }
       
       formatResponse(data, language) {
           if (language === 'zh') {
               return `找到 ${data.count} 条已治理数据记录：\n${this.formatDataList(data.items, 'zh')}`;
           } else {
               return `Found ${data.count} governed data records:\n${this.formatDataList(data.items, 'en')}`;
           }
       }
   }
   ```

4. **Gateway Configuration**:
   ```yaml
   # docker-compose.ai-integration.yml
   services:
     openclaw-gateway:
       environment:
         # Inject language settings from SuperInsight
         - OPENCLAW_SYSTEM_PROMPT=${OPENCLAW_SYSTEM_PROMPT}
         - OPENCLAW_USER_LANGUAGE=${USER_LANGUAGE:-zh}
         - OPENCLAW_LOCALE=${LOCALE:-zh-CN}
         # SuperInsight API settings
         - SUPERINSIGHT_API_URL=http://app:8000
         - SUPERINSIGHT_API_KEY=${OPENCLAW_API_KEY}
   ```

5. **User Language Preference Flow**:
   ```
   User Login → SuperInsight detects/stores language preference (zh/en)
        ↓
   User registers OpenClaw gateway → Language preference passed to gateway
        ↓
   Gateway deployment → System prompt injected with language instructions
        ↓
   User sends message via WhatsApp/Telegram → Skill uses language preference
        ↓
   Skill queries SuperInsight API → Accept-Language header set
        ↓
   Response formatted in user's language → Sent back through OpenClaw
   ```

**Default Language**: Chinese (zh-CN) - Following SuperInsight's default

**Language Detection Priority**:
1. User's explicit language preference in SuperInsight profile
2. Gateway configuration language setting
3. Default to Chinese (zh)

**Supported Languages**:
- Chinese (zh-CN) - Primary, default
- English (en-US) - Secondary

**Integration Points**:
- Gateway registration: Store user's language preference
- Gateway deployment: Inject language-specific system prompt
- Skill execution: Use Accept-Language header in API calls
- Response formatting: Apply locale-specific formatting
- Error messages: Use SuperInsight's TranslationManager

**Benefits of This Approach**:
1. No modification to OpenClaw core required
2. Leverages SuperInsight's existing i18n infrastructure
3. Consistent language experience across platform
4. Easy to extend to additional languages
5. Respects user's language preference throughout the system

**Translation File Synchronization** (Using existing validation):
- All language files must have identical key structures
- Use existing `TranslationValidator` for consistency checks
- No duplicate keys allowed within a file

**Integration Approach**:
1. Use existing `TranslationManager` for all backend translations
2. Use existing `react-i18next` setup for frontend
3. Add new translation keys to existing TRANSLATIONS dict (backend)
4. Create new namespace files following existing structure (frontend)
5. Use existing validation tools to ensure consistency
6. Leverage existing hot-reload for development

### Monitoring and Observability

**Prometheus Metrics**:
- `ai_gateway_requests_total{gateway_id, status}` - Total requests
- `ai_gateway_request_duration_seconds{gateway_id}` - Request latency
- `ai_gateway_errors_total{gateway_id, error_type}` - Error count
- `ai_gateway_rate_limit_exceeded_total{gateway_id}` - Rate limit violations
- `ai_skill_execution_duration_seconds{gateway_id, skill_name}` - Skill execution time

**Health Check Endpoints**:
- `/health` - Overall system health
- `/health/gateway/{id}` - Specific gateway health
- `/health/database` - Database connectivity
- `/health/docker` - Docker daemon connectivity

**Logging Strategy**:
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include request_id in all logs for tracing
- Separate audit logs from application logs

## Deployment Strategy

### Phase 1: Core Infrastructure (Week 1-2)
1. Database schema creation
2. Gateway Manager implementation
3. Authentication Service implementation
4. Basic API endpoints

### Phase 2: Data Access (Week 3-4)
1. Data Access API implementation
2. Multi-tenant isolation
3. Format transformation
4. Rate limiting

### Phase 3: OpenClaw Integration (Week 5-6)
1. Docker Compose configuration
2. SuperInsight Skill development
3. Skill Manager implementation
4. Hot reload functionality

### Phase 4: Security & Audit (Week 7-8)
1. Audit logging implementation
2. Security event detection
3. Credential rotation
4. Comprehensive testing

### Phase 5: Monitoring & i18n (Week 9-10)
1. Prometheus metrics integration
2. Health check implementation
3. Internationalization
4. Dashboard development

### Phase 6: Testing & Documentation (Week 11-12)
1. Property-based testing
2. Integration testing
3. Performance testing
4. Documentation and training

## Conversational Workflow Design Components

### 9. Workflow Designer Service

**Responsibility**: Parses natural language workflow descriptions and generates structured workflow definitions.

**Key Classes**:

```python
class WorkflowDesigner:
    """Parses and generates workflow definitions from natural language."""
    
    def parse_workflow_description(
        self,
        description: str,
        tenant_id: str
    ) -> WorkflowDefinition:
        """Parse natural language into structured workflow."""
        
    def validate_workflow(
        self,
        workflow: WorkflowDefinition,
        tenant_id: str
    ) -> ValidationResult:
        """Validate workflow against available datasets and permissions."""
        
    def execute_workflow(
        self,
        workflow_id: str,
        use_governed_data: bool = True
    ) -> WorkflowResult:
        """Execute workflow with governed or raw data."""
        
    def compare_results(
        self,
        workflow_id: str
    ) -> ComparisonResult:
        """Execute workflow with both data types and compare results."""
```

**API Endpoints**:

- `POST /api/v1/ai-integration/workflows/parse` - Parse natural language to workflow
- `POST /api/v1/ai-integration/workflows` - Save workflow definition
- `GET /api/v1/ai-integration/workflows` - List workflows
- `GET /api/v1/ai-integration/workflows/{id}` - Get workflow details
- `POST /api/v1/ai-integration/workflows/{id}/execute` - Execute workflow
- `POST /api/v1/ai-integration/workflows/{id}/compare` - Compare governed vs raw data results

### 10. Quality Comparison Service

**Responsibility**: Evaluates and compares data quality between governed and raw data sources.

**Key Classes**:

```python
class QualityComparisonService:
    """Compares quality metrics between governed and raw data."""
    
    def evaluate_quality(
        self,
        data: Any,
        is_governed: bool
    ) -> QualityMetrics:
        """Evaluate data quality using Ragas framework."""
        
    def compare_datasets(
        self,
        governed_data: Any,
        raw_data: Any
    ) -> ComparisonMetrics:
        """Compare quality metrics between datasets."""
        
    def generate_comparison_report(
        self,
        comparison: ComparisonMetrics
    ) -> ComparisonReport:
        """Generate detailed comparison report with visualizations."""
```

**Quality Metrics**:
- **Completeness**: Percentage of non-null values
- **Accuracy**: Validation against known ground truth
- **Consistency**: Cross-field validation and format compliance
- **Timeliness**: Data freshness and update frequency
- **AI Confidence**: Model confidence scores when using data
- **Semantic Quality**: Ragas-based semantic evaluation

### 11. LLM Configuration Integration (Reuses Existing System)

**Responsibility**: Integrates OpenClaw with existing LLM configuration management system.

**Existing Components to Reuse**:

```python
# From src/ai/llm_config_manager.py
class LLMConfigManager:
    """Existing LLM configuration manager - REUSE"""
    async def get_config(tenant_id: Optional[str] = None) -> LLMConfig
    async def save_config(config: LLMConfig, tenant_id: Optional[str] = None) -> LLMConfig
    async def hot_reload(tenant_id: Optional[str] = None) -> LLMConfig
    async def log_usage(...)
    
# From src/ai/llm_switcher.py
class LLMSwitcher:
    """Existing LLM provider switcher - REUSE"""
    async def generate(...) -> LLMResponse
    async def stream_generate(...) -> AsyncIterator[str]
    def switch_method(method: LLMMethod) -> None
    async def health_check(...) -> Dict[LLMMethod, HealthStatus]
    
# From src/ai/china_llm_adapter.py
class ChinaLLMProvider:
    """Existing China LLM providers - REUSE"""
    # Supports: Qwen, Zhipu, Baidu, Hunyuan
```

**New Integration Layer**:

```python
class OpenClawLLMBridge:
    """Bridges OpenClaw with existing LLM system."""
    
    def __init__(
        self,
        config_manager: LLMConfigManager,
        llm_switcher: LLMSwitcher
    ):
        self.config_manager = config_manager
        self.llm_switcher = llm_switcher
        
    async def get_openclaw_env_vars(
        self,
        gateway_id: str,
        tenant_id: str
    ) -> Dict[str, str]:
        """Generate OpenClaw environment variables from LLM config."""
        config = await self.config_manager.get_config(tenant_id)
        
        # Map LLMConfig to OpenClaw environment variables
        return {
            'LLM_PROVIDER': self._map_provider(config.active_method),
            'LLM_API_ENDPOINT': self._get_endpoint(config),
            'LLM_MODEL': self._get_model(config),
            'LLM_API_KEY': self._get_api_key(config),
            'LLM_TEMPERATURE': str(config.temperature),
            'LLM_MAX_TOKENS': str(config.max_tokens),
        }
        
    def _map_provider(self, method: LLMMethod) -> str:
        """Map LLMMethod to OpenClaw provider name."""
        mapping = {
            LLMMethod.OPENAI: 'openai',
            LLMMethod.ANTHROPIC: 'anthropic',
            LLMMethod.QWEN: 'qwen',
            LLMMethod.ZHIPU: 'zhipu',
            LLMMethod.BAIDU: 'baidu',
            LLMMethod.OLLAMA: 'ollama',
            LLMMethod.DOCKER: 'ollama',  # Docker LLM uses Ollama protocol
        }
        return mapping.get(method, 'openai')
        
    async def handle_llm_request(
        self,
        gateway_id: str,
        prompt: str,
        options: Optional[Dict] = None
    ) -> LLMResponse:
        """Handle LLM request from OpenClaw skill."""
        # Use existing LLMSwitcher
        return await self.llm_switcher.generate(
            prompt=prompt,
            options=GenerateOptions(**(options or {}))
        )
        
    async def monitor_usage(
        self,
        gateway_id: str,
        response: LLMResponse
    ) -> None:
        """Log LLM usage for monitoring."""
        # Extend existing log_usage
        await self.config_manager.log_usage(
            method=self.llm_switcher.get_current_method(),
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_ms=response.latency_ms,
            metadata={'gateway_id': gateway_id}
        )
```

**API Endpoints** (Extend existing admin API):

- `GET /api/v1/admin/config/llm` - List LLM configs (EXISTING)
- `POST /api/v1/admin/config/llm` - Create LLM config (EXISTING)
- `PUT /api/v1/admin/config/llm/{id}` - Update LLM config (EXISTING)
- `DELETE /api/v1/admin/config/llm/{id}` - Delete LLM config (EXISTING)
- `POST /api/v1/admin/config/llm/{id}/test` - Test connection (EXISTING)
- `POST /api/v1/ai-integration/gateways/{id}/llm-config` - NEW: Link gateway to LLM config
- `GET /api/v1/ai-integration/gateways/{id}/llm-status` - NEW: Get LLM status for gateway

### 12. LLM Monitoring Extension

**Responsibility**: Extends existing monitoring to track OpenClaw-specific LLM usage.

**Existing Monitoring to Extend**:

```python
# Existing in src/ai/llm/health_monitor.py
class HealthMonitor:
    """Existing health monitoring - EXTEND"""
    
# Existing in src/ai/llm/audit_service.py  
class AuditService:
    """Existing audit logging - EXTEND"""
```

**New Monitoring Extension**:

```python
class OpenClawLLMMonitor:
    """Extends existing monitoring for OpenClaw."""
    
    def __init__(
        self,
        health_monitor: HealthMonitor,
        audit_service: AuditService
    ):
        self.health_monitor = health_monitor
        self.audit_service = audit_service
        
    async def record_gateway_usage(
        self,
        gateway_id: str,
        skill_name: str,
        llm_response: LLMResponse
    ) -> None:
        """Record OpenClaw gateway LLM usage."""
        await self.audit_service.log_llm_request(
            gateway_id=gateway_id,
            skill_name=skill_name,
            method=llm_response.method,
            model=llm_response.model,
            tokens=llm_response.usage.total_tokens,
            latency_ms=llm_response.latency_ms,
            cost=self._estimate_cost(llm_response)
        )
        
    async def get_gateway_stats(
        self,
        gateway_id: str,
        time_range: TimeRange
    ) -> GatewayLLMStats:
        """Get LLM usage stats for gateway."""
        # Query existing audit logs
        logs = await self.audit_service.query_logs(
            filters={'gateway_id': gateway_id},
            time_range=time_range
        )
        
        return GatewayLLMStats(
            total_requests=len(logs),
            total_tokens=sum(log.tokens for log in logs),
            total_cost=sum(log.cost for log in logs),
            avg_latency=sum(log.latency_ms for log in logs) / len(logs),
            provider_breakdown=self._group_by_provider(logs)
        )
```

**Prometheus Metrics** (Extend existing):
- `llm_requests_total{gateway_id, skill_name, provider, model}` - EXTEND existing metric
- `llm_tokens_total{gateway_id, skill_name, provider, model}` - EXTEND existing metric
- `llm_cost_total{gateway_id, skill_name, provider}` - NEW metric
- `openclaw_skill_executions_total{gateway_id, skill_name}` - NEW metric

### LLM Configuration Schema

**Note**: This system reuses existing LLM configuration infrastructure from `src/ai/llm_schemas.py`. The following schemas are already implemented:

**Existing Pydantic Models** (from `src/ai/llm_schemas.py`):
- `LLMMethod` - Enum of supported LLM providers (LOCAL_OLLAMA, CLOUD_OPENAI, CLOUD_AZURE, CHINA_QWEN, CHINA_ZHIPU, CHINA_BAIDU, CHINA_HUNYUAN)
- `LLMConfig` - Complete LLM configuration with local, cloud, and China provider configs
- `LocalConfig` - Configuration for Ollama
- `CloudConfig` - Configuration for OpenAI and Azure
- `ChinaLLMConfig` - Configuration for Qwen, Zhipu, Baidu, Hunyuan
- `GenerateOptions` - Text generation parameters (temperature, max_tokens, top_p, etc.)
- `LLMResponse` - Unified response format with usage, latency, and metadata
- `TokenUsage` - Token usage statistics
- `HealthStatus` - Health status for LLM providers
- `LLMError` - Unified error format

**New Database Models** (to be created for gateway-LLM linking):

```python
class GatewayLLMConfig(Base):
    """Links gateway to existing LLM configuration."""
    __tablename__ = "ai_gateway_llm_configs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    gateway_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_gateways.id"))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Reference to tenant's LLM config (managed by existing LLMConfigManager)
    # No need to duplicate LLM provider data - use existing system
    
    # Gateway-specific overrides (optional)
    model_override: Mapped[Optional[str]] = mapped_column(String(100))
    temperature_override: Mapped[Optional[float]] = mapped_column(Float)
    max_tokens_override: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.utcnow)
```

**Integration Approach**:
1. Use existing `LLMConfigManager` to get tenant's LLM configuration
2. Use existing `LLMSwitcher` for all LLM requests
3. Use existing `ChinaLLMProvider` for China-based models
4. Extend existing usage logging with gateway_id and skill_name
5. Map existing `LLMConfig` to OpenClaw environment variables via `OpenClawLLMBridge`

### Supported LLM Providers

**Note**: All providers below are already supported by the existing LLM infrastructure in `src/ai/`.

**Cloud Providers** (via `LLMMethod` enum):
- **CLOUD_OPENAI**: OpenAI GPT-4, GPT-3.5-turbo, etc.
- **CLOUD_AZURE**: Azure-hosted OpenAI models
- **CHINA_QWEN**: Alibaba Qwen (通义千问) - via `ChinaLLMProvider`
- **CHINA_ZHIPU**: Zhipu ChatGLM (智谱清言) - via `ChinaLLMProvider`
- **CHINA_BAIDU**: Baidu ERNIE Bot (文心一言) - via `ChinaLLMProvider`
- **CHINA_HUNYUAN**: Tencent Hunyuan (腾讯混元) - via `ChinaLLMProvider`

**Private Deployments**:
- **LOCAL_OLLAMA**: Local Ollama deployment (Llama, Mistral, Qwen, etc.)
- **Docker LLM**: Containerized LLM service (uses Ollama protocol)

**Additional Providers** (supported by existing `LLMSwitcher`):
- **Anthropic**: Claude models
- **Groq**: High-speed inference

**Integration**: OpenClaw will use `OpenClawLLMBridge` to map these providers to OpenClaw-compatible environment variables.

### Docker Compose Integration for LLM

```yaml
# Enhanced docker-compose.yml for LLM configuration
services:
  openclaw-gateway:
    image: openclaw/gateway:latest
    container_name: superinsight-openclaw-gateway
    environment:
      - SUPERINSIGHT_API_URL=http://app:8000
      - SUPERINSIGHT_API_KEY=${OPENCLAW_API_KEY}
      - SUPERINSIGHT_TENANT_ID=${TENANT_ID}
      # LLM Configuration (injected dynamically)
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
      - LLM_API_ENDPOINT=${LLM_API_ENDPOINT:-http://ollama:11434}
      - LLM_MODEL=${LLM_MODEL:-llama2}
      - LLM_API_KEY=${LLM_API_KEY:-}
      - LLM_TEMPERATURE=${LLM_TEMPERATURE:-0.7}
      - LLM_MAX_TOKENS=${LLM_MAX_TOKENS:-2048}
    networks:
      - superinsight_network
    ports:
      - "3000:3000"
    volumes:
      - openclaw_config:/app/config
      - openclaw_memory:/app/memory
    depends_on:
      - app
      - ollama
    restart: unless-stopped

  openclaw-agent:
    image: openclaw/agent:latest
    container_name: superinsight-openclaw-agent
    environment:
      - GATEWAY_URL=http://openclaw-gateway:3000
      - SUPERINSIGHT_API_URL=http://app:8000
      - SUPERINSIGHT_API_KEY=${OPENCLAW_API_KEY}
      # Inherit LLM configuration from gateway
    networks:
      - superinsight_network
    volumes:
      - openclaw_skills:/app/skills
      - openclaw_memory:/app/memory
    depends_on:
      - openclaw-gateway
      - app
    restart: unless-stopped
```

### Workflow Definition Schema

```python
class WorkflowDefinition(BaseModel):
    """Structured workflow definition."""
    id: str
    name: str
    description: str
    tenant_id: str
    
    # Data sources
    data_sources: List[DataSource]
    
    # Processing steps
    steps: List[ProcessingStep]
    
    # Output configuration
    output: OutputConfig
    
    # Quality requirements
    quality_requirements: QualityRequirements
    
    # Metadata
    created_at: datetime
    created_by: str
    version: int


class DataSource(BaseModel):
    """Data source specification."""
    type: str  # dataset, annotation, knowledge_graph
    identifier: str
    filters: Dict[str, Any]
    use_governed: bool = True


class ProcessingStep(BaseModel):
    """Processing step in workflow."""
    step_type: str  # filter, transform, aggregate, join
    parameters: Dict[str, Any]
    description: str


class OutputConfig(BaseModel):
    """Output configuration."""
    format: str  # json, csv, parquet
    destination: str  # api_response, file, database
    include_quality_metrics: bool = True


class QualityRequirements(BaseModel):
    """Quality requirements for workflow."""
    min_completeness: float = 0.8
    min_accuracy: float = 0.9
    min_consistency: float = 0.85
    require_lineage: bool = True
```

## Frontend Components

### 1. Workflow Playground Page

**Location**: `frontend/src/pages/AIIntegration/WorkflowPlayground.tsx`

**Components**:

```typescript
interface WorkflowPlaygroundProps {
  tenantId: string;
  gatewayId: string;
}

const WorkflowPlayground: React.FC<WorkflowPlaygroundProps> = ({
  tenantId,
  gatewayId
}) => {
  // Three-panel layout:
  // 1. Chat interface (left) - OpenClaw conversation
  // 2. Workflow definition (center) - Generated workflow
  // 3. Results panel (right) - Execution results with quality metrics
  
  return (
    <Layout>
      <ChatPanel gateway={gatewayId} onWorkflowGenerated={handleWorkflow} />
      <WorkflowPanel workflow={currentWorkflow} onExecute={handleExecute} />
      <ResultsPanel 
        results={executionResults} 
        comparison={comparisonMetrics}
        history={executionHistory}
      />
    </Layout>
  );
};
```

**Features**:
- Real-time chat with OpenClaw
- Live workflow definition preview
- Toggle between governed/raw data modes
- Execution history with comparison metrics
- Save to production workflow library

### 2. Data Quality Comparison Dashboard

**Location**: `frontend/src/pages/AIIntegration/QualityComparison.tsx`

**Components**:

```typescript
interface QualityComparisonProps {
  workflowId: string;
}

const QualityComparison: React.FC<QualityComparisonProps> = ({
  workflowId
}) => {
  // Split-view comparison:
  // Left: Governed data results
  // Right: Raw data results
  // Bottom: Quality metrics comparison
  
  return (
    <Layout>
      <ComparisonHeader workflow={workflow} />
      <SplitView>
        <DataPanel 
          title="AI友好型数据（已治理）"
          data={governedResults}
          qualityMetrics={governedMetrics}
          highlight="success"
        />
        <DataPanel 
          title="原始数据（未治理）"
          data={rawResults}
          qualityMetrics={rawMetrics}
          highlight="warning"
        />
      </SplitView>
      <MetricsComparison 
        governed={governedMetrics}
        raw={rawMetrics}
        showDifferences={true}
      />
    </Layout>
  );
};
```

**Visualization Features**:
- Side-by-side data display with color coding
- Quality metric radar charts
- Difference highlighting (green for improvements)
- Lineage visualization showing governance steps
- Export comparison report (PDF/Excel)

### 3. Workflow Library Page

**Location**: `frontend/src/pages/AIIntegration/WorkflowLibrary.tsx`

**Features**:
- List all saved workflows
- Filter by creator, date, quality score
- Quick execute button
- Clone and modify workflows
- Share workflows with team members
- Workflow templates gallery

### 4. Gateway Management Dashboard

**Location**: `frontend/src/pages/AIIntegration/GatewayManagement.tsx`

**Enhanced Features**:
- Gateway registration and configuration
- Real-time status monitoring
- Workflow execution statistics
- Channel connectivity status
- Usage analytics and cost tracking

## OpenClaw Skill Enhancement

### SuperInsight Workflow Skill

**Location**: `skills/superinsight-workflow/SKILL.md`

```markdown
---
name: superinsight-workflow
description: Design and execute data workflows using SuperInsight governed data
user-invocable: true
---

# SuperInsight Workflow Designer

This skill enables conversational workflow design and execution.

## Capabilities

1. **Workflow Design**: Parse natural language descriptions into structured workflows
2. **Data Query**: Access governed datasets with quality guarantees
3. **Quality Comparison**: Compare results using governed vs. raw data
4. **Execution**: Run workflows and return formatted results

## Example Conversations

**User**: "I need to analyze customer feedback from the last quarter, filter for negative sentiment, and group by product category."

**Agent**: "I'll create a workflow for you:
1. Data Source: Customer feedback dataset (Q4 2025)
2. Filter: Sentiment score < 0.3 (negative)
3. Group by: Product category
4. Output: Summary statistics with quality metrics

Would you like me to execute this with governed data?"

**User**: "Yes, and show me the difference if we used raw data."

**Agent**: "Executing comparison... 

Results with AI-friendly data (governed):
- 1,247 negative feedback entries
- 98.5% data completeness
- 95.2% sentiment accuracy
- Grouped into 12 product categories

Results with raw data:
- 1,089 entries (158 missing due to data quality issues)
- 87.3% data completeness
- 78.4% sentiment accuracy (inconsistent formats)
- Only 9 categories identified (missing mappings)

The governed data provides 14.5% more complete results with 21% higher accuracy."
```

**Implementation**: `skills/superinsight-workflow/index.js`

```javascript
// Node.js skill implementation
const axios = require('axios');

class SuperInsightWorkflowSkill {
  constructor(config) {
    this.apiUrl = config.SUPERINSIGHT_API_URL;
    this.apiKey = config.SUPERINSIGHT_API_KEY;
    this.tenantId = config.SUPERINSIGHT_TENANT_ID;
  }
  
  async parseWorkflow(description) {
    const response = await axios.post(
      `${this.apiUrl}/api/v1/ai-integration/workflows/parse`,
      { description, tenant_id: this.tenantId },
      { headers: { 'Authorization': `Bearer ${this.apiKey}` } }
    );
    return response.data;
  }
  
  async executeWorkflow(workflowId, useGoverned = true) {
    const response = await axios.post(
      `${this.apiUrl}/api/v1/ai-integration/workflows/${workflowId}/execute`,
      { use_governed_data: useGoverned },
      { headers: { 'Authorization': `Bearer ${this.apiKey}` } }
    );
    return response.data;
  }
  
  async compareResults(workflowId) {
    const response = await axios.post(
      `${this.apiUrl}/api/v1/ai-integration/workflows/${workflowId}/compare`,
      {},
      { headers: { 'Authorization': `Bearer ${this.apiKey}` } }
    );
    return response.data;
  }
  
  formatComparisonForChat(comparison) {
    // Format comparison results for conversational display
    const governed = comparison.governed_metrics;
    const raw = comparison.raw_metrics;
    
    return `
Results with AI-friendly data (governed):
- ${governed.record_count} records
- ${(governed.completeness * 100).toFixed(1)}% data completeness
- ${(governed.accuracy * 100).toFixed(1)}% accuracy
- Quality score: ${governed.overall_quality.toFixed(2)}/1.0

Results with raw data:
- ${raw.record_count} records
- ${(raw.completeness * 100).toFixed(1)}% data completeness
- ${(raw.accuracy * 100).toFixed(1)}% accuracy
- Quality score: ${raw.overall_quality.toFixed(2)}/1.0

Improvement: ${((governed.overall_quality - raw.overall_quality) * 100).toFixed(1)}% better quality with governed data
    `.trim();
  }
}

module.exports = SuperInsightWorkflowSkill;
```

## User Journey Example

### Scenario: Business Analyst Designing Customer Analysis Workflow

1. **User opens Workflow Playground** in SuperInsight frontend
2. **User types in chat**: "I want to analyze customer complaints about delivery delays in the past month"
3. **OpenClaw (via SuperInsight Skill)**:
   - Parses the request
   - Identifies data sources: customer_feedback dataset
   - Suggests filters: complaint_type='delivery', date_range='last_30_days'
   - Displays workflow definition in center panel
4. **User reviews workflow** and clicks "Execute with Comparison"
5. **System executes workflow** with both governed and raw data
6. **Results panel shows**:
   - Left side: Governed data results (342 complaints, 97% complete, clear categorization)
   - Right side: Raw data results (289 complaints, 81% complete, inconsistent categories)
   - Bottom: Quality metrics comparison with radar chart
7. **User sees value**: Governed data provides 18% more complete insights
8. **User clicks "Save to Production"**: Workflow saved for scheduled execution
9. **User shares link** with team members to view comparison

## Future Enhancements

1. **Additional Gateway Support**: Integrate other AI gateways (LangChain, AutoGPT)
2. **Advanced Analytics**: ML-based usage pattern analysis
3. **Skill Marketplace**: Community-contributed skills
4. **Multi-Region Deployment**: Geographic distribution for low latency
5. **GraphQL API**: Alternative to REST for flexible data queries
6. **Webhook Support**: Real-time notifications for gateway events
7. **Advanced Rate Limiting**: Per-skill and per-user rate limits
8. **Cost Tracking**: Track and bill based on API usage
9. **Workflow Templates**: Pre-built workflow templates for common use cases
10. **Collaborative Workflows**: Multi-user workflow design and review
11. **A/B Testing**: Compare different workflow configurations
12. **Automated Optimization**: AI-suggested workflow improvements based on execution history
