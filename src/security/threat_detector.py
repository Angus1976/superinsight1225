"""
Advanced Threat Detection Engine for SuperInsight Platform.

Provides machine learning-based threat detection, behavioral analysis,
and intelligent security pattern recognition.
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter, deque
import statistics
import hashlib
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, select

from src.security.models import AuditLogModel, AuditAction
from src.security.security_event_monitor import SecurityEvent, SecurityEventType, ThreatLevel
from src.database.connection import get_db_session


class ThreatCategory(Enum):
    """威胁分类"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    SYSTEM_INTEGRITY = "system_integrity"
    NETWORK_SECURITY = "network_security"
    APPLICATION_SECURITY = "application_security"


class DetectionMethod(Enum):
    """检测方法"""
    RULE_BASED = "rule_based"
    STATISTICAL = "statistical"
    BEHAVIORAL = "behavioral"
    MACHINE_LEARNING = "machine_learning"
    HYBRID = "hybrid"


@dataclass
class ThreatSignature:
    """威胁签名"""
    signature_id: str
    name: str
    category: ThreatCategory
    detection_method: DetectionMethod
    confidence_threshold: float
    patterns: List[str] = field(default_factory=list)
    statistical_rules: Dict[str, Any] = field(default_factory=dict)
    behavioral_indicators: List[str] = field(default_factory=list)
    severity_weight: float = 1.0


@dataclass
class BehaviorProfile:
    """用户行为画像"""
    user_id: str
    tenant_id: str
    profile_created: datetime
    last_updated: datetime
    
    # 行为统计
    action_patterns: Dict[str, float] = field(default_factory=dict)
    resource_access_patterns: Dict[str, float] = field(default_factory=dict)
    time_patterns: Dict[int, float] = field(default_factory=dict)  # 按小时统计
    ip_patterns: Dict[str, float] = field(default_factory=dict)
    
    # 统计指标
    avg_session_duration: float = 0.0
    avg_actions_per_session: float = 0.0
    peak_activity_hours: List[int] = field(default_factory=list)
    
    # 异常检测基线
    action_frequency_baseline: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # (mean, std)
    access_volume_baseline: Tuple[float, float] = (0.0, 0.0)
    
    # 风险指标
    risk_score: float = 0.0
    anomaly_count: int = 0
    last_anomaly_time: Optional[datetime] = None


class AdvancedThreatDetector:
    """
    高级威胁检测引擎
    
    功能：
    - 基于规则的威胁检测
    - 统计异常检测
    - 行为分析和画像
    - 机器学习威胁识别
    - 威胁情报集成
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 威胁签名库
        self.threat_signatures = self._initialize_threat_signatures()
        
        # 用户行为画像
        self.behavior_profiles: Dict[str, BehaviorProfile] = {}
        
        # 检测缓存
        self.detection_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        # 统计数据
        self.detection_stats = {
            'total_detections': 0,
            'false_positives': 0,
            'confirmed_threats': 0,
            'detection_accuracy': 0.0
        }
        
        # 威胁情报
        self.threat_intelligence = {
            'malicious_ips': set(),
            'suspicious_patterns': [],
            'known_attack_signatures': []
        }
        
        # 实时监控队列
        self.event_queue = deque(maxlen=10000)
        
        self.logger.info("Advanced Threat Detector initialized")
    
    def _initialize_threat_signatures(self) -> Dict[str, ThreatSignature]:
        """初始化威胁签名库"""
        
        signatures = {}
        
        # SQL注入检测签名
        signatures['sql_injection'] = ThreatSignature(
            signature_id='sql_injection',
            name='SQL注入攻击',
            category=ThreatCategory.APPLICATION_SECURITY,
            detection_method=DetectionMethod.RULE_BASED,
            confidence_threshold=0.8,
            patterns=[
                r"union\s+select", r"drop\s+table", r"insert\s+into",
                r"update\s+set", r"delete\s+from", r"exec\s*\(",
                r"sp_executesql", r"xp_cmdshell", r"--\s*$",
                r"\/\*.*\*\/", r";\s*--", r"'\s*or\s*'1'\s*=\s*'1"
            ],
            severity_weight=2.0
        )
        
        # XSS攻击检测签名
        signatures['xss_attack'] = ThreatSignature(
            signature_id='xss_attack',
            name='跨站脚本攻击',
            category=ThreatCategory.APPLICATION_SECURITY,
            detection_method=DetectionMethod.RULE_BASED,
            confidence_threshold=0.7,
            patterns=[
                r"<script[^>]*>", r"javascript:", r"onload\s*=",
                r"onerror\s*=", r"onclick\s*=", r"onmouseover\s*=",
                r"eval\s*\(", r"document\.cookie", r"window\.location"
            ],
            severity_weight=1.5
        )
        
        # 路径遍历攻击签名
        signatures['path_traversal'] = ThreatSignature(
            signature_id='path_traversal',
            name='路径遍历攻击',
            category=ThreatCategory.APPLICATION_SECURITY,
            detection_method=DetectionMethod.RULE_BASED,
            confidence_threshold=0.9,
            patterns=[
                r"\.\.\/", r"\.\.\\", r"\/etc\/passwd", r"\/etc\/shadow",
                r"\/windows\/system32", r"cmd\.exe", r"powershell\.exe"
            ],
            severity_weight=1.8
        )
        
        # 暴力破解攻击签名
        signatures['brute_force'] = ThreatSignature(
            signature_id='brute_force',
            name='暴力破解攻击',
            category=ThreatCategory.AUTHENTICATION,
            detection_method=DetectionMethod.STATISTICAL,
            confidence_threshold=0.85,
            statistical_rules={
                'max_failures_per_minute': 10,
                'max_failures_per_hour': 50,
                'unique_usernames_threshold': 5,
                'time_window_seconds': 300
            },
            severity_weight=1.7
        )
        
        # 权限提升攻击签名
        signatures['privilege_escalation'] = ThreatSignature(
            signature_id='privilege_escalation',
            name='权限提升攻击',
            category=ThreatCategory.AUTHORIZATION,
            detection_method=DetectionMethod.BEHAVIORAL,
            confidence_threshold=0.75,
            behavioral_indicators=[
                'rapid_permission_changes',
                'unusual_admin_access',
                'cross_tenant_access_attempt',
                'system_resource_modification'
            ],
            severity_weight=2.5
        )
        
        # 数据泄露签名
        signatures['data_exfiltration'] = ThreatSignature(
            signature_id='data_exfiltration',
            name='数据泄露攻击',
            category=ThreatCategory.DATA_ACCESS,
            detection_method=DetectionMethod.HYBRID,
            confidence_threshold=0.8,
            statistical_rules={
                'max_export_size_mb': 1000,
                'max_exports_per_hour': 20,
                'unusual_export_time_threshold': 0.1  # 10%的用户在此时间导出
            },
            behavioral_indicators=[
                'bulk_data_access',
                'unusual_export_patterns',
                'after_hours_activity'
            ],
            severity_weight=3.0
        )
        
        # 异常行为签名
        signatures['anomalous_behavior'] = ThreatSignature(
            signature_id='anomalous_behavior',
            name='异常用户行为',
            category=ThreatCategory.SYSTEM_INTEGRITY,
            detection_method=DetectionMethod.MACHINE_LEARNING,
            confidence_threshold=0.6,
            behavioral_indicators=[
                'unusual_access_patterns',
                'geographic_anomaly',
                'device_fingerprint_change',
                'activity_time_anomaly'
            ],
            severity_weight=1.2
        )
        
        return signatures
    
    async def detect_threats(
        self,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[Tuple[SecurityEvent, float]]:
        """
        执行威胁检测
        
        Returns:
            List of (SecurityEvent, confidence_score) tuples
        """
        
        detected_threats = []
        
        # 更新行为画像
        await self._update_behavior_profiles(audit_logs, db)
        
        # 执行各种检测方法
        for signature_id, signature in self.threat_signatures.items():
            
            if signature.detection_method == DetectionMethod.RULE_BASED:
                threats = await self._rule_based_detection(signature, audit_logs)
            elif signature.detection_method == DetectionMethod.STATISTICAL:
                threats = await self._statistical_detection(signature, audit_logs, db)
            elif signature.detection_method == DetectionMethod.BEHAVIORAL:
                threats = await self._behavioral_detection(signature, audit_logs, db)
            elif signature.detection_method == DetectionMethod.MACHINE_LEARNING:
                threats = await self._ml_based_detection(signature, audit_logs, db)
            elif signature.detection_method == DetectionMethod.HYBRID:
                threats = await self._hybrid_detection(signature, audit_logs, db)
            else:
                continue
            
            detected_threats.extend(threats)
        
        # 去重和排序
        detected_threats = self._deduplicate_and_rank_threats(detected_threats)
        
        # 更新统计信息
        self.detection_stats['total_detections'] += len(detected_threats)
        
        return detected_threats
    
    async def _rule_based_detection(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel]
    ) -> List[Tuple[SecurityEvent, float]]:
        """基于规则的威胁检测"""
        
        threats = []
        
        for log in audit_logs:
            if not log.details:
                continue
            
            # 将审计日志详情转换为字符串进行模式匹配
            log_content = json.dumps(log.details).lower()
            if log.user_agent:
                log_content += " " + log.user_agent.lower()
            
            # 检查每个模式
            matched_patterns = []
            for pattern in signature.patterns:
                import re
                if re.search(pattern, log_content, re.IGNORECASE):
                    matched_patterns.append(pattern)
            
            if matched_patterns:
                # 计算置信度
                confidence = min(
                    len(matched_patterns) / len(signature.patterns) * signature.severity_weight,
                    1.0
                )
                
                if confidence >= signature.confidence_threshold:
                    # 创建安全事件
                    event = SecurityEvent(
                        event_id=self._generate_event_id(signature.signature_id),
                        event_type=self._map_category_to_event_type(signature.category),
                        threat_level=self._calculate_threat_level(confidence),
                        tenant_id=log.tenant_id,
                        user_id=log.user_id,
                        ip_address=str(log.ip_address) if log.ip_address else None,
                        timestamp=datetime.utcnow(),
                        description=f"检测到{signature.name}：匹配{len(matched_patterns)}个威胁模式",
                        details={
                            'signature_id': signature.signature_id,
                            'detection_method': signature.detection_method.value,
                            'matched_patterns': matched_patterns,
                            'confidence_score': confidence,
                            'log_content_sample': log_content[:200]
                        },
                        source_audit_log_id=log.id
                    )
                    
                    threats.append((event, confidence))
        
        return threats
    
    async def _statistical_detection(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[Tuple[SecurityEvent, float]]:
        """基于统计的威胁检测"""
        
        threats = []
        rules = signature.statistical_rules
        
        if signature.signature_id == 'brute_force':
            threats.extend(await self._detect_brute_force_statistical(signature, audit_logs, rules))
        
        return threats
    
    async def _detect_brute_force_statistical(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel],
        rules: Dict[str, Any]
    ) -> List[Tuple[SecurityEvent, float]]:
        """统计方法检测暴力破解"""
        
        threats = []
        
        # 按IP分组失败登录
        failed_logins_by_ip = defaultdict(list)
        
        for log in audit_logs:
            if (log.action == AuditAction.LOGIN and 
                log.details and 
                log.details.get('status') in ['failed', 'invalid', 'blocked']):
                
                ip_key = str(log.ip_address) if log.ip_address else 'unknown'
                failed_logins_by_ip[ip_key].append(log)
        
        # 分析每个IP的失败模式
        for ip_address, failed_logs in failed_logins_by_ip.items():
            
            # 时间窗口内的失败次数
            recent_failures = [
                log for log in failed_logs
                if (datetime.utcnow() - log.timestamp).total_seconds() <= rules['time_window_seconds']
            ]
            
            if len(recent_failures) >= rules['max_failures_per_minute']:
                
                # 计算统计指标
                unique_usernames = len(set(
                    log.details.get('username', 'unknown') 
                    for log in recent_failures if log.details
                ))
                
                failure_rate = len(recent_failures) / (rules['time_window_seconds'] / 60)
                
                # 计算置信度
                confidence = min(
                    (len(recent_failures) / rules['max_failures_per_hour']) * 
                    (unique_usernames / rules['unique_usernames_threshold']) *
                    signature.severity_weight,
                    1.0
                )
                
                if confidence >= signature.confidence_threshold:
                    
                    event = SecurityEvent(
                        event_id=self._generate_event_id(signature.signature_id),
                        event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                        threat_level=self._calculate_threat_level(confidence),
                        tenant_id=recent_failures[0].tenant_id,
                        user_id=None,
                        ip_address=ip_address if ip_address != 'unknown' else None,
                        timestamp=datetime.utcnow(),
                        description=f"统计检测到暴力破解攻击：{len(recent_failures)}次失败登录",
                        details={
                            'signature_id': signature.signature_id,
                            'detection_method': signature.detection_method.value,
                            'failure_count': len(recent_failures),
                            'unique_usernames': unique_usernames,
                            'failure_rate_per_minute': failure_rate,
                            'confidence_score': confidence,
                            'time_window_seconds': rules['time_window_seconds']
                        },
                        source_audit_log_id=recent_failures[0].id
                    )
                    
                    threats.append((event, confidence))
        
        return threats
    
    async def _behavioral_detection(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[Tuple[SecurityEvent, float]]:
        """基于行为的威胁检测"""
        
        threats = []
        
        if signature.signature_id == 'privilege_escalation':
            threats.extend(await self._detect_privilege_escalation_behavioral(signature, audit_logs, db))
        
        return threats
    
    async def _detect_privilege_escalation_behavioral(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[Tuple[SecurityEvent, float]]:
        """行为分析检测权限提升"""
        
        threats = []
        
        # 按用户分组权限相关操作
        privilege_ops_by_user = defaultdict(list)
        
        for log in audit_logs:
            if (log.action in [AuditAction.UPDATE, AuditAction.CREATE] and
                log.resource_type in ['user', 'role', 'permission', 'tenant']):
                
                user_key = str(log.user_id) if log.user_id else 'unknown'
                privilege_ops_by_user[user_key].append(log)
        
        # 分析每个用户的权限操作行为
        for user_id, ops_logs in privilege_ops_by_user.items():
            
            if user_id == 'unknown' or len(ops_logs) < 2:
                continue
            
            # 获取用户行为画像
            profile = self.behavior_profiles.get(user_id)
            if not profile:
                continue
            
            # 分析行为异常
            behavioral_anomalies = []
            
            # 检查操作频率异常
            current_ops_count = len(ops_logs)
            baseline_ops = profile.action_frequency_baseline.get('privilege_ops', (0, 1))
            
            if baseline_ops[1] > 0:  # 有历史数据
                z_score = abs(current_ops_count - baseline_ops[0]) / baseline_ops[1]
                if z_score > 3.0:  # 3个标准差
                    behavioral_anomalies.append('rapid_permission_changes')
            
            # 检查跨租户访问
            tenant_ids = set(log.tenant_id for log in ops_logs)
            if len(tenant_ids) > 1:
                behavioral_anomalies.append('cross_tenant_access_attempt')
            
            # 检查系统资源修改
            system_resources = ['user', 'role', 'permission']
            if any(log.resource_type in system_resources for log in ops_logs):
                behavioral_anomalies.append('system_resource_modification')
            
            # 检查异常管理员访问
            admin_indicators = ['admin', 'root', 'superuser', 'system']
            for log in ops_logs:
                if log.details:
                    details_str = json.dumps(log.details).lower()
                    if any(indicator in details_str for indicator in admin_indicators):
                        behavioral_anomalies.append('unusual_admin_access')
                        break
            
            # 计算置信度
            matched_indicators = [
                indicator for indicator in signature.behavioral_indicators
                if indicator in behavioral_anomalies
            ]
            
            if matched_indicators:
                confidence = min(
                    len(matched_indicators) / len(signature.behavioral_indicators) * 
                    signature.severity_weight,
                    1.0
                )
                
                if confidence >= signature.confidence_threshold:
                    
                    event = SecurityEvent(
                        event_id=self._generate_event_id(signature.signature_id),
                        event_type=SecurityEventType.PRIVILEGE_ESCALATION,
                        threat_level=self._calculate_threat_level(confidence),
                        tenant_id=ops_logs[0].tenant_id,
                        user_id=UUID(user_id),
                        ip_address=str(ops_logs[0].ip_address) if ops_logs[0].ip_address else None,
                        timestamp=datetime.utcnow(),
                        description=f"行为分析检测到权限提升攻击：{len(matched_indicators)}个异常行为",
                        details={
                            'signature_id': signature.signature_id,
                            'detection_method': signature.detection_method.value,
                            'behavioral_anomalies': behavioral_anomalies,
                            'matched_indicators': matched_indicators,
                            'confidence_score': confidence,
                            'operations_count': current_ops_count,
                            'affected_resources': list(set(log.resource_type for log in ops_logs))
                        },
                        source_audit_log_id=ops_logs[0].id
                    )
                    
                    threats.append((event, confidence))
        
        return threats
    
    async def _ml_based_detection(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[Tuple[SecurityEvent, float]]:
        """基于机器学习的威胁检测"""
        
        threats = []
        
        if signature.signature_id == 'anomalous_behavior':
            threats.extend(await self._detect_anomalous_behavior_ml(signature, audit_logs, db))
        
        return threats
    
    async def _detect_anomalous_behavior_ml(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[Tuple[SecurityEvent, float]]:
        """机器学习检测异常行为"""
        
        threats = []
        
        # 按用户分组
        logs_by_user = defaultdict(list)
        for log in audit_logs:
            if log.user_id:
                user_key = str(log.user_id)
                logs_by_user[user_key].append(log)
        
        # 对每个用户进行异常检测
        for user_id, user_logs in logs_by_user.items():
            
            profile = self.behavior_profiles.get(user_id)
            if not profile or len(user_logs) < 5:  # 需要足够的数据
                continue
            
            # 提取特征
            features = self._extract_behavioral_features(user_logs, profile)
            
            # 简化的异常检测（在实际应用中会使用更复杂的ML模型）
            anomaly_score = self._calculate_anomaly_score(features, profile)
            
            if anomaly_score > 0.7:  # 异常阈值
                
                # 识别具体的异常指标
                anomaly_indicators = self._identify_anomaly_indicators(features, profile)
                
                confidence = min(anomaly_score * signature.severity_weight, 1.0)
                
                if confidence >= signature.confidence_threshold:
                    
                    event = SecurityEvent(
                        event_id=self._generate_event_id(signature.signature_id),
                        event_type=SecurityEventType.ANOMALOUS_BEHAVIOR,
                        threat_level=self._calculate_threat_level(confidence),
                        tenant_id=user_logs[0].tenant_id,
                        user_id=UUID(user_id),
                        ip_address=str(user_logs[0].ip_address) if user_logs[0].ip_address else None,
                        timestamp=datetime.utcnow(),
                        description=f"机器学习检测到异常用户行为：异常评分{anomaly_score:.2f}",
                        details={
                            'signature_id': signature.signature_id,
                            'detection_method': signature.detection_method.value,
                            'anomaly_score': anomaly_score,
                            'anomaly_indicators': anomaly_indicators,
                            'confidence_score': confidence,
                            'behavioral_features': features,
                            'baseline_comparison': self._compare_with_baseline(features, profile)
                        },
                        source_audit_log_id=user_logs[0].id
                    )
                    
                    threats.append((event, confidence))
        
        return threats
    
    async def _hybrid_detection(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[Tuple[SecurityEvent, float]]:
        """混合检测方法"""
        
        threats = []
        
        if signature.signature_id == 'data_exfiltration':
            threats.extend(await self._detect_data_exfiltration_hybrid(signature, audit_logs, db))
        
        return threats
    
    async def _detect_data_exfiltration_hybrid(
        self,
        signature: ThreatSignature,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> List[Tuple[SecurityEvent, float]]:
        """混合方法检测数据泄露"""
        
        threats = []
        
        # 统计检测部分
        export_logs = [log for log in audit_logs if log.action == AuditAction.EXPORT]
        
        if not export_logs:
            return threats
        
        # 按用户分组导出操作
        exports_by_user = defaultdict(list)
        for log in export_logs:
            if log.user_id:
                user_key = str(log.user_id)
                exports_by_user[user_key].append(log)
        
        rules = signature.statistical_rules
        
        for user_id, user_exports in exports_by_user.items():
            
            # 统计分析
            total_size = sum(
                log.details.get('export_size_mb', 0) 
                for log in user_exports if log.details
            )
            export_count = len(user_exports)
            
            statistical_score = 0.0
            if total_size >= rules['max_export_size_mb']:
                statistical_score += 0.4
            if export_count >= rules['max_exports_per_hour']:
                statistical_score += 0.3
            
            # 行为分析
            profile = self.behavior_profiles.get(user_id)
            behavioral_score = 0.0
            
            if profile:
                # 检查导出时间异常
                export_hours = [log.timestamp.hour for log in user_exports]
                unusual_hours = [
                    hour for hour in export_hours 
                    if hour not in profile.peak_activity_hours
                ]
                
                if len(unusual_hours) / len(export_hours) > 0.5:  # 超过50%在异常时间
                    behavioral_score += 0.2
                
                # 检查批量访问模式
                if export_count > profile.avg_actions_per_session * 3:
                    behavioral_score += 0.2
            
            # 综合评分
            combined_score = (statistical_score + behavioral_score) * signature.severity_weight
            
            if combined_score >= signature.confidence_threshold:
                
                # 识别具体的异常指标
                anomaly_indicators = []
                if total_size >= rules['max_export_size_mb']:
                    anomaly_indicators.append('bulk_data_access')
                if export_count >= rules['max_exports_per_hour']:
                    anomaly_indicators.append('unusual_export_patterns')
                if behavioral_score > 0:
                    anomaly_indicators.append('after_hours_activity')
                
                event = SecurityEvent(
                    event_id=self._generate_event_id(signature.signature_id),
                    event_type=SecurityEventType.DATA_EXFILTRATION,
                    threat_level=self._calculate_threat_level(combined_score),
                    tenant_id=user_exports[0].tenant_id,
                    user_id=UUID(user_id),
                    ip_address=str(user_exports[0].ip_address) if user_exports[0].ip_address else None,
                    timestamp=datetime.utcnow(),
                    description=f"混合检测到数据泄露风险：导出{total_size}MB数据，{export_count}次操作",
                    details={
                        'signature_id': signature.signature_id,
                        'detection_method': signature.detection_method.value,
                        'statistical_score': statistical_score,
                        'behavioral_score': behavioral_score,
                        'combined_score': combined_score,
                        'total_export_size_mb': total_size,
                        'export_count': export_count,
                        'anomaly_indicators': anomaly_indicators,
                        'confidence_score': combined_score
                    },
                    source_audit_log_id=user_exports[0].id
                )
                
                threats.append((event, combined_score))
        
        return threats
    
    async def _update_behavior_profiles(self, audit_logs: List[AuditLogModel], db: Session):
        """更新用户行为画像"""
        
        # 按用户分组
        logs_by_user = defaultdict(list)
        for log in audit_logs:
            if log.user_id:
                user_key = str(log.user_id)
                logs_by_user[user_key].append(log)
        
        # 更新每个用户的画像
        for user_id, user_logs in logs_by_user.items():
            
            if user_id not in self.behavior_profiles:
                # 创建新的行为画像
                self.behavior_profiles[user_id] = BehaviorProfile(
                    user_id=user_id,
                    tenant_id=user_logs[0].tenant_id,
                    profile_created=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
            
            profile = self.behavior_profiles[user_id]
            
            # 更新行为模式
            self._update_action_patterns(profile, user_logs)
            self._update_resource_patterns(profile, user_logs)
            self._update_time_patterns(profile, user_logs)
            self._update_ip_patterns(profile, user_logs)
            
            # 更新统计基线
            await self._update_statistical_baseline(profile, user_id, db)
            
            profile.last_updated = datetime.utcnow()
    
    def _update_action_patterns(self, profile: BehaviorProfile, logs: List[AuditLogModel]):
        """更新操作模式"""
        
        action_counts = Counter(log.action.value for log in logs)
        total_actions = len(logs)
        
        for action, count in action_counts.items():
            frequency = count / total_actions
            
            # 使用指数移动平均更新
            alpha = 0.3  # 学习率
            if action in profile.action_patterns:
                profile.action_patterns[action] = (
                    alpha * frequency + (1 - alpha) * profile.action_patterns[action]
                )
            else:
                profile.action_patterns[action] = frequency
    
    def _update_resource_patterns(self, profile: BehaviorProfile, logs: List[AuditLogModel]):
        """更新资源访问模式"""
        
        resource_counts = Counter(log.resource_type for log in logs)
        total_accesses = len(logs)
        
        for resource, count in resource_counts.items():
            frequency = count / total_accesses
            
            alpha = 0.3
            if resource in profile.resource_access_patterns:
                profile.resource_access_patterns[resource] = (
                    alpha * frequency + (1 - alpha) * profile.resource_access_patterns[resource]
                )
            else:
                profile.resource_access_patterns[resource] = frequency
    
    def _update_time_patterns(self, profile: BehaviorProfile, logs: List[AuditLogModel]):
        """更新时间模式"""
        
        hour_counts = Counter(log.timestamp.hour for log in logs)
        total_actions = len(logs)
        
        for hour, count in hour_counts.items():
            frequency = count / total_actions
            
            alpha = 0.3
            if hour in profile.time_patterns:
                profile.time_patterns[hour] = (
                    alpha * frequency + (1 - alpha) * profile.time_patterns[hour]
                )
            else:
                profile.time_patterns[hour] = frequency
        
        # 更新峰值活动时间
        if profile.time_patterns:
            sorted_hours = sorted(
                profile.time_patterns.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            profile.peak_activity_hours = [hour for hour, _ in sorted_hours[:6]]  # 前6个小时
    
    def _update_ip_patterns(self, profile: BehaviorProfile, logs: List[AuditLogModel]):
        """更新IP模式"""
        
        ip_counts = Counter(
            str(log.ip_address) for log in logs 
            if log.ip_address
        )
        total_accesses = len([log for log in logs if log.ip_address])
        
        if total_accesses == 0:
            return
        
        for ip, count in ip_counts.items():
            frequency = count / total_accesses
            
            alpha = 0.3
            if ip in profile.ip_patterns:
                profile.ip_patterns[ip] = (
                    alpha * frequency + (1 - alpha) * profile.ip_patterns[ip]
                )
            else:
                profile.ip_patterns[ip] = frequency
    
    async def _update_statistical_baseline(self, profile: BehaviorProfile, user_id: str, db: Session):
        """更新统计基线"""
        
        # 获取历史数据（过去30天）
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.user_id == UUID(user_id),
                AuditLogModel.timestamp >= thirty_days_ago
            )
        )
        
        historical_logs = db.execute(stmt).scalars().all()
        
        if len(historical_logs) < 10:  # 需要足够的历史数据
            return
        
        # 按天分组计算统计基线
        daily_actions = defaultdict(int)
        daily_exports = defaultdict(float)
        
        for log in historical_logs:
            date_key = log.timestamp.date()
            daily_actions[date_key] += 1
            
            if log.action == AuditAction.EXPORT and log.details:
                daily_exports[date_key] += log.details.get('export_size_mb', 0)
        
        # 计算基线统计
        if daily_actions:
            action_counts = list(daily_actions.values())
            profile.action_frequency_baseline['total_actions'] = (
                statistics.mean(action_counts),
                statistics.stdev(action_counts) if len(action_counts) > 1 else 0
            )
        
        if daily_exports:
            export_sizes = list(daily_exports.values())
            profile.access_volume_baseline = (
                statistics.mean(export_sizes),
                statistics.stdev(export_sizes) if len(export_sizes) > 1 else 0
            )
    
    def _extract_behavioral_features(self, logs: List[AuditLogModel], profile: BehaviorProfile) -> Dict[str, float]:
        """提取行为特征"""
        
        features = {}
        
        # 操作频率特征
        action_counts = Counter(log.action.value for log in logs)
        features['total_actions'] = len(logs)
        features['unique_actions'] = len(action_counts)
        features['action_diversity'] = len(action_counts) / len(logs) if logs else 0
        
        # 时间特征
        if logs:
            hours = [log.timestamp.hour for log in logs]
            features['avg_hour'] = statistics.mean(hours)
            features['hour_std'] = statistics.stdev(hours) if len(hours) > 1 else 0
            
            # 与历史峰值时间的偏差
            if profile.peak_activity_hours:
                hour_deviations = [
                    min(abs(hour - peak_hour) for peak_hour in profile.peak_activity_hours)
                    for hour in hours
                ]
                features['time_deviation'] = statistics.mean(hour_deviations)
            else:
                features['time_deviation'] = 0
        
        # 资源访问特征
        resource_counts = Counter(log.resource_type for log in logs)
        features['unique_resources'] = len(resource_counts)
        features['resource_diversity'] = len(resource_counts) / len(logs) if logs else 0
        
        # IP特征
        ip_addresses = set(str(log.ip_address) for log in logs if log.ip_address)
        features['unique_ips'] = len(ip_addresses)
        
        return features
    
    def _calculate_anomaly_score(self, features: Dict[str, float], profile: BehaviorProfile) -> float:
        """计算异常评分"""
        
        anomaly_score = 0.0
        
        # 操作频率异常
        if 'total_actions' in profile.action_frequency_baseline:
            baseline = profile.action_frequency_baseline['total_actions']
            if baseline[1] > 0:  # 有标准差
                z_score = abs(features['total_actions'] - baseline[0]) / baseline[1]
                anomaly_score += min(z_score / 3.0, 1.0) * 0.3  # 30%权重
        
        # 时间模式异常
        if features.get('time_deviation', 0) > 6:  # 超过6小时偏差
            anomaly_score += 0.2
        
        # 资源访问异常
        if features.get('resource_diversity', 0) > 0.8:  # 访问资源过于分散
            anomaly_score += 0.2
        
        # IP异常
        if features.get('unique_ips', 0) > 3:  # 使用多个IP
            anomaly_score += 0.3
        
        return min(anomaly_score, 1.0)
    
    def _identify_anomaly_indicators(self, features: Dict[str, float], profile: BehaviorProfile) -> List[str]:
        """识别异常指标"""
        
        indicators = []
        
        if features.get('time_deviation', 0) > 6:
            indicators.append('activity_time_anomaly')
        
        if features.get('unique_ips', 0) > 3:
            indicators.append('geographic_anomaly')
        
        if features.get('resource_diversity', 0) > 0.8:
            indicators.append('unusual_access_patterns')
        
        # 检查操作频率异常
        if 'total_actions' in profile.action_frequency_baseline:
            baseline = profile.action_frequency_baseline['total_actions']
            if baseline[1] > 0:
                z_score = abs(features['total_actions'] - baseline[0]) / baseline[1]
                if z_score > 3.0:
                    indicators.append('unusual_activity_volume')
        
        return indicators
    
    def _compare_with_baseline(self, features: Dict[str, float], profile: BehaviorProfile) -> Dict[str, Any]:
        """与基线比较"""
        
        comparison = {}
        
        if 'total_actions' in profile.action_frequency_baseline:
            baseline = profile.action_frequency_baseline['total_actions']
            comparison['action_frequency'] = {
                'current': features['total_actions'],
                'baseline_mean': baseline[0],
                'baseline_std': baseline[1],
                'z_score': abs(features['total_actions'] - baseline[0]) / baseline[1] if baseline[1] > 0 else 0
            }
        
        if profile.access_volume_baseline[1] > 0:
            comparison['access_volume'] = {
                'baseline_mean': profile.access_volume_baseline[0],
                'baseline_std': profile.access_volume_baseline[1]
            }
        
        return comparison
    
    def _deduplicate_and_rank_threats(
        self, 
        threats: List[Tuple[SecurityEvent, float]]
    ) -> List[Tuple[SecurityEvent, float]]:
        """去重和排序威胁"""
        
        # 按置信度排序
        threats.sort(key=lambda x: x[1], reverse=True)
        
        # 简单去重（基于事件类型、用户、IP的组合）
        seen_combinations = set()
        deduplicated_threats = []
        
        for event, confidence in threats:
            combination = (
                event.event_type.value,
                str(event.user_id) if event.user_id else 'none',
                event.ip_address or 'none',
                event.tenant_id
            )
            
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                deduplicated_threats.append((event, confidence))
        
        return deduplicated_threats
    
    def _map_category_to_event_type(self, category: ThreatCategory) -> SecurityEventType:
        """映射威胁分类到事件类型"""
        
        mapping = {
            ThreatCategory.AUTHENTICATION: SecurityEventType.AUTHENTICATION_FAILURE,
            ThreatCategory.AUTHORIZATION: SecurityEventType.PRIVILEGE_ESCALATION,
            ThreatCategory.DATA_ACCESS: SecurityEventType.DATA_EXFILTRATION,
            ThreatCategory.APPLICATION_SECURITY: SecurityEventType.MALICIOUS_REQUEST,
            ThreatCategory.SYSTEM_INTEGRITY: SecurityEventType.ANOMALOUS_BEHAVIOR,
            ThreatCategory.NETWORK_SECURITY: SecurityEventType.SUSPICIOUS_ACTIVITY
        }
        
        return mapping.get(category, SecurityEventType.SUSPICIOUS_ACTIVITY)
    
    def _calculate_threat_level(self, confidence: float) -> ThreatLevel:
        """根据置信度计算威胁等级"""
        
        if confidence >= 0.9:
            return ThreatLevel.CRITICAL
        elif confidence >= 0.7:
            return ThreatLevel.HIGH
        elif confidence >= 0.5:
            return ThreatLevel.MEDIUM
        elif confidence >= 0.3:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.INFO
    
    def _generate_event_id(self, signature_id: str) -> str:
        """生成事件ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        hash_suffix = hashlib.md5(f"{signature_id}_{timestamp}".encode()).hexdigest()[:8]
        return f"THR_{signature_id.upper()}_{timestamp}_{hash_suffix}"
    
    # 公共接口方法
    
    def get_detection_statistics(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        
        accuracy = 0.0
        if self.detection_stats['total_detections'] > 0:
            accuracy = (
                self.detection_stats['confirmed_threats'] / 
                self.detection_stats['total_detections']
            )
        
        return {
            'total_detections': self.detection_stats['total_detections'],
            'confirmed_threats': self.detection_stats['confirmed_threats'],
            'false_positives': self.detection_stats['false_positives'],
            'detection_accuracy': accuracy,
            'active_signatures': len(self.threat_signatures),
            'behavior_profiles': len(self.behavior_profiles)
        }
    
    def get_user_behavior_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户行为画像"""
        
        profile = self.behavior_profiles.get(user_id)
        if not profile:
            return None
        
        return {
            'user_id': profile.user_id,
            'tenant_id': profile.tenant_id,
            'profile_created': profile.profile_created.isoformat(),
            'last_updated': profile.last_updated.isoformat(),
            'action_patterns': profile.action_patterns,
            'resource_access_patterns': profile.resource_access_patterns,
            'time_patterns': profile.time_patterns,
            'peak_activity_hours': profile.peak_activity_hours,
            'risk_score': profile.risk_score,
            'anomaly_count': profile.anomaly_count
        }
    
    def update_threat_intelligence(self, intelligence_data: Dict[str, Any]):
        """更新威胁情报"""
        
        if 'malicious_ips' in intelligence_data:
            self.threat_intelligence['malicious_ips'].update(intelligence_data['malicious_ips'])
        
        if 'suspicious_patterns' in intelligence_data:
            self.threat_intelligence['suspicious_patterns'].extend(intelligence_data['suspicious_patterns'])
        
        if 'attack_signatures' in intelligence_data:
            self.threat_intelligence['known_attack_signatures'].extend(intelligence_data['attack_signatures'])
        
        self.logger.info("Threat intelligence updated")


# 全局威胁检测器实例
threat_detector = AdvancedThreatDetector()


def get_threat_detector() -> AdvancedThreatDetector:
    """获取威胁检测器实例"""
    return threat_detector