"""
Security Event Monitor for SuperInsight Platform.

Provides comprehensive security event monitoring, threat detection, and alerting
based on existing Prometheus monitoring and audit systems.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
from uuid import UUID
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, select
from prometheus_client import Counter as PrometheusCounter, Gauge, Histogram

from src.system.prometheus_integration import PrometheusMetricsExporter, PrometheusConfig
from src.security.audit_service import EnhancedAuditService, AuditService, RiskLevel
from src.security.models import AuditLogModel, AuditAction
from src.database.connection import get_db_session


class ThreatLevel(Enum):
    """威胁等级分类"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """安全事件类型"""
    AUTHENTICATION_FAILURE = "authentication_failure"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MALICIOUS_REQUEST = "malicious_request"
    BRUTE_FORCE_ATTACK = "brute_force_attack"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    POLICY_VIOLATION = "policy_violation"


@dataclass
class SecurityEvent:
    """安全事件数据结构"""
    event_id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    tenant_id: str
    user_id: Optional[UUID]
    ip_address: Optional[str]
    timestamp: datetime
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    source_audit_log_id: Optional[str] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None


@dataclass
class ThreatPattern:
    """威胁模式定义"""
    pattern_id: str
    name: str
    description: str
    detection_rules: Dict[str, Any]
    threat_level: ThreatLevel
    auto_response: bool = False
    response_actions: List[str] = field(default_factory=list)


class SecurityEventMonitor(PrometheusMetricsExporter):
    """
    安全事件监控器，扩展Prometheus监控系统。
    
    功能：
    - 实时安全事件监控
    - 威胁检测和分析
    - 自动告警和响应
    - 安全指标收集
    - 异常行为检测
    """
    
    def __init__(self, config: Optional[PrometheusConfig] = None):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.audit_service = EnhancedAuditService()
        
        # 安全事件存储
        self.active_events: Dict[str, SecurityEvent] = {}
        self.resolved_events: List[SecurityEvent] = []
        
        # 威胁检测模式
        self.threat_patterns = self._initialize_threat_patterns()
        
        # 监控状态
        self.monitoring_enabled = True
        self.last_scan_time = datetime.utcnow()
        
        # 初始化安全指标
        self._initialize_security_metrics()
        
        # 异常检测缓存
        self.behavior_baselines: Dict[str, Dict[str, Any]] = {}
        self.ip_reputation_cache: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("Security Event Monitor initialized")
    
    def _initialize_security_metrics(self):
        """初始化安全相关的Prometheus指标"""
        
        # 安全事件计数器
        self.security_metrics = {
            'security_events_total': PrometheusCounter(
                'security_events_total',
                'Total number of security events detected',
                labelnames=['event_type', 'threat_level', 'tenant_id'],
                registry=self.registry
            ),
            'threat_detections_total': PrometheusCounter(
                'threat_detections_total',
                'Total number of threat detections',
                labelnames=['pattern_id', 'threat_level', 'tenant_id'],
                registry=self.registry
            ),
            'security_alerts_total': PrometheusCounter(
                'security_alerts_total',
                'Total number of security alerts generated',
                labelnames=['alert_type', 'severity', 'tenant_id'],
                registry=self.registry
            ),
            'failed_authentication_attempts': PrometheusCounter(
                'failed_authentication_attempts_total',
                'Total failed authentication attempts',
                labelnames=['tenant_id', 'ip_address', 'reason'],
                registry=self.registry
            ),
            'privilege_escalation_attempts': PrometheusCounter(
                'privilege_escalation_attempts_total',
                'Total privilege escalation attempts',
                labelnames=['tenant_id', 'user_id', 'resource_type'],
                registry=self.registry
            ),
            'data_access_violations': PrometheusCounter(
                'data_access_violations_total',
                'Total data access violations',
                labelnames=['tenant_id', 'resource_type', 'violation_type'],
                registry=self.registry
            ),
            
            # 安全状态指标
            'active_security_events': Gauge(
                'active_security_events',
                'Number of active security events',
                labelnames=['threat_level', 'tenant_id'],
                registry=self.registry
            ),
            'security_score': Gauge(
                'security_score',
                'Overall security score (0-100)',
                labelnames=['tenant_id'],
                registry=self.registry
            ),
            'threat_level_distribution': Gauge(
                'threat_level_distribution',
                'Distribution of threat levels',
                labelnames=['threat_level', 'tenant_id'],
                registry=self.registry
            ),
            
            # 性能指标
            'security_scan_duration_seconds': Histogram(
                'security_scan_duration_seconds',
                'Time taken for security scans',
                labelnames=['scan_type'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
                registry=self.registry
            ),
            'threat_detection_latency_seconds': Histogram(
                'threat_detection_latency_seconds',
                'Latency of threat detection',
                labelnames=['pattern_id'],
                buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
                registry=self.registry
            ),
        }
        
        self.logger.info("Security metrics initialized")
    
    def _initialize_threat_patterns(self) -> Dict[str, ThreatPattern]:
        """初始化威胁检测模式"""
        
        patterns = {}
        
        # 暴力破解攻击检测
        patterns['brute_force_login'] = ThreatPattern(
            pattern_id='brute_force_login',
            name='暴力破解登录攻击',
            description='检测短时间内多次失败登录尝试',
            detection_rules={
                'time_window': 300,  # 5分钟
                'failure_threshold': 10,
                'unique_ip_threshold': 3,
                'actions': [AuditAction.LOGIN],
                'failure_indicators': ['failed', 'invalid', 'blocked']
            },
            threat_level=ThreatLevel.HIGH,
            auto_response=True,
            response_actions=['block_ip', 'notify_admin', 'increase_monitoring']
        )
        
        # 权限提升攻击检测
        patterns['privilege_escalation'] = ThreatPattern(
            pattern_id='privilege_escalation',
            name='权限提升攻击',
            description='检测异常的权限提升操作',
            detection_rules={
                'time_window': 600,  # 10分钟
                'escalation_threshold': 3,
                'actions': [AuditAction.UPDATE],
                'sensitive_resources': ['user', 'role', 'permission', 'tenant'],
                'risk_indicators': ['admin', 'root', 'superuser']
            },
            threat_level=ThreatLevel.CRITICAL,
            auto_response=True,
            response_actions=['suspend_user', 'notify_security_team', 'audit_review']
        )
        
        # 数据泄露检测
        patterns['data_exfiltration'] = ThreatPattern(
            pattern_id='data_exfiltration',
            name='数据泄露风险',
            description='检测大量数据导出或异常访问',
            detection_rules={
                'time_window': 3600,  # 1小时
                'export_size_threshold': 1000,  # MB
                'export_count_threshold': 50,
                'actions': [AuditAction.EXPORT, AuditAction.READ],
                'sensitive_data_types': ['user_data', 'annotation', 'dataset']
            },
            threat_level=ThreatLevel.HIGH,
            auto_response=True,
            response_actions=['limit_exports', 'notify_dpo', 'audit_review']
        )
        
        # 异常行为检测
        patterns['anomalous_behavior'] = ThreatPattern(
            pattern_id='anomalous_behavior',
            name='异常用户行为',
            description='检测与历史行为模式不符的活动',
            detection_rules={
                'time_window': 86400,  # 24小时
                'deviation_threshold': 3.0,  # 标准差倍数
                'min_baseline_days': 7,
                'behavior_metrics': ['action_frequency', 'resource_access', 'time_patterns']
            },
            threat_level=ThreatLevel.MEDIUM,
            auto_response=False,
            response_actions=['flag_for_review', 'increase_monitoring']
        )
        
        # 恶意请求检测
        patterns['malicious_requests'] = ThreatPattern(
            pattern_id='malicious_requests',
            name='恶意请求攻击',
            description='检测SQL注入、XSS等恶意请求',
            detection_rules={
                'time_window': 60,  # 1分钟
                'request_threshold': 5,
                'malicious_patterns': [
                    'union select', 'drop table', 'insert into', 'update set',
                    '<script>', 'javascript:', 'onload=', 'onerror=',
                    '../../../', '..\\..\\..\\', '/etc/passwd', 'cmd.exe'
                ],
                'suspicious_headers': ['x-forwarded-for', 'x-real-ip']
            },
            threat_level=ThreatLevel.CRITICAL,
            auto_response=True,
            response_actions=['block_request', 'block_ip', 'notify_security_team']
        )
        
        return patterns
    
    async def start_monitoring(self):
        """启动安全事件监控"""
        if not self.monitoring_enabled:
            self.monitoring_enabled = True
        
        # 启动Prometheus指标收集
        await self.start_collection()
        
        # 启动安全监控循环
        asyncio.create_task(self._security_monitoring_loop())
        
        self.logger.info("Security event monitoring started")
    
    async def stop_monitoring(self):
        """停止安全事件监控"""
        self.monitoring_enabled = False
        await self.stop_collection()
        
        self.logger.info("Security event monitoring stopped")
    
    async def _security_monitoring_loop(self):
        """安全监控主循环"""
        while self.monitoring_enabled:
            try:
                scan_start_time = datetime.utcnow()
                
                # 执行威胁检测扫描
                await self._perform_threat_detection_scan()
                
                # 更新安全指标
                await self._update_security_metrics()
                
                # 检查和处理告警
                await self._process_security_alerts()
                
                # 清理过期事件
                await self._cleanup_expired_events()
                
                # 记录扫描性能
                scan_duration = (datetime.utcnow() - scan_start_time).total_seconds()
                self.security_metrics['security_scan_duration_seconds'].labels(
                    scan_type='full_scan'
                ).observe(scan_duration)
                
                self.last_scan_time = datetime.utcnow()
                
                # 等待下一次扫描
                await asyncio.sleep(30)  # 30秒扫描间隔
                
            except Exception as e:
                self.logger.error(f"Security monitoring loop error: {e}")
                await asyncio.sleep(60)  # 错误时等待更长时间
    
    async def _perform_threat_detection_scan(self):
        """执行威胁检测扫描"""
        
        # 获取数据库会话
        with get_db_session() as db:
            # 获取最近的审计日志
            recent_logs = await self._get_recent_audit_logs(db)
            
            # 对每个威胁模式进行检测
            for pattern_id, pattern in self.threat_patterns.items():
                detection_start_time = datetime.utcnow()
                
                try:
                    # 执行模式检测
                    detected_events = await self._detect_threat_pattern(
                        pattern, recent_logs, db
                    )
                    
                    # 处理检测到的事件
                    for event in detected_events:
                        await self._handle_security_event(event, db)
                    
                    # 记录检测延迟
                    detection_duration = (datetime.utcnow() - detection_start_time).total_seconds()
                    self.security_metrics['threat_detection_latency_seconds'].labels(
                        pattern_id=pattern_id
                    ).observe(detection_duration)
                    
                except Exception as e:
                    self.logger.error(f"Threat pattern detection error ({pattern_id}): {e}")
    
    async def _get_recent_audit_logs(self, db: Session, hours: int = 1) -> List[AuditLogModel]:
        """获取最近的审计日志"""
        
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        stmt = select(AuditLogModel).where(
            AuditLogModel.timestamp >= time_threshold
        ).order_by(desc(AuditLogModel.timestamp))
        
        return db.execute(stmt).scalars().all()
    
    async def _detect_threat_pattern(
        self,
        pattern: ThreatPattern,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[SecurityEvent]:
        """检测特定威胁模式"""
        
        detected_events = []
        
        if pattern.pattern_id == 'brute_force_login':
            detected_events.extend(
                await self._detect_brute_force_attacks(pattern, audit_logs)
            )
        elif pattern.pattern_id == 'privilege_escalation':
            detected_events.extend(
                await self._detect_privilege_escalation(pattern, audit_logs)
            )
        elif pattern.pattern_id == 'data_exfiltration':
            detected_events.extend(
                await self._detect_data_exfiltration(pattern, audit_logs)
            )
        elif pattern.pattern_id == 'anomalous_behavior':
            detected_events.extend(
                await self._detect_anomalous_behavior(pattern, audit_logs, db)
            )
        elif pattern.pattern_id == 'malicious_requests':
            detected_events.extend(
                await self._detect_malicious_requests(pattern, audit_logs)
            )
        
        return detected_events
    
    async def _detect_brute_force_attacks(
        self,
        pattern: ThreatPattern,
        audit_logs: List[AuditLogModel]
    ) -> List[SecurityEvent]:
        """检测暴力破解攻击"""
        
        events = []
        rules = pattern.detection_rules
        
        # 按IP地址分组失败登录
        failed_logins_by_ip = defaultdict(list)
        
        for log in audit_logs:
            if (log.action == AuditAction.LOGIN and 
                log.details and 
                any(indicator in str(log.details.get('status', '')).lower() 
                    for indicator in rules['failure_indicators'])):
                
                ip_key = str(log.ip_address) if log.ip_address else 'unknown'
                failed_logins_by_ip[ip_key].append(log)
        
        # 检查每个IP的失败次数
        for ip_address, failed_logs in failed_logins_by_ip.items():
            if len(failed_logs) >= rules['failure_threshold']:
                
                # 检查时间窗口
                time_span = (failed_logs[0].timestamp - failed_logs[-1].timestamp).total_seconds()
                if time_span <= rules['time_window']:
                    
                    # 创建安全事件
                    event = SecurityEvent(
                        event_id=self._generate_event_id(),
                        event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                        threat_level=pattern.threat_level,
                        tenant_id=failed_logs[0].tenant_id,
                        user_id=None,  # 攻击者未知
                        ip_address=ip_address if ip_address != 'unknown' else None,
                        timestamp=datetime.utcnow(),
                        description=f"检测到来自IP {ip_address}的暴力破解攻击，{len(failed_logs)}次失败登录",
                        details={
                            'pattern_id': pattern.pattern_id,
                            'failed_attempts': len(failed_logs),
                            'time_window_seconds': time_span,
                            'affected_accounts': list(set(
                                log.details.get('username', 'unknown') 
                                for log in failed_logs if log.details
                            )),
                            'first_attempt': failed_logs[-1].timestamp.isoformat(),
                            'last_attempt': failed_logs[0].timestamp.isoformat()
                        },
                        source_audit_log_id=failed_logs[0].id
                    )
                    
                    events.append(event)
        
        return events
    
    async def _detect_privilege_escalation(
        self,
        pattern: ThreatPattern,
        audit_logs: List[AuditLogModel]
    ) -> List[SecurityEvent]:
        """检测权限提升攻击"""
        
        events = []
        rules = pattern.detection_rules
        
        # 按用户分组权限相关操作
        privilege_ops_by_user = defaultdict(list)
        
        for log in audit_logs:
            if (log.action in rules['actions'] and 
                log.resource_type in rules['sensitive_resources']):
                
                user_key = str(log.user_id) if log.user_id else 'unknown'
                privilege_ops_by_user[user_key].append(log)
        
        # 检查每个用户的权限操作
        for user_id, ops_logs in privilege_ops_by_user.items():
            if len(ops_logs) >= rules['escalation_threshold']:
                
                # 检查是否包含风险指标
                risk_operations = []
                for log in ops_logs:
                    if log.details:
                        details_str = json.dumps(log.details).lower()
                        if any(indicator in details_str for indicator in rules['risk_indicators']):
                            risk_operations.append(log)
                
                if risk_operations:
                    # 创建安全事件
                    event = SecurityEvent(
                        event_id=self._generate_event_id(),
                        event_type=SecurityEventType.PRIVILEGE_ESCALATION,
                        threat_level=pattern.threat_level,
                        tenant_id=ops_logs[0].tenant_id,
                        user_id=UUID(user_id) if user_id != 'unknown' else None,
                        ip_address=str(ops_logs[0].ip_address) if ops_logs[0].ip_address else None,
                        timestamp=datetime.utcnow(),
                        description=f"检测到用户 {user_id} 的权限提升攻击，{len(risk_operations)}个高风险操作",
                        details={
                            'pattern_id': pattern.pattern_id,
                            'total_operations': len(ops_logs),
                            'risk_operations': len(risk_operations),
                            'affected_resources': list(set(log.resource_type for log in ops_logs)),
                            'risk_indicators_found': [
                                indicator for indicator in rules['risk_indicators']
                                if any(indicator in json.dumps(log.details).lower() 
                                      for log in risk_operations if log.details)
                            ]
                        },
                        source_audit_log_id=risk_operations[0].id
                    )
                    
                    events.append(event)
        
        return events
    
    async def _detect_data_exfiltration(
        self,
        pattern: ThreatPattern,
        audit_logs: List[AuditLogModel]
    ) -> List[SecurityEvent]:
        """检测数据泄露风险"""
        
        events = []
        rules = pattern.detection_rules
        
        # 按用户分组数据访问操作
        data_ops_by_user = defaultdict(list)
        
        for log in audit_logs:
            if log.action in rules['actions']:
                user_key = str(log.user_id) if log.user_id else 'unknown'
                data_ops_by_user[user_key].append(log)
        
        # 检查每个用户的数据操作
        for user_id, ops_logs in data_ops_by_user.items():
            
            # 计算导出数据量
            total_export_size = 0
            export_count = 0
            
            for log in ops_logs:
                if log.action == AuditAction.EXPORT and log.details:
                    export_size = log.details.get('export_size_mb', 0)
                    total_export_size += export_size
                    export_count += 1
            
            # 检查是否超过阈值
            if (total_export_size >= rules['export_size_threshold'] or 
                export_count >= rules['export_count_threshold']):
                
                # 创建安全事件
                event = SecurityEvent(
                    event_id=self._generate_event_id(),
                    event_type=SecurityEventType.DATA_EXFILTRATION,
                    threat_level=pattern.threat_level,
                    tenant_id=ops_logs[0].tenant_id,
                    user_id=UUID(user_id) if user_id != 'unknown' else None,
                    ip_address=str(ops_logs[0].ip_address) if ops_logs[0].ip_address else None,
                    timestamp=datetime.utcnow(),
                    description=f"检测到用户 {user_id} 的数据泄露风险，导出 {total_export_size}MB 数据",
                    details={
                        'pattern_id': pattern.pattern_id,
                        'total_export_size_mb': total_export_size,
                        'export_count': export_count,
                        'total_operations': len(ops_logs),
                        'data_types_accessed': list(set(
                            log.resource_type for log in ops_logs
                            if log.resource_type in rules['sensitive_data_types']
                        ))
                    },
                    source_audit_log_id=ops_logs[0].id
                )
                
                events.append(event)
        
        return events
    
    async def _detect_anomalous_behavior(
        self,
        pattern: ThreatPattern,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[SecurityEvent]:
        """检测异常用户行为"""
        
        events = []
        rules = pattern.detection_rules
        
        # 按用户分组操作
        ops_by_user = defaultdict(list)
        for log in audit_logs:
            if log.user_id:
                user_key = str(log.user_id)
                ops_by_user[user_key].append(log)
        
        # 检查每个用户的行为异常
        for user_id, user_logs in ops_by_user.items():
            
            # 获取用户历史行为基线
            baseline = await self._get_user_behavior_baseline(user_id, db)
            
            if not baseline:
                continue  # 没有足够的历史数据
            
            # 计算当前行为指标
            current_metrics = self._calculate_behavior_metrics(user_logs)
            
            # 检测异常
            anomalies = self._detect_behavior_anomalies(
                current_metrics, baseline, rules['deviation_threshold']
            )
            
            if anomalies:
                # 创建安全事件
                event = SecurityEvent(
                    event_id=self._generate_event_id(),
                    event_type=SecurityEventType.ANOMALOUS_BEHAVIOR,
                    threat_level=pattern.threat_level,
                    tenant_id=user_logs[0].tenant_id,
                    user_id=UUID(user_id),
                    ip_address=str(user_logs[0].ip_address) if user_logs[0].ip_address else None,
                    timestamp=datetime.utcnow(),
                    description=f"检测到用户 {user_id} 的异常行为模式",
                    details={
                        'pattern_id': pattern.pattern_id,
                        'anomalies_detected': anomalies,
                        'current_metrics': current_metrics,
                        'baseline_metrics': baseline,
                        'deviation_threshold': rules['deviation_threshold']
                    },
                    source_audit_log_id=user_logs[0].id
                )
                
                events.append(event)
        
        return events
    
    async def _detect_malicious_requests(
        self,
        pattern: ThreatPattern,
        audit_logs: List[AuditLogModel]
    ) -> List[SecurityEvent]:
        """检测恶意请求攻击"""
        
        events = []
        rules = pattern.detection_rules
        
        # 检查每个审计日志中的恶意模式
        malicious_logs = []
        
        for log in audit_logs:
            if log.details:
                details_str = json.dumps(log.details).lower()
                
                # 检查恶意模式
                detected_patterns = []
                for pattern_str in rules['malicious_patterns']:
                    if pattern_str in details_str:
                        detected_patterns.append(pattern_str)
                
                if detected_patterns:
                    malicious_logs.append((log, detected_patterns))
        
        # 按IP分组恶意请求
        malicious_by_ip = defaultdict(list)
        for log, patterns in malicious_logs:
            ip_key = str(log.ip_address) if log.ip_address else 'unknown'
            malicious_by_ip[ip_key].append((log, patterns))
        
        # 检查每个IP的恶意请求数量
        for ip_address, ip_logs in malicious_by_ip.items():
            if len(ip_logs) >= rules['request_threshold']:
                
                all_patterns = set()
                for _, patterns in ip_logs:
                    all_patterns.update(patterns)
                
                # 创建安全事件
                event = SecurityEvent(
                    event_id=self._generate_event_id(),
                    event_type=SecurityEventType.MALICIOUS_REQUEST,
                    threat_level=pattern.threat_level,
                    tenant_id=ip_logs[0][0].tenant_id,
                    user_id=ip_logs[0][0].user_id,
                    ip_address=ip_address if ip_address != 'unknown' else None,
                    timestamp=datetime.utcnow(),
                    description=f"检测到来自IP {ip_address}的恶意请求攻击，{len(ip_logs)}个恶意请求",
                    details={
                        'pattern_id': pattern.pattern_id,
                        'malicious_requests': len(ip_logs),
                        'detected_patterns': list(all_patterns),
                        'attack_types': self._classify_attack_types(all_patterns)
                    },
                    source_audit_log_id=ip_logs[0][0].id
                )
                
                events.append(event)
        
        return events
    
    async def _handle_security_event(self, event: SecurityEvent, db: Session):
        """处理安全事件"""
        
        # 存储事件
        self.active_events[event.event_id] = event
        
        # 更新Prometheus指标
        self.security_metrics['security_events_total'].labels(
            event_type=event.event_type.value,
            threat_level=event.threat_level.value,
            tenant_id=event.tenant_id
        ).inc()
        
        self.security_metrics['threat_detections_total'].labels(
            pattern_id=event.details.get('pattern_id', 'unknown'),
            threat_level=event.threat_level.value,
            tenant_id=event.tenant_id
        ).inc()
        
        # 记录到审计日志
        await self._log_security_event_to_audit(event, db)
        
        # 触发告警
        await self._trigger_security_alert(event)
        
        # 自动响应
        pattern = self.threat_patterns.get(event.details.get('pattern_id'))
        if pattern and pattern.auto_response:
            await self._execute_auto_response(event, pattern)
        
        self.logger.warning(f"Security event detected: {event.description}")
    
    async def _log_security_event_to_audit(self, event: SecurityEvent, db: Session):
        """将安全事件记录到审计日志"""
        
        try:
            audit_log = AuditLogModel(
                user_id=event.user_id,
                tenant_id=event.tenant_id,
                action=AuditAction.CREATE,
                resource_type="security_event",
                resource_id=event.event_id,
                ip_address=event.ip_address,
                details={
                    "event_type": event.event_type.value,
                    "threat_level": event.threat_level.value,
                    "description": event.description,
                    "event_details": event.details,
                    "source_audit_log_id": event.source_audit_log_id
                }
            )
            
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to log security event to audit: {e}")
            db.rollback()
    
    async def _trigger_security_alert(self, event: SecurityEvent):
        """触发安全告警"""
        
        alert_data = {
            "alert_type": "security_event",
            "severity": event.threat_level.value,
            "tenant_id": event.tenant_id,
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "description": event.description,
            "timestamp": event.timestamp.isoformat(),
            "details": event.details
        }
        
        # 更新告警指标
        self.security_metrics['security_alerts_total'].labels(
            alert_type=event.event_type.value,
            severity=event.threat_level.value,
            tenant_id=event.tenant_id
        ).inc()
        
        # 发送到实时告警系统
        try:
            from src.security.real_time_alert_system import send_security_alert
            await send_security_alert(event)
        except Exception as e:
            self.logger.error(f"Failed to send real-time alert: {e}")
        
        # 记录到日志
        self.logger.critical(f"SECURITY ALERT: {alert_data}")
    
    async def _execute_auto_response(self, event: SecurityEvent, pattern: ThreatPattern):
        """执行自动响应"""
        
        for action in pattern.response_actions:
            try:
                if action == 'block_ip' and event.ip_address:
                    await self._block_ip_address(event.ip_address, event.tenant_id)
                elif action == 'suspend_user' and event.user_id:
                    await self._suspend_user(event.user_id, event.tenant_id)
                elif action == 'notify_admin':
                    await self._notify_administrators(event)
                elif action == 'increase_monitoring':
                    await self._increase_monitoring_level(event.tenant_id)
                
                self.logger.info(f"Auto-response action executed: {action} for event {event.event_id}")
                
            except Exception as e:
                self.logger.error(f"Auto-response action failed ({action}): {e}")
    
    async def _update_security_metrics(self):
        """更新安全指标"""
        
        # 按威胁等级统计活跃事件
        threat_level_counts = defaultdict(int)
        tenant_counts = defaultdict(lambda: defaultdict(int))
        
        for event in self.active_events.values():
            threat_level_counts[event.threat_level.value] += 1
            tenant_counts[event.tenant_id][event.threat_level.value] += 1
        
        # 更新Prometheus指标
        for tenant_id, tenant_threats in tenant_counts.items():
            for threat_level, count in tenant_threats.items():
                self.security_metrics['active_security_events'].labels(
                    threat_level=threat_level,
                    tenant_id=tenant_id
                ).set(count)
            
            # 计算安全评分
            security_score = self._calculate_security_score(tenant_threats)
            self.security_metrics['security_score'].labels(
                tenant_id=tenant_id
            ).set(security_score)
    
    def _calculate_security_score(self, threat_counts: Dict[str, int]) -> float:
        """计算安全评分（0-100）"""
        
        # 威胁等级权重
        weights = {
            ThreatLevel.INFO.value: 0,
            ThreatLevel.LOW.value: 1,
            ThreatLevel.MEDIUM.value: 3,
            ThreatLevel.HIGH.value: 7,
            ThreatLevel.CRITICAL.value: 15
        }
        
        # 计算威胁分数
        threat_score = sum(
            threat_counts.get(level, 0) * weight
            for level, weight in weights.items()
        )
        
        # 转换为安全评分（分数越高，安全性越低）
        max_score = 100
        security_score = max(0, max_score - threat_score)
        
        return security_score
    
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_suffix = hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:8]
        return f"SEC_{timestamp}_{random_suffix}"
    
    # 辅助方法
    
    async def _get_user_behavior_baseline(self, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """获取用户行为基线"""
        # 这里应该从历史数据计算基线，简化实现
        return self.behavior_baselines.get(user_id)
    
    def _calculate_behavior_metrics(self, logs: List[AuditLogModel]) -> Dict[str, Any]:
        """计算行为指标"""
        
        if not logs:
            return {}
        
        # 操作频率
        action_counts = Counter(log.action.value for log in logs)
        
        # 资源访问模式
        resource_counts = Counter(log.resource_type for log in logs)
        
        # 时间模式
        hour_counts = Counter(log.timestamp.hour for log in logs)
        
        return {
            'action_frequency': dict(action_counts),
            'resource_access': dict(resource_counts),
            'time_patterns': dict(hour_counts),
            'total_operations': len(logs)
        }
    
    def _detect_behavior_anomalies(
        self,
        current_metrics: Dict[str, Any],
        baseline: Dict[str, Any],
        threshold: float
    ) -> List[str]:
        """检测行为异常"""
        
        anomalies = []
        
        # 简化的异常检测逻辑
        current_total = current_metrics.get('total_operations', 0)
        baseline_total = baseline.get('total_operations', 0)
        
        if baseline_total > 0:
            deviation = abs(current_total - baseline_total) / baseline_total
            if deviation > threshold:
                anomalies.append(f"operation_frequency_anomaly_{deviation:.2f}")
        
        return anomalies
    
    def _classify_attack_types(self, patterns: List[str]) -> List[str]:
        """分类攻击类型"""
        
        attack_types = []
        
        sql_patterns = ['union select', 'drop table', 'insert into', 'update set']
        xss_patterns = ['<script>', 'javascript:', 'onload=', 'onerror=']
        path_patterns = ['../../../', '..\\..\\..\\', '/etc/passwd']
        
        if any(p in patterns for p in sql_patterns):
            attack_types.append('sql_injection')
        if any(p in patterns for p in xss_patterns):
            attack_types.append('xss')
        if any(p in patterns for p in path_patterns):
            attack_types.append('path_traversal')
        
        return attack_types
    
    # 自动响应方法（简化实现）
    
    async def _block_ip_address(self, ip_address: str, tenant_id: str):
        """封禁IP地址"""
        self.logger.warning(f"Auto-response: Blocking IP {ip_address} for tenant {tenant_id}")
    
    async def _suspend_user(self, user_id: UUID, tenant_id: str):
        """暂停用户账户"""
        self.logger.warning(f"Auto-response: Suspending user {user_id} for tenant {tenant_id}")
    
    async def _notify_administrators(self, event: SecurityEvent):
        """通知管理员"""
        self.logger.warning(f"Auto-response: Notifying administrators about event {event.event_id}")
    
    async def _increase_monitoring_level(self, tenant_id: str):
        """提高监控级别"""
        self.logger.info(f"Auto-response: Increasing monitoring level for tenant {tenant_id}")
    
    # 清理方法
    
    async def _cleanup_expired_events(self):
        """清理过期事件"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=24)  # 24小时后清理
        
        expired_events = [
            event_id for event_id, event in self.active_events.items()
            if event.timestamp < cutoff_time
        ]
        
        for event_id in expired_events:
            event = self.active_events.pop(event_id)
            self.resolved_events.append(event)
        
        # 限制已解决事件的数量
        if len(self.resolved_events) > 1000:
            self.resolved_events = self.resolved_events[-1000:]
    
    async def _process_security_alerts(self):
        """处理安全告警"""
        
        # 检查是否有需要升级的告警
        critical_events = [
            event for event in self.active_events.values()
            if event.threat_level == ThreatLevel.CRITICAL and not event.resolved
        ]
        
        if len(critical_events) > 5:  # 超过5个关键事件
            await self._escalate_security_incident(critical_events)
    
    async def _escalate_security_incident(self, events: List[SecurityEvent]):
        """升级安全事件"""
        
        incident_data = {
            "incident_type": "multiple_critical_threats",
            "severity": "critical",
            "event_count": len(events),
            "affected_tenants": list(set(event.tenant_id for event in events)),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.critical(f"SECURITY INCIDENT ESCALATED: {incident_data}")
    
    # 公共接口方法
    
    def get_active_events(self, tenant_id: Optional[str] = None) -> List[SecurityEvent]:
        """获取活跃的安全事件"""
        
        events = list(self.active_events.values())
        
        if tenant_id:
            events = [event for event in events if event.tenant_id == tenant_id]
        
        return sorted(events, key=lambda x: x.timestamp, reverse=True)
    
    def get_security_summary(self, tenant_id: str) -> Dict[str, Any]:
        """获取安全摘要"""
        
        tenant_events = [
            event for event in self.active_events.values()
            if event.tenant_id == tenant_id
        ]
        
        threat_counts = Counter(event.threat_level.value for event in tenant_events)
        event_type_counts = Counter(event.event_type.value for event in tenant_events)
        
        return {
            "tenant_id": tenant_id,
            "active_events_count": len(tenant_events),
            "threat_level_distribution": dict(threat_counts),
            "event_type_distribution": dict(event_type_counts),
            "security_score": self._calculate_security_score(threat_counts),
            "last_scan_time": self.last_scan_time.isoformat(),
            "monitoring_status": "active" if self.monitoring_enabled else "inactive"
        }
    
    def resolve_event(self, event_id: str, resolution_notes: str) -> bool:
        """解决安全事件"""
        
        if event_id in self.active_events:
            event = self.active_events.pop(event_id)
            event.resolved = True
            event.resolution_notes = resolution_notes
            self.resolved_events.append(event)
            
            self.logger.info(f"Security event resolved: {event_id}")
            return True
        
        return False


# 全局安全事件监控器实例
security_event_monitor = SecurityEventMonitor()


# 便捷函数
async def start_security_monitoring(config: Optional[PrometheusConfig] = None):
    """启动安全事件监控"""
    global security_event_monitor
    if config:
        security_event_monitor = SecurityEventMonitor(config)
    
    await security_event_monitor.start_monitoring()


async def stop_security_monitoring():
    """停止安全事件监控"""
    await security_event_monitor.stop_monitoring()


def get_security_monitor() -> SecurityEventMonitor:
    """获取安全监控器实例"""
    return security_event_monitor