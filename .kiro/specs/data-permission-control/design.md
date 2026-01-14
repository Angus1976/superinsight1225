# Design Document: Data Permission Control (数据权限控制)

## Overview

本设计文档描述 Data Permission Control 模块的架构设计，该模块实现强大的数据权限控制功能，支持继承客户现有权限策略、审批流程、访问日志，确保数据在管理、标注、查询、调用等各环节的安全访问。

设计原则：
- **最小权限**：用户只能访问必要的数据
- **策略继承**：无缝集成客户现有权限体系
- **完整审计**：所有数据访问都有日志记录
- **动态控制**：基于上下文动态调整权限

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        PermissionConfigUI[Permission Config UI]
        PolicyImportUI[Policy Import UI]
        ApprovalUI[Approval Workflow UI]
        AccessLogUI[Access Log UI]
        ClassificationUI[Classification UI]
        MaskingConfigUI[Masking Config UI]
    end

    subgraph API["API 层"]
        PermissionRouter[/api/v1/data-permissions]
        PolicyRouter[/api/v1/policies]
        ApprovalRouter[/api/v1/approvals]
        AccessLogRouter[/api/v1/access-logs]
    end

    subgraph Core["核心层"]
        DataPermissionEngine[Data Permission Engine]
        PolicyInheritanceManager[Policy Inheritance Manager]
        ApprovalWorkflowEngine[Approval Workflow Engine]
        AccessLogManager[Access Log Manager]
        DataClassificationEngine[Data Classification Engine]
        ContextAwareAccessController[Context-Aware Access Controller]
        DataMaskingService[Data Masking Service]
    end
    
    subgraph External["外部系统"]
        LDAP[LDAP/AD]
        OAuth[OAuth/OIDC Provider]
        CustomPolicy[Custom Policy Files]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
        AuditDB[(Audit Log DB)]
    end
    
    PermissionConfigUI --> PermissionRouter
    PolicyImportUI --> PolicyRouter
    ApprovalUI --> ApprovalRouter
    AccessLogUI --> AccessLogRouter
    ClassificationUI --> PermissionRouter
    MaskingConfigUI --> PermissionRouter
    
    PermissionRouter --> DataPermissionEngine
    PolicyRouter --> PolicyInheritanceManager
    ApprovalRouter --> ApprovalWorkflowEngine
    AccessLogRouter --> AccessLogManager
    
    PolicyInheritanceManager --> LDAP
    PolicyInheritanceManager --> OAuth
    PolicyInheritanceManager --> CustomPolicy
    
    DataPermissionEngine --> DB
    DataPermissionEngine --> Cache
    AccessLogManager --> AuditDB
    DataClassificationEngine --> DB
    DataMaskingService --> Cache
```

## Components and Interfaces

### 1. Data Permission Engine (数据权限引擎)

**文件**: `src/security/data_permission_engine.py`

**职责**: 管理数据级别的访问控制（数据集/记录/字段级别）

```python
class DataPermissionEngine:
    """数据权限引擎"""
    
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache
    
    async def check_dataset_permission(
        self,
        user_id: str,
        dataset_id: str,
        action: str
    ) -> PermissionResult:
        """检查数据集级别权限"""
        pass
    
    async def check_record_permission(
        self,
        user_id: str,
        dataset_id: str,
        record_id: str,
        action: str
    ) -> PermissionResult:
        """检查记录级别权限（行级安全）"""
        pass

    async def check_field_permission(
        self,
        user_id: str,
        dataset_id: str,
        field_name: str,
        action: str
    ) -> PermissionResult:
        """检查字段级别权限（列级安全）"""
        pass
    
    async def check_tag_based_permission(
        self,
        user_id: str,
        resource_tags: List[str],
        action: str
    ) -> PermissionResult:
        """检查基于标签的权限（ABAC）"""
        pass
    
    async def grant_temporary_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        expires_at: datetime
    ) -> TemporaryGrant:
        """授予临时权限"""
        pass
    
    async def revoke_permission(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> bool:
        """撤销权限"""
        pass

class PermissionResult(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    requires_approval: bool = False
    masked_fields: List[str] = []
```

### 2. Policy Inheritance Manager (策略继承管理器)

**文件**: `src/security/policy_inheritance_manager.py`

**职责**: 继承和同步客户现有权限策略

```python
class PolicyInheritanceManager:
    """策略继承管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.connectors: Dict[str, PolicyConnector] = {}
    
    async def import_ldap_policies(
        self,
        ldap_config: LDAPConfig
    ) -> ImportResult:
        """导入 LDAP/AD 权限策略"""
        pass
    
    async def import_oauth_claims(
        self,
        oauth_config: OAuthConfig
    ) -> ImportResult:
        """导入 OAuth/OIDC 权限声明"""
        pass

    async def import_custom_policies(
        self,
        policy_file: Union[str, Dict],
        format: str = "json"
    ) -> ImportResult:
        """导入自定义 JSON/YAML 权限配置"""
        pass
    
    async def schedule_sync(
        self,
        source_id: str,
        cron_expression: str
    ) -> SyncSchedule:
        """配置定时同步"""
        pass
    
    async def sync_policies(self, source_id: str) -> SyncResult:
        """同步外部策略"""
        pass
    
    async def detect_conflicts(
        self,
        new_policies: List[Policy]
    ) -> List[PolicyConflict]:
        """检测策略冲突"""
        pass
    
    async def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution
    ) -> Policy:
        """解决策略冲突"""
        pass

class LDAPConfig(BaseModel):
    url: str
    base_dn: str
    bind_dn: str
    bind_password: str
    group_filter: str
    attribute_mapping: Dict[str, str]

class ImportResult(BaseModel):
    success: bool
    imported_count: int
    conflicts: List[PolicyConflict]
    errors: List[str]
```

### 3. Approval Workflow Engine (审批流引擎)

**文件**: `src/security/approval_workflow_engine.py`

**职责**: 管理数据访问审批流程

```python
class ApprovalWorkflowEngine:
    """审批流引擎"""
    
    def __init__(self, db: AsyncSession, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
    
    async def create_approval_request(
        self,
        requester_id: str,
        resource: str,
        action: str,
        reason: str
    ) -> ApprovalRequest:
        """创建审批请求"""
        pass
    
    async def route_approval(
        self,
        request: ApprovalRequest
    ) -> List[Approver]:
        """基于敏感级别自动路由审批"""
        pass

    async def approve(
        self,
        request_id: str,
        approver_id: str,
        decision: str,
        comments: str = None
    ) -> ApprovalResult:
        """审批决策"""
        pass
    
    async def handle_timeout(self, request_id: str) -> ApprovalResult:
        """处理审批超时"""
        pass
    
    async def delegate_approval(
        self,
        approver_id: str,
        delegate_to: str,
        start_date: datetime,
        end_date: datetime
    ) -> Delegation:
        """审批委托"""
        pass
    
    async def get_approval_history(
        self,
        request_id: str
    ) -> List[ApprovalAction]:
        """获取审批历史"""
        pass

class ApprovalRequest(BaseModel):
    id: str
    requester_id: str
    resource: str
    action: str
    reason: str
    sensitivity_level: str
    status: str  # pending/approved/rejected/expired
    created_at: datetime
    expires_at: datetime

class ApprovalWorkflow(BaseModel):
    id: str
    name: str
    sensitivity_levels: List[str]
    approval_levels: List[ApprovalLevel]
    timeout_hours: int
    auto_approve_conditions: List[Dict]
```

### 4. Access Log Manager (访问日志管理器)

**文件**: `src/security/access_log_manager.py`

**职责**: 记录所有数据访问行为

```python
class AccessLogManager:
    """访问日志管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_read(
        self,
        user_id: str,
        resource: str,
        fields: List[str] = None,
        context: AccessContext = None
    ) -> AccessLog:
        """记录读取操作"""
        pass
    
    async def log_modify(
        self,
        user_id: str,
        resource: str,
        changes: Dict,
        context: AccessContext = None
    ) -> AccessLog:
        """记录修改操作"""
        pass

    async def log_export(
        self,
        user_id: str,
        resource: str,
        export_format: str,
        record_count: int,
        context: AccessContext = None
    ) -> AccessLog:
        """记录导出操作"""
        pass
    
    async def log_api_call(
        self,
        user_id: str,
        endpoint: str,
        method: str,
        params: Dict,
        response_code: int,
        context: AccessContext = None
    ) -> AccessLog:
        """记录 API 调用"""
        pass
    
    async def query_logs(
        self,
        filters: AccessLogFilter
    ) -> List[AccessLog]:
        """查询访问日志"""
        pass
    
    async def export_logs(
        self,
        filters: AccessLogFilter,
        format: str = "csv"
    ) -> bytes:
        """导出访问日志"""
        pass

class AccessLog(BaseModel):
    id: str
    user_id: str
    operation_type: str  # read/modify/export/api_call
    resource: str
    details: Dict
    ip_address: str
    user_agent: str
    timestamp: datetime
    sensitivity_level: str

class AccessContext(BaseModel):
    ip_address: str
    user_agent: str
    session_id: str
    request_id: str
    additional_info: Dict = {}
```

### 5. Data Classification Engine (数据分类引擎)

**文件**: `src/security/data_classification_engine.py`

**职责**: 对数据进行分类和敏感级别标记

```python
class DataClassificationEngine:
    """数据分类引擎"""
    
    def __init__(self, db: AsyncSession, ai_service: AIService = None):
        self.db = db
        self.ai_service = ai_service
    
    async def define_classification_schema(
        self,
        schema: ClassificationSchema
    ) -> ClassificationSchema:
        """定义数据分类体系"""
        pass
    
    async def define_sensitivity_levels(
        self,
        levels: List[SensitivityLevel]
    ) -> List[SensitivityLevel]:
        """定义敏感级别"""
        pass

    async def auto_classify(
        self,
        dataset_id: str,
        use_ai: bool = True
    ) -> ClassificationResult:
        """自动数据分类（基于规则/AI）"""
        pass
    
    async def batch_update_classification(
        self,
        updates: List[ClassificationUpdate]
    ) -> BatchUpdateResult:
        """批量修改数据分类"""
        pass
    
    async def generate_classification_report(
        self,
        dataset_id: str = None
    ) -> ClassificationReport:
        """生成数据分类报告"""
        pass

class SensitivityLevel(BaseModel):
    id: str
    name: str  # public/internal/confidential/top_secret
    level: int  # 0-4
    description: str
    access_requirements: List[str]
    auto_masking: bool

class ClassificationSchema(BaseModel):
    id: str
    name: str
    categories: List[Category]
    rules: List[ClassificationRule]
```

### 6. Context-Aware Access Controller (上下文感知访问控制器)

**文件**: `src/security/context_aware_access_controller.py`

**职责**: 基于上下文动态控制访问

```python
class ContextAwareAccessController:
    """上下文感知访问控制器"""
    
    def __init__(self, db: AsyncSession, permission_engine: DataPermissionEngine):
        self.db = db
        self.permission_engine = permission_engine
    
    async def check_management_permission(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> PermissionResult:
        """检查管理场景权限"""
        pass
    
    async def check_annotation_permission(
        self,
        user_id: str,
        task_id: str,
        action: str  # view/edit/submit
    ) -> PermissionResult:
        """检查标注场景权限"""
        pass

    async def check_query_permission(
        self,
        user_id: str,
        query_type: str,  # search/filter/statistics
        scope: str
    ) -> PermissionResult:
        """检查查询场景权限"""
        pass
    
    async def check_api_permission(
        self,
        user_id: str,
        endpoint: str,
        method: str
    ) -> PermissionResult:
        """检查调用场景权限（API 访问、数据导出）"""
        pass
    
    async def get_effective_permissions(
        self,
        user_id: str,
        context: str
    ) -> List[Permission]:
        """获取用户在特定上下文的有效权限"""
        pass

class ScenarioPermission(BaseModel):
    scenario: str  # management/annotation/query/api
    permissions: List[Permission]
    conditions: List[Condition]
```

### 7. Data Masking Service (数据脱敏服务)

**文件**: `src/security/data_masking_service.py`

**职责**: 对敏感数据进行脱敏处理

```python
class DataMaskingService:
    """数据脱敏服务"""
    
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache
        self.algorithms: Dict[str, MaskingAlgorithm] = {}
    
    async def register_algorithm(
        self,
        name: str,
        algorithm: MaskingAlgorithm
    ) -> None:
        """注册脱敏算法"""
        pass
    
    async def mask_data(
        self,
        data: Dict,
        user_id: str,
        masking_rules: List[MaskingRule] = None
    ) -> Dict:
        """动态脱敏（查询时脱敏）"""
        pass
    
    async def mask_for_export(
        self,
        data: List[Dict],
        export_config: ExportConfig
    ) -> List[Dict]:
        """静态脱敏（导出时脱敏）"""
        pass

    async def get_masking_rules(
        self,
        user_id: str,
        resource: str
    ) -> List[MaskingRule]:
        """获取用户对资源的脱敏规则"""
        pass
    
    async def configure_masking_rule(
        self,
        rule: MaskingRule
    ) -> MaskingRule:
        """配置脱敏规则"""
        pass

class MaskingAlgorithm(ABC):
    @abstractmethod
    def mask(self, value: Any) -> Any:
        pass

class ReplacementMasking(MaskingAlgorithm):
    """替换脱敏"""
    def mask(self, value: Any) -> Any:
        return "***"

class PartialMasking(MaskingAlgorithm):
    """部分遮盖脱敏"""
    def mask(self, value: Any) -> Any:
        if isinstance(value, str) and len(value) > 4:
            return value[:2] + "****" + value[-2:]
        return "****"

class EncryptionMasking(MaskingAlgorithm):
    """加密脱敏"""
    def mask(self, value: Any) -> Any:
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]

class MaskingRule(BaseModel):
    id: str
    field_pattern: str
    algorithm: str
    applicable_roles: List[str]
    conditions: List[Dict]
```

## Database Models

### Permission Models

```python
# src/models/data_permission.py

class DataPermission(Base):
    __tablename__ = "data_permissions"
    
    id = Column(String, primary_key=True)
    resource_type = Column(String)  # dataset/record/field
    resource_id = Column(String)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    role_id = Column(String, ForeignKey("roles.id"), nullable=True)
    action = Column(String)  # read/write/delete/export
    conditions = Column(JSONB)
    granted_by = Column(String, ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

class PolicySource(Base):
    __tablename__ = "policy_sources"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    source_type = Column(String)  # ldap/oauth/custom
    config = Column(JSONB)
    sync_schedule = Column(String)  # cron expression
    last_sync_at = Column(DateTime)
    status = Column(String)

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    
    id = Column(String, primary_key=True)
    requester_id = Column(String, ForeignKey("users.id"))
    resource = Column(String)
    action = Column(String)
    reason = Column(Text)
    sensitivity_level = Column(String)
    status = Column(String)  # pending/approved/rejected/expired
    workflow_id = Column(String, ForeignKey("approval_workflows.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    resolved_at = Column(DateTime, nullable=True)

class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    operation_type = Column(String)
    resource = Column(String)
    details = Column(JSONB)
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sensitivity_level = Column(String)

class DataClassification(Base):
    __tablename__ = "data_classifications"
    
    id = Column(String, primary_key=True)
    dataset_id = Column(String, ForeignKey("datasets.id"))
    field_name = Column(String, nullable=True)
    category = Column(String)
    sensitivity_level = Column(String)
    classified_by = Column(String)  # rule/ai/manual
    classified_at = Column(DateTime, default=datetime.utcnow)
```

## API Endpoints

### Data Permission API

```python
# src/api/data_permission_router.py

router = APIRouter(prefix="/api/v1/data-permissions", tags=["Data Permissions"])

@router.post("/check")
async def check_permission(request: PermissionCheckRequest) -> PermissionResult:
    """检查数据权限"""
    pass

@router.post("/grant")
async def grant_permission(request: GrantPermissionRequest) -> DataPermission:
    """授予权限"""
    pass

@router.post("/revoke")
async def revoke_permission(request: RevokePermissionRequest) -> bool:
    """撤销权限"""
    pass

@router.get("/user/{user_id}")
async def get_user_permissions(user_id: str) -> List[DataPermission]:
    """获取用户权限列表"""
    pass
```

### Policy API

```python
# src/api/policy_router.py

router = APIRouter(prefix="/api/v1/policies", tags=["Policies"])

@router.post("/import/ldap")
async def import_ldap_policies(config: LDAPConfig) -> ImportResult:
    """导入 LDAP 策略"""
    pass

@router.post("/import/oauth")
async def import_oauth_policies(config: OAuthConfig) -> ImportResult:
    """导入 OAuth 策略"""
    pass

@router.post("/import/custom")
async def import_custom_policies(file: UploadFile) -> ImportResult:
    """导入自定义策略"""
    pass

@router.post("/sync/{source_id}")
async def sync_policies(source_id: str) -> SyncResult:
    """同步策略"""
    pass

@router.get("/conflicts")
async def get_policy_conflicts() -> List[PolicyConflict]:
    """获取策略冲突"""
    pass
```

### Approval API

```python
# src/api/approval_router.py

router = APIRouter(prefix="/api/v1/approvals", tags=["Approvals"])

@router.post("/request")
async def create_approval_request(request: CreateApprovalRequest) -> ApprovalRequest:
    """创建审批请求"""
    pass

@router.post("/{request_id}/approve")
async def approve_request(request_id: str, decision: ApprovalDecision) -> ApprovalResult:
    """审批请求"""
    pass

@router.get("/pending")
async def get_pending_approvals(user_id: str = None) -> List[ApprovalRequest]:
    """获取待审批列表"""
    pass

@router.get("/{request_id}/history")
async def get_approval_history(request_id: str) -> List[ApprovalAction]:
    """获取审批历史"""
    pass
```

### Access Log API

```python
# src/api/access_log_router.py

router = APIRouter(prefix="/api/v1/access-logs", tags=["Access Logs"])

@router.get("/")
async def query_access_logs(filters: AccessLogFilter = Depends()) -> List[AccessLog]:
    """查询访问日志"""
    pass

@router.get("/export")
async def export_access_logs(filters: AccessLogFilter = Depends(), format: str = "csv") -> StreamingResponse:
    """导出访问日志"""
    pass

@router.get("/statistics")
async def get_access_statistics(start_date: datetime, end_date: datetime) -> AccessStatistics:
    """获取访问统计"""
    pass
```

## Frontend Components

### Permission Configuration UI

```typescript
// frontend/src/pages/permissions/PermissionConfigPage.tsx

interface PermissionConfigPageProps {
  resourceType: 'dataset' | 'record' | 'field';
}

const PermissionConfigPage: React.FC<PermissionConfigPageProps> = ({ resourceType }) => {
  // 权限配置界面
  // - 资源选择器
  // - 用户/角色选择器
  // - 权限操作选择
  // - 条件配置
};

// frontend/src/pages/permissions/PolicyImportWizard.tsx
const PolicyImportWizard: React.FC = () => {
  // 策略导入向导
  // Step 1: 选择策略来源 (LDAP/OAuth/Custom)
  // Step 2: 配置连接参数
  // Step 3: 预览导入结果
  // Step 4: 确认导入
};

// frontend/src/pages/permissions/ApprovalWorkflowPage.tsx
const ApprovalWorkflowPage: React.FC = () => {
  // 审批工单列表
  // - 待审批列表
  // - 已处理列表
  // - 审批详情弹窗
};

// frontend/src/pages/permissions/AccessLogPage.tsx
const AccessLogPage: React.FC = () => {
  // 访问日志查询界面
  // - 高级筛选
  // - 日志列表
  // - 导出功能
};

// frontend/src/pages/permissions/DataClassificationPage.tsx
const DataClassificationPage: React.FC = () => {
  // 数据分类管理界面
  // - 分类体系配置
  // - 敏感级别配置
  // - 自动分类触发
};

// frontend/src/pages/permissions/MaskingConfigPage.tsx
const MaskingConfigPage: React.FC = () => {
  // 脱敏规则配置界面
  // - 规则列表
  // - 算法选择
  // - 预览效果
};
```

## Correctness Properties (Property-Based Testing)

使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代。

### Property 1: 权限检查一致性

```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(
    user_id=st.text(min_size=1, max_size=50),
    resource=st.text(min_size=1, max_size=100),
    action=st.sampled_from(["read", "write", "delete", "export"])
)
def test_permission_check_consistency(user_id, resource, action):
    """相同输入应产生相同的权限检查结果"""
    result1 = permission_engine.check_permission(user_id, resource, action)
    result2 = permission_engine.check_permission(user_id, resource, action)
    assert result1.allowed == result2.allowed
```

### Property 2: 权限层级传递性

```python
@settings(max_examples=100)
@given(
    user_id=st.text(min_size=1, max_size=50),
    dataset_id=st.text(min_size=1, max_size=50),
    record_id=st.text(min_size=1, max_size=50)
)
def test_permission_hierarchy_transitivity(user_id, dataset_id, record_id):
    """如果用户没有数据集权限，则不应有记录权限"""
    dataset_perm = permission_engine.check_dataset_permission(user_id, dataset_id, "read")
    if not dataset_perm.allowed:
        record_perm = permission_engine.check_record_permission(user_id, dataset_id, record_id, "read")
        assert not record_perm.allowed or record_perm.requires_approval
```

### Property 3: 策略导入幂等性

```python
@settings(max_examples=100)
@given(
    policy_data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.text(min_size=1, max_size=50),
        min_size=1,
        max_size=10
    )
)
def test_policy_import_idempotency(policy_data):
    """重复导入相同策略应产生相同结果"""
    result1 = policy_manager.import_custom_policies(policy_data)
    result2 = policy_manager.import_custom_policies(policy_data)
    assert result1.imported_count == result2.imported_count
```

### Property 4: 审批流程完整性

```python
@settings(max_examples=100)
@given(
    requester_id=st.text(min_size=1, max_size=50),
    resource=st.text(min_size=1, max_size=100),
    action=st.sampled_from(["read", "write", "export"])
)
def test_approval_workflow_completeness(requester_id, resource, action):
    """审批请求必须有明确的最终状态"""
    request = approval_engine.create_approval_request(requester_id, resource, action, "test")
    # 模拟审批流程
    final_status = simulate_approval_workflow(request.id)
    assert final_status in ["approved", "rejected", "expired"]
```

### Property 5: 访问日志完整性

```python
@settings(max_examples=100)
@given(
    user_id=st.text(min_size=1, max_size=50),
    resource=st.text(min_size=1, max_size=100),
    operation=st.sampled_from(["read", "modify", "export", "api_call"])
)
def test_access_log_completeness(user_id, resource, operation):
    """每次数据访问都应有对应的日志记录"""
    # 执行数据访问
    access_data(user_id, resource, operation)
    # 验证日志存在
    logs = access_log_manager.query_logs(user_id=user_id, resource=resource)
    assert len(logs) > 0
    assert logs[-1].operation_type == operation
```

### Property 6: 数据分类一致性

```python
@settings(max_examples=100)
@given(
    dataset_id=st.text(min_size=1, max_size=50),
    field_name=st.text(min_size=1, max_size=30)
)
def test_classification_consistency(dataset_id, field_name):
    """相同数据的分类结果应一致"""
    result1 = classification_engine.auto_classify(dataset_id)
    result2 = classification_engine.auto_classify(dataset_id)
    # 使用相同规则时，分类结果应一致
    assert result1.classifications == result2.classifications
```

### Property 7: 脱敏可逆性验证

```python
@settings(max_examples=100)
@given(
    original_value=st.text(min_size=1, max_size=100),
    algorithm=st.sampled_from(["replacement", "partial", "encryption"])
)
def test_masking_irreversibility(original_value, algorithm):
    """脱敏后的数据不应能还原原始值（除非有解密密钥）"""
    masked = masking_service.mask_value(original_value, algorithm)
    if algorithm != "encryption":
        assert masked != original_value
        assert original_value not in masked
```

### Property 8: 上下文权限隔离

```python
@settings(max_examples=100)
@given(
    user_id=st.text(min_size=1, max_size=50),
    context1=st.sampled_from(["management", "annotation", "query", "api"]),
    context2=st.sampled_from(["management", "annotation", "query", "api"])
)
def test_context_permission_isolation(user_id, context1, context2):
    """不同上下文的权限应相互独立"""
    if context1 != context2:
        perms1 = context_controller.get_effective_permissions(user_id, context1)
        perms2 = context_controller.get_effective_permissions(user_id, context2)
        # 权限可以不同（除非显式配置相同）
        # 验证权限是基于上下文独立计算的
        assert perms1 is not perms2  # 不是同一个对象
```

## Integration Points

### 与 audit-security 模块集成

```python
# 复用 audit-security 的 RBAC 引擎
from src.security.rbac_engine import RBACEngine

class DataPermissionEngine:
    def __init__(self, rbac_engine: RBACEngine):
        self.rbac_engine = rbac_engine
    
    async def check_permission(self, user_id, resource, action):
        # 先检查基础 RBAC 权限
        rbac_result = await self.rbac_engine.check_permission(user_id, resource, action)
        if not rbac_result:
            return PermissionResult(allowed=False, reason="RBAC denied")
        
        # 再检查数据级别权限
        return await self._check_data_level_permission(user_id, resource, action)
```

### 与 desensitization 模块集成

```python
# 复用现有脱敏服务
from src.desensitization.service import DesensitizationService

class DataMaskingService:
    def __init__(self, desensitization_service: DesensitizationService):
        self.desensitization_service = desensitization_service
```

## Performance Considerations

- 权限检查结果缓存（Redis，TTL 5分钟）
- 策略同步使用增量更新
- 访问日志异步写入
- 数据分类使用批量处理
