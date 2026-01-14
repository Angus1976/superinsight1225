# Design Document: Audit & Security (审计与安全)

## Overview

本设计文档描述 Audit & Security 模块的架构设计，该模块实现完整的企业级审计和安全功能，包括细粒度 RBAC 权限控制、SSO 单点登录、完整审计日志、合规报告和安全监控。

设计原则：
- **最小权限**：用户只能访问必要的资源
- **完整审计**：所有操作都有审计记录
- **防篡改**：审计日志不可篡改
- **实时监控**：及时发现安全威胁

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        RBACUI[RBAC Config UI]
        SSOUI[SSO Config UI]
        AuditUI[Audit Log UI]
        SecurityDashboard[Security Dashboard]
        ComplianceUI[Compliance UI]
    end

    subgraph API["API 层"]
        RBACRouter[/api/v1/rbac]
        SSORouter[/api/v1/sso]
        AuditRouter[/api/v1/audit]
        SecurityRouter[/api/v1/security]
    end
    
    subgraph Core["核心层"]
        RBACEngine[RBAC Engine]
        PermissionManager[Permission Manager]
        SSOProvider[SSO Provider]
        AuditLogger[Audit Logger]
        ComplianceReporter[Compliance Reporter]
        SecurityMonitor[Security Monitor]
        EncryptionService[Encryption Service]
        SessionManager[Session Manager]
    end
    
    subgraph External["外部服务"]
        LDAP[LDAP/AD]
        SAML[SAML IdP]
        OAuth[OAuth Provider]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        AuditDB[(Audit DB)]
        Cache[(Redis)]
    end
    
    RBACUI --> RBACRouter
    SSOUI --> SSORouter
    AuditUI --> AuditRouter
    SecurityDashboard --> SecurityRouter
    ComplianceUI --> AuditRouter
    
    RBACRouter --> RBACEngine
    RBACRouter --> PermissionManager
    SSORouter --> SSOProvider
    AuditRouter --> AuditLogger
    AuditRouter --> ComplianceReporter
    SecurityRouter --> SecurityMonitor
    
    SSOProvider --> LDAP
    SSOProvider --> SAML
    SSOProvider --> OAuth
    
    RBACEngine --> DB
    RBACEngine --> Cache
    PermissionManager --> Cache
    AuditLogger --> AuditDB
    SecurityMonitor --> DB
    EncryptionService --> DB
    SessionManager --> Cache
```


## Components and Interfaces

### 1. RBAC Engine (RBAC 引擎)

**文件**: `src/security/rbac_engine.py`

**职责**: 基于角色的访问控制

```python
class RBACEngine:
    """RBAC 引擎"""
    
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache
    
    async def create_role(self, role: CreateRoleRequest) -> Role:
        """创建角色"""
        new_role = Role(
            name=role.name,
            description=role.description,
            permissions=role.permissions,
            parent_role_id=role.parent_role_id
        )
        
        await self.db.add(new_role)
        await self._invalidate_cache()
        
        return new_role
    
    async def assign_role(self, user_id: str, role_id: str) -> UserRole:
        """分配角色给用户"""
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id
        )
        
        await self.db.add(user_role)
        await self._invalidate_user_cache(user_id)
        
        return user_role
    
    async def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> bool:
        """检查用户权限"""
        # 从缓存获取用户权限
        permissions = await self._get_user_permissions(user_id)
        
        # 检查是否有匹配的权限
        for perm in permissions:
            if self._match_permission(perm, resource, action):
                return True
        
        return False
    
    async def _get_user_permissions(self, user_id: str) -> List[Permission]:
        """获取用户所有权限（包括继承的）"""
        cache_key = f"user_permissions:{user_id}"
        
        cached = await self.cache.get(cache_key)
        if cached:
            return [Permission.parse_raw(p) for p in json.loads(cached)]
        
        # 获取用户角色
        roles = await self.get_user_roles(user_id)
        
        # 收集所有权限（包括继承的）
        permissions = set()
        for role in roles:
            role_perms = await self._get_role_permissions_recursive(role.id)
            permissions.update(role_perms)
        
        # 缓存结果
        await self.cache.set(
            cache_key,
            json.dumps([p.json() for p in permissions]),
            ex=3600
        )
        
        return list(permissions)
    
    async def _get_role_permissions_recursive(self, role_id: str) -> Set[Permission]:
        """递归获取角色权限（包括父角色）"""
        role = await self.get_role(role_id)
        permissions = set(role.permissions)
        
        if role.parent_role_id:
            parent_perms = await self._get_role_permissions_recursive(role.parent_role_id)
            permissions.update(parent_perms)
        
        return permissions
    
    def _match_permission(self, perm: Permission, resource: str, action: str) -> bool:
        """匹配权限"""
        # 支持通配符匹配
        resource_match = fnmatch.fnmatch(resource, perm.resource)
        action_match = perm.action == "*" or perm.action == action
        
        return resource_match and action_match

class Role(BaseModel):
    id: str
    name: str
    description: str
    permissions: List[Permission]
    parent_role_id: Optional[str] = None
    created_at: datetime

class Permission(BaseModel):
    resource: str  # e.g., "projects/*", "datasets/123"
    action: str    # e.g., "read", "write", "delete", "*"
```

### 2. Permission Manager (权限管理器)

**文件**: `src/security/permission_manager.py`

**职责**: 管理细粒度权限和动态策略

```python
class PermissionManager:
    """权限管理器"""
    
    def __init__(
        self,
        db: AsyncSession,
        rbac_engine: RBACEngine,
        audit_logger: AuditLogger
    ):
        self.db = db
        self.rbac_engine = rbac_engine
        self.audit_logger = audit_logger
    
    async def check_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: AccessContext = None
    ) -> AccessDecision:
        """检查访问权限（包括动态策略）"""
        # 基础 RBAC 检查
        rbac_allowed = await self.rbac_engine.check_permission(user_id, resource, action)
        
        if not rbac_allowed:
            decision = AccessDecision(allowed=False, reason="RBAC denied")
            await self._log_decision(user_id, resource, action, decision)
            return decision
        
        # 动态策略检查
        if context:
            policy_result = await self._check_dynamic_policies(user_id, resource, action, context)
            if not policy_result.allowed:
                await self._log_decision(user_id, resource, action, policy_result)
                return policy_result
        
        decision = AccessDecision(allowed=True)
        await self._log_decision(user_id, resource, action, decision)
        return decision
    
    async def _check_dynamic_policies(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: AccessContext
    ) -> AccessDecision:
        """检查动态策略"""
        policies = await self.get_active_policies(resource)
        
        for policy in policies:
            if policy.policy_type == "time_range":
                if not self._check_time_range(policy.config, context.timestamp):
                    return AccessDecision(allowed=False, reason="Outside allowed time range")
            
            elif policy.policy_type == "ip_whitelist":
                if not self._check_ip_whitelist(policy.config, context.ip_address):
                    return AccessDecision(allowed=False, reason="IP not in whitelist")
            
            elif policy.policy_type == "sensitivity_level":
                if not await self._check_sensitivity_level(user_id, resource, policy.config):
                    return AccessDecision(allowed=False, reason="Insufficient clearance level")
            
            elif policy.policy_type == "attribute":
                if not await self._check_attribute_policy(user_id, policy.config):
                    return AccessDecision(allowed=False, reason="Attribute policy denied")
        
        return AccessDecision(allowed=True)
    
    def _check_time_range(self, config: Dict, timestamp: datetime) -> bool:
        """检查时间范围"""
        start_hour = config.get("start_hour", 0)
        end_hour = config.get("end_hour", 24)
        allowed_days = config.get("allowed_days", [0, 1, 2, 3, 4, 5, 6])
        
        current_hour = timestamp.hour
        current_day = timestamp.weekday()
        
        return (start_hour <= current_hour < end_hour) and (current_day in allowed_days)
    
    def _check_ip_whitelist(self, config: Dict, ip_address: str) -> bool:
        """检查 IP 白名单"""
        whitelist = config.get("whitelist", [])
        
        for pattern in whitelist:
            if ipaddress.ip_address(ip_address) in ipaddress.ip_network(pattern):
                return True
        
        return False
    
    async def _log_decision(
        self,
        user_id: str,
        resource: str,
        action: str,
        decision: AccessDecision
    ) -> None:
        """记录权限决策"""
        await self.audit_logger.log(
            event_type="permission_decision",
            user_id=user_id,
            resource=resource,
            action=action,
            result=decision.allowed,
            reason=decision.reason
        )

class AccessContext(BaseModel):
    ip_address: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None
    attributes: Dict = {}

class AccessDecision(BaseModel):
    allowed: bool
    reason: Optional[str] = None
```

### 3. SSO Provider (SSO 提供者)

**文件**: `src/security/sso_provider.py`

**职责**: 支持多种 SSO 协议

```python
class SSOProvider:
    """SSO 提供者"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.providers: Dict[str, SSOConnector] = {}
    
    async def configure_provider(self, config: SSOConfig) -> SSOProviderInfo:
        """配置 SSO 提供者"""
        connector = self._create_connector(config)
        self.providers[config.name] = connector
        
        # 保存配置
        await self._save_config(config)
        
        return SSOProviderInfo(
            name=config.name,
            protocol=config.protocol,
            status="configured"
        )
    
    def _create_connector(self, config: SSOConfig) -> SSOConnector:
        """创建 SSO 连接器"""
        if config.protocol == "saml":
            return SAMLConnector(config)
        elif config.protocol == "oauth2":
            return OAuth2Connector(config)
        elif config.protocol == "oidc":
            return OIDCConnector(config)
        elif config.protocol == "ldap":
            return LDAPConnector(config)
        else:
            raise ValueError(f"Unsupported protocol: {config.protocol}")
    
    async def initiate_login(self, provider_name: str, redirect_uri: str) -> LoginInitiation:
        """发起 SSO 登录"""
        connector = self.providers.get(provider_name)
        if not connector:
            raise ProviderNotFoundError(provider_name)
        
        return await connector.initiate_login(redirect_uri)
    
    async def handle_callback(
        self,
        provider_name: str,
        callback_data: Dict
    ) -> SSOLoginResult:
        """处理 SSO 回调"""
        connector = self.providers.get(provider_name)
        if not connector:
            raise ProviderNotFoundError(provider_name)
        
        # 验证回调数据
        user_info = await connector.validate_callback(callback_data)
        
        # 创建或更新用户
        user = await self._sync_user(user_info)
        
        # 生成本地会话
        session = await self._create_session(user)
        
        return SSOLoginResult(
            user=user,
            session=session,
            provider=provider_name
        )
    
    async def _sync_user(self, user_info: SSOUserInfo) -> User:
        """同步用户信息"""
        existing = await self.db.query(User).filter(
            User.sso_id == user_info.sso_id
        ).first()
        
        if existing:
            # 更新用户信息
            existing.email = user_info.email
            existing.name = user_info.name
            existing.attributes = user_info.attributes
            return existing
        else:
            # 创建新用户
            new_user = User(
                sso_id=user_info.sso_id,
                email=user_info.email,
                name=user_info.name,
                attributes=user_info.attributes
            )
            await self.db.add(new_user)
            return new_user
    
    async def logout(self, user_id: str, provider_name: str) -> LogoutResult:
        """SSO 登出"""
        connector = self.providers.get(provider_name)
        
        # 本地登出
        await self._destroy_session(user_id)
        
        # 如果支持单点登出，通知 IdP
        if connector and connector.supports_slo:
            await connector.initiate_logout(user_id)
        
        return LogoutResult(success=True)

class SSOConfig(BaseModel):
    name: str
    protocol: str  # saml/oauth2/oidc/ldap
    entity_id: Optional[str] = None
    sso_url: Optional[str] = None
    slo_url: Optional[str] = None
    certificate: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    ldap_url: Optional[str] = None
    ldap_base_dn: Optional[str] = None
    attribute_mapping: Dict[str, str] = {}

class SAMLConnector(SSOConnector):
    """SAML 连接器"""
    pass

class OAuth2Connector(SSOConnector):
    """OAuth2 连接器"""
    pass

class OIDCConnector(SSOConnector):
    """OIDC 连接器"""
    pass

class LDAPConnector(SSOConnector):
    """LDAP 连接器"""
    pass
```

### 4. Audit Logger (审计日志记录器)

**文件**: `src/security/audit_logger.py`

**职责**: 记录所有操作的审计日志

```python
class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._previous_hash: Optional[str] = None
    
    async def log(
        self,
        event_type: str,
        user_id: str,
        resource: str = None,
        action: str = None,
        result: bool = None,
        details: Dict = None,
        ip_address: str = None,
        **kwargs
    ) -> AuditLog:
        """记录审计日志"""
        # 获取上一条日志的哈希（用于链式验证）
        previous_hash = await self._get_previous_hash()
        
        # 创建日志记录
        log_entry = AuditLog(
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            ip_address=ip_address,
            previous_hash=previous_hash,
            **kwargs
        )
        
        # 计算当前日志的哈希
        log_entry.hash = self._calculate_hash(log_entry)
        
        await self.db.add(log_entry)
        self._previous_hash = log_entry.hash
        
        return log_entry
    
    def _calculate_hash(self, log_entry: AuditLog) -> str:
        """计算日志哈希（用于防篡改）"""
        data = f"{log_entry.event_type}|{log_entry.user_id}|{log_entry.resource}|" \
               f"{log_entry.action}|{log_entry.timestamp}|{log_entry.previous_hash}"
        
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def _get_previous_hash(self) -> Optional[str]:
        """获取上一条日志的哈希"""
        if self._previous_hash:
            return self._previous_hash
        
        last_log = await self.db.query(AuditLog).order_by(
            AuditLog.timestamp.desc()
        ).first()
        
        return last_log.hash if last_log else None
    
    async def verify_integrity(self, start_id: str = None, end_id: str = None) -> IntegrityResult:
        """验证审计日志完整性"""
        logs = await self.get_logs_range(start_id, end_id)
        
        for i, log in enumerate(logs):
            # 验证哈希
            expected_hash = self._calculate_hash(log)
            if log.hash != expected_hash:
                return IntegrityResult(
                    valid=False,
                    error=f"Hash mismatch at log {log.id}"
                )
            
            # 验证链式哈希
            if i > 0 and log.previous_hash != logs[i-1].hash:
                return IntegrityResult(
                    valid=False,
                    error=f"Chain broken at log {log.id}"
                )
        
        return IntegrityResult(valid=True, verified_count=len(logs))
    
    async def query_logs(
        self,
        user_id: str = None,
        event_type: str = None,
        resource: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """查询审计日志"""
        query = self.db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if resource:
            query = query.filter(AuditLog.resource.like(f"%{resource}%"))
        if start_time:
            query = query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditLog.timestamp <= end_time)
        
        return await query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    async def export_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = "json"
    ) -> bytes:
        """导出审计日志"""
        logs = await self.query_logs(start_time=start_time, end_time=end_time, limit=10000)
        
        if format == "json":
            return json.dumps([log.dict() for log in logs], default=str).encode()
        elif format == "csv":
            return self._to_csv(logs)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def apply_retention_policy(self, retention_days: int) -> int:
        """应用保留策略"""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        # 归档旧日志
        old_logs = await self.db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff
        ).all()
        
        await self._archive_logs(old_logs)
        
        # 删除已归档的日志
        deleted = await self.db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff
        ).delete()
        
        return deleted

class AuditLog(BaseModel):
    id: str
    event_type: str
    user_id: str
    resource: Optional[str]
    action: Optional[str]
    result: Optional[bool]
    details: Dict
    ip_address: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    previous_hash: Optional[str]
    hash: Optional[str]
```


### 5. Compliance Reporter (合规报告器)

**文件**: `src/security/compliance_reporter.py`

**职责**: 生成合规报告

```python
class ComplianceReporter:
    """合规报告器"""
    
    def __init__(self, db: AsyncSession, audit_logger: AuditLogger):
        self.db = db
        self.audit_logger = audit_logger
    
    async def generate_gdpr_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> GDPRReport:
        """生成 GDPR 合规报告"""
        # 数据主体访问请求统计
        dsar_stats = await self._get_dsar_stats(start_date, end_date)
        
        # 数据处理活动记录
        processing_activities = await self._get_processing_activities(start_date, end_date)
        
        # 数据泄露事件
        breach_incidents = await self._get_breach_incidents(start_date, end_date)
        
        # 同意管理统计
        consent_stats = await self._get_consent_stats(start_date, end_date)
        
        return GDPRReport(
            period_start=start_date,
            period_end=end_date,
            dsar_stats=dsar_stats,
            processing_activities=processing_activities,
            breach_incidents=breach_incidents,
            consent_stats=consent_stats
        )
    
    async def generate_soc2_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> SOC2Report:
        """生成 SOC 2 合规报告"""
        # 安全控制评估
        security_controls = await self._assess_security_controls()
        
        # 可用性指标
        availability_metrics = await self._get_availability_metrics(start_date, end_date)
        
        # 处理完整性
        processing_integrity = await self._assess_processing_integrity(start_date, end_date)
        
        # 保密性控制
        confidentiality_controls = await self._assess_confidentiality_controls()
        
        # 隐私控制
        privacy_controls = await self._assess_privacy_controls()
        
        return SOC2Report(
            period_start=start_date,
            period_end=end_date,
            security_controls=security_controls,
            availability_metrics=availability_metrics,
            processing_integrity=processing_integrity,
            confidentiality_controls=confidentiality_controls,
            privacy_controls=privacy_controls
        )
    
    async def generate_access_report(
        self,
        start_date: datetime,
        end_date: datetime,
        resource_filter: str = None
    ) -> AccessReport:
        """生成数据访问报告"""
        # 获取访问日志
        access_logs = await self.audit_logger.query_logs(
            event_type="data_access",
            resource=resource_filter,
            start_time=start_date,
            end_time=end_date
        )
        
        # 按用户统计
        by_user = self._group_by_user(access_logs)
        
        # 按资源统计
        by_resource = self._group_by_resource(access_logs)
        
        # 异常访问检测
        anomalies = await self._detect_access_anomalies(access_logs)
        
        return AccessReport(
            period_start=start_date,
            period_end=end_date,
            total_accesses=len(access_logs),
            by_user=by_user,
            by_resource=by_resource,
            anomalies=anomalies
        )
    
    async def generate_permission_change_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> PermissionChangeReport:
        """生成权限变更报告"""
        # 获取权限变更日志
        change_logs = await self.audit_logger.query_logs(
            event_type="permission_change",
            start_time=start_date,
            end_time=end_date
        )
        
        # 分类统计
        role_changes = [l for l in change_logs if l.details.get("change_type") == "role"]
        permission_grants = [l for l in change_logs if l.details.get("change_type") == "grant"]
        permission_revokes = [l for l in change_logs if l.details.get("change_type") == "revoke"]
        
        return PermissionChangeReport(
            period_start=start_date,
            period_end=end_date,
            total_changes=len(change_logs),
            role_changes=len(role_changes),
            permission_grants=len(permission_grants),
            permission_revokes=len(permission_revokes),
            details=change_logs
        )
    
    async def schedule_report(
        self,
        report_type: str,
        schedule: str,  # cron 表达式
        recipients: List[str],
        config: Dict = None
    ) -> ReportSchedule:
        """创建定时报告"""
        pass

class GDPRReport(BaseModel):
    period_start: datetime
    period_end: datetime
    dsar_stats: Dict
    processing_activities: List[Dict]
    breach_incidents: List[Dict]
    consent_stats: Dict
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class SOC2Report(BaseModel):
    period_start: datetime
    period_end: datetime
    security_controls: List[ControlAssessment]
    availability_metrics: Dict
    processing_integrity: Dict
    confidentiality_controls: List[ControlAssessment]
    privacy_controls: List[ControlAssessment]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 6. Security Monitor (安全监控器)

**文件**: `src/security/security_monitor.py`

**职责**: 实时监控安全事件

```python
class SecurityMonitor:
    """安全监控器"""
    
    def __init__(
        self,
        db: AsyncSession,
        audit_logger: AuditLogger,
        notification_service: NotificationService
    ):
        self.db = db
        self.audit_logger = audit_logger
        self.notification_service = notification_service
    
    async def monitor_login_attempts(self, user_id: str, ip_address: str, success: bool) -> Optional[SecurityEvent]:
        """监控登录尝试"""
        # 记录登录尝试
        await self.audit_logger.log(
            event_type="login_attempt",
            user_id=user_id,
            ip_address=ip_address,
            result=success
        )
        
        if not success:
            # 检查失败次数
            failed_count = await self._get_failed_login_count(user_id, minutes=30)
            
            if failed_count >= 5:
                event = await self._create_security_event(
                    event_type="brute_force_attempt",
                    severity="high",
                    user_id=user_id,
                    details={"failed_count": failed_count, "ip_address": ip_address}
                )
                await self._send_alert(event)
                return event
        else:
            # 检查异地登录
            if await self._is_unusual_location(user_id, ip_address):
                event = await self._create_security_event(
                    event_type="unusual_location_login",
                    severity="medium",
                    user_id=user_id,
                    details={"ip_address": ip_address}
                )
                await self._send_alert(event)
                return event
        
        return None
    
    async def monitor_data_access(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> Optional[SecurityEvent]:
        """监控数据访问"""
        # 检查大量下载
        if action == "download":
            download_count = await self._get_download_count(user_id, minutes=60)
            
            if download_count >= 100:
                event = await self._create_security_event(
                    event_type="mass_download",
                    severity="high",
                    user_id=user_id,
                    details={"download_count": download_count, "resource": resource}
                )
                await self._send_alert(event)
                return event
        
        # 检查敏感数据访问
        if await self._is_sensitive_resource(resource):
            event = await self._create_security_event(
                event_type="sensitive_data_access",
                severity="medium",
                user_id=user_id,
                details={"resource": resource, "action": action}
            )
            # 记录但不一定告警
            return event
        
        return None
    
    async def monitor_permission_escalation(
        self,
        user_id: str,
        target_user_id: str,
        new_role: str
    ) -> Optional[SecurityEvent]:
        """监控权限提升"""
        # 检查是否是自我提权
        if user_id == target_user_id:
            event = await self._create_security_event(
                event_type="self_privilege_escalation",
                severity="critical",
                user_id=user_id,
                details={"new_role": new_role}
            )
            await self._send_alert(event)
            return event
        
        # 检查是否提升到高权限角色
        if await self._is_high_privilege_role(new_role):
            event = await self._create_security_event(
                event_type="high_privilege_grant",
                severity="high",
                user_id=user_id,
                details={"target_user": target_user_id, "new_role": new_role}
            )
            await self._send_alert(event)
            return event
        
        return None
    
    async def _create_security_event(
        self,
        event_type: str,
        severity: str,
        user_id: str,
        details: Dict
    ) -> SecurityEvent:
        """创建安全事件"""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            details=details,
            status="open"
        )
        
        await self.db.add(event)
        return event
    
    async def _send_alert(self, event: SecurityEvent) -> None:
        """发送安全告警"""
        # 获取安全管理员
        admins = await self._get_security_admins()
        
        for admin in admins:
            await self.notification_service.send(
                user_id=admin.id,
                channel="email",
                title=f"安全告警 - {event.severity.upper()}",
                message=f"检测到安全事件: {event.event_type}"
            )
    
    async def generate_security_posture_report(self) -> SecurityPostureReport:
        """生成安全态势报告"""
        # 统计各类安全事件
        events_by_type = await self._get_events_by_type(days=30)
        
        # 计算风险评分
        risk_score = self._calculate_risk_score(events_by_type)
        
        # 获取趋势
        trend = await self._get_security_trend(days=30)
        
        return SecurityPostureReport(
            risk_score=risk_score,
            events_by_type=events_by_type,
            trend=trend,
            recommendations=self._generate_recommendations(events_by_type)
        )

class SecurityEvent(BaseModel):
    id: str
    event_type: str
    severity: str  # low/medium/high/critical
    user_id: str
    details: Dict
    status: str  # open/investigating/resolved
    created_at: datetime
    resolved_at: Optional[datetime] = None
```

### 7. Data Encryption Service (数据加密服务)

**文件**: `src/security/encryption_service.py`

**职责**: 数据加密和密钥管理

```python
class DataEncryptionService:
    """数据加密服务"""
    
    def __init__(self, key_store: KeyStore):
        self.key_store = key_store
        self._current_key: Optional[EncryptionKey] = None
    
    async def encrypt(self, data: bytes, key_id: str = None) -> EncryptedData:
        """加密数据"""
        key = await self._get_key(key_id)
        
        # 生成随机 IV
        iv = os.urandom(16)
        
        # AES-256-GCM 加密
        cipher = Cipher(
            algorithms.AES(key.key_bytes),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            ciphertext=ciphertext,
            iv=iv,
            tag=encryptor.tag,
            key_id=key.id,
            algorithm="AES-256-GCM"
        )
    
    async def decrypt(self, encrypted: EncryptedData) -> bytes:
        """解密数据"""
        key = await self._get_key(encrypted.key_id)
        
        cipher = Cipher(
            algorithms.AES(key.key_bytes),
            modes.GCM(encrypted.iv, encrypted.tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        return decryptor.update(encrypted.ciphertext) + decryptor.finalize()
    
    async def encrypt_field(self, value: str, field_name: str) -> str:
        """加密数据库字段"""
        encrypted = await self.encrypt(value.encode())
        
        # 返回 base64 编码的加密数据
        return base64.b64encode(
            json.dumps({
                "ciphertext": base64.b64encode(encrypted.ciphertext).decode(),
                "iv": base64.b64encode(encrypted.iv).decode(),
                "tag": base64.b64encode(encrypted.tag).decode(),
                "key_id": encrypted.key_id
            }).encode()
        ).decode()
    
    async def decrypt_field(self, encrypted_value: str) -> str:
        """解密数据库字段"""
        data = json.loads(base64.b64decode(encrypted_value))
        
        encrypted = EncryptedData(
            ciphertext=base64.b64decode(data["ciphertext"]),
            iv=base64.b64decode(data["iv"]),
            tag=base64.b64decode(data["tag"]),
            key_id=data["key_id"]
        )
        
        return (await self.decrypt(encrypted)).decode()
    
    async def rotate_key(self) -> EncryptionKey:
        """轮换密钥"""
        # 生成新密钥
        new_key = await self.key_store.generate_key()
        
        # 标记旧密钥为待轮换
        if self._current_key:
            await self.key_store.mark_for_rotation(self._current_key.id)
        
        self._current_key = new_key
        return new_key
    
    async def re_encrypt_with_new_key(self, encrypted: EncryptedData) -> EncryptedData:
        """使用新密钥重新加密"""
        # 解密
        plaintext = await self.decrypt(encrypted)
        
        # 使用当前密钥重新加密
        return await self.encrypt(plaintext)

class EncryptedData(BaseModel):
    ciphertext: bytes
    iv: bytes
    tag: bytes
    key_id: str
    algorithm: str = "AES-256-GCM"

class KeyStore:
    """密钥存储"""
    
    async def generate_key(self) -> EncryptionKey:
        """生成新密钥"""
        key_bytes = os.urandom(32)  # 256 bits
        
        key = EncryptionKey(
            id=str(uuid4()),
            key_bytes=key_bytes,
            algorithm="AES-256",
            status="active"
        )
        
        await self._store_key(key)
        return key
    
    async def get_key(self, key_id: str) -> EncryptionKey:
        """获取密钥"""
        pass
    
    async def mark_for_rotation(self, key_id: str) -> None:
        """标记密钥待轮换"""
        pass
    
    async def destroy_key(self, key_id: str) -> None:
        """销毁密钥"""
        pass
```

### 8. Session Manager (会话管理器)

**文件**: `src/security/session_manager.py`

**职责**: 管理用户会话

```python
class SessionManager:
    """会话管理器"""
    
    def __init__(self, cache: Redis, audit_logger: AuditLogger):
        self.cache = cache
        self.audit_logger = audit_logger
        self.default_timeout = 3600  # 1 hour
        self.max_concurrent_sessions = 5
    
    async def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str = None
    ) -> Session:
        """创建会话"""
        # 检查并发会话限制
        current_sessions = await self.get_user_sessions(user_id)
        
        if len(current_sessions) >= self.max_concurrent_sessions:
            # 删除最旧的会话
            oldest = min(current_sessions, key=lambda s: s.created_at)
            await self.destroy_session(oldest.id)
        
        session = Session(
            id=str(uuid4()),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        # 存储会话
        await self.cache.set(
            f"session:{session.id}",
            session.json(),
            ex=self.default_timeout
        )
        
        # 添加到用户会话列表
        await self.cache.sadd(f"user_sessions:{user_id}", session.id)
        
        await self.audit_logger.log(
            event_type="session_created",
            user_id=user_id,
            ip_address=ip_address,
            details={"session_id": session.id}
        )
        
        return session
    
    async def validate_session(self, session_id: str) -> Optional[Session]:
        """验证会话"""
        session_data = await self.cache.get(f"session:{session_id}")
        
        if not session_data:
            return None
        
        session = Session.parse_raw(session_data)
        
        # 更新最后活动时间
        session.last_activity = datetime.utcnow()
        await self.cache.set(
            f"session:{session_id}",
            session.json(),
            ex=self.default_timeout
        )
        
        return session
    
    async def destroy_session(self, session_id: str) -> None:
        """销毁会话"""
        session_data = await self.cache.get(f"session:{session_id}")
        
        if session_data:
            session = Session.parse_raw(session_data)
            
            # 从用户会话列表移除
            await self.cache.srem(f"user_sessions:{session.user_id}", session_id)
            
            # 删除会话
            await self.cache.delete(f"session:{session_id}")
            
            await self.audit_logger.log(
                event_type="session_destroyed",
                user_id=session.user_id,
                details={"session_id": session_id}
            )
    
    async def force_logout(self, user_id: str) -> int:
        """强制登出用户所有会话"""
        sessions = await self.get_user_sessions(user_id)
        
        for session in sessions:
            await self.destroy_session(session.id)
        
        await self.audit_logger.log(
            event_type="force_logout",
            user_id=user_id,
            details={"session_count": len(sessions)}
        )
        
        return len(sessions)
    
    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """获取用户所有会话"""
        session_ids = await self.cache.smembers(f"user_sessions:{user_id}")
        
        sessions = []
        for session_id in session_ids:
            session_data = await self.cache.get(f"session:{session_id}")
            if session_data:
                sessions.append(Session.parse_raw(session_data))
        
        return sessions
    
    async def get_active_sessions(self) -> List[Session]:
        """获取所有活跃会话"""
        pass
    
    async def configure_timeout(self, timeout_seconds: int) -> None:
        """配置会话超时"""
        self.default_timeout = timeout_seconds
    
    async def configure_max_concurrent(self, max_sessions: int) -> None:
        """配置最大并发会话数"""
        self.max_concurrent_sessions = max_sessions

class Session(BaseModel):
    id: str
    user_id: str
    ip_address: str
    user_agent: Optional[str]
    created_at: datetime
    last_activity: datetime
```


### 9. API Router (API 路由)

**文件**: `src/api/security.py`

```python
router = APIRouter(prefix="/api/v1", tags=["Security"])

# RBAC
@router.post("/rbac/roles")
async def create_role(request: CreateRoleRequest) -> Role:
    """创建角色"""
    pass

@router.get("/rbac/roles")
async def list_roles() -> List[Role]:
    """列出角色"""
    pass

@router.put("/rbac/roles/{role_id}")
async def update_role(role_id: str, request: UpdateRoleRequest) -> Role:
    """更新角色"""
    pass

@router.delete("/rbac/roles/{role_id}")
async def delete_role(role_id: str) -> None:
    """删除角色"""
    pass

@router.post("/rbac/users/{user_id}/roles")
async def assign_role(user_id: str, request: AssignRoleRequest) -> UserRole:
    """分配角色"""
    pass

@router.delete("/rbac/users/{user_id}/roles/{role_id}")
async def revoke_role(user_id: str, role_id: str) -> None:
    """撤销角色"""
    pass

@router.post("/rbac/check")
async def check_permission(request: CheckPermissionRequest) -> AccessDecision:
    """检查权限"""
    pass

# SSO
@router.post("/sso/providers")
async def configure_sso_provider(request: SSOConfig) -> SSOProviderInfo:
    """配置 SSO 提供者"""
    pass

@router.get("/sso/providers")
async def list_sso_providers() -> List[SSOProviderInfo]:
    """列出 SSO 提供者"""
    pass

@router.get("/sso/login/{provider}")
async def initiate_sso_login(provider: str, redirect_uri: str) -> LoginInitiation:
    """发起 SSO 登录"""
    pass

@router.post("/sso/callback/{provider}")
async def handle_sso_callback(provider: str, request: SSOCallbackRequest) -> SSOLoginResult:
    """处理 SSO 回调"""
    pass

@router.post("/sso/logout")
async def sso_logout() -> LogoutResult:
    """SSO 登出"""
    pass

# 审计日志
@router.get("/audit/logs")
async def query_audit_logs(
    user_id: str = None,
    event_type: str = None,
    resource: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = 100
) -> List[AuditLog]:
    """查询审计日志"""
    pass

@router.post("/audit/logs/export")
async def export_audit_logs(request: ExportRequest) -> Response:
    """导出审计日志"""
    pass

@router.post("/audit/verify-integrity")
async def verify_audit_integrity(request: VerifyRequest) -> IntegrityResult:
    """验证审计日志完整性"""
    pass

# 合规报告
@router.post("/compliance/reports/gdpr")
async def generate_gdpr_report(request: ReportRequest) -> GDPRReport:
    """生成 GDPR 报告"""
    pass

@router.post("/compliance/reports/soc2")
async def generate_soc2_report(request: ReportRequest) -> SOC2Report:
    """生成 SOC 2 报告"""
    pass

@router.post("/compliance/reports/access")
async def generate_access_report(request: AccessReportRequest) -> AccessReport:
    """生成访问报告"""
    pass

@router.post("/compliance/reports/permission-changes")
async def generate_permission_change_report(request: ReportRequest) -> PermissionChangeReport:
    """生成权限变更报告"""
    pass

# 安全监控
@router.get("/security/events")
async def list_security_events(
    severity: str = None,
    status: str = None,
    limit: int = 100
) -> List[SecurityEvent]:
    """列出安全事件"""
    pass

@router.post("/security/events/{event_id}/resolve")
async def resolve_security_event(event_id: str, request: ResolveRequest) -> SecurityEvent:
    """解决安全事件"""
    pass

@router.get("/security/posture")
async def get_security_posture() -> SecurityPostureReport:
    """获取安全态势"""
    pass

# 会话管理
@router.get("/sessions")
async def list_user_sessions(user_id: str = None) -> List[Session]:
    """列出会话"""
    pass

@router.delete("/sessions/{session_id}")
async def destroy_session(session_id: str) -> None:
    """销毁会话"""
    pass

@router.post("/sessions/force-logout/{user_id}")
async def force_logout_user(user_id: str) -> int:
    """强制登出用户"""
    pass

@router.put("/sessions/config")
async def configure_sessions(request: SessionConfigRequest) -> None:
    """配置会话参数"""
    pass
```

## Data Models

### 数据库模型

```python
class RoleModel(Base):
    """角色表"""
    __tablename__ = "roles"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSONB, default=[])
    parent_role_id = Column(UUID, ForeignKey("roles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserRoleModel(Base):
    """用户角色关联表"""
    __tablename__ = "user_roles"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    role_id = Column(UUID, ForeignKey("roles.id"), nullable=False)
    granted_by = Column(UUID, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )

class DynamicPolicyModel(Base):
    """动态策略表"""
    __tablename__ = "dynamic_policies"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    policy_type = Column(String(50), nullable=False)
    resource_pattern = Column(String(200), nullable=False)
    config = Column(JSONB, nullable=False)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class SSOProviderModel(Base):
    """SSO 提供者配置表"""
    __tablename__ = "sso_providers"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    protocol = Column(String(20), nullable=False)
    config = Column(JSONB, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLogModel(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(UUID, nullable=False, index=True)
    resource = Column(String(200), nullable=True, index=True)
    action = Column(String(50), nullable=True)
    result = Column(Boolean, nullable=True)
    details = Column(JSONB, default={})
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    previous_hash = Column(String(64), nullable=True)
    hash = Column(String(64), nullable=False)

class SecurityEventModel(Base):
    """安全事件表"""
    __tablename__ = "security_events"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    user_id = Column(UUID, nullable=False, index=True)
    details = Column(JSONB, nullable=False)
    status = Column(String(20), default="open", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
```

## Correctness Properties (Property-Based Testing)

使用 Hypothesis 库进行属性测试，每个属性至少运行 100 次迭代。

### Property 1: 权限检查确定性

```python
@given(
    user_id=st.text(min_size=1, max_size=36),
    resource=st.text(min_size=1, max_size=100),
    action=st.sampled_from(["read", "write", "delete", "admin"])
)
@settings(max_examples=100)
def test_permission_check_deterministic(user_id, resource, action):
    """权限检查必须是确定性的"""
    result1 = check_permission(user_id, resource, action)
    result2 = check_permission(user_id, resource, action)
    
    assert result1.allowed == result2.allowed
```

### Property 2: 角色继承传递性

```python
@given(
    roles=st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=5, unique=True)
)
@settings(max_examples=100)
def test_role_inheritance_transitivity(roles):
    """角色继承必须满足传递性"""
    # 创建角色链: role1 -> role2 -> role3
    for i in range(len(roles) - 1):
        create_role(roles[i], parent=roles[i+1])
    
    # 最底层角色应该继承所有父角色的权限
    bottom_role_perms = get_role_permissions(roles[0])
    
    for role in roles[1:]:
        role_perms = get_role_permissions(role)
        for perm in role_perms:
            assert perm in bottom_role_perms
```

### Property 3: 审计日志不可篡改

```python
@given(
    logs=st.lists(
        st.fixed_dictionaries({
            "event_type": st.text(min_size=1, max_size=20),
            "user_id": st.text(min_size=1, max_size=36),
            "resource": st.text(min_size=1, max_size=100)
        }),
        min_size=2,
        max_size=10
    )
)
@settings(max_examples=100)
def test_audit_log_tamper_proof(logs):
    """审计日志必须防篡改"""
    # 创建日志
    log_ids = []
    for log in logs:
        created = create_audit_log(**log)
        log_ids.append(created.id)
    
    # 验证完整性
    result = verify_integrity(log_ids[0], log_ids[-1])
    assert result.valid
    
    # 尝试篡改中间日志
    tamper_log(log_ids[1])
    
    # 验证应该失败
    result = verify_integrity(log_ids[0], log_ids[-1])
    assert not result.valid
```

### Property 4: 会话超时正确性

```python
@given(
    timeout_seconds=st.integers(min_value=60, max_value=86400)
)
@settings(max_examples=100)
def test_session_timeout_correctness(timeout_seconds):
    """会话超时必须正确执行"""
    configure_session_timeout(timeout_seconds)
    
    session = create_session("user1", "127.0.0.1")
    
    # 在超时前验证应该成功
    assert validate_session(session.id) is not None
    
    # 模拟超时
    advance_time(timeout_seconds + 1)
    
    # 超时后验证应该失败
    assert validate_session(session.id) is None
```

### Property 5: 加密解密可逆性

```python
@given(
    data=st.binary(min_size=1, max_size=10000)
)
@settings(max_examples=100)
def test_encryption_reversibility(data):
    """加密解密必须可逆"""
    encrypted = encrypt(data)
    decrypted = decrypt(encrypted)
    
    assert decrypted == data
```

### Property 6: 动态策略优先级

```python
@given(
    policies=st.lists(
        st.fixed_dictionaries({
            "priority": st.integers(min_value=0, max_value=100),
            "allowed": st.booleans()
        }),
        min_size=2,
        max_size=5
    )
)
@settings(max_examples=100)
def test_policy_priority_order(policies):
    """动态策略必须按优先级执行"""
    # 创建策略
    for policy in policies:
        create_policy(priority=policy["priority"], allowed=policy["allowed"])
    
    # 检查访问
    result = check_access_with_policies()
    
    # 结果应该等于最高优先级策略的结果
    highest_priority = max(policies, key=lambda p: p["priority"])
    assert result.allowed == highest_priority["allowed"]
```

### Property 7: SSO 用户同步幂等性

```python
@given(
    user_info=st.fixed_dictionaries({
        "sso_id": st.text(min_size=1, max_size=100),
        "email": st.emails(),
        "name": st.text(min_size=1, max_size=100)
    })
)
@settings(max_examples=100)
def test_sso_user_sync_idempotent(user_info):
    """SSO 用户同步必须是幂等的"""
    user1 = sync_sso_user(user_info)
    user2 = sync_sso_user(user_info)
    
    assert user1.id == user2.id
    assert user1.email == user2.email
```

### Property 8: 安全事件严重程度单调性

```python
@given(
    failed_attempts=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=100)
def test_security_event_severity_monotonic(failed_attempts):
    """更多失败尝试应该产生更高严重程度"""
    event1 = detect_brute_force(failed_attempts)
    event2 = detect_brute_force(failed_attempts + 5)
    
    severity_order = ["low", "medium", "high", "critical"]
    
    if event1 and event2:
        assert severity_order.index(event2.severity) >= severity_order.index(event1.severity)
```

## Frontend Components

### 1. RBAC 配置界面

**文件**: `frontend/src/pages/security/RBACConfig.tsx`

```typescript
const RBACConfig: React.FC = () => {
  const { data: roles } = useQuery(['roles'], securityApi.listRoles);
  
  return (
    <Tabs>
      <TabPane tab="角色管理" key="roles">
        <RoleList roles={roles} onEdit={handleEditRole} />
        <Button type="primary" onClick={() => setCreateModalVisible(true)}>
          创建角色
        </Button>
      </TabPane>
      <TabPane tab="权限分配" key="permissions">
        <PermissionMatrix roles={roles} />
      </TabPane>
      <TabPane tab="用户角色" key="user-roles">
        <UserRoleAssignment />
      </TabPane>
    </Tabs>
  );
};
```

### 2. 审计日志查询界面

**文件**: `frontend/src/pages/security/AuditLogs.tsx`

```typescript
const AuditLogs: React.FC = () => {
  const [filters, setFilters] = useState<AuditLogFilters>({});
  const { data: logs, isLoading } = useQuery(
    ['audit-logs', filters],
    () => securityApi.queryAuditLogs(filters)
  );

  return (
    <Card title="审计日志">
      <Form layout="inline" onFinish={setFilters}>
        <Form.Item name="user_id" label="用户">
          <UserSelect />
        </Form.Item>
        <Form.Item name="event_type" label="事件类型">
          <Select options={eventTypeOptions} />
        </Form.Item>
        <Form.Item name="dateRange" label="时间范围">
          <RangePicker />
        </Form.Item>
        <Button type="primary" htmlType="submit">查询</Button>
        <Button onClick={handleExport}>导出</Button>
      </Form>
      
      <Table
        dataSource={logs}
        columns={[
          { title: '时间', dataIndex: 'timestamp', render: formatDateTime },
          { title: '用户', dataIndex: 'user_id' },
          { title: '事件类型', dataIndex: 'event_type' },
          { title: '资源', dataIndex: 'resource' },
          { title: '操作', dataIndex: 'action' },
          { title: '结果', dataIndex: 'result', render: renderResult },
          { title: 'IP', dataIndex: 'ip_address' },
        ]}
        loading={isLoading}
      />
    </Card>
  );
};
```

### 3. 安全仪表板

**文件**: `frontend/src/pages/security/SecurityDashboard.tsx`

```typescript
const SecurityDashboard: React.FC = () => {
  const { data: posture } = useQuery(['security-posture'], securityApi.getSecurityPosture);
  const { data: events } = useQuery(['security-events'], securityApi.listSecurityEvents);

  return (
    <div>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="风险评分"
              value={posture?.risk_score}
              suffix="/ 100"
              valueStyle={{ color: getRiskColor(posture?.risk_score) }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Statistic title="活跃会话" value={posture?.active_sessions} />
        </Col>
        <Col span={6}>
          <Statistic title="待处理事件" value={events?.filter(e => e.status === 'open').length} />
        </Col>
        <Col span={6}>
          <Statistic title="今日登录" value={posture?.today_logins} />
        </Col>
      </Row>
      
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="安全事件趋势">
            <Line data={posture?.trend} xField="date" yField="count" seriesField="severity" />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="事件分布">
            <Pie data={posture?.events_by_type} angleField="count" colorField="type" />
          </Card>
        </Col>
      </Row>
      
      <Card title="最近安全事件" style={{ marginTop: 16 }}>
        <Table
          dataSource={events?.slice(0, 10)}
          columns={[
            { title: '时间', dataIndex: 'created_at', render: formatDateTime },
            { title: '类型', dataIndex: 'event_type' },
            { title: '严重程度', dataIndex: 'severity', render: renderSeverity },
            { title: '用户', dataIndex: 'user_id' },
            { title: '状态', dataIndex: 'status', render: renderStatus },
            { title: '操作', render: (_, record) => (
              <Button size="small" onClick={() => handleResolve(record)}>处理</Button>
            )}
          ]}
        />
      </Card>
    </div>
  );
};
```

## Error Handling

```python
class SecurityError(Exception):
    """安全模块基础异常"""
    pass

class PermissionDeniedError(SecurityError):
    """权限拒绝"""
    pass

class RoleNotFoundError(SecurityError):
    """角色不存在"""
    pass

class SSOProviderNotFoundError(SecurityError):
    """SSO 提供者不存在"""
    pass

class SSOAuthenticationError(SecurityError):
    """SSO 认证失败"""
    pass

class SessionExpiredError(SecurityError):
    """会话过期"""
    pass

class AuditIntegrityError(SecurityError):
    """审计日志完整性错误"""
    pass

class EncryptionError(SecurityError):
    """加密错误"""
    pass
```

## Performance Considerations

1. **权限缓存**: 缓存用户权限减少数据库查询
2. **审计日志批量写入**: 使用批量写入提高性能
3. **会话存储**: 使用 Redis 存储会话数据
4. **异步监控**: 安全监控使用异步处理
5. **索引优化**: 为审计日志常用查询字段创建索引
6. **日志归档**: 定期归档旧日志减少查询压力
