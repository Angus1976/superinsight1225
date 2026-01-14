# Design Document: Multi-Tenant Workspace (多租户工作空间)

## Overview

本设计文档描述 Multi-Tenant Workspace 模块的架构设计，该模块扩展现有 `src/multi_tenant/` 和 `src/security/`，实现完整的多租户工作空间管理，包括租户隔离、工作空间管理、成员管理、资源配额和跨租户协作。

设计原则：
- **安全优先**：租户数据完全隔离，防止跨租户泄露
- **灵活配置**：支持多层级配额和权限继承
- **可扩展**：支持自定义角色和权限
- **协作友好**：支持受控的跨租户协作

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        AdminConsole[Admin Console]
        TenantUI[Tenant Config UI]
        WorkspaceUI[Workspace Config UI]
        MemberUI[Member Config UI]
        QuotaUI[Quota Config UI]
    end

    subgraph API["API 层"]
        TenantRouter[/api/v1/tenants]
        WorkspaceRouter[/api/v1/workspaces]
        MemberRouter[/api/v1/members]
        QuotaRouter[/api/v1/quotas]
        AdminRouter[/api/v1/admin]
    end
    
    subgraph Core["核心层"]
        TenantManager[Tenant Manager]
        WorkspaceManager[Workspace Manager]
        MemberManager[Member Manager]
        QuotaManager[Quota Manager]
        IsolationEngine[Isolation Engine]
        CrossTenantCollab[Cross Tenant Collaborator]
    end
    
    subgraph Security["安全层"]
        TenantFilter[Tenant Filter Middleware]
        PermissionChecker[Permission Checker]
        AuditLogger[Audit Logger]
        Encryptor[Data Encryptor]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
    end
    
    AdminConsole --> AdminRouter
    TenantUI --> TenantRouter
    WorkspaceUI --> WorkspaceRouter
    MemberUI --> MemberRouter
    QuotaUI --> QuotaRouter
    
    TenantRouter --> TenantManager
    WorkspaceRouter --> WorkspaceManager
    MemberRouter --> MemberManager
    QuotaRouter --> QuotaManager
    AdminRouter --> TenantManager
    AdminRouter --> QuotaManager
    
    TenantManager --> IsolationEngine
    WorkspaceManager --> IsolationEngine
    MemberManager --> PermissionChecker
    
    IsolationEngine --> TenantFilter
    IsolationEngine --> Encryptor
    
    TenantFilter --> DB
    PermissionChecker --> Cache
    AuditLogger --> DB
    
    CrossTenantCollab --> PermissionChecker
    CrossTenantCollab --> AuditLogger
```

## Components and Interfaces

### 1. Tenant Manager (租户管理器)

**文件**: `src/multi_tenant/tenant_manager.py`

**职责**: 管理租户的创建、配置和生命周期

```python
class TenantManager:
    """租户管理器"""
    
    def __init__(self, db: AsyncSession, audit_logger: AuditLogger):
        self.db = db
        self.audit_logger = audit_logger
    
    async def create_tenant(self, config: TenantCreateConfig) -> Tenant:
        """创建租户"""
        tenant = Tenant(
            id=uuid4(),
            name=config.name,
            status=TenantStatus.ACTIVE,
            config=self._get_default_config(),
            quota=self._get_default_quota()
        )
        await self.db.add(tenant)
        await self.audit_logger.log("tenant_created", tenant.id)
        return tenant
    
    async def update_tenant(self, tenant_id: str, updates: TenantUpdateConfig) -> Tenant:
        """更新租户"""
        pass
    
    async def delete_tenant(self, tenant_id: str) -> None:
        """删除租户"""
        pass
    
    async def set_status(self, tenant_id: str, status: TenantStatus) -> Tenant:
        """设置租户状态"""
        pass
    
    async def is_operation_allowed(self, tenant_id: str) -> bool:
        """检查租户是否允许操作"""
        tenant = await self.get_tenant(tenant_id)
        return tenant.status == TenantStatus.ACTIVE
    
    def _get_default_config(self) -> TenantConfig:
        """获取默认配置"""
        pass
    
    def _get_default_quota(self) -> TenantQuota:
        """获取默认配额"""
        pass

class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"

class TenantCreateConfig(BaseModel):
    name: str
    description: Optional[str] = None
    admin_email: str
    plan: str = "free"

class Tenant(BaseModel):
    id: UUID
    name: str
    status: TenantStatus
    config: TenantConfig
    quota: TenantQuota
    created_at: datetime
```

### 2. Workspace Manager (工作空间管理器)

**文件**: `src/multi_tenant/workspace_manager.py`

**职责**: 管理工作空间的创建和配置

```python
class WorkspaceManager:
    """工作空间管理器"""
    
    def __init__(self, db: AsyncSession, tenant_manager: TenantManager):
        self.db = db
        self.tenant_manager = tenant_manager
    
    async def create_workspace(
        self,
        tenant_id: str,
        config: WorkspaceCreateConfig
    ) -> Workspace:
        """创建工作空间"""
        # 继承租户默认配置
        tenant = await self.tenant_manager.get_tenant(tenant_id)
        workspace = Workspace(
            id=uuid4(),
            tenant_id=tenant_id,
            parent_id=config.parent_id,
            name=config.name,
            config=tenant.config.workspace_defaults
        )
        return workspace
    
    async def create_from_template(
        self,
        tenant_id: str,
        template_id: str,
        name: str
    ) -> Workspace:
        """从模板创建工作空间"""
        pass
    
    async def update_workspace(self, workspace_id: str, updates: WorkspaceUpdateConfig) -> Workspace:
        """更新工作空间"""
        pass
    
    async def delete_workspace(self, workspace_id: str) -> None:
        """删除工作空间"""
        pass
    
    async def archive_workspace(self, workspace_id: str) -> Workspace:
        """归档工作空间"""
        pass
    
    async def restore_workspace(self, workspace_id: str) -> Workspace:
        """恢复工作空间"""
        pass
    
    async def move_workspace(self, workspace_id: str, new_parent_id: str) -> Workspace:
        """移动工作空间（调整层级）"""
        pass
    
    async def get_hierarchy(self, tenant_id: str) -> List[WorkspaceNode]:
        """获取工作空间层级结构"""
        pass

class WorkspaceCreateConfig(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    template_id: Optional[str] = None

class WorkspaceNode(BaseModel):
    workspace: Workspace
    children: List["WorkspaceNode"] = []
```

### 3. Member Manager (成员管理器)

**文件**: `src/multi_tenant/member_manager.py`

**职责**: 管理工作空间成员和角色

```python
class MemberManager:
    """成员管理器"""
    
    def __init__(self, db: AsyncSession, permission_checker: PermissionChecker):
        self.db = db
        self.permission_checker = permission_checker
    
    async def invite_member(
        self,
        workspace_id: str,
        email: str,
        role: MemberRole = MemberRole.MEMBER
    ) -> Invitation:
        """邀请成员"""
        pass
    
    async def add_member(
        self,
        workspace_id: str,
        user_id: str,
        role: MemberRole = MemberRole.MEMBER
    ) -> WorkspaceMember:
        """添加成员"""
        pass
    
    async def remove_member(self, workspace_id: str, user_id: str) -> None:
        """移除成员"""
        # 撤销所有权限
        await self.permission_checker.revoke_all_permissions(workspace_id, user_id)
        pass
    
    async def update_role(self, workspace_id: str, user_id: str, role: MemberRole) -> WorkspaceMember:
        """更新成员角色"""
        pass
    
    async def batch_add_members(
        self,
        workspace_id: str,
        members: List[MemberAddRequest]
    ) -> List[WorkspaceMember]:
        """批量添加成员"""
        pass
    
    async def batch_remove_members(self, workspace_id: str, user_ids: List[str]) -> None:
        """批量移除成员"""
        pass
    
    async def create_custom_role(self, workspace_id: str, role_config: CustomRoleConfig) -> CustomRole:
        """创建自定义角色"""
        pass
    
    async def get_members(self, workspace_id: str) -> List[WorkspaceMember]:
        """获取成员列表"""
        pass

class MemberRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"

class WorkspaceMember(BaseModel):
    user_id: str
    workspace_id: str
    role: MemberRole
    custom_role_id: Optional[str] = None
    joined_at: datetime
    last_active_at: Optional[datetime] = None

class CustomRoleConfig(BaseModel):
    name: str
    permissions: List[str]
    description: Optional[str] = None
```

### 4. Quota Manager (配额管理器)

**文件**: `src/multi_tenant/quota_manager.py`

**职责**: 管理资源配额和使用限制

```python
class QuotaManager:
    """配额管理器"""
    
    def __init__(self, db: AsyncSession, cache: Redis, notification_service: NotificationService):
        self.db = db
        self.cache = cache
        self.notification_service = notification_service
    
    async def set_quota(
        self,
        entity_id: str,
        entity_type: EntityType,
        quota_config: QuotaConfig
    ) -> Quota:
        """设置配额"""
        pass
    
    async def get_usage(self, entity_id: str, entity_type: EntityType) -> QuotaUsage:
        """获取使用情况"""
        pass
    
    async def check_quota(
        self,
        entity_id: str,
        entity_type: EntityType,
        resource_type: ResourceType,
        amount: int = 1
    ) -> QuotaCheckResult:
        """检查配额"""
        usage = await self.get_usage(entity_id, entity_type)
        quota = await self.get_quota(entity_id, entity_type)
        
        current = getattr(usage, resource_type.value)
        limit = getattr(quota, resource_type.value)
        
        percentage = (current + amount) / limit * 100
        
        if percentage >= 100:
            return QuotaCheckResult(allowed=False, reason="quota_exceeded")
        
        if percentage >= 80:
            await self.notification_service.send_warning(
                entity_id, f"{resource_type.value} usage at {percentage:.1f}%"
            )
        
        return QuotaCheckResult(allowed=True, percentage=percentage)
    
    async def increment_usage(
        self,
        entity_id: str,
        entity_type: EntityType,
        resource_type: ResourceType,
        amount: int = 1
    ) -> QuotaUsage:
        """增加使用量"""
        pass
    
    async def set_temporary_quota(
        self,
        entity_id: str,
        entity_type: EntityType,
        quota_config: QuotaConfig,
        expires_at: datetime
    ) -> TemporaryQuota:
        """设置临时配额"""
        pass
    
    async def inherit_quota(self, workspace_id: str, tenant_id: str) -> Quota:
        """继承租户配额"""
        pass

class EntityType(str, Enum):
    TENANT = "tenant"
    WORKSPACE = "workspace"

class ResourceType(str, Enum):
    STORAGE = "storage_bytes"
    PROJECTS = "project_count"
    USERS = "user_count"
    API_CALLS = "api_call_count"

class QuotaConfig(BaseModel):
    storage_bytes: int = 10 * 1024 * 1024 * 1024  # 10GB
    project_count: int = 100
    user_count: int = 50
    api_call_count: int = 100000  # per month

class QuotaUsage(BaseModel):
    storage_bytes: int = 0
    project_count: int = 0
    user_count: int = 0
    api_call_count: int = 0
    last_updated: datetime

class QuotaCheckResult(BaseModel):
    allowed: bool
    percentage: float = 0
    reason: Optional[str] = None
```

### 5. Isolation Engine (隔离引擎)

**文件**: `src/multi_tenant/isolation_engine.py`

**职责**: 确保租户数据隔离

```python
class IsolationEngine:
    """隔离引擎"""
    
    def __init__(self, db: AsyncSession, encryptor: DataEncryptor, audit_logger: AuditLogger):
        self.db = db
        self.encryptor = encryptor
        self.audit_logger = audit_logger
    
    def get_tenant_filter(self, tenant_id: str) -> BinaryExpression:
        """获取租户过滤条件"""
        return TenantModel.tenant_id == tenant_id
    
    async def verify_tenant_access(self, user_id: str, tenant_id: str) -> bool:
        """验证用户的租户归属"""
        user = await self.db.get(User, user_id)
        if user.tenant_id != tenant_id:
            await self.audit_logger.log_cross_tenant_attempt(user_id, tenant_id)
            return False
        return True
    
    async def apply_tenant_filter(self, query: Select, tenant_id: str) -> Select:
        """应用租户过滤"""
        return query.where(self.get_tenant_filter(tenant_id))
    
    async def encrypt_tenant_data(self, tenant_id: str, data: bytes) -> bytes:
        """加密租户数据"""
        key = await self.get_tenant_encryption_key(tenant_id)
        return self.encryptor.encrypt(data, key)
    
    async def decrypt_tenant_data(self, tenant_id: str, encrypted_data: bytes) -> bytes:
        """解密租户数据"""
        key = await self.get_tenant_encryption_key(tenant_id)
        return self.encryptor.decrypt(encrypted_data, key)
    
    async def check_cross_tenant_access(
        self,
        source_tenant_id: str,
        target_tenant_id: str,
        resource_id: str
    ) -> bool:
        """检查跨租户访问权限"""
        pass

class TenantFilterMiddleware:
    """租户过滤中间件"""
    
    async def __call__(self, request: Request, call_next):
        tenant_id = request.state.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant not identified")
        
        # 注入租户上下文
        request.state.tenant_filter = lambda q: q.where(TenantModel.tenant_id == tenant_id)
        
        response = await call_next(request)
        return response
```

### 6. Cross Tenant Collaborator (跨租户协作器)

**文件**: `src/multi_tenant/cross_tenant_collaborator.py`

**职责**: 支持跨租户资源共享

```python
class CrossTenantCollaborator:
    """跨租户协作器"""
    
    def __init__(self, db: AsyncSession, audit_logger: AuditLogger):
        self.db = db
        self.audit_logger = audit_logger
    
    async def create_share(
        self,
        resource_id: str,
        resource_type: str,
        permission: SharePermission,
        expires_in: timedelta = timedelta(days=7)
    ) -> ShareLink:
        """创建共享链接"""
        token = self._generate_token()
        share = ShareLink(
            id=uuid4(),
            resource_id=resource_id,
            resource_type=resource_type,
            permission=permission,
            token=token,
            expires_at=datetime.utcnow() + expires_in
        )
        return share
    
    async def access_shared_resource(
        self,
        token: str,
        accessor_tenant_id: str
    ) -> SharedResource:
        """访问共享资源"""
        share = await self.get_share_by_token(token)
        
        # 检查是否过期
        if share.expires_at < datetime.utcnow():
            raise ShareExpiredError()
        
        # 检查白名单
        if not await self.is_tenant_whitelisted(share.owner_tenant_id, accessor_tenant_id):
            raise TenantNotWhitelistedError()
        
        # 记录访问日志
        await self.audit_logger.log_cross_tenant_access(
            accessor_tenant_id, share.owner_tenant_id, share.resource_id
        )
        
        return SharedResource(share=share, permission=share.permission)
    
    async def revoke_share(self, share_id: str) -> None:
        """撤销共享"""
        pass
    
    async def set_whitelist(self, tenant_id: str, allowed_tenants: List[str]) -> None:
        """设置允许协作的租户白名单"""
        pass
    
    async def is_tenant_whitelisted(self, owner_tenant_id: str, accessor_tenant_id: str) -> bool:
        """检查租户是否在白名单中"""
        pass
    
    def _generate_token(self) -> str:
        """生成访问令牌"""
        return secrets.token_urlsafe(32)

class SharePermission(str, Enum):
    READ_ONLY = "read_only"
    EDIT = "edit"

class ShareLink(BaseModel):
    id: UUID
    resource_id: str
    resource_type: str
    permission: SharePermission
    token: str
    owner_tenant_id: str
    expires_at: datetime
    created_at: datetime
```

### 7. API Router (API 路由)

**文件**: `src/api/multi_tenant.py`

```python
router = APIRouter(prefix="/api/v1", tags=["Multi-Tenant"])

# 租户管理
@router.post("/tenants")
async def create_tenant(request: TenantCreateRequest) -> Tenant:
    pass

@router.get("/tenants")
async def list_tenants() -> List[Tenant]:
    pass

@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str) -> Tenant:
    pass

@router.put("/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, request: TenantUpdateRequest) -> Tenant:
    pass

@router.put("/tenants/{tenant_id}/status")
async def set_tenant_status(tenant_id: str, status: TenantStatus) -> Tenant:
    pass

@router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str) -> None:
    pass

# 工作空间管理
@router.post("/workspaces")
async def create_workspace(request: WorkspaceCreateRequest) -> Workspace:
    pass

@router.get("/workspaces")
async def list_workspaces(tenant_id: str = None) -> List[Workspace]:
    pass

@router.get("/workspaces/hierarchy")
async def get_workspace_hierarchy(tenant_id: str) -> List[WorkspaceNode]:
    pass

@router.put("/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, request: WorkspaceUpdateRequest) -> Workspace:
    pass

@router.post("/workspaces/{workspace_id}/archive")
async def archive_workspace(workspace_id: str) -> Workspace:
    pass

@router.post("/workspaces/{workspace_id}/restore")
async def restore_workspace(workspace_id: str) -> Workspace:
    pass

@router.put("/workspaces/{workspace_id}/move")
async def move_workspace(workspace_id: str, new_parent_id: str) -> Workspace:
    pass

# 成员管理
@router.post("/workspaces/{workspace_id}/members/invite")
async def invite_member(workspace_id: str, request: InviteRequest) -> Invitation:
    pass

@router.post("/workspaces/{workspace_id}/members")
async def add_member(workspace_id: str, request: AddMemberRequest) -> WorkspaceMember:
    pass

@router.get("/workspaces/{workspace_id}/members")
async def list_members(workspace_id: str) -> List[WorkspaceMember]:
    pass

@router.put("/workspaces/{workspace_id}/members/{user_id}/role")
async def update_member_role(workspace_id: str, user_id: str, role: MemberRole) -> WorkspaceMember:
    pass

@router.delete("/workspaces/{workspace_id}/members/{user_id}")
async def remove_member(workspace_id: str, user_id: str) -> None:
    pass

@router.post("/workspaces/{workspace_id}/members/batch")
async def batch_add_members(workspace_id: str, request: BatchAddRequest) -> List[WorkspaceMember]:
    pass

# 配额管理
@router.get("/quotas/{entity_type}/{entity_id}")
async def get_quota(entity_type: EntityType, entity_id: str) -> Quota:
    pass

@router.put("/quotas/{entity_type}/{entity_id}")
async def set_quota(entity_type: EntityType, entity_id: str, request: QuotaConfig) -> Quota:
    pass

@router.get("/quotas/{entity_type}/{entity_id}/usage")
async def get_usage(entity_type: EntityType, entity_id: str) -> QuotaUsage:
    pass

# 跨租户协作
@router.post("/shares")
async def create_share(request: CreateShareRequest) -> ShareLink:
    pass

@router.get("/shares/{token}")
async def access_share(token: str) -> SharedResource:
    pass

@router.delete("/shares/{share_id}")
async def revoke_share(share_id: str) -> None:
    pass

@router.put("/tenants/{tenant_id}/whitelist")
async def set_whitelist(tenant_id: str, request: WhitelistRequest) -> None:
    pass

# 管理员控制台
@router.get("/admin/dashboard")
async def get_admin_dashboard() -> AdminDashboard:
    pass

@router.get("/admin/services")
async def get_service_status() -> List[ServiceStatus]:
    pass

@router.put("/admin/config")
async def update_system_config(request: SystemConfigRequest) -> SystemConfig:
    pass

@router.get("/admin/audit-logs")
async def get_audit_logs(filters: AuditLogFilters = None) -> List[AuditLog]:
    pass
```

## Data Models

### 数据库模型

```python
class Tenant(Base):
    """租户表"""
    __tablename__ = "tenants"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active")
    config = Column(JSONB, default={})
    plan = Column(String(50), default="free")
    admin_email = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Workspace(Base):
    """工作空间表"""
    __tablename__ = "workspaces"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    parent_id = Column(UUID, ForeignKey("workspaces.id"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSONB, default={})
    status = Column(String(20), default="active")  # active/archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkspaceMember(Base):
    """工作空间成员表"""
    __tablename__ = "workspace_members"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    workspace_id = Column(UUID, ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)
    custom_role_id = Column(UUID, ForeignKey("custom_roles.id"), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, nullable=True)

class CustomRole(Base):
    """自定义角色表"""
    __tablename__ = "custom_roles"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    workspace_id = Column(UUID, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSONB, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)

class TenantQuota(Base):
    """租户配额表"""
    __tablename__ = "tenant_quotas"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, unique=True)
    storage_bytes = Column(BigInteger, default=10737418240)  # 10GB
    project_count = Column(Integer, default=100)
    user_count = Column(Integer, default=50)
    api_call_count = Column(Integer, default=100000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QuotaUsage(Base):
    """配额使用表"""
    __tablename__ = "quota_usage"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    entity_id = Column(UUID, nullable=False)
    entity_type = Column(String(20), nullable=False)  # tenant/workspace
    storage_bytes = Column(BigInteger, default=0)
    project_count = Column(Integer, default=0)
    user_count = Column(Integer, default=0)
    api_call_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

class ShareLink(Base):
    """共享链接表"""
    __tablename__ = "share_links"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    resource_id = Column(UUID, nullable=False)
    resource_type = Column(String(50), nullable=False)
    owner_tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    permission = Column(String(20), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TenantWhitelist(Base):
    """租户白名单表"""
    __tablename__ = "tenant_whitelist"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    owner_tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    allowed_tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CrossTenantAccessLog(Base):
    """跨租户访问日志表"""
    __tablename__ = "cross_tenant_access_logs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    accessor_tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    owner_tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    resource_id = Column(UUID, nullable=False)
    resource_type = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 租户和工作空间 ID 唯一性

*For any* 创建的租户或工作空间，其 ID 应在整个系统中唯一，不存在重复。

**Validates: Requirements 1.2, 2.2**

### Property 2: 默认配置初始化

*For any* 新创建的租户，应自动初始化默认配置和资源配额；新创建的工作空间应继承租户的默认配置。

**Validates: Requirements 1.3, 2.4**

### Property 3: 禁用租户访问阻止

*For any* 状态为禁用的租户，该租户下的所有操作请求应被拒绝。

**Validates: Requirements 1.5**

### Property 4: 工作空间层级完整性

*For any* 工作空间层级操作（移动、删除），应保持层级结构的完整性，不产生孤立节点或循环引用。

**Validates: Requirements 2.3**

### Property 5: 成员移除权限撤销

*For any* 被移除的工作空间成员，其所有权限应被立即撤销，无法再访问该工作空间的任何资源。

**Validates: Requirements 3.6**

### Property 6: 配额使用追踪准确性

*For any* 资源操作（创建/删除），配额使用量应准确更新，反映实际资源使用情况。

**Validates: Requirements 4.2**

### Property 7: 配额阈值执行

*For any* 资源使用达到配额 80% 时应发送预警；达到 100% 时应阻止新资源创建。

**Validates: Requirements 4.3, 4.4**

### Property 8: 租户数据隔离

*For any* 数据库查询，应自动注入租户过滤条件；用户只能访问其所属租户的数据。

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

### Property 9: 跨租户共享令牌过期

*For any* 跨租户共享链接，过期后应无法访问；访问时应验证令牌有效性。

**Validates: Requirements 6.3**

### Property 10: 跨租户白名单执行

*For any* 跨租户访问请求，只有白名单中的租户才能访问共享资源。

**Validates: Requirements 6.6**

### Property 11: 审计日志完整性

*For any* 租户操作、跨租户访问尝试，应记录完整的审计日志，包括操作类型、操作人、时间、结果。

**Validates: Requirements 1.6, 5.6, 6.5**

## Error Handling

### 错误分类

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| 租户不存在 | TENANT_NOT_FOUND | 返回 404 |
| 租户已禁用 | TENANT_DISABLED | 返回 403，阻止操作 |
| 工作空间不存在 | WORKSPACE_NOT_FOUND | 返回 404 |
| 权限不足 | PERMISSION_DENIED | 返回 403 |
| 配额超限 | QUOTA_EXCEEDED | 返回 429，阻止创建 |
| 共享已过期 | SHARE_EXPIRED | 返回 410 |
| 租户不在白名单 | TENANT_NOT_WHITELISTED | 返回 403 |
| 跨租户访问拒绝 | CROSS_TENANT_ACCESS_DENIED | 返回 403，记录日志 |

## Testing Strategy

### 单元测试

- 测试租户 CRUD 操作
- 测试工作空间层级管理
- 测试成员角色分配
- 测试配额计算和检查
- 测试数据隔离过滤

### 属性测试

```python
from hypothesis import given, strategies as st

@given(st.lists(st.text(min_size=1), min_size=2, max_size=100))
def test_tenant_id_uniqueness(tenant_names: List[str]):
    """Property 1: 租户 ID 唯一性"""
    tenants = [tenant_manager.create_tenant(TenantCreateConfig(name=n)) for n in tenant_names]
    ids = [t.id for t in tenants]
    assert len(ids) == len(set(ids))

@given(st.integers(min_value=0, max_value=100), st.integers(min_value=1, max_value=100))
def test_quota_threshold_enforcement(usage: int, limit: int):
    """Property 7: 配额阈值执行"""
    percentage = usage / limit * 100
    result = quota_manager.check_quota(entity_id, EntityType.TENANT, ResourceType.PROJECTS, 1)
    
    if percentage >= 100:
        assert result.allowed == False
    else:
        assert result.allowed == True

@given(st.text(min_size=1), st.text(min_size=1))
def test_tenant_data_isolation(tenant1_id: str, tenant2_id: str):
    """Property 8: 租户数据隔离"""
    # 租户1创建数据
    data = create_data_for_tenant(tenant1_id)
    
    # 租户2查询不应看到租户1的数据
    results = query_data_as_tenant(tenant2_id)
    assert data.id not in [r.id for r in results]
```

### 集成测试

- 测试完整的租户创建 → 工作空间创建 → 成员邀请流程
- 测试跨租户协作场景
- 测试配额预警和阻止流程
- 测试管理员控制台功能
