# Design Document

## Overview

多租户工作空间隔离系统为SuperInsight 2.3提供企业级的数据和资源隔离能力。系统采用分层隔离架构，在数据库、API、应用层面实现严格的租户和工作空间边界，确保多个组织可以安全地共享同一平台实例。

## Architecture Design

### System Architecture

```
Multi-Tenant Workspace System
├── Tenant Management Layer
│   ├── Tenant Registry
│   ├── Resource Quota Manager
│   └── Tenant Configuration
├── Workspace Isolation Layer
│   ├── Workspace Manager
│   ├── Project Association
│   └── Permission Controller
├── Data Isolation Engine
│   ├── Row-Level Security
│   ├── Query Filter Injection
│   └── Cross-Tenant Prevention
├── API Middleware Layer
│   ├── Context Extraction
│   ├── Permission Validation
│   └── Request Routing
└── Label Studio Integration
    ├── Project Isolation
    ├── User Synchronization
    └── Configuration Management
```

### Component Architecture

```typescript
interface MultiTenantSystem {
  tenantManager: TenantManager;
  workspaceManager: WorkspaceManager;
  isolationEngine: IsolationEngine;
  middlewareLayer: MiddlewareLayer;
  labelStudioIntegration: LabelStudioIntegration;
}

interface TenantManager {
  createTenant(config: TenantConfig): Promise<Tenant>;
  getTenant(tenantId: string): Promise<Tenant>;
  updateTenantQuota(tenantId: string, quota: ResourceQuota): Promise<void>;
  deactivateTenant(tenantId: string): Promise<void>;
}

interface WorkspaceManager {
  createWorkspace(tenantId: string, config: WorkspaceConfig): Promise<Workspace>;
  getWorkspaces(tenantId: string): Promise<Workspace[]>;
  switchWorkspace(userId: string, workspaceId: string): Promise<void>;
}
```

## Data Models

### Tenant Model

```typescript
interface Tenant {
  id: string;
  name: string;
  domain?: string;
  status: TenantStatus;
  config: TenantConfig;
  quota: ResourceQuota;
  createdAt: Date;
  updatedAt: Date;
  metadata: Record<string, any>;
}

interface TenantConfig {
  maxWorkspaces: number;
  maxUsers: number;
  features: string[];
  customSettings: Record<string, any>;
  labelStudioConfig: LabelStudioTenantConfig;
}

interface ResourceQuota {
  storage: number;        // GB
  apiCalls: number;       // per month
  concurrentUsers: number;
  dataProcessing: number; // GB per month
}

enum TenantStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING = 'pending'
}
```

### Workspace Model

```typescript
interface Workspace {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  status: WorkspaceStatus;
  config: WorkspaceConfig;
  labelStudioProjectId?: string;
  createdAt: Date;
  updatedAt: Date;
  metadata: Record<string, any>;
}

interface WorkspaceConfig {
  dataRetentionDays: number;
  allowedFileTypes: string[];
  maxFileSize: number;
  qualityThresholds: QualityThresholds;
  annotationSettings: AnnotationSettings;
}

enum WorkspaceStatus {
  ACTIVE = 'active',
  ARCHIVED = 'archived',
  MAINTENANCE = 'maintenance'
}
```

### User Tenant Association Model

```typescript
interface UserTenantAssociation {
  id: string;
  userId: string;
  tenantId: string;
  role: TenantRole;
  permissions: string[];
  workspaceAccess: WorkspaceAccess[];
  createdAt: Date;
  lastAccessAt: Date;
}

interface WorkspaceAccess {
  workspaceId: string;
  role: WorkspaceRole;
  permissions: string[];
  grantedAt: Date;
  grantedBy: string;
}

enum TenantRole {
  TENANT_ADMIN = 'tenant_admin',
  WORKSPACE_MANAGER = 'workspace_manager',
  USER = 'user'
}

enum WorkspaceRole {
  WORKSPACE_ADMIN = 'workspace_admin',
  ANNOTATOR = 'annotator',
  REVIEWER = 'reviewer',
  VIEWER = 'viewer'
}
```

## Database Schema Design

### Multi-Tenant Table Structure

```sql
-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE,
    status tenant_status NOT NULL DEFAULT 'pending',
    config JSONB NOT NULL DEFAULT '{}',
    quota JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Workspaces table
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status workspace_status NOT NULL DEFAULT 'active',
    config JSONB NOT NULL DEFAULT '{}',
    label_studio_project_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(tenant_id, name)
);

-- User tenant associations
CREATE TABLE user_tenant_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role tenant_role NOT NULL,
    permissions TEXT[] DEFAULT '{}',
    workspace_access JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_access_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, tenant_id)
);
```

### Row-Level Security Implementation

```sql
-- Enable RLS on all tenant-aware tables
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE annotations ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY tenant_isolation_policy ON tasks
    FOR ALL TO authenticated_users
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE POLICY workspace_isolation_policy ON tasks
    FOR ALL TO authenticated_users
    USING (
        tenant_id = current_setting('app.current_tenant_id')::UUID AND
        workspace_id = current_setting('app.current_workspace_id')::UUID
    );
```

## Implementation Strategy

### Phase 1: 基于现有代码的扩展策略

#### 现有代码基础分析
SuperInsight已具备多租户的基础架构，我们将基于以下现有模块进行扩展：

**现有租户中间件基础**:
```python
# 现有: src/middleware/tenant_middleware.py
# 扩展策略: 增强租户上下文提取和工作空间隔离
class TenantContextMiddleware:
    # 现有功能: 基础租户识别
    # 新增功能: 工作空间级别隔离
    pass
```

**现有数据库模型基础**:
```python
# 现有: src/database/models.py
# 扩展策略: 添加tenant_id和workspace_id字段
# 现有模型将通过数据库迁移添加多租户支持
```

**现有Label Studio集成**:
```python
# 现有: src/label_studio/tenant_isolation.py
# 扩展策略: 增强项目级别隔离
# 现有: src/label_studio/integration.py
# 扩展策略: 支持工作空间到项目的映射
```

#### Database Schema Migration (基于现有数据库)

**扩展现有数据库模型**:
```sql
-- 基于现有 src/database/models.py 的扩展
-- 为现有表添加多租户支持

-- 扩展现有用户表
ALTER TABLE users ADD COLUMN default_tenant_id UUID;
ALTER TABLE users ADD COLUMN default_workspace_id UUID;

-- 扩展现有任务表 (基于 src/models/task.py)
ALTER TABLE tasks ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE tasks ADD COLUMN workspace_id UUID REFERENCES workspaces(id);

-- 扩展现有标注表 (基于 src/models/annotation.py)  
ALTER TABLE annotations ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE annotations ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
```

### Phase 2: 中间件集成 (扩展现有中间件)

#### 增强现有租户中间件
```python
# 扩展: src/middleware/tenant_middleware.py
from src.middleware.tenant_middleware import TenantContextMiddleware as BaseTenantMiddleware

class EnhancedTenantContextMiddleware(BaseTenantMiddleware):
    """扩展现有租户中间件，增加工作空间支持"""
    
    def __init__(self, app):
        super().__init__(app)
        # 保持现有功能，增加工作空间处理
    
    async def extract_workspace_context(self, request: Request) -> Optional[str]:
        """新增: 工作空间上下文提取"""
        # 基于现有租户提取逻辑，增加工作空间层级
        tenant_id = await self.extract_tenant_id(request)  # 复用现有方法
        workspace_id = request.headers.get("X-Workspace-ID")
        
        if workspace_id:
            # 验证工作空间属于当前租户
            if await self.validate_workspace_access(tenant_id, workspace_id):
                return workspace_id
        
        # 返回默认工作空间
        return await self.get_default_workspace(tenant_id)
```

#### 扩展现有数据库会话管理
```python
# 扩展: src/database/connection.py
from src.database.connection import get_db_session

class TenantAwareSession:
    """基于现有数据库连接，增加租户上下文"""
    
    def __init__(self, session, tenant_id: str, workspace_id: str):
        self.session = session  # 复用现有session
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self._setup_context()
    
    def _setup_context(self):
        """设置PostgreSQL会话变量，基于现有RLS策略"""
        # 扩展现有的数据库上下文设置
        self.session.execute(f"SET app.current_tenant_id = '{self.tenant_id}'")
        self.session.execute(f"SET app.current_workspace_id = '{self.workspace_id}'")
```

### Phase 3: API层集成 (扩展现有API)

#### 扩展现有认证API
```python
# 扩展: src/api/auth.py
from src.api.auth import router as auth_router

@auth_router.post("/switch-tenant")
async def switch_tenant(
    tenant_data: TenantSwitchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新增: 租户切换功能，基于现有认证系统"""
    # 复用现有的用户验证逻辑
    # 增加租户切换和工作空间管理
    pass

@auth_router.get("/tenants/{tenant_id}/workspaces")
async def get_workspaces(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """新增: 工作空间管理，集成现有权限系统"""
    # 基于现有权限检查逻辑
    # 增加工作空间级别的权限验证
    pass
```

#### 扩展现有管理API
```python
# 扩展: src/api/admin.py
from src.api.admin import router as admin_router

@admin_router.post("/tenants")
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_admin_user),  # 复用现有管理员验证
    db: Session = Depends(get_db)
):
    """新增: 租户管理，基于现有管理员权限"""
    # 集成现有的管理员权限检查
    # 增加租户创建和配置逻辑
    pass
```

### Phase 4: Label Studio集成 (扩展现有集成)

#### 增强现有Label Studio集成
```python
# 扩展: src/label_studio/integration.py
from src.label_studio.integration import LabelStudioIntegration

class MultiTenantLabelStudioIntegration(LabelStudioIntegration):
    """扩展现有Label Studio集成，增加多租户支持"""
    
    def __init__(self):
        super().__init__()  # 保持现有初始化逻辑
    
    async def create_tenant_organization(self, tenant_id: str):
        """新增: 为租户创建Label Studio组织"""
        # 基于现有的Label Studio API调用逻辑
        # 增加租户级别的组织管理
        org_data = {
            "title": f"Tenant-{tenant_id}",
            "description": f"Organization for tenant {tenant_id}"
        }
        
        # 复用现有的API调用方法
        organization = await self.call_label_studio_api(
            "POST", "/api/organizations/", org_data
        )
        
        return organization
    
    async def create_workspace_project(self, workspace_id: str, tenant_org_id: str):
        """新增: 为工作空间创建Label Studio项目"""
        # 基于现有的项目创建逻辑
        # 增加工作空间到项目的映射
        workspace = await self.get_workspace(workspace_id)
        
        project_data = {
            "title": f"Workspace-{workspace.name}",
            "organization": tenant_org_id,
            "label_config": workspace.config.get("label_config", self.DEFAULT_CONFIG)
        }
        
        # 复用现有的项目创建方法
        project = await self.create_project(project_data)
        
        # 更新工作空间配置
        await self.update_workspace_config(workspace_id, {
            "label_studio_project_id": project.id
        })
        
        return project
```

#### 扩展现有租户隔离
```python
# 扩展: src/label_studio/tenant_isolation.py
from src.label_studio.tenant_isolation import TenantIsolation

class WorkspaceIsolation(TenantIsolation):
    """基于现有租户隔离，增加工作空间级别隔离"""
    
    async def sync_workspace_users(self, workspace_id: str):
        """新增: 同步工作空间用户到Label Studio"""
        # 基于现有的用户同步逻辑
        # 增加工作空间级别的用户权限管理
        
        workspace = await self.get_workspace(workspace_id)
        users = await self.get_workspace_users(workspace_id)
        
        for user in users:
            # 复用现有的用户同步方法
            await self.sync_user_to_project(
                workspace.label_studio_project_id,
                user.email,
                self.map_workspace_role_to_label_studio(user.workspace_role)
            )
```

## Security Implementation

### Access Control Matrix

```python
TENANT_PERMISSIONS = {
    TenantRole.TENANT_ADMIN: [
        "tenant.manage",
        "workspace.create",
        "workspace.manage",
        "user.invite",
        "user.manage",
        "billing.view"
    ],
    TenantRole.WORKSPACE_MANAGER: [
        "workspace.manage",
        "user.invite",
        "task.manage"
    ],
    TenantRole.USER: [
        "workspace.view",
        "task.view"
    ]
}

WORKSPACE_PERMISSIONS = {
    WorkspaceRole.WORKSPACE_ADMIN: [
        "workspace.configure",
        "task.create",
        "task.assign",
        "annotation.review",
        "user.manage"
    ],
    WorkspaceRole.ANNOTATOR: [
        "task.annotate",
        "annotation.create",
        "annotation.update"
    ],
    WorkspaceRole.REVIEWER: [
        "annotation.review",
        "annotation.approve",
        "quality.assess"
    ],
    WorkspaceRole.VIEWER: [
        "task.view",
        "annotation.view",
        "report.view"
    ]
}
```

### Permission Validation Service

```python
class PermissionService:
    async def can_access_tenant(self, user_id: str, tenant_id: str) -> bool:
        """Check if user has access to tenant"""
        association = await self.get_user_tenant_association(user_id, tenant_id)
        return association is not None and association.tenant.status == TenantStatus.ACTIVE
    
    async def can_access_workspace(self, user_id: str, workspace_id: str) -> bool:
        """Check if user has access to workspace"""
        workspace = await workspace_service.get_workspace(workspace_id)
        if not await self.can_access_tenant(user_id, workspace.tenant_id):
            return False
        
        association = await self.get_user_tenant_association(user_id, workspace.tenant_id)
        workspace_access = [
            access for access in association.workspace_access 
            if access.workspace_id == workspace_id
        ]
        
        return len(workspace_access) > 0
    
    async def has_permission(
        self, 
        user_id: str, 
        permission: str, 
        tenant_id: str = None, 
        workspace_id: str = None
    ) -> bool:
        """Check if user has specific permission"""
        if workspace_id:
            return await self.has_workspace_permission(user_id, workspace_id, permission)
        elif tenant_id:
            return await self.has_tenant_permission(user_id, tenant_id, permission)
        else:
            return await self.has_global_permission(user_id, permission)
```

## Performance Optimization

### Database Optimization

#### Partitioning Strategy
```sql
-- Partition large tables by tenant_id
CREATE TABLE tasks_partitioned (
    LIKE tasks INCLUDING ALL
) PARTITION BY HASH (tenant_id);

-- Create partitions
CREATE TABLE tasks_partition_0 PARTITION OF tasks_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE tasks_partition_1 PARTITION OF tasks_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE tasks_partition_2 PARTITION OF tasks_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE tasks_partition_3 PARTITION OF tasks_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

#### Connection Pooling
```python
from sqlalchemy.pool import QueuePool
from sqlalchemy import create_engine

class TenantAwareConnectionPool:
    def __init__(self):
        self.pools = {}
    
    def get_engine(self, tenant_id: str):
        """Get tenant-specific database engine"""
        if tenant_id not in self.pools:
            # Create tenant-specific connection pool
            database_url = self.get_tenant_database_url(tenant_id)
            engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True
            )
            self.pools[tenant_id] = engine
        
        return self.pools[tenant_id]
```

### Caching Strategy

#### Multi-Level Caching
```python
from redis import Redis
import json

class TenantAwareCache:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    def get_cache_key(self, tenant_id: str, workspace_id: str, key: str) -> str:
        """Generate tenant/workspace-specific cache key"""
        return f"tenant:{tenant_id}:workspace:{workspace_id}:{key}"
    
    async def get(self, tenant_id: str, workspace_id: str, key: str):
        """Get cached value with tenant/workspace isolation"""
        cache_key = self.get_cache_key(tenant_id, workspace_id, key)
        value = await self.redis.get(cache_key)
        return json.loads(value) if value else None
    
    async def set(
        self, 
        tenant_id: str, 
        workspace_id: str, 
        key: str, 
        value: any, 
        ttl: int = 3600
    ):
        """Set cached value with tenant/workspace isolation"""
        cache_key = self.get_cache_key(tenant_id, workspace_id, key)
        await self.redis.setex(cache_key, ttl, json.dumps(value))
    
    async def invalidate_tenant(self, tenant_id: str):
        """Invalidate all cache entries for a tenant"""
        pattern = f"tenant:{tenant_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

## Monitoring and Analytics

### Tenant Metrics Collection

```python
class TenantMetricsCollector:
    def __init__(self, metrics_client):
        self.metrics = metrics_client
    
    async def record_api_call(self, tenant_id: str, endpoint: str, duration: float):
        """Record API call metrics per tenant"""
        self.metrics.increment(
            "api_calls_total",
            tags={"tenant_id": tenant_id, "endpoint": endpoint}
        )
        self.metrics.histogram(
            "api_call_duration",
            duration,
            tags={"tenant_id": tenant_id, "endpoint": endpoint}
        )
    
    async def record_storage_usage(self, tenant_id: str, workspace_id: str, bytes_used: int):
        """Record storage usage per workspace"""
        self.metrics.gauge(
            "storage_usage_bytes",
            bytes_used,
            tags={"tenant_id": tenant_id, "workspace_id": workspace_id}
        )
    
    async def record_user_activity(self, tenant_id: str, workspace_id: str, user_id: str):
        """Record user activity"""
        self.metrics.increment(
            "user_activity_total",
            tags={
                "tenant_id": tenant_id, 
                "workspace_id": workspace_id,
                "user_id": user_id
            }
        )
```

### Resource Usage Dashboard

```python
class TenantResourceDashboard:
    async def get_tenant_overview(self, tenant_id: str) -> TenantOverview:
        """Get comprehensive tenant resource overview"""
        return TenantOverview(
            tenant_id=tenant_id,
            workspaces_count=await self.count_workspaces(tenant_id),
            users_count=await self.count_users(tenant_id),
            storage_used=await self.calculate_storage_usage(tenant_id),
            api_calls_month=await self.count_api_calls_month(tenant_id),
            quota_utilization=await self.calculate_quota_utilization(tenant_id)
        )
    
    async def get_workspace_metrics(self, workspace_id: str) -> WorkspaceMetrics:
        """Get workspace-specific metrics"""
        return WorkspaceMetrics(
            workspace_id=workspace_id,
            tasks_count=await self.count_tasks(workspace_id),
            annotations_count=await self.count_annotations(workspace_id),
            active_users=await self.count_active_users(workspace_id),
            quality_score=await self.calculate_quality_score(workspace_id)
        )
```

## Migration Strategy

### Data Migration Plan

```python
class TenantMigrationService:
    async def migrate_existing_data(self):
        """Migrate existing single-tenant data to multi-tenant structure"""
        
        # Step 1: Create default tenant
        default_tenant = await self.create_default_tenant()
        
        # Step 2: Create default workspace
        default_workspace = await self.create_default_workspace(default_tenant.id)
        
        # Step 3: Update existing data
        await self.update_existing_tables(default_tenant.id, default_workspace.id)
        
        # Step 4: Migrate users
        await self.migrate_users_to_tenant(default_tenant.id)
        
        # Step 5: Setup Label Studio integration
        await self.setup_label_studio_migration(default_workspace.id)
    
    async def update_existing_tables(self, tenant_id: str, workspace_id: str):
        """Update existing tables with tenant/workspace IDs"""
        tables = ['tasks', 'annotations', 'datasets', 'models']
        
        for table in tables:
            await self.db.execute(f"""
                UPDATE {table} 
                SET tenant_id = '{tenant_id}', workspace_id = '{workspace_id}'
                WHERE tenant_id IS NULL
            """)
```

This comprehensive design provides a robust foundation for multi-tenant workspace isolation in SuperInsight 2.3, ensuring data security, performance, and scalability while maintaining ease of use and management.