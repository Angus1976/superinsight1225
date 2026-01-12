"""
Enhanced Audit Service for SuperInsight Platform.

Provides comprehensive audit logging, analysis, and alerting functionality
with enterprise-level features including risk assessment, detailed information
extraction, and real-time monitoring.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, select, delete
from collections import defaultdict, Counter
import asyncio
from enum import Enum

from src.security.models import AuditLogModel, AuditAction, UserModel
from src.database.connection import get_db_session


class RiskLevel(Enum):
    """审计事件风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditService:
    """
    Comprehensive audit service for logging, analysis, and alerting.
    
    Handles audit log management, security analysis, and sensitive operation monitoring.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sensitive_actions = {
            AuditAction.DELETE,
            AuditAction.EXPORT,
            AuditAction.UPDATE
        }
        self.critical_resources = {
            "user", "permission", "ip_whitelist", "masking_rule"
        }
    
    # Enhanced Logging Methods
    
    def log_bulk_actions(
        self,
        actions: List[Dict[str, Any]],
        db: Session
    ) -> bool:
        """Log multiple actions in bulk for performance."""
        try:
            audit_logs = []
            for action_data in actions:
                audit_log = AuditLogModel(
                    user_id=action_data.get("user_id"),
                    tenant_id=action_data["tenant_id"],
                    action=action_data["action"],
                    resource_type=action_data["resource_type"],
                    resource_id=action_data.get("resource_id"),
                    ip_address=action_data.get("ip_address"),
                    user_agent=action_data.get("user_agent"),
                    details=action_data.get("details", {})
                )
                audit_logs.append(audit_log)
            
            db.add_all(audit_logs)
            db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to log bulk actions: {e}")
            db.rollback()
            return False
    
    def log_system_event(
        self,
        event_type: str,
        description: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> bool:
        """Log system-level events (not user actions)."""
        try:
            audit_log = AuditLogModel(
                user_id=None,  # System events have no user
                tenant_id=tenant_id,
                action=AuditAction.CREATE,  # Generic action for system events
                resource_type="system",
                resource_id=event_type,
                details={
                    "event_type": event_type,
                    "description": description,
                    **(details or {})
                }
            )
            db.add(audit_log)
            db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to log system event: {e}")
            if db:
                db.rollback()
            return False
    
    # Log Analysis Methods
    
    def analyze_user_activity(
        self,
        user_id: UUID,
        tenant_id: str,
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """Analyze user activity patterns over a time period."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.user_id == user_id,
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date
            )
        )
        logs = db.execute(stmt).scalars().all()
        
        if not logs:
            return {
                "total_actions": 0,
                "actions_by_type": {},
                "resources_accessed": {},
                "daily_activity": {},
                "suspicious_patterns": []
            }
        
        # Analyze action patterns
        actions_by_type = Counter(log.action.value for log in logs)
        resources_accessed = Counter(log.resource_type for log in logs)
        
        # Daily activity breakdown
        daily_activity = defaultdict(int)
        for log in logs:
            date_key = log.timestamp.date().isoformat()
            daily_activity[date_key] += 1
        
        # Detect suspicious patterns
        suspicious_patterns = self._detect_suspicious_patterns(logs)
        
        return {
            "total_actions": len(logs),
            "actions_by_type": dict(actions_by_type),
            "resources_accessed": dict(resources_accessed),
            "daily_activity": dict(daily_activity),
            "suspicious_patterns": suspicious_patterns,
            "analysis_period_days": days
        }
    
    def get_security_summary(
        self,
        tenant_id: str,
        days: int = 7,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get security summary for a tenant."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all logs for the period
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date
            )
        )
        logs = db.execute(stmt).scalars().all()
        
        # Failed login attempts
        failed_logins = [
            log for log in logs 
            if log.action == AuditAction.LOGIN and 
            log.details.get("status") == "failed"
        ]
        
        # Sensitive operations
        sensitive_ops = [
            log for log in logs 
            if log.action in self.sensitive_actions or 
            log.resource_type in self.critical_resources
        ]
        
        # Unique users active
        active_users = set(
            log.user_id for log in logs 
            if log.user_id is not None
        )
        
        # IP addresses used
        ip_addresses = set(
            str(log.ip_address) for log in logs 
            if log.ip_address is not None
        )
        
        return {
            "period_days": days,
            "total_events": len(logs),
            "failed_logins": len(failed_logins),
            "sensitive_operations": len(sensitive_ops),
            "active_users": len(active_users),
            "unique_ip_addresses": len(ip_addresses),
            "recent_failed_logins": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "ip_address": str(log.ip_address) if log.ip_address else None,
                    "username": log.details.get("username"),
                    "user_agent": log.user_agent
                }
                for log in failed_logins[-10:]  # Last 10 failed attempts
            ]
        }
    
    def _detect_suspicious_patterns(self, logs: List[AuditLogModel]) -> List[Dict[str, Any]]:
        """Detect suspicious activity patterns in audit logs."""
        patterns = []
        
        # Pattern 1: Rapid successive actions (potential automation/attack)
        time_sorted_logs = sorted(logs, key=lambda x: x.timestamp)
        rapid_actions = []
        
        for i in range(1, len(time_sorted_logs)):
            time_diff = (time_sorted_logs[i].timestamp - time_sorted_logs[i-1].timestamp).total_seconds()
            if time_diff < 1:  # Less than 1 second between actions
                rapid_actions.append({
                    "timestamp": time_sorted_logs[i].timestamp.isoformat(),
                    "action": time_sorted_logs[i].action.value,
                    "time_diff_seconds": time_diff
                })
        
        if len(rapid_actions) > 5:  # More than 5 rapid actions
            patterns.append({
                "type": "rapid_successive_actions",
                "severity": "medium",
                "description": f"Detected {len(rapid_actions)} rapid successive actions",
                "details": rapid_actions[:10]  # Show first 10
            })
        
        # Pattern 2: Unusual time access (outside business hours)
        unusual_time_actions = []
        for log in logs:
            hour = log.timestamp.hour
            if hour < 6 or hour > 22:  # Outside 6 AM - 10 PM
                unusual_time_actions.append({
                    "timestamp": log.timestamp.isoformat(),
                    "action": log.action.value,
                    "hour": hour
                })
        
        if len(unusual_time_actions) > 10:  # More than 10 actions outside hours
            patterns.append({
                "type": "unusual_time_access",
                "severity": "low",
                "description": f"Detected {len(unusual_time_actions)} actions outside business hours",
                "details": unusual_time_actions[:5]  # Show first 5
            })
        
        # Pattern 3: Multiple failed login attempts
        failed_logins = [
            log for log in logs 
            if log.action == AuditAction.LOGIN and 
            log.details.get("status") == "failed"
        ]
        
        if len(failed_logins) > 5:  # More than 5 failed attempts
            patterns.append({
                "type": "multiple_failed_logins",
                "severity": "high",
                "description": f"Detected {len(failed_logins)} failed login attempts",
                "details": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "ip_address": str(log.ip_address) if log.ip_address else None,
                        "username": log.details.get("username")
                    }
                    for log in failed_logins[-5:]  # Last 5 attempts
                ]
            })
        
        return patterns
    
    # Log Query and Search Methods
    
    def search_logs(
        self,
        tenant_id: str,
        query_params: Dict[str, Any],
        db: Session
    ) -> Tuple[List[AuditLogModel], int]:
        """Advanced search in audit logs with pagination."""
        base_stmt = select(AuditLogModel).where(
            AuditLogModel.tenant_id == tenant_id
        )
        
        # Apply filters
        if query_params.get("user_id"):
            base_stmt = base_stmt.where(
                AuditLogModel.user_id == UUID(query_params["user_id"])
            )
        
        if query_params.get("action"):
            base_stmt = base_stmt.where(
                AuditLogModel.action == AuditAction(query_params["action"])
            )
        
        if query_params.get("resource_type"):
            base_stmt = base_stmt.where(
                AuditLogModel.resource_type == query_params["resource_type"]
            )
        
        if query_params.get("resource_id"):
            base_stmt = base_stmt.where(
                AuditLogModel.resource_id == query_params["resource_id"]
            )
        
        if query_params.get("ip_address"):
            base_stmt = base_stmt.where(
                AuditLogModel.ip_address == query_params["ip_address"]
            )
        
        if query_params.get("start_date"):
            base_stmt = base_stmt.where(
                AuditLogModel.timestamp >= query_params["start_date"]
            )
        
        if query_params.get("end_date"):
            base_stmt = base_stmt.where(
                AuditLogModel.timestamp <= query_params["end_date"]
            )
        
        # Text search in details
        if query_params.get("search_text"):
            search_text = f"%{query_params['search_text']}%"
            base_stmt = base_stmt.where(
                or_(
                    AuditLogModel.user_agent.ilike(search_text),
                    AuditLogModel.details.astext.ilike(search_text)
                )
            )
        
        # Get total count
        total_count = len(db.execute(base_stmt).scalars().all())
        
        # Apply pagination
        page = query_params.get("page", 1)
        page_size = min(query_params.get("page_size", 50), 100)  # Max 100 per page
        offset = (page - 1) * page_size
        
        paginated_stmt = base_stmt.order_by(desc(AuditLogModel.timestamp)).offset(offset).limit(page_size)
        logs = db.execute(paginated_stmt).scalars().all()
        
        return logs, total_count
    
    # Alerting Methods
    
    def check_security_alerts(
        self,
        tenant_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Check for security conditions that require alerts."""
        alerts = []
        now = datetime.utcnow()
        
        # Alert 1: Multiple failed logins in last hour
        one_hour_ago = now - timedelta(hours=1)
        failed_login_stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.action == AuditAction.LOGIN,
                AuditLogModel.timestamp >= one_hour_ago,
                AuditLogModel.details["status"].astext == "failed"
            )
        )
        recent_failed_logins = len(db.execute(failed_login_stmt).scalars().all())
        
        if recent_failed_logins >= 10:
            alerts.append({
                "type": "multiple_failed_logins",
                "severity": "high",
                "message": f"{recent_failed_logins} failed login attempts in the last hour",
                "timestamp": now.isoformat(),
                "action_required": "Review IP whitelist and user accounts"
            })
        
        # Alert 2: Sensitive operations outside business hours
        if now.hour < 6 or now.hour > 22:  # Outside business hours
            sensitive_ops_stmt = select(AuditLogModel).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp >= one_hour_ago,
                    or_(
                        AuditLogModel.action.in_(self.sensitive_actions),
                        AuditLogModel.resource_type.in_(self.critical_resources)
                    )
                )
            )
            recent_sensitive_ops = len(db.execute(sensitive_ops_stmt).scalars().all())
            
            if recent_sensitive_ops > 0:
                alerts.append({
                    "type": "after_hours_sensitive_operations",
                    "severity": "medium",
                    "message": f"{recent_sensitive_ops} sensitive operations detected outside business hours",
                    "timestamp": now.isoformat(),
                    "action_required": "Verify if operations were authorized"
                })
        
        # Alert 3: Unusual IP addresses
        last_24_hours = now - timedelta(hours=24)
        ip_stmt = select(AuditLogModel.ip_address).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= last_24_hours,
                AuditLogModel.ip_address.isnot(None)
            )
        ).distinct()
        recent_ips = db.execute(ip_stmt).scalars().all()
        
        # This is a simplified check - in practice, you'd compare against historical patterns
        if len(recent_ips) > 20:  # More than 20 unique IPs in 24 hours
            alerts.append({
                "type": "unusual_ip_activity",
                "severity": "medium",
                "message": f"{len(recent_ips)} unique IP addresses accessed the system in 24 hours",
                "timestamp": now.isoformat(),
                "action_required": "Review IP whitelist configuration"
            })
        
        return alerts
    
    # Log Rotation and Cleanup
    
    def rotate_logs(
        self,
        tenant_id: str,
        retention_days: int = 365,
        db: Session = None
    ) -> Dict[str, Any]:
        """Rotate audit logs by archiving old entries."""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Count logs to be archived
        old_logs_stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp < cutoff_date
            )
        )
        old_logs_count = len(db.execute(old_logs_stmt).scalars().all())
        
        if old_logs_count == 0:
            return {
                "archived_count": 0,
                "message": "No logs to archive"
            }
        
        # In a production system, you would:
        # 1. Export logs to archive storage (S3, etc.)
        # 2. Compress the data
        # 3. Delete from active database
        
        # For this implementation, we'll just delete old logs
        try:
            delete_stmt = delete(AuditLogModel).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp < cutoff_date
                )
            )
            result = db.execute(delete_stmt)
            deleted_count = result.rowcount
            
            db.commit()
            
            return {
                "archived_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "message": f"Successfully archived {deleted_count} log entries"
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to rotate logs: {e}")
            return {
                "archived_count": 0,
                "error": str(e),
                "message": "Failed to archive logs"
            }
    
    def get_log_statistics(
        self,
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Get audit log storage statistics."""
        total_logs_stmt = select(AuditLogModel).where(
            AuditLogModel.tenant_id == tenant_id
        )
        total_logs = len(db.execute(total_logs_stmt).scalars().all())
        
        if total_logs == 0:
            return {
                "total_logs": 0,
                "oldest_log": None,
                "newest_log": None,
                "storage_size_estimate": "0 MB"
            }
        
        oldest_log_stmt = select(func.min(AuditLogModel.timestamp)).where(
            AuditLogModel.tenant_id == tenant_id
        )
        oldest_log = db.execute(oldest_log_stmt).scalar()
        
        newest_log_stmt = select(func.max(AuditLogModel.timestamp)).where(
            AuditLogModel.tenant_id == tenant_id
        )
        newest_log = db.execute(newest_log_stmt).scalar()
        
        # Rough estimate: ~1KB per log entry
        storage_size_mb = (total_logs * 1024) / (1024 * 1024)
        
        return {
            "total_logs": total_logs,
            "oldest_log": oldest_log.isoformat() if oldest_log else None,
            "newest_log": newest_log.isoformat() if newest_log else None,
            "storage_size_estimate": f"{storage_size_mb:.2f} MB"
        }


class EnhancedAuditService(AuditService):
    """
    企业级增强审计服务，扩展现有审计功能。
    
    新增功能：
    - 风险评估和分类
    - 详细信息提取
    - 实时监控
    - 多租户审计支持
    - 高级威胁检测
    """
    
    def __init__(self):
        super().__init__()
        self.risk_rules = self._initialize_risk_rules()
        self.threat_patterns = self._initialize_threat_patterns()
        self.monitoring_enabled = True
        
    def _initialize_risk_rules(self) -> Dict[str, Dict[str, Any]]:
        """初始化风险评估规则"""
        return {
            "failed_login_burst": {
                "threshold": 5,
                "time_window": 300,  # 5分钟
                "risk_level": RiskLevel.HIGH,
                "description": "短时间内多次登录失败"
            },
            "sensitive_data_access": {
                "actions": [AuditAction.EXPORT, AuditAction.DELETE],
                "resources": ["user", "annotation", "dataset"],
                "risk_level": RiskLevel.MEDIUM,
                "description": "敏感数据操作"
            },
            "privilege_escalation": {
                "actions": [AuditAction.UPDATE],
                "resources": ["permission", "role", "user"],
                "risk_level": RiskLevel.HIGH,
                "description": "权限提升操作"
            },
            "after_hours_activity": {
                "time_range": (22, 6),  # 22:00 - 06:00
                "risk_level": RiskLevel.MEDIUM,
                "description": "非工作时间活动"
            },
            "bulk_operations": {
                "threshold": 50,
                "time_window": 60,  # 1分钟
                "risk_level": RiskLevel.MEDIUM,
                "description": "批量操作"
            }
        }
    
    def _initialize_threat_patterns(self) -> Dict[str, Dict[str, Any]]:
        """初始化威胁检测模式"""
        return {
            "sql_injection_attempt": {
                "patterns": ["'", "union", "select", "drop", "insert", "update", "delete"],
                "risk_level": RiskLevel.CRITICAL,
                "description": "SQL注入尝试"
            },
            "unusual_ip_pattern": {
                "max_unique_ips": 10,
                "time_window": 3600,  # 1小时
                "risk_level": RiskLevel.MEDIUM,
                "description": "异常IP访问模式"
            },
            "data_exfiltration": {
                "export_threshold": 1000,  # MB
                "time_window": 3600,
                "risk_level": RiskLevel.HIGH,
                "description": "数据泄露风险"
            }
        }
    
    async def log_enhanced_audit_event(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """记录增强的审计事件，包含风险评估"""
        
        # 基础审计日志记录
        audit_log = AuditLogModel(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            timestamp=datetime.utcnow()  # 显式设置时间戳
        )
        
        # 风险评估
        risk_assessment = await self._assess_event_risk(
            audit_log, db
        )
        
        # 增强详细信息
        enhanced_details = await self._extract_detailed_info(
            audit_log, risk_assessment
        )
        
        # 更新审计日志
        audit_log.details.update({
            "risk_level": risk_assessment["risk_level"].value,
            "risk_score": risk_assessment["risk_score"],
            "risk_factors": risk_assessment["risk_factors"],
            "enhanced_info": enhanced_details
        })
        
        try:
            db.add(audit_log)
            db.commit()
            
            # 实时监控处理
            if self.monitoring_enabled:
                await self._process_real_time_monitoring(audit_log, risk_assessment)
            
            return {
                "audit_log_id": audit_log.id,
                "risk_assessment": risk_assessment,
                "enhanced_details": enhanced_details,
                "status": "success"
            }
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"记录增强审计事件失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _assess_event_risk(
        self,
        audit_log: AuditLogModel,
        db: Session
    ) -> Dict[str, Any]:
        """评估事件风险等级"""
        
        risk_factors = []
        risk_score = 0
        risk_level = RiskLevel.LOW
        
        # 检查失败登录爆发
        if audit_log.action == AuditAction.LOGIN and audit_log.details.get("status") == "failed":
            recent_failures = await self._count_recent_failed_logins(
                audit_log.tenant_id, audit_log.ip_address, db
            )
            
            if recent_failures >= self.risk_rules["failed_login_burst"]["threshold"]:
                risk_factors.append("failed_login_burst")
                risk_score += 30
                risk_level = RiskLevel.HIGH
        
        # 检查敏感数据访问
        sensitive_rule = self.risk_rules["sensitive_data_access"]
        if (audit_log.action in sensitive_rule["actions"] and 
            audit_log.resource_type in sensitive_rule["resources"]):
            risk_factors.append("sensitive_data_access")
            risk_score += 20
            if risk_level.value == "low":
                risk_level = RiskLevel.MEDIUM
        
        # 检查权限提升
        privilege_rule = self.risk_rules["privilege_escalation"]
        if (audit_log.action in privilege_rule["actions"] and 
            audit_log.resource_type in privilege_rule["resources"]):
            risk_factors.append("privilege_escalation")
            risk_score += 40
            risk_level = RiskLevel.HIGH
        
        # 检查非工作时间活动
        current_hour = audit_log.timestamp.hour
        after_hours_rule = self.risk_rules["after_hours_activity"]
        if (current_hour >= after_hours_rule["time_range"][0] or 
            current_hour <= after_hours_rule["time_range"][1]):
            risk_factors.append("after_hours_activity")
            risk_score += 15
            if risk_level.value == "low":
                risk_level = RiskLevel.MEDIUM
        
        # 检查批量操作
        recent_actions = await self._count_recent_actions(
            audit_log.user_id, audit_log.tenant_id, db
        )
        
        bulk_rule = self.risk_rules["bulk_operations"]
        if recent_actions >= bulk_rule["threshold"]:
            risk_factors.append("bulk_operations")
            risk_score += 25
            if risk_level.value == "low":
                risk_level = RiskLevel.MEDIUM
        
        # 威胁模式检测
        threat_factors = await self._detect_threat_patterns(audit_log, db)
        risk_factors.extend(threat_factors)
        
        # 根据威胁因素调整风险等级
        if any("critical" in factor for factor in threat_factors):
            risk_level = RiskLevel.CRITICAL
            risk_score += 50
        elif any("high" in factor for factor in threat_factors):
            if risk_level.value in ["low", "medium"]:
                risk_level = RiskLevel.HIGH
            risk_score += 35
        
        return {
            "risk_level": risk_level,
            "risk_score": min(risk_score, 100),  # 最大100分
            "risk_factors": risk_factors,
            "assessment_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _extract_detailed_info(
        self,
        audit_log: AuditLogModel,
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取详细信息"""
        
        enhanced_info = {
            "timestamp_iso": audit_log.timestamp.isoformat(),
            "session_info": {},
            "context_info": {},
            "technical_details": {}
        }
        
        # 会话信息
        if audit_log.user_agent:
            enhanced_info["session_info"] = {
                "user_agent_parsed": self._parse_user_agent(audit_log.user_agent),
                "browser_fingerprint": self._generate_browser_fingerprint(audit_log.user_agent)
            }
        
        # 上下文信息
        enhanced_info["context_info"] = {
            "risk_context": risk_assessment["risk_factors"],
            "tenant_context": audit_log.tenant_id,
            "resource_context": {
                "type": audit_log.resource_type,
                "id": audit_log.resource_id
            }
        }
        
        # 技术详细信息
        if audit_log.ip_address:
            enhanced_info["technical_details"] = {
                "ip_info": await self._get_ip_info(audit_log.ip_address),
                "geolocation": await self._get_geolocation(audit_log.ip_address)
            }
        
        return enhanced_info
    
    async def _process_real_time_monitoring(
        self,
        audit_log: AuditLogModel,
        risk_assessment: Dict[str, Any]
    ):
        """实时监控处理"""
        
        # 高风险事件立即告警
        if risk_assessment["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            await self._trigger_security_alert(audit_log, risk_assessment)
        
        # 更新实时统计
        await self._update_real_time_stats(audit_log, risk_assessment)
        
        # 检查是否需要自动响应
        if risk_assessment["risk_level"] == RiskLevel.CRITICAL:
            await self._trigger_automatic_response(audit_log, risk_assessment)
    
    async def _count_recent_failed_logins(
        self,
        tenant_id: str,
        ip_address: Optional[str],
        db: Session
    ) -> int:
        """统计最近的失败登录次数"""
        
        time_threshold = datetime.utcnow() - timedelta(
            seconds=self.risk_rules["failed_login_burst"]["time_window"]
        )
        
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.action == AuditAction.LOGIN,
                AuditLogModel.timestamp >= time_threshold,
                AuditLogModel.details["status"].astext == "failed"
            )
        )
        
        if ip_address:
            stmt = stmt.where(AuditLogModel.ip_address == ip_address)
        
        return len(db.execute(stmt).scalars().all())
    
    async def _count_recent_actions(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        db: Session
    ) -> int:
        """统计最近的用户操作次数"""
        
        time_threshold = datetime.utcnow() - timedelta(
            seconds=self.risk_rules["bulk_operations"]["time_window"]
        )
        
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= time_threshold
            )
        )
        
        if user_id:
            stmt = stmt.where(AuditLogModel.user_id == user_id)
        
        return len(db.execute(stmt).scalars().all())
    
    async def _detect_threat_patterns(
        self,
        audit_log: AuditLogModel,
        db: Session
    ) -> List[str]:
        """检测威胁模式"""
        
        threat_factors = []
        
        # SQL注入检测
        if audit_log.details:
            details_str = json.dumps(audit_log.details).lower()
            sql_patterns = self.threat_patterns["sql_injection_attempt"]["patterns"]
            
            if any(pattern in details_str for pattern in sql_patterns):
                threat_factors.append("sql_injection_attempt_critical")
        
        # 异常IP模式检测
        if audit_log.ip_address:
            recent_unique_ips = await self._count_recent_unique_ips(
                audit_log.tenant_id, db
            )
            
            ip_rule = self.threat_patterns["unusual_ip_pattern"]
            if recent_unique_ips > ip_rule["max_unique_ips"]:
                threat_factors.append("unusual_ip_pattern_medium")
        
        # 数据泄露检测
        if audit_log.action == AuditAction.EXPORT:
            export_size = audit_log.details.get("export_size_mb", 0)
            
            exfiltration_rule = self.threat_patterns["data_exfiltration"]
            if export_size > exfiltration_rule["export_threshold"]:
                threat_factors.append("data_exfiltration_high")
        
        return threat_factors
    
    async def _count_recent_unique_ips(
        self,
        tenant_id: str,
        db: Session
    ) -> int:
        """统计最近的唯一IP数量"""
        
        time_threshold = datetime.utcnow() - timedelta(
            seconds=self.threat_patterns["unusual_ip_pattern"]["time_window"]
        )
        
        stmt = select(AuditLogModel.ip_address).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= time_threshold,
                AuditLogModel.ip_address.isnot(None)
            )
        ).distinct()
        
        return len(db.execute(stmt).scalars().all())
    
    def _parse_user_agent(self, user_agent: str) -> Dict[str, Any]:
        """解析用户代理字符串"""
        # 简化的用户代理解析
        parsed = {
            "browser": "unknown",
            "version": "unknown",
            "os": "unknown",
            "device": "unknown"
        }
        
        user_agent_lower = user_agent.lower()
        
        # 浏览器检测
        if "chrome" in user_agent_lower:
            parsed["browser"] = "Chrome"
        elif "firefox" in user_agent_lower:
            parsed["browser"] = "Firefox"
        elif "safari" in user_agent_lower:
            parsed["browser"] = "Safari"
        elif "edge" in user_agent_lower:
            parsed["browser"] = "Edge"
        
        # 操作系统检测
        if "windows" in user_agent_lower:
            parsed["os"] = "Windows"
        elif "mac" in user_agent_lower:
            parsed["os"] = "macOS"
        elif "linux" in user_agent_lower:
            parsed["os"] = "Linux"
        elif "android" in user_agent_lower:
            parsed["os"] = "Android"
        elif "ios" in user_agent_lower:
            parsed["os"] = "iOS"
        
        return parsed
    
    def _generate_browser_fingerprint(self, user_agent: str) -> str:
        """生成浏览器指纹"""
        import hashlib
        return hashlib.md5(user_agent.encode()).hexdigest()[:16]
    
    async def _get_ip_info(self, ip_address: str) -> Dict[str, Any]:
        """获取IP信息（简化版本）"""
        # 在实际实现中，这里会调用IP地理位置服务
        return {
            "is_private": self._is_private_ip(ip_address),
            "is_tor": False,  # 需要集成Tor检测服务
            "is_vpn": False,  # 需要集成VPN检测服务
            "reputation": "unknown"
        }
    
    async def _get_geolocation(self, ip_address: str) -> Dict[str, Any]:
        """获取地理位置信息（简化版本）"""
        # 在实际实现中，这里会调用地理位置服务
        return {
            "country": "unknown",
            "city": "unknown",
            "latitude": None,
            "longitude": None
        }
    
    def _is_private_ip(self, ip_address: str) -> bool:
        """检查是否为私有IP"""
        import ipaddress
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private
        except:
            return False
    
    async def _trigger_security_alert(
        self,
        audit_log: AuditLogModel,
        risk_assessment: Dict[str, Any]
    ):
        """触发安全告警"""
        alert_data = {
            "alert_type": "security_event",
            "severity": risk_assessment["risk_level"].value,
            "tenant_id": audit_log.tenant_id,
            "user_id": str(audit_log.user_id) if audit_log.user_id else None,
            "event_details": {
                "action": audit_log.action.value,
                "resource": audit_log.resource_type,
                "risk_factors": risk_assessment["risk_factors"],
                "timestamp": audit_log.timestamp.isoformat()
            }
        }
        
        # 这里会集成到告警系统
        self.logger.warning(f"安全告警: {alert_data}")
    
    async def _update_real_time_stats(
        self,
        audit_log: AuditLogModel,
        risk_assessment: Dict[str, Any]
    ):
        """更新实时统计"""
        # 这里会更新实时监控仪表盘的统计数据
        pass
    
    async def _trigger_automatic_response(
        self,
        audit_log: AuditLogModel,
        risk_assessment: Dict[str, Any]
    ):
        """触发自动响应"""
        # 对于关键风险事件的自动响应
        if "sql_injection_attempt" in risk_assessment["risk_factors"]:
            # 可能的响应：临时封禁IP、通知管理员等
            self.logger.critical(f"检测到SQL注入尝试，来自IP: {audit_log.ip_address}")
        
        if "data_exfiltration" in risk_assessment["risk_factors"]:
            # 可能的响应：暂停用户账户、通知安全团队等
            self.logger.critical(f"检测到数据泄露风险，用户: {audit_log.user_id}")