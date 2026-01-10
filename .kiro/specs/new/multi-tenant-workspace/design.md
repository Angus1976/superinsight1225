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

### Phase 1: Database Schema Migration

#### Multi-Tenant Schema Updates
```sql
-- Add tenant_id and workspace_id to existing tables
ALTER TABLE tasks ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE tasks ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE annotations ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE annotations ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE datasets ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE datasets ADD COLUMN workspace_id UUID REFERENCES workspaces(id);

-- Create indexes for performance
CREATE INDEX idx_tasks_tenant_workspace ON tasks(tenant_id, workspace_id);
CREATE INDEX idx_annotations_tenant_workspace ON annotations(tenant_id, workspace_id);
CREATE INDEX idx_datasets_tenant_workspace ON datasets(tenant_id, workspace_id);
```

### Phase 2: Middleware Implementation

#### Tenant Context Middleware
```python
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

class TenantContextMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Extract tenant context
            tenant_id = await self.extract_tenant_id(request)
            workspace_id = await self.extract_workspace_id(request)
            
            # Validate permissions
            if not await self.validate_access(request, tenant_id, workspace_id):
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Set context
            scope["tenant_id"] = tenant_id
            scope["workspace_id"] = workspace_id
        
        await self.app(scope, receive, send)
    
    async def extract_tenant_id(self, request: Request) -> Optional[str]:
        # Extract from header, subdomain, or JWT token
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            # Extract from subdomain
            host = request.headers.get("host", "")
            if "." in host:
                subdomain = host.split(".")[0]
                tenant_id = await self.resolve_tenant_by_subdomain(subdomain)
        return tenant_id
```

#### Database Session Context
```python
from sqlalchemy import event
from sqlalchemy.orm import Session

class TenantAwareSession:
    def __init__(self, session: Session, tenant_id: str, workspace_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self._setup_context()
    
    def _setup_context(self):
        # Set PostgreSQL session variables for RLS
        self.session.execute(
            f"SET app.current_tenant_id = '{self.tenant_id}'"
        )
        self.session.execute(
            f"SET app.current_workspace_id = '{self.workspace_id}'"
        )
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
```

### Phase 3: API Layer Integration

#### Tenant-Aware API Endpoints
```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter()

@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new tenant (platform admin only)"""
    tenant = await tenant_service.create_tenant(db, tenant_data)
    await label_studio_service.setup_tenant_integration(tenant.id)
    return tenant

@router.get("/tenants/{tenant_id}/workspaces", response_model=List[WorkspaceResponse])
async def get_workspaces(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """Get workspaces for a tenant"""
    if not await permission_service.can_access_tenant(current_user.id, tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    workspaces = await workspace_service.get_tenant_workspaces(tenant_id)
    return workspaces

@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user)
):
    """Create a new workspace within current tenant"""
    workspace = await workspace_service.create_workspace(
        tenant_context.tenant_id, 
        workspace_data,
        created_by=current_user.id
    )
    
    # Create Label Studio project
    await label_studio_service.create_project_for_workspace(workspace.id)
    
    return workspace
```

### Phase 4: Label Studio Integration

#### Project Isolation Setup
```python
class LabelStudioTenantIntegration:
    def __init__(self, label_studio_client):
        self.client = label_studio_client
    
    async def setup_tenant_integration(self, tenant_id: str):
        """Setup Label Studio integration for a new tenant"""
        # Create tenant-specific organization in Label Studio
        org_data = {
            "title": f"Tenant-{tenant_id}",
            "description": f"Organization for tenant {tenant_id}"
        }
        organization = await self.client.create_organization(org_data)
        
        # Store organization mapping
        await self.store_tenant_organization_mapping(tenant_id, organization.id)
        
        return organization
    
    async def create_project_for_workspace(self, workspace_id: str):
        """Create Label Studio project for workspace"""
        workspace = await workspace_service.get_workspace(workspace_id)
        tenant_org_id = await self.get_tenant_organization_id(workspace.tenant_id)
        
        project_data = {
            "title": f"Workspace-{workspace.name}",
            "description": f"Project for workspace {workspace.name}",
            "organization": tenant_org_id,
            "label_config": workspace.config.get("label_config", DEFAULT_LABEL_CONFIG)
        }
        
        project = await self.client.create_project(project_data)
        
        # Update workspace with project ID
        await workspace_service.update_workspace(
            workspace_id, 
            {"label_studio_project_id": project.id}
        )
        
        return project
    
    async def sync_workspace_users(self, workspace_id: str):
        """Sync workspace users to Label Studio project"""
        workspace = await workspace_service.get_workspace(workspace_id)
        users = await workspace_service.get_workspace_users(workspace_id)
        
        for user in users:
            await self.add_user_to_project(
                workspace.label_studio_project_id,
                user.email,
                self.map_role_to_label_studio(user.workspace_role)
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