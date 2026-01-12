# Design Document

## Overview

审计安全系统为SuperInsight 2.3提供企业级安全合规能力，包含全面的审计日志记录、智能数据脱敏和细粒度RBAC权限控制。系统基于现有安全架构扩展，确保数据安全、操作可追溯和合规要求满足。

## Architecture Design

### System Architecture

```
Audit Security System
├── Audit Logging Engine
│   ├── Event Collector
│   ├── Log Processor
│   └── Audit Storage
├── Data Desensitization Layer
│   ├── Presidio Integration
│   ├── Pattern Detector
│   └── Masking Engine
├── RBAC Permission System
│   ├── Role Manager
│   ├── Permission Controller
│   └── Access Validator
├── Security Event Monitor
│   ├── Threat Detector
│   ├── Anomaly Analyzer
│   └── Alert Manager
└── Compliance Reporter
    ├── Report Generator
    ├── Audit Trail
    └── Compliance Dashboard
```

### Component Architecture

```typescript
interface AuditSecuritySystem {
  auditLogger: AuditLogger;
  desensitizer: DataDesensitizer;
  rbacManager: RBACManager;
  securityMonitor: SecurityMonitor;
  complianceReporter: ComplianceReporter;
}

interface AuditLogger {
  logEvent(event: AuditEvent): Promise<void>;
  queryLogs(criteria: QueryCriteria): Promise<AuditLog[]>;
  exportLogs(format: ExportFormat): Promise<Buffer>;
}

interface DataDesensitizer {
  detectSensitiveData(text: string): Promise<SensitiveDataMatch[]>;
  maskData(text: string, policy: MaskingPolicy): Promise<string>;
  validateDesensitization(original: string, masked: string): Promise<boolean>;
}
```

## Data Models

### Audit Event Model

```typescript
interface AuditEvent {
  id: string;
  timestamp: Date;
  userId: string;
  tenantId: string;
  workspaceId?: string;
  eventType: AuditEventType;
  resource: string;
  action: string;
  details: AuditEventDetails;
  ipAddress: string;
  userAgent: string;
  sessionId: string;
  result: EventResult;
  riskLevel: RiskLevel;
  metadata: Record<string, any>;
}

interface AuditEventDetails {
  resourceId?: string;
  resourceType?: string;
  oldValues?: Record<string, any>;
  newValues?: Record<string, any>;
  affectedRecords?: number;
  queryParameters?: Record<string, any>;
  requestBody?: any;
  responseStatus?: number;
}

enum AuditEventType {
  USER_LOGIN = 'user_login',
  USER_LOGOUT = 'user_logout',
  DATA_ACCESS = 'data_access',
  DATA_MODIFICATION = 'data_modification',
  DATA_EXPORT = 'data_export',
  PERMISSION_CHANGE = 'permission_change',
  SYSTEM_CONFIG = 'system_config',
  SECURITY_EVENT = 'security_event'
}

enum EventResult {
  SUCCESS = 'success',
  FAILURE = 'failure',
  PARTIAL = 'partial',
  BLOCKED = 'blocked'
}

enum RiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}
```

### RBAC Model

```typescript
interface Role {
  id: string;
  name: string;
  description: string;
  tenantId: string;
  permissions: Permission[];
  isSystemRole: boolean;
  createdAt: Date;
  updatedAt: Date;
  metadata: Record<string, any>;
}

interface Permission {
  id: string;
  resource: string;
  action: string;
  conditions?: PermissionCondition[];
  effect: PermissionEffect;
  priority: number;
}

interface PermissionCondition {
  field: string;
  operator: ConditionOperator;
  value: any;
  context?: string;
}

enum PermissionEffect {
  ALLOW = 'allow',
  DENY = 'deny'
}

enum ConditionOperator {
  EQUALS = 'equals',
  NOT_EQUALS = 'not_equals',
  IN = 'in',
  NOT_IN = 'not_in',
  GREATER_THAN = 'greater_than',
  LESS_THAN = 'less_than',
  CONTAINS = 'contains',
  REGEX = 'regex'
}
```

### Data Sensitivity Model

```typescript
interface SensitivityPolicy {
  id: string;
  name: string;
  tenantId: string;
  patterns: SensitivityPattern[];
  maskingRules: MaskingRule[];
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

interface SensitivityPattern {
  id: string;
  name: string;
  pattern: string;
  patternType: PatternType;
  sensitivityLevel: SensitivityLevel;
  entityType: string;
  confidence: number;
}

interface MaskingRule {
  id: string;
  entityType: string;
  maskingType: MaskingType;
  maskingConfig: MaskingConfig;
  conditions: MaskingCondition[];
}

enum PatternType {
  REGEX = 'regex',
  PRESIDIO = 'presidio',
  CUSTOM = 'custom'
}

enum SensitivityLevel {
  PUBLIC = 'public',
  INTERNAL = 'internal',
  CONFIDENTIAL = 'confidential',
  RESTRICTED = 'restricted'
}

enum MaskingType {
  REDACT = 'redact',
  REPLACE = 'replace',
  HASH = 'hash',
  ENCRYPT = 'encrypt',
  PARTIAL = 'partial'
}
```

## Database Schema Design

### Audit Tables

```sql
-- 审计事件表
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    workspace_id UUID REFERENCES workspaces(id),
    event_type audit_event_type NOT NULL,
    resource VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(255),
    result event_result NOT NULL,
    risk_level risk_level NOT NULL DEFAULT 'low',
    metadata JSONB DEFAULT '{}'
);

-- 审计事件索引
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp);
CREATE INDEX idx_audit_events_user_id ON audit_events(user_id);
CREATE INDEX idx_audit_events_tenant_id ON audit_events(tenant_id);
CREATE INDEX idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX idx_audit_events_risk_level ON audit_events(risk_level);

-- 角色权限表
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tenant_id UUID REFERENCES tenants(id),
    permissions JSONB NOT NULL DEFAULT '[]',
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(tenant_id, name)
);

-- 用户角色关联表
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    role_id UUID NOT NULL REFERENCES roles(id),
    tenant_id UUID REFERENCES tenants(id),
    workspace_id UUID REFERENCES workspaces(id),
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, role_id, tenant_id, workspace_id)
);

-- 敏感数据策略表
CREATE TABLE sensitivity_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    tenant_id UUID REFERENCES tenants(id),
    patterns JSONB NOT NULL DEFAULT '[]',
    masking_rules JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
```

## Implementation Strategy

### Phase 1: 基于现有安全架构扩展

#### 扩展现有审计服务
```python
# 扩展 src/security/audit_service.py
from src.security.audit_service import AuditService

class EnhancedAuditService(AuditService):
    """扩展现有审计服务，增加企业级功能"""
    
    def __init__(self):
        super().__init__()  # 保持现有审计逻辑
        self.event_processor = AuditEventProcessor()
        self.risk_analyzer = RiskAnalyzer()
    
    async def log_event(
        self, 
        event_type: AuditEventType,
        user_id: str,
        resource: str,
        action: str,
        details: dict = None,
        request: Request = None
    ):
        """增强的事件记录功能"""
        # 基于现有审计记录逻辑
        base_event = await super().log_event(event_type, user_id, resource, action)
        
        # 增加风险评估
        risk_level = await self.risk_analyzer.assess_risk(
            event_type, user_id, resource, action, details
        )
        
        # 增加详细信息提取
        enhanced_details = await self.extract_enhanced_details(
            request, details
        )
        
        # 创建增强审计事件
        audit_event = AuditEvent(
            **base_event,
            details=enhanced_details,
            risk_level=risk_level,
            ip_address=self.extract_ip_address(request),
            user_agent=self.extract_user_agent(request),
            session_id=self.extract_session_id(request)
        )
        
        # 存储到审计数据库
        await self.store_audit_event(audit_event)
        
        # 触发实时监控
        await self.trigger_security_monitoring(audit_event)
        
        return audit_event
```

#### 扩展现有脱敏功能
```python
# 扩展 src/api/desensitization.py
from src.api.desensitization import DesensitizationAPI

class PresidioDesensitizer(DesensitizationAPI):
    """基于Presidio的智能脱敏系统"""
    
    def __init__(self):
        super().__init__()  # 保持现有脱敏逻辑
        self.presidio_analyzer = self.init_presidio_analyzer()
        self.presidio_anonymizer = self.init_presidio_anonymizer()
    
    def init_presidio_analyzer(self):
        """初始化Presidio分析器"""
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        
        # 配置中文支持
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "zh", "model_name": "zh_core_web_sm"},
                {"lang_code": "en", "model_name": "en_core_web_sm"}
            ]
        }
        
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        
        return AnalyzerEngine(nlp_engine=nlp_engine)
    
    async def detect_sensitive_data(self, text: str, language: str = "zh") -> List[dict]:
        """检测敏感数据"""
        # 基于现有检测逻辑扩展
        base_results = await super().detect_sensitive_data(text)
        
        # 使用Presidio进行高级检测
        presidio_results = self.presidio_analyzer.analyze(
            text=text,
            language=language,
            entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "IBAN_CODE"]
        )
        
        # 合并检测结果
        combined_results = self.merge_detection_results(base_results, presidio_results)
        
        return combined_results
    
    async def mask_sensitive_data(
        self, 
        text: str, 
        masking_policy: MaskingPolicy,
        language: str = "zh"
    ) -> str:
        """智能数据脱敏"""
        # 检测敏感数据
        sensitive_entities = await self.detect_sensitive_data(text, language)
        
        # 应用脱敏策略
        anonymized_text = self.presidio_anonymizer.anonymize(
            text=text,
            analyzer_results=sensitive_entities,
            operators=self.build_anonymization_operators(masking_policy)
        )
        
        return anonymized_text.text
```

#### 扩展现有权限控制
```python
# 扩展 src/security/controller.py
from src.security.controller import SecurityController

class RBACController(SecurityController):
    """基于角色的访问控制器"""
    
    def __init__(self):
        super().__init__()  # 保持现有安全控制逻辑
        self.role_manager = RoleManager()
        self.permission_evaluator = PermissionEvaluator()
    
    async def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: dict = None
    ) -> bool:
        """细粒度权限检查"""
        # 基于现有权限检查逻辑
        base_permission = await super().check_permission(user_id, resource, action)
        
        if not base_permission:
            return False
        
        # 获取用户角色
        user_roles = await self.role_manager.get_user_roles(user_id)
        
        # 评估权限
        for role in user_roles:
            if await self.permission_evaluator.evaluate_role_permission(
                role, resource, action, context
            ):
                return True
        
        return False
    
    async def get_user_permissions(self, user_id: str) -> List[Permission]:
        """获取用户所有权限"""
        user_roles = await self.role_manager.get_user_roles(user_id)
        permissions = []
        
        for role in user_roles:
            role_permissions = await self.role_manager.get_role_permissions(role.id)
            permissions.extend(role_permissions)
        
        # 去重和优先级排序
        return self.deduplicate_and_sort_permissions(permissions)
```

### Phase 2: 安全监控和告警

#### 安全事件监控
```python
# src/security/security_monitor.py
from src.monitoring.prometheus_integration import PrometheusIntegration

class SecurityEventMonitor(PrometheusIntegration):
    """安全事件监控系统"""
    
    def __init__(self):
        super().__init__()  # 复用现有监控基础
        self.threat_detector = ThreatDetector()
        self.anomaly_analyzer = AnomalyAnalyzer()
        self.alert_manager = AlertManager()
    
    async def monitor_audit_events(self):
        """监控审计事件"""
        # 基于现有监控指标
        recent_events = await self.get_recent_audit_events()
        
        for event in recent_events:
            # 威胁检测
            threat_score = await self.threat_detector.analyze_event(event)
            if threat_score > self.THREAT_THRESHOLD:
                await self.handle_security_threat(event, threat_score)
            
            # 异常检测
            anomaly_score = await self.anomaly_analyzer.analyze_event(event)
            if anomaly_score > self.ANOMALY_THRESHOLD:
                await self.handle_security_anomaly(event, anomaly_score)
    
    async def handle_security_threat(self, event: AuditEvent, threat_score: float):
        """处理安全威胁"""
        # 记录安全事件
        security_event = SecurityEvent(
            type=SecurityEventType.THREAT_DETECTED,
            audit_event_id=event.id,
            threat_score=threat_score,
            description=f"Threat detected for user {event.user_id}",
            recommended_actions=await self.get_threat_response_actions(event)
        )
        
        await self.store_security_event(security_event)
        
        # 发送告警
        await self.alert_manager.send_security_alert(security_event)
        
        # 自动响应
        if threat_score > self.AUTO_RESPONSE_THRESHOLD:
            await self.execute_auto_response(event, security_event)
```

#### 异常行为分析
```python
class AnomalyAnalyzer:
    """异常行为分析器"""
    
    def __init__(self):
        self.ml_model = self.load_anomaly_detection_model()
        self.baseline_calculator = BaselineCalculator()
    
    async def analyze_event(self, event: AuditEvent) -> float:
        """分析事件异常程度"""
        # 提取事件特征
        features = await self.extract_event_features(event)
        
        # 获取用户基线行为
        user_baseline = await self.baseline_calculator.get_user_baseline(event.user_id)
        
        # 计算异常分数
        anomaly_score = self.ml_model.predict_anomaly(features, user_baseline)
        
        return anomaly_score
    
    async def extract_event_features(self, event: AuditEvent) -> dict:
        """提取事件特征"""
        return {
            "hour_of_day": event.timestamp.hour,
            "day_of_week": event.timestamp.weekday(),
            "event_type": event.event_type,
            "resource_type": event.resource,
            "action_type": event.action,
            "ip_location": await self.get_ip_location(event.ip_address),
            "user_agent_type": self.classify_user_agent(event.user_agent),
            "session_duration": await self.get_session_duration(event.session_id)
        }
```

### Phase 3: 合规报告和仪表盘

#### 合规报告生成器
```python
# src/compliance/report_generator.py
class ComplianceReportGenerator:
    """合规报告生成器"""
    
    def __init__(self):
        self.audit_service = EnhancedAuditService()
        self.template_engine = ReportTemplateEngine()
    
    async def generate_audit_report(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        report_type: ComplianceReportType
    ) -> ComplianceReport:
        """生成审计报告"""
        
        # 查询审计数据
        audit_data = await self.audit_service.query_audit_events(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # 生成报告内容
        report_content = await self.generate_report_content(audit_data, report_type)
        
        # 应用报告模板
        formatted_report = await self.template_engine.apply_template(
            report_content, report_type
        )
        
        return ComplianceReport(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            report_type=report_type,
            period_start=start_date,
            period_end=end_date,
            content=formatted_report,
            generated_at=datetime.utcnow()
        )
    
    async def generate_gdpr_report(self, tenant_id: str, period: DateRange) -> dict:
        """生成GDPR合规报告"""
        return {
            "data_processing_activities": await self.get_data_processing_activities(tenant_id, period),
            "consent_records": await self.get_consent_records(tenant_id, period),
            "data_subject_requests": await self.get_data_subject_requests(tenant_id, period),
            "data_breaches": await self.get_data_breaches(tenant_id, period),
            "privacy_impact_assessments": await self.get_privacy_assessments(tenant_id, period)
        }
```

## Security Implementation

### Access Control Matrix

```python
# 企业级权限矩阵
ENTERPRISE_PERMISSIONS = {
    # 系统管理员
    "system_admin": [
        "system.manage",
        "tenant.create",
        "tenant.manage", 
        "user.manage_all",
        "audit.view_all",
        "security.configure"
    ],
    
    # 租户管理员
    "tenant_admin": [
        "tenant.configure",
        "workspace.create",
        "workspace.manage",
        "user.invite",
        "user.manage",
        "audit.view_tenant",
        "billing.view",
        "compliance.generate_reports"
    ],
    
    # 安全管理员
    "security_admin": [
        "security.configure",
        "audit.view_all",
        "audit.export",
        "compliance.manage",
        "threat.investigate",
        "policy.manage"
    ],
    
    # 数据保护官
    "data_protection_officer": [
        "privacy.manage",
        "consent.manage",
        "data_subject_request.handle",
        "privacy_assessment.conduct",
        "compliance.gdpr_reports"
    ],
    
    # 工作空间管理员
    "workspace_admin": [
        "workspace.configure",
        "task.create",
        "task.assign",
        "user.manage_workspace",
        "audit.view_workspace",
        "quality.manage"
    ],
    
    # 标注员
    "annotator": [
        "task.view_assigned",
        "annotation.create",
        "annotation.update",
        "file.upload",
        "profile.view"
    ],
    
    # 审核员
    "reviewer": [
        "annotation.review",
        "annotation.approve",
        "quality.assess",
        "report.view",
        "task.view_all"
    ],
    
    # 观察员
    "observer": [
        "task.view",
        "annotation.view",
        "report.view",
        "dashboard.view"
    ]
}

# 资源级权限控制
RESOURCE_PERMISSIONS = {
    "task": {
        "create": ["workspace_admin", "project_manager"],
        "read": ["annotator", "reviewer", "observer"],
        "update": ["workspace_admin", "task_owner"],
        "delete": ["workspace_admin"],
        "assign": ["workspace_admin", "project_manager"]
    },
    
    "annotation": {
        "create": ["annotator"],
        "read": ["annotator", "reviewer", "observer"],
        "update": ["annotator", "annotation_owner"],
        "delete": ["workspace_admin", "annotation_owner"],
        "review": ["reviewer"],
        "approve": ["reviewer", "workspace_admin"]
    },
    
    "user": {
        "create": ["tenant_admin", "workspace_admin"],
        "read": ["workspace_admin", "user_self"],
        "update": ["tenant_admin", "workspace_admin", "user_self"],
        "delete": ["tenant_admin"],
        "invite": ["tenant_admin", "workspace_admin"]
    }
}
```

### Data Classification and Protection

```python
class DataClassificationService:
    """数据分类和保护服务"""
    
    def __init__(self):
        self.classifier = DataClassifier()
        self.protector = DataProtector()
    
    async def classify_data(self, data: str, context: dict) -> DataClassification:
        """数据分类"""
        # 自动分类
        auto_classification = await self.classifier.auto_classify(data)
        
        # 上下文分析
        context_classification = await self.classifier.analyze_context(context)
        
        # 合并分类结果
        final_classification = self.merge_classifications(
            auto_classification, context_classification
        )
        
        return final_classification
    
    async def apply_protection(
        self, 
        data: str, 
        classification: DataClassification,
        access_context: AccessContext
    ) -> str:
        """应用数据保护"""
        protection_policy = await self.get_protection_policy(
            classification, access_context
        )
        
        if protection_policy.requires_masking:
            return await self.protector.mask_data(data, protection_policy.masking_rules)
        elif protection_policy.requires_encryption:
            return await self.protector.encrypt_data(data, protection_policy.encryption_key)
        elif protection_policy.access_denied:
            raise AccessDeniedError("Access to this data is not permitted")
        
        return data
```

## Performance Optimization

### Audit Log Optimization

```python
class OptimizedAuditStorage:
    """优化的审计存储"""
    
    def __init__(self):
        self.batch_processor = BatchProcessor()
        self.compression_engine = CompressionEngine()
        self.archival_service = ArchivalService()
    
    async def store_audit_events(self, events: List[AuditEvent]):
        """批量存储审计事件"""
        # 批量处理
        batches = self.batch_processor.create_batches(events, batch_size=1000)
        
        for batch in batches:
            # 压缩存储
            compressed_batch = await self.compression_engine.compress(batch)
            
            # 异步存储
            await self.store_compressed_batch(compressed_batch)
    
    async def archive_old_logs(self, retention_days: int = 2555):  # 7年保留期
        """归档旧日志"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        old_logs = await self.query_logs_before_date(cutoff_date)
        
        # 归档到冷存储
        await self.archival_service.archive_logs(old_logs)
        
        # 删除已归档的日志
        await self.delete_archived_logs(old_logs)
```

### Permission Caching

```python
class PermissionCache:
    """权限缓存系统"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 3600  # 1小时
    
    async def get_user_permissions(self, user_id: str) -> Optional[List[Permission]]:
        """获取缓存的用户权限"""
        cache_key = f"permissions:user:{user_id}"
        cached_permissions = await self.redis.get(cache_key)
        
        if cached_permissions:
            return json.loads(cached_permissions)
        
        return None
    
    async def cache_user_permissions(self, user_id: str, permissions: List[Permission]):
        """缓存用户权限"""
        cache_key = f"permissions:user:{user_id}"
        permissions_json = json.dumps([p.dict() for p in permissions])
        
        await self.redis.setex(cache_key, self.cache_ttl, permissions_json)
    
    async def invalidate_user_permissions(self, user_id: str):
        """失效用户权限缓存"""
        cache_key = f"permissions:user:{user_id}"
        await self.redis.delete(cache_key)
```

## Monitoring and Analytics

### Security Metrics Dashboard

```python
class SecurityMetricsDashboard:
    """安全指标仪表盘"""
    
    async def get_security_overview(self, tenant_id: str) -> SecurityOverview:
        """获取安全概览"""
        return SecurityOverview(
            total_audit_events=await self.count_audit_events(tenant_id),
            security_incidents=await self.count_security_incidents(tenant_id),
            failed_login_attempts=await self.count_failed_logins(tenant_id),
            data_access_violations=await self.count_access_violations(tenant_id),
            compliance_score=await self.calculate_compliance_score(tenant_id),
            risk_level=await self.assess_overall_risk(tenant_id)
        )
    
    async def get_threat_intelligence(self, tenant_id: str) -> ThreatIntelligence:
        """获取威胁情报"""
        return ThreatIntelligence(
            active_threats=await self.get_active_threats(tenant_id),
            threat_trends=await self.analyze_threat_trends(tenant_id),
            attack_patterns=await self.identify_attack_patterns(tenant_id),
            recommended_actions=await self.get_security_recommendations(tenant_id)
        )
```

This comprehensive design provides enterprise-grade audit, security, and compliance capabilities for SuperInsight 2.3, ensuring data protection, regulatory compliance, and security monitoring while building upon the existing security infrastructure.