"""
Audit Event Processor for SuperInsight Platform.

处理审计事件的分类、风险分析和异常检测。
基于现有事件处理模式，添加企业级审计事件处理能力。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from uuid import UUID
import json

from src.security.audit_service import EnhancedAuditService, RiskLevel
from src.security.models import AuditLogModel, AuditAction

logger = logging.getLogger(__name__)


class EventCategory(Enum):
    """审计事件分类"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_ADMINISTRATION = "system_administration"
    SECURITY_VIOLATION = "security_violation"
    COMPLIANCE = "compliance"


class ProcessingStatus(Enum):
    """事件处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_ATTENTION = "requires_attention"


@dataclass
class EventProcessingResult:
    """事件处理结果"""
    event_id: str
    status: ProcessingStatus
    category: EventCategory
    risk_level: RiskLevel
    anomalies_detected: List[str]
    recommendations: List[str]
    processing_time_ms: float
    metadata: Dict[str, Any]


class AuditEventProcessor:
    """
    审计事件处理器
    
    负责：
    - 事件分类和标记
    - 风险分析和评估
    - 异常检测和模式识别
    - 处理结果生成和存储
    """
    
    def __init__(self, enhanced_audit_service: EnhancedAuditService):
        self.audit_service = enhanced_audit_service
        self.processing_queue = asyncio.Queue()
        self.processing_workers = []
        self.is_running = False
        
        # 事件分类规则
        self.classification_rules = self._initialize_classification_rules()
        
        # 异常检测配置
        self.anomaly_detectors = self._initialize_anomaly_detectors()
        
        # 处理统计
        self.processing_stats = {
            "events_processed": 0,
            "events_failed": 0,
            "anomalies_detected": 0,
            "high_risk_events": 0,
            "processing_time_total": 0.0
        }
    
    def _initialize_classification_rules(self) -> Dict[EventCategory, Dict[str, Any]]:
        """初始化事件分类规则"""
        return {
            EventCategory.AUTHENTICATION: {
                "actions": [AuditAction.LOGIN, AuditAction.LOGOUT],
                "keywords": ["login", "logout", "authenticate", "session"],
                "priority": 1
            },
            EventCategory.AUTHORIZATION: {
                "actions": [AuditAction.READ],
                "resources": ["permission", "role", "access_control"],
                "keywords": ["permission", "role", "access", "authorize"],
                "priority": 2
            },
            EventCategory.DATA_ACCESS: {
                "actions": [AuditAction.READ],
                "resources": ["dataset", "annotation", "task", "project"],
                "keywords": ["view", "read", "access", "query"],
                "priority": 3
            },
            EventCategory.DATA_MODIFICATION: {
                "actions": [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE],
                "resources": ["dataset", "annotation", "task", "project"],
                "keywords": ["create", "update", "delete", "modify", "change"],
                "priority": 4
            },
            EventCategory.SYSTEM_ADMINISTRATION: {
                "actions": [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE],
                "resources": ["user", "tenant", "workspace", "system", "configuration"],
                "keywords": ["admin", "configure", "system", "manage"],
                "priority": 5
            },
            EventCategory.SECURITY_VIOLATION: {
                "keywords": ["violation", "breach", "attack", "injection", "unauthorized"],
                "risk_factors": ["sql_injection", "privilege_escalation", "failed_login_burst"],
                "priority": 6
            },
            EventCategory.COMPLIANCE: {
                "actions": [AuditAction.EXPORT],
                "keywords": ["export", "backup", "archive", "compliance", "audit"],
                "priority": 7
            }
        }
    
    def _initialize_anomaly_detectors(self) -> Dict[str, Callable]:
        """初始化异常检测器"""
        return {
            "time_based_anomaly": self._detect_time_based_anomaly,
            "frequency_anomaly": self._detect_frequency_anomaly,
            "pattern_anomaly": self._detect_pattern_anomaly,
            "behavioral_anomaly": self._detect_behavioral_anomaly,
            "geographic_anomaly": self._detect_geographic_anomaly
        }
    
    async def start_processing(self, num_workers: int = 3):
        """启动事件处理"""
        if self.is_running:
            logger.warning("事件处理器已在运行")
            return
        
        self.is_running = True
        
        # 启动处理工作线程
        for i in range(num_workers):
            worker = asyncio.create_task(self._processing_worker(f"worker-{i}"))
            self.processing_workers.append(worker)
        
        logger.info(f"审计事件处理器启动，{num_workers} 个工作线程")
    
    async def stop_processing(self):
        """停止事件处理"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 等待所有工作线程完成
        for worker in self.processing_workers:
            worker.cancel()
        
        await asyncio.gather(*self.processing_workers, return_exceptions=True)
        self.processing_workers.clear()
        
        logger.info("审计事件处理器已停止")
    
    async def process_event(self, audit_log: AuditLogModel) -> EventProcessingResult:
        """处理单个审计事件"""
        start_time = datetime.utcnow()
        
        try:
            # 事件分类
            category = await self._classify_event(audit_log)
            
            # 风险评估
            risk_level = await self._assess_event_risk(audit_log)
            
            # 异常检测
            anomalies = await self._detect_anomalies(audit_log)
            
            # 生成建议
            recommendations = await self._generate_recommendations(
                audit_log, category, risk_level, anomalies
            )
            
            # 计算处理时间
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # 更新统计
            self._update_processing_stats(risk_level, anomalies, processing_time)
            
            result = EventProcessingResult(
                event_id=str(audit_log.id),
                status=ProcessingStatus.COMPLETED,
                category=category,
                risk_level=risk_level,
                anomalies_detected=anomalies,
                recommendations=recommendations,
                processing_time_ms=processing_time,
                metadata={
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor_version": "1.0.0"
                }
            )
            
            # 如果是高风险事件或检测到异常，标记需要关注
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or anomalies:
                result.status = ProcessingStatus.REQUIRES_ATTENTION
            
            return result
            
        except Exception as e:
            logger.error(f"处理审计事件失败 {audit_log.id}: {e}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.processing_stats["events_failed"] += 1
            
            return EventProcessingResult(
                event_id=str(audit_log.id),
                status=ProcessingStatus.FAILED,
                category=EventCategory.DATA_ACCESS,  # 默认分类
                risk_level=RiskLevel.LOW,
                anomalies_detected=[],
                recommendations=[],
                processing_time_ms=processing_time,
                metadata={"error": str(e)}
            )
    
    async def queue_event_for_processing(self, audit_log: AuditLogModel):
        """将事件加入处理队列"""
        await self.processing_queue.put(audit_log)
    
    async def _processing_worker(self, worker_name: str):
        """处理工作线程"""
        logger.info(f"启动处理工作线程: {worker_name}")
        
        while self.is_running:
            try:
                # 从队列获取事件，超时1秒
                audit_log = await asyncio.wait_for(
                    self.processing_queue.get(), timeout=1.0
                )
                
                # 处理事件
                result = await self.process_event(audit_log)
                
                # 标记任务完成
                self.processing_queue.task_done()
                
                logger.debug(f"{worker_name} 处理事件 {result.event_id}: {result.status.value}")
                
            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except asyncio.CancelledError:
                # 工作线程被取消
                break
            except Exception as e:
                logger.error(f"{worker_name} 处理事件时发生错误: {e}")
    
    async def _classify_event(self, audit_log: AuditLogModel) -> EventCategory:
        """对事件进行分类"""
        
        # 按优先级检查分类规则
        sorted_categories = sorted(
            self.classification_rules.items(),
            key=lambda x: x[1].get("priority", 999)
        )
        
        for category, rules in sorted_categories:
            # 检查动作匹配
            if "actions" in rules and audit_log.action in rules["actions"]:
                return category
            
            # 检查资源类型匹配
            if ("resources" in rules and 
                audit_log.resource_type in rules["resources"]):
                return category
            
            # 检查关键词匹配
            if "keywords" in rules:
                event_text = f"{audit_log.action.value} {audit_log.resource_type} {json.dumps(audit_log.details or {})}"
                if any(keyword in event_text.lower() for keyword in rules["keywords"]):
                    return category
            
            # 检查风险因素匹配
            if "risk_factors" in rules:
                event_risk_factors = audit_log.details.get("risk_factors", [])
                if any(factor in event_risk_factors for factor in rules["risk_factors"]):
                    return category
        
        # 默认分类
        return EventCategory.DATA_ACCESS
    
    async def _assess_event_risk(self, audit_log: AuditLogModel) -> RiskLevel:
        """评估事件风险等级"""
        # 从审计日志的详细信息中获取风险等级
        risk_level_str = audit_log.details.get("risk_level", "low")
        
        try:
            return RiskLevel(risk_level_str)
        except ValueError:
            return RiskLevel.LOW
    
    async def _detect_anomalies(self, audit_log: AuditLogModel) -> List[str]:
        """检测事件异常"""
        anomalies = []
        
        # 运行所有异常检测器
        for detector_name, detector_func in self.anomaly_detectors.items():
            try:
                is_anomaly = await detector_func(audit_log)
                if is_anomaly:
                    anomalies.append(detector_name)
            except Exception as e:
                logger.error(f"异常检测器 {detector_name} 执行失败: {e}")
        
        return anomalies
    
    async def _detect_time_based_anomaly(self, audit_log: AuditLogModel) -> bool:
        """检测基于时间的异常"""
        # 检查是否在异常时间进行操作
        hour = audit_log.timestamp.hour
        
        # 深夜操作（凌晨2-5点）
        if 2 <= hour <= 5:
            return True
        
        # 周末的工作时间操作
        weekday = audit_log.timestamp.weekday()
        if weekday >= 5 and 9 <= hour <= 17:  # 周六日的工作时间
            return True
        
        return False
    
    async def _detect_frequency_anomaly(self, audit_log: AuditLogModel) -> bool:
        """检测频率异常"""
        # 检查是否存在异常高频操作
        risk_factors = audit_log.details.get("risk_factors", [])
        
        return any(factor in ["bulk_operations", "failed_login_burst"] 
                  for factor in risk_factors)
    
    async def _detect_pattern_anomaly(self, audit_log: AuditLogModel) -> bool:
        """检测模式异常"""
        # 检查是否存在异常操作模式
        risk_factors = audit_log.details.get("risk_factors", [])
        
        return any(factor.endswith("_critical") or factor.endswith("_high") 
                  for factor in risk_factors)
    
    async def _detect_behavioral_anomaly(self, audit_log: AuditLogModel) -> bool:
        """检测行为异常"""
        # 检查用户行为是否异常
        if not audit_log.user_id:
            return False
        
        # 检查是否存在权限提升或敏感操作
        risk_factors = audit_log.details.get("risk_factors", [])
        
        return any(factor in ["privilege_escalation", "sensitive_data_access"] 
                  for factor in risk_factors)
    
    async def _detect_geographic_anomaly(self, audit_log: AuditLogModel) -> bool:
        """检测地理位置异常"""
        # 检查IP地址是否异常
        if not audit_log.ip_address:
            return False
        
        enhanced_info = audit_log.details.get("enhanced_info", {})
        technical_details = enhanced_info.get("technical_details", {})
        ip_info = technical_details.get("ip_info", {})
        
        # 检查是否为Tor或VPN
        if ip_info.get("is_tor") or ip_info.get("is_vpn"):
            return True
        
        # 检查是否为异常IP模式
        risk_factors = audit_log.details.get("risk_factors", [])
        return "unusual_ip_pattern" in risk_factors
    
    async def _generate_recommendations(
        self,
        audit_log: AuditLogModel,
        category: EventCategory,
        risk_level: RiskLevel,
        anomalies: List[str]
    ) -> List[str]:
        """生成处理建议"""
        recommendations = []
        
        # 基于风险等级的建议
        if risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "立即调查此事件",
                "考虑暂停相关用户账户",
                "通知安全团队",
                "检查相关系统日志"
            ])
        elif risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "优先调查此事件",
                "验证用户身份",
                "检查操作合法性"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "监控后续活动",
                "记录用户行为模式"
            ])
        
        # 基于事件分类的建议
        if category == EventCategory.AUTHENTICATION:
            if "failed_login_burst" in audit_log.details.get("risk_factors", []):
                recommendations.append("考虑临时限制IP访问")
        
        elif category == EventCategory.DATA_MODIFICATION:
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                recommendations.append("验证数据修改的授权")
        
        elif category == EventCategory.SECURITY_VIOLATION:
            recommendations.extend([
                "立即启动安全响应流程",
                "保存相关证据",
                "评估影响范围"
            ])
        
        # 基于异常检测的建议
        if "time_based_anomaly" in anomalies:
            recommendations.append("验证非工作时间操作的合理性")
        
        if "geographic_anomaly" in anomalies:
            recommendations.append("验证异常地理位置访问")
        
        if "behavioral_anomaly" in anomalies:
            recommendations.append("分析用户行为模式变化")
        
        return list(set(recommendations))  # 去重
    
    def _update_processing_stats(
        self,
        risk_level: RiskLevel,
        anomalies: List[str],
        processing_time: float
    ):
        """更新处理统计"""
        self.processing_stats["events_processed"] += 1
        self.processing_stats["processing_time_total"] += processing_time
        
        if anomalies:
            self.processing_stats["anomalies_detected"] += 1
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self.processing_stats["high_risk_events"] += 1
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        stats = self.processing_stats.copy()
        
        if stats["events_processed"] > 0:
            stats["average_processing_time_ms"] = (
                stats["processing_time_total"] / stats["events_processed"]
            )
            stats["anomaly_detection_rate"] = (
                stats["anomalies_detected"] / stats["events_processed"] * 100
            )
            stats["high_risk_event_rate"] = (
                stats["high_risk_events"] / stats["events_processed"] * 100
            )
        else:
            stats["average_processing_time_ms"] = 0
            stats["anomaly_detection_rate"] = 0
            stats["high_risk_event_rate"] = 0
        
        return stats
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "queue_size": self.processing_queue.qsize(),
            "is_running": self.is_running,
            "active_workers": len(self.processing_workers),
            "processing_stats": self.get_processing_stats()
        }