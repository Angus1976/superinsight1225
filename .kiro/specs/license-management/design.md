# Design Document: License Management (许可管理)

## Overview

本设计文档描述 License Management 模块的架构设计，该模块实现灵活的私有化部署许可管理功能，支持并发用户控制、时间控制、CPU 核心数控制等多种授权方式，以及远程密钥授权和激活机制。

设计原则：
- **安全性**：许可证使用数字签名和加密保护
- **灵活性**：支持多种授权模式和组合
- **可审计**：所有许可操作都有完整记录
- **离线支持**：支持离线环境的许可验证

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        LicenseDashboard[License Dashboard]
        ActivationUI[Activation UI]
        UsageMonitor[Usage Monitor]
        LicenseConfig[License Config]
    end

    subgraph API["API 层"]
        LicenseRouter[/api/v1/license]
        ActivationRouter[/api/v1/activation]
        UsageRouter[/api/v1/usage]
    end
    
    subgraph Core["核心层"]
        LicenseManager[License Manager]
        LicenseValidator[License Validator]
        ConcurrentUserController[Concurrent User Controller]
        TimeController[Time Controller]
        ResourceController[Resource Controller]
        RemoteActivationService[Remote Activation Service]
        LicenseAuditLogger[License Audit Logger]
    end
    
    subgraph External["外部服务"]
        LicenseServer[License Server]
        HardwareFingerprint[Hardware Fingerprint]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
        LicenseFile[License File]
    end

    LicenseDashboard --> LicenseRouter
    ActivationUI --> ActivationRouter
    UsageMonitor --> UsageRouter
    LicenseConfig --> LicenseRouter
    
    LicenseRouter --> LicenseManager
    LicenseRouter --> LicenseValidator
    ActivationRouter --> RemoteActivationService
    UsageRouter --> ConcurrentUserController
    UsageRouter --> ResourceController
    
    RemoteActivationService --> LicenseServer
    RemoteActivationService --> HardwareFingerprint
    
    LicenseManager --> DB
    LicenseManager --> LicenseFile
    ConcurrentUserController --> Cache
    TimeController --> DB
    ResourceController --> DB
    LicenseAuditLogger --> DB
```

## Components and Interfaces

### 1. License Manager (许可管理器)

**文件**: `src/license/license_manager.py`

**职责**: 管理许可证的完整生命周期

```python
class LicenseManager:
    """许可管理器"""
    
    def __init__(self, db: AsyncSession, validator: LicenseValidator):
        self.db = db
        self.validator = validator
        self._license_cache: Optional[License] = None
    
    async def create_license(
        self,
        license_type: str,
        features: List[str],
        limits: LicenseLimits,
        validity: LicenseValidity
    ) -> License:
        """创建许可证"""
        pass
    
    async def activate_license(
        self,
        license_key: str,
        hardware_id: str
    ) -> ActivationResult:
        """激活许可证"""
        pass
    
    async def renew_license(
        self,
        license_id: str,
        new_validity: LicenseValidity
    ) -> License:
        """续期许可证"""
        pass
    
    async def upgrade_license(
        self,
        license_id: str,
        new_features: List[str],
        new_limits: LicenseLimits
    ) -> License:
        """升级许可证"""
        pass
    
    async def revoke_license(
        self,
        license_id: str,
        reason: str
    ) -> bool:
        """撤销许可证"""
        pass
    
    async def get_current_license(self) -> Optional[License]:
        """获取当前许可证"""
        pass

class License(BaseModel):
    id: str
    license_key: str
    license_type: str  # trial/basic/professional/enterprise
    features: List[str]
    limits: LicenseLimits
    validity: LicenseValidity
    hardware_id: Optional[str]
    status: str  # active/expired/revoked/suspended
    signature: str
    created_at: datetime
    activated_at: Optional[datetime]

class LicenseLimits(BaseModel):
    max_concurrent_users: int
    max_cpu_cores: int
    max_storage_gb: int
    max_projects: int
    max_datasets: int
```

### 2. License Validator (许可验证器)

**文件**: `src/license/license_validator.py`

**职责**: 验证许可证的有效性和完整性

```python
class LicenseValidator:
    """许可验证器"""
    
    def __init__(self, public_key: str):
        self.public_key = public_key
    
    async def validate_license(self, license: License) -> ValidationResult:
        """验证许可证"""
        # 验证签名
        if not self._verify_signature(license):
            return ValidationResult(valid=False, reason="Invalid signature")
        
        # 验证有效期
        if not self._check_validity(license):
            return ValidationResult(valid=False, reason="License expired")
        
        # 验证硬件绑定
        if not await self._check_hardware_binding(license):
            return ValidationResult(valid=False, reason="Hardware mismatch")
        
        return ValidationResult(valid=True)
    
    def _verify_signature(self, license: License) -> bool:
        """验证数字签名"""
        pass
    
    def _check_validity(self, license: License) -> bool:
        """检查有效期"""
        now = datetime.utcnow()
        return license.validity.start_date <= now <= license.validity.end_date
    
    async def _check_hardware_binding(self, license: License) -> bool:
        """检查硬件绑定"""
        if not license.hardware_id:
            return True
        current_hardware_id = await self._get_hardware_fingerprint()
        return license.hardware_id == current_hardware_id
    
    async def detect_tampering(self, license: License) -> bool:
        """检测篡改"""
        pass

class ValidationResult(BaseModel):
    valid: bool
    reason: Optional[str] = None
    warnings: List[str] = []
```

### 3. Concurrent User Controller (并发用户控制器)

**文件**: `src/license/concurrent_user_controller.py`

**职责**: 管理同时在线用户数

```python
class ConcurrentUserController:
    """并发用户控制器"""
    
    def __init__(self, cache: Redis, license_manager: LicenseManager):
        self.cache = cache
        self.license_manager = license_manager
    
    async def check_concurrent_limit(self, user_id: str) -> ConcurrentCheckResult:
        """检查并发限制"""
        license = await self.license_manager.get_current_license()
        if not license:
            return ConcurrentCheckResult(allowed=False, reason="No valid license")
        
        current_count = await self._get_current_user_count()
        max_users = license.limits.max_concurrent_users
        
        if current_count >= max_users:
            return ConcurrentCheckResult(
                allowed=False,
                reason=f"Concurrent user limit reached ({current_count}/{max_users})"
            )
        
        return ConcurrentCheckResult(allowed=True, current=current_count, max=max_users)

    async def register_user_session(
        self,
        user_id: str,
        session_id: str,
        priority: int = 0
    ) -> bool:
        """注册用户会话"""
        pass
    
    async def release_user_session(
        self,
        user_id: str,
        session_id: str
    ) -> bool:
        """释放用户会话"""
        pass
    
    async def get_active_sessions(self) -> List[UserSession]:
        """获取活跃会话列表"""
        pass
    
    async def force_logout_user(
        self,
        user_id: str,
        reason: str
    ) -> bool:
        """强制登出用户"""
        pass

class UserSession(BaseModel):
    user_id: str
    session_id: str
    priority: int
    login_time: datetime
    last_activity: datetime
    ip_address: str
```

### 4. Time Controller (时间控制器)

**文件**: `src/license/time_controller.py`

**职责**: 管理许可证的有效期

```python
class TimeController:
    """时间控制器"""
    
    def __init__(self, db: AsyncSession, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
    
    async def check_license_validity(self, license: License) -> ValidityStatus:
        """检查许可证有效期状态"""
        now = datetime.utcnow()
        
        if now < license.validity.start_date:
            return ValidityStatus(status="not_started", days_until_start=...)
        
        if now > license.validity.end_date:
            grace_end = license.validity.end_date + timedelta(days=license.validity.grace_period_days)
            if now <= grace_end:
                return ValidityStatus(status="grace_period", days_remaining=...)
            return ValidityStatus(status="expired")
        
        days_remaining = (license.validity.end_date - now).days
        return ValidityStatus(status="active", days_remaining=days_remaining)
    
    async def send_expiry_reminder(self, license: License) -> None:
        """发送过期提醒"""
        pass
    
    async def apply_expiry_restrictions(self, license: License) -> List[str]:
        """应用过期限制"""
        pass

class LicenseValidity(BaseModel):
    start_date: datetime
    end_date: datetime
    subscription_type: str  # perpetual/monthly/yearly
    grace_period_days: int = 7
    auto_renew: bool = False
```

### 5. Resource Controller (资源控制器)

**文件**: `src/license/resource_controller.py`

**职责**: 管理 CPU 核心数等资源限制

```python
class ResourceController:
    """资源控制器"""
    
    def __init__(self, db: AsyncSession, license_manager: LicenseManager):
        self.db = db
        self.license_manager = license_manager
    
    async def check_cpu_limit(self) -> ResourceCheckResult:
        """检查 CPU 核心数限制"""
        license = await self.license_manager.get_current_license()
        if not license:
            return ResourceCheckResult(allowed=False, reason="No valid license")
        
        available_cores = self._detect_cpu_cores()
        max_cores = license.limits.max_cpu_cores
        
        if available_cores > max_cores:
            return ResourceCheckResult(
                allowed=True,
                warning=f"System has {available_cores} cores, license allows {max_cores}"
            )
        
        return ResourceCheckResult(allowed=True, current=available_cores, max=max_cores)
    
    def _detect_cpu_cores(self) -> int:
        """检测系统 CPU 核心数"""
        import multiprocessing
        return multiprocessing.cpu_count()
    
    async def get_resource_usage(self) -> ResourceUsage:
        """获取资源使用情况"""
        pass
    
    async def record_resource_usage(self) -> None:
        """记录资源使用历史"""
        pass

class ResourceCheckResult(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    warning: Optional[str] = None
    current: Optional[int] = None
    max: Optional[int] = None
```

### 6. Remote Activation Service (远程激活服务)

**文件**: `src/license/remote_activation_service.py`

**职责**: 处理许可证的远程授权和激活

```python
class RemoteActivationService:
    """远程激活服务"""
    
    def __init__(self, license_server_url: str, api_key: str):
        self.license_server_url = license_server_url
        self.api_key = api_key
    
    async def activate_online(
        self,
        license_key: str,
        hardware_fingerprint: str
    ) -> ActivationResult:
        """在线激活"""
        pass
    
    async def generate_offline_request(
        self,
        license_key: str,
        hardware_fingerprint: str
    ) -> OfflineActivationRequest:
        """生成离线激活请求"""
        pass
    
    async def activate_offline(
        self,
        activation_code: str
    ) -> ActivationResult:
        """离线激活"""
        pass

    async def get_hardware_fingerprint(self) -> str:
        """获取硬件指纹"""
        # 组合多个硬件标识
        cpu_id = self._get_cpu_id()
        mac_address = self._get_mac_address()
        disk_serial = self._get_disk_serial()
        
        fingerprint_data = f"{cpu_id}|{mac_address}|{disk_serial}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    async def verify_activation_status(self) -> VerificationResult:
        """验证激活状态（定期校验）"""
        pass
    
    async def remote_revoke(self, license_id: str) -> bool:
        """远程撤销许可证"""
        pass

class ActivationResult(BaseModel):
    success: bool
    license: Optional[License] = None
    error: Optional[str] = None
    activation_id: Optional[str] = None

class OfflineActivationRequest(BaseModel):
    request_code: str
    hardware_fingerprint: str
    license_key: str
    expires_at: datetime
```

### 7. License Audit Logger (许可审计日志器)

**文件**: `src/license/license_audit_logger.py`

**职责**: 记录许可相关操作

```python
class LicenseAuditLogger:
    """许可审计日志器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_activation(
        self,
        license_id: str,
        hardware_id: str,
        result: str
    ) -> LicenseAuditLog:
        """记录激活操作"""
        pass
    
    async def log_validation(
        self,
        license_id: str,
        result: str,
        details: Dict = None
    ) -> LicenseAuditLog:
        """记录验证操作"""
        pass
    
    async def log_concurrent_usage(
        self,
        current_users: int,
        max_users: int
    ) -> LicenseAuditLog:
        """记录并发使用情况"""
        pass
    
    async def log_resource_usage(
        self,
        resource_type: str,
        current_value: int,
        max_value: int
    ) -> LicenseAuditLog:
        """记录资源使用情况"""
        pass
    
    async def generate_usage_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> LicenseUsageReport:
        """生成使用报告"""
        pass
    
    async def export_audit_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "csv"
    ) -> bytes:
        """导出审计日志"""
        pass

class LicenseAuditLog(BaseModel):
    id: str
    event_type: str
    license_id: str
    details: Dict
    timestamp: datetime
    ip_address: Optional[str]
```

## Database Models

### License Models

```python
# src/models/license.py

class LicenseRecord(Base):
    __tablename__ = "licenses"
    
    id = Column(String, primary_key=True)
    license_key = Column(String, unique=True, index=True)
    license_type = Column(String)  # trial/basic/professional/enterprise
    features = Column(JSONB)
    limits = Column(JSONB)
    validity_start = Column(DateTime)
    validity_end = Column(DateTime)
    subscription_type = Column(String)
    grace_period_days = Column(Integer, default=7)
    hardware_id = Column(String, nullable=True)
    status = Column(String)  # active/expired/revoked/suspended
    signature = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

class LicenseActivation(Base):
    __tablename__ = "license_activations"
    
    id = Column(String, primary_key=True)
    license_id = Column(String, ForeignKey("licenses.id"))
    hardware_fingerprint = Column(String)
    activation_type = Column(String)  # online/offline
    activation_code = Column(String, nullable=True)
    activated_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    status = Column(String)

class ConcurrentSession(Base):
    __tablename__ = "concurrent_sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    session_id = Column(String, unique=True)
    priority = Column(Integer, default=0)
    login_time = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    user_agent = Column(String)
    is_active = Column(Boolean, default=True)

class LicenseAuditLogRecord(Base):
    __tablename__ = "license_audit_logs"
    
    id = Column(String, primary_key=True)
    event_type = Column(String)
    license_id = Column(String, ForeignKey("licenses.id"), nullable=True)
    details = Column(JSONB)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)
```

## API Endpoints

### License API

```python
# src/api/license_router.py

router = APIRouter(prefix="/api/v1/license", tags=["License"])

@router.get("/status")
async def get_license_status() -> LicenseStatus:
    """获取许可证状态"""
    pass

@router.post("/activate")
async def activate_license(request: ActivateLicenseRequest) -> ActivationResult:
    """激活许可证"""
    pass

@router.post("/activate/offline")
async def activate_offline(request: OfflineActivationRequest) -> ActivationResult:
    """离线激活"""
    pass

@router.get("/features")
async def get_available_features() -> List[FeatureInfo]:
    """获取可用功能列表"""
    pass

@router.get("/limits")
async def get_license_limits() -> LicenseLimits:
    """获取许可限制"""
    pass
```

### Usage API

```python
# src/api/usage_router.py

router = APIRouter(prefix="/api/v1/usage", tags=["Usage"])

@router.get("/concurrent")
async def get_concurrent_usage() -> ConcurrentUsageInfo:
    """获取并发用户使用情况"""
    pass

@router.get("/resources")
async def get_resource_usage() -> ResourceUsageInfo:
    """获取资源使用情况"""
    pass

@router.get("/sessions")
async def get_active_sessions() -> List[UserSession]:
    """获取活跃会话列表"""
    pass

@router.post("/sessions/{session_id}/terminate")
async def terminate_session(session_id: str) -> bool:
    """终止会话"""
    pass

@router.get("/report")
async def get_usage_report(
    start_date: datetime,
    end_date: datetime
) -> LicenseUsageReport:
    """获取使用报告"""
    pass
```

## Frontend Components

### License Dashboard

```typescript
// frontend/src/pages/license/LicenseDashboard.tsx

const LicenseDashboard: React.FC = () => {
  // 许可证状态概览
  // - 许可证类型和状态
  // - 有效期信息
  // - 并发用户使用情况
  // - 资源使用情况
  // - 功能模块状态
};

// frontend/src/pages/license/ActivationWizard.tsx
const ActivationWizard: React.FC = () => {
  // 激活向导
  // Step 1: 输入许可证密钥
  // Step 2: 选择激活方式（在线/离线）
  // Step 3: 确认激活
};

// frontend/src/pages/license/UsageMonitor.tsx
const UsageMonitor: React.FC = () => {
  // 使用情况监控
  // - 实时并发用户图表
  // - 资源使用趋势
  // - 活跃会话列表
};

// frontend/src/pages/license/LicenseReport.tsx
const LicenseReport: React.FC = () => {
  // 许可使用报告
  // - 使用统计
  // - 趋势分析
  // - 导出功能
};
```

## Correctness Properties (Property-Based Testing)

使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代。

### Property 1: 许可证签名验证

```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(
    license_data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.text(min_size=1, max_size=50),
        min_size=1,
        max_size=10
    )
)
def test_license_signature_verification(license_data):
    """签名后的许可证应能通过验证"""
    license = create_license(license_data)
    signed_license = sign_license(license, private_key)
    assert validator.verify_signature(signed_license) == True
```

### Property 2: 并发用户限制一致性

```python
@settings(max_examples=100)
@given(
    max_users=st.integers(min_value=1, max_value=1000),
    login_attempts=st.integers(min_value=1, max_value=100)
)
def test_concurrent_user_limit_consistency(max_users, login_attempts):
    """并发用户数不应超过许可限制"""
    controller = ConcurrentUserController(max_users=max_users)
    successful_logins = 0
    
    for i in range(login_attempts):
        result = controller.check_concurrent_limit(f"user_{i}")
        if result.allowed:
            controller.register_user_session(f"user_{i}", f"session_{i}")
            successful_logins += 1
    
    assert successful_logins <= max_users
```

### Property 3: 时间有效性检查

```python
@settings(max_examples=100)
@given(
    start_offset=st.integers(min_value=-365, max_value=365),
    duration_days=st.integers(min_value=1, max_value=365)
)
def test_time_validity_check(start_offset, duration_days):
    """许可证有效期检查应正确"""
    now = datetime.utcnow()
    start_date = now + timedelta(days=start_offset)
    end_date = start_date + timedelta(days=duration_days)
    
    license = create_license_with_validity(start_date, end_date)
    status = time_controller.check_license_validity(license)
    
    if now < start_date:
        assert status.status == "not_started"
    elif now > end_date:
        assert status.status in ["grace_period", "expired"]
    else:
        assert status.status == "active"
```

### Property 4: 硬件指纹一致性

```python
@settings(max_examples=100)
@given(
    iterations=st.integers(min_value=2, max_value=10)
)
def test_hardware_fingerprint_consistency(iterations):
    """相同硬件的指纹应一致"""
    fingerprints = []
    for _ in range(iterations):
        fp = activation_service.get_hardware_fingerprint()
        fingerprints.append(fp)
    
    assert len(set(fingerprints)) == 1  # 所有指纹应相同
```

### Property 5: 许可证状态转换

```python
@settings(max_examples=100)
@given(
    initial_status=st.sampled_from(["active", "expired", "suspended"]),
    action=st.sampled_from(["renew", "revoke", "suspend", "reactivate"])
)
def test_license_status_transitions(initial_status, action):
    """许可证状态转换应遵循有效路径"""
    license = create_license_with_status(initial_status)
    
    valid_transitions = {
        "active": ["revoke", "suspend"],
        "expired": ["renew", "revoke"],
        "suspended": ["reactivate", "revoke"],
        "revoked": []  # 终态，不能转换
    }
    
    if action in valid_transitions.get(initial_status, []):
        result = license_manager.transition_status(license, action)
        assert result.success == True
    else:
        # 无效转换应被拒绝或保持原状态
        pass
```

### Property 6: 会话释放正确性

```python
@settings(max_examples=100)
@given(
    user_count=st.integers(min_value=1, max_value=50),
    logout_count=st.integers(min_value=0, max_value=50)
)
def test_session_release_correctness(user_count, logout_count):
    """会话释放后应正确更新并发计数"""
    controller = ConcurrentUserController(max_users=100)
    
    # 登录用户
    for i in range(user_count):
        controller.register_user_session(f"user_{i}", f"session_{i}")
    
    initial_count = controller.get_current_user_count()
    assert initial_count == user_count
    
    # 登出部分用户
    actual_logout = min(logout_count, user_count)
    for i in range(actual_logout):
        controller.release_user_session(f"user_{i}", f"session_{i}")
    
    final_count = controller.get_current_user_count()
    assert final_count == user_count - actual_logout
```

### Property 7: 审计日志完整性

```python
@settings(max_examples=100)
@given(
    event_type=st.sampled_from(["activation", "validation", "renewal", "revocation"]),
    license_id=st.text(min_size=1, max_size=50)
)
def test_audit_log_completeness(event_type, license_id):
    """每个许可操作都应有对应的审计日志"""
    # 执行许可操作
    perform_license_operation(event_type, license_id)
    
    # 验证日志存在
    logs = audit_logger.query_logs(license_id=license_id, event_type=event_type)
    assert len(logs) > 0
    assert logs[-1].event_type == event_type
```

### Property 8: 功能模块访问控制

```python
@settings(max_examples=100)
@given(
    license_type=st.sampled_from(["basic", "professional", "enterprise"]),
    feature=st.sampled_from(["ai_annotation", "knowledge_graph", "advanced_analytics", "api_access"])
)
def test_feature_access_control(license_type, feature):
    """功能访问应符合许可类型"""
    license = create_license_with_type(license_type)
    
    feature_matrix = {
        "basic": ["api_access"],
        "professional": ["api_access", "ai_annotation"],
        "enterprise": ["api_access", "ai_annotation", "knowledge_graph", "advanced_analytics"]
    }
    
    allowed_features = feature_matrix.get(license_type, [])
    access_result = license_manager.check_feature_access(license, feature)
    
    if feature in allowed_features:
        assert access_result.allowed == True
    else:
        assert access_result.allowed == False
```

## Security Considerations

### 许可证加密

```python
class LicenseEncryption:
    """许可证加密服务"""
    
    def encrypt_license(self, license: License) -> bytes:
        """加密许可证"""
        # 使用 AES-256-GCM 加密
        pass
    
    def decrypt_license(self, encrypted_data: bytes) -> License:
        """解密许可证"""
        pass
    
    def sign_license(self, license: License, private_key: str) -> str:
        """签名许可证"""
        # 使用 RSA-SHA256 签名
        pass
```

### 防篡改机制

- 许可证文件使用数字签名
- 硬件指纹绑定防止复制
- 定期在线校验（可配置）
- 审计日志记录所有操作

## Performance Considerations

- 许可证验证结果缓存（Redis，TTL 5分钟）
- 并发用户计数使用 Redis 原子操作
- 硬件指纹计算结果缓存
- 审计日志异步写入
