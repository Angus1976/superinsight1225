"""
Permission Audit Integration for SuperInsight Platform.

Integrates RBAC permission operations with the audit system to provide
comprehensive permission monitoring, analysis, and alerting.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, select
from collections import defaultdict, Counter
from enum import Enum

from src.security.audit_service import EnhancedAuditService, RiskLevel
from src.security.models import AuditAction, AuditLogModel
from src.security.rbac_models import (
    RoleModel, PermissionModel, UserRoleModel, 
    ResourceModel, ResourcePermissionModel
)

logger = logging.getLogger(__name__)


class PermissionEventType(Enum):
    """权限事件类型"""
    PERMISSION_CHECK = "permission_check"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    PERMISSION_ESCALATION = "permission_escalation"
    BULK_PERMISSION_CHECK = "bulk_permission_check"
    CACHE_INVALIDATION = "cache_invalidation"


class PermissionAuditIntegration:
    """
    权限审计集成服务。
    
    负责将RBAC权限操作集成到审计系统中，提供：
    - 权限检查审计
    - 权限变更审计
    - 权限异常检测
    - 权限使用分析
    - 权限违规告警
    """
    
    def __init__(self):
        self.audit_service = EnhancedAuditService()
        self.logger = logging.getLogger(__name__)
        
        # 权限风险规则
        self.permission_risk_rules = {
            "excessive_permission_checks": {
                "threshold": 100,
                "time_window": 300,  # 5分钟
                "risk_level": RiskLevel.MEDIUM,
                "description": "过度权限检查"
            },
            "permission_escalation_attempt": {
                "sensitive_permissions": [
                    "admin_access", "delete_user", "modify_permissions",
                    "export_sensitive_data", "system_config"
                ],
                "risk_level": RiskLevel.HIGH,
                "description": "权限提升尝试"
            },
            "unusual_permission_pattern": {
                "max_unique_permissions": 20,
                "time_window": 3600,  # 1小时
                "risk_level": RiskLevel.MEDIUM,
                "description": "异常权限访问模式"
            },
            "bulk_permission_abuse": {
                "threshold": 50,
                "time_window": 60,  # 1分钟
                "risk_level": RiskLevel.HIGH,
                "description": "批量权限滥用"
            }
        }
    
    async def log_permission_check(
        self,
        user_id: UUID,
        tenant_id: str,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        result: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        cache_hit: bool = False,
        response_time_ms: Optional[float] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        记录权限检查事件。
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            permission_name: 权限名称
            resource_id: 资源ID（可选）
            resource_type: 资源类型（可选）
            result: 权限检查结果
            ip_address: IP地址
            user_agent: 用户代理
            cache_hit: 是否命中缓存
            response_time_ms: 响应时间（毫秒）
            db: 数据库会话
            
        Returns:
            审计结果
        """
        try:
            # 构建详细信息
            details = {
                "permission_name": permission_name,
                "resource_id": resource_id,
                "resource_type": resource_type,
                "check_result": result,
                "cache_hit": cache_hit,
                "response_time_ms": response_time_ms,
                "event_type": PermissionEventType.PERMISSION_CHECK.value
            }
            
            # 确定审计动作
            action = AuditAction.READ if result else AuditAction.LOGIN  # 使用LOGIN表示拒绝访问
            
            # 记录增强审计事件
            audit_result = await self.audit_service.log_enhanced_audit_event(
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                resource_type="permission",
                resource_id=permission_name,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                db=db
            )
            
            # 如果权限被拒绝，进行额外的风险分析
            if not result:
                await self._analyze_permission_denial(
                    user_id, tenant_id, permission_name, db
                )
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"记录权限检查失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def log_role_assignment(
        self,
        user_id: UUID,
        role_id: UUID,
        assigned_by: UUID,
        tenant_id: str,
        role_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """记录角色分配事件"""
        try:
            details = {
                "role_id": str(role_id),
                "role_name": role_name,
                "assigned_by": str(assigned_by),
                "event_type": PermissionEventType.ROLE_ASSIGNED.value
            }
            
            audit_result = await self.audit_service.log_enhanced_audit_event(
                user_id=assigned_by,  # 执行操作的用户
                tenant_id=tenant_id,
                action=AuditAction.UPDATE,
                resource_type="user_role",
                resource_id=str(user_id),
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                db=db
            )
            
            # 检查是否为权限提升
            await self._check_permission_escalation(
                user_id, role_id, assigned_by, tenant_id, db
            )
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"记录角色分配失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def log_role_revocation(
        self,
        user_id: UUID,
        role_id: UUID,
        revoked_by: UUID,
        tenant_id: str,
        role_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """记录角色撤销事件"""
        try:
            details = {
                "role_id": str(role_id),
                "role_name": role_name,
                "revoked_by": str(revoked_by),
                "event_type": PermissionEventType.ROLE_REVOKED.value
            }
            
            audit_result = await self.audit_service.log_enhanced_audit_event(
                user_id=revoked_by,  # 执行操作的用户
                tenant_id=tenant_id,
                action=AuditAction.DELETE,
                resource_type="user_role",
                resource_id=str(user_id),
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                db=db
            )
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"记录角色撤销失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def log_bulk_permission_check(
        self,
        user_id: UUID,
        tenant_id: str,
        permissions: List[str],
        results: Dict[str, bool],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        cache_hits: int = 0,
        total_response_time_ms: Optional[float] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """记录批量权限检查事件"""
        try:
            details = {
                "permissions_checked": permissions,
                "results": results,
                "total_permissions": len(permissions),
                "granted_permissions": sum(results.values()),
                "denied_permissions": len(permissions) - sum(results.values()),
                "cache_hits": cache_hits,
                "cache_hit_rate": (cache_hits / len(permissions)) * 100 if permissions else 0,
                "total_response_time_ms": total_response_time_ms,
                "average_response_time_ms": (total_response_time_ms / len(permissions)) if permissions and total_response_time_ms else None,
                "event_type": PermissionEventType.BULK_PERMISSION_CHECK.value
            }
            
            audit_result = await self.audit_service.log_enhanced_audit_event(
                user_id=user_id,
                tenant_id=tenant_id,
                action=AuditAction.READ,
                resource_type="permission_batch",
                resource_id=f"bulk_check_{len(permissions)}",
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                db=db
            )
            
            # 检查批量权限滥用
            await self._check_bulk_permission_abuse(
                user_id, tenant_id, len(permissions), db
            )
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"记录批量权限检查失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def log_cache_invalidation(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        triggered_by: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        invalidated_keys_count: int = 0,
        db: Session = None
    ) -> Dict[str, Any]:
        """记录缓存失效事件"""
        try:
            details = {
                "invalidation_event_type": event_type,
                "event_data": event_data,
                "invalidated_keys_count": invalidated_keys_count,
                "event_type": PermissionEventType.CACHE_INVALIDATION.value
            }
            
            audit_result = await self.audit_service.log_enhanced_audit_event(
                user_id=triggered_by,
                tenant_id=tenant_id or "system",
                action=AuditAction.UPDATE,
                resource_type="permission_cache",
                resource_id=event_type,
                details=details,
                db=db
            )
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"记录缓存失效失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _analyze_permission_denial(
        self,
        user_id: UUID,
        tenant_id: str,
        permission_name: str,
        db: Session
    ):
        """分析权限拒绝事件"""
        try:
            # 统计最近的权限拒绝次数
            recent_denials = await self._count_recent_permission_denials(
                user_id, tenant_id, db
            )
            
            # 检查是否为敏感权限
            sensitive_permissions = self.permission_risk_rules["permission_escalation_attempt"]["sensitive_permissions"]
            if permission_name in sensitive_permissions:
                await self._trigger_permission_escalation_alert(
                    user_id, tenant_id, permission_name, db
                )
            
            # 检查是否存在异常模式
            if recent_denials > 10:  # 最近有超过10次权限拒绝
                await self._trigger_unusual_permission_pattern_alert(
                    user_id, tenant_id, recent_denials, db
                )
                
        except Exception as e:
            self.logger.error(f"分析权限拒绝失败: {e}")
    
    async def _check_permission_escalation(
        self,
        user_id: UUID,
        role_id: UUID,
        assigned_by: UUID,
        tenant_id: str,
        db: Session
    ):
        """检查权限提升"""
        try:
            # 获取角色的权限
            role_permissions = db.query(PermissionModel).join(
                RolePermissionModel, PermissionModel.id == RolePermissionModel.permission_id
            ).filter(
                RolePermissionModel.role_id == role_id
            ).all()
            
            # 检查是否包含敏感权限
            sensitive_permissions = self.permission_risk_rules["permission_escalation_attempt"]["sensitive_permissions"]
            has_sensitive = any(
                perm.name in sensitive_permissions 
                for perm in role_permissions
            )
            
            if has_sensitive:
                await self._trigger_permission_escalation_alert(
                    user_id, tenant_id, f"role_assignment_{role_id}", db
                )
                
        except Exception as e:
            self.logger.error(f"检查权限提升失败: {e}")
    
    async def _check_bulk_permission_abuse(
        self,
        user_id: UUID,
        tenant_id: str,
        permission_count: int,
        db: Session
    ):
        """检查批量权限滥用"""
        try:
            rule = self.permission_risk_rules["bulk_permission_abuse"]
            
            if permission_count >= rule["threshold"]:
                # 记录高风险事件
                await self.audit_service.log_enhanced_audit_event(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    action=AuditAction.READ,
                    resource_type="security_alert",
                    resource_id="bulk_permission_abuse",
                    details={
                        "alert_type": "bulk_permission_abuse",
                        "permission_count": permission_count,
                        "threshold": rule["threshold"],
                        "risk_level": rule["risk_level"].value
                    }
                )
                
        except Exception as e:
            self.logger.error(f"检查批量权限滥用失败: {e}")
    
    async def _count_recent_permission_denials(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Session,
        hours: int = 1
    ) -> int:
        """统计最近的权限拒绝次数"""
        try:
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            
            stmt = select(AuditLogModel).where(
                and_(
                    AuditLogModel.user_id == user_id,
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.resource_type == "permission",
                    AuditLogModel.action == AuditAction.LOGIN,  # 权限拒绝使用LOGIN表示
                    AuditLogModel.timestamp >= time_threshold,
                    AuditLogModel.details["check_result"].astext == "false"
                )
            )
            
            return len(db.execute(stmt).scalars().all())
            
        except Exception as e:
            self.logger.error(f"统计权限拒绝次数失败: {e}")
            return 0
    
    async def _trigger_permission_escalation_alert(
        self,
        user_id: UUID,
        tenant_id: str,
        permission_or_role: str,
        db: Session
    ):
        """触发权限提升告警"""
        try:
            alert_data = {
                "alert_type": "permission_escalation_attempt",
                "severity": "high",
                "user_id": str(user_id),
                "tenant_id": tenant_id,
                "permission_or_role": permission_or_role,
                "timestamp": datetime.utcnow().isoformat(),
                "description": "检测到权限提升尝试"
            }
            
            # 记录安全告警
            await self.audit_service.log_enhanced_audit_event(
                user_id=user_id,
                tenant_id=tenant_id,
                action=AuditAction.CREATE,
                resource_type="security_alert",
                resource_id="permission_escalation",
                details=alert_data
            )
            
            self.logger.warning(f"权限提升告警: {alert_data}")
            
        except Exception as e:
            self.logger.error(f"触发权限提升告警失败: {e}")
    
    async def _trigger_unusual_permission_pattern_alert(
        self,
        user_id: UUID,
        tenant_id: str,
        denial_count: int,
        db: Session
    ):
        """触发异常权限模式告警"""
        try:
            alert_data = {
                "alert_type": "unusual_permission_pattern",
                "severity": "medium",
                "user_id": str(user_id),
                "tenant_id": tenant_id,
                "denial_count": denial_count,
                "timestamp": datetime.utcnow().isoformat(),
                "description": f"用户在短时间内被拒绝访问{denial_count}次"
            }
            
            # 记录安全告警
            await self.audit_service.log_enhanced_audit_event(
                user_id=user_id,
                tenant_id=tenant_id,
                action=AuditAction.CREATE,
                resource_type="security_alert",
                resource_id="unusual_permission_pattern",
                details=alert_data
            )
            
            self.logger.warning(f"异常权限模式告警: {alert_data}")
            
        except Exception as e:
            self.logger.error(f"触发异常权限模式告警失败: {e}")
    
    # 权限使用分析方法
    
    async def analyze_permission_usage(
        self,
        tenant_id: str,
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """分析权限使用情况"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 获取权限相关的审计日志
            stmt = select(AuditLogModel).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp >= start_date,
                    or_(
                        AuditLogModel.resource_type == "permission",
                        AuditLogModel.resource_type == "user_role",
                        AuditLogModel.resource_type == "permission_batch"
                    )
                )
            )
            logs = db.execute(stmt).scalars().all()
            
            # 分析权限检查统计
            permission_checks = [
                log for log in logs 
                if log.resource_type == "permission"
            ]
            
            # 分析角色变更统计
            role_changes = [
                log for log in logs 
                if log.resource_type == "user_role"
            ]
            
            # 分析批量权限检查
            batch_checks = [
                log for log in logs 
                if log.resource_type == "permission_batch"
            ]
            
            # 统计最常检查的权限
            permission_usage = Counter()
            for log in permission_checks:
                if log.details and "permission_name" in log.details:
                    permission_usage[log.details["permission_name"]] += 1
            
            # 统计权限检查成功率
            successful_checks = sum(
                1 for log in permission_checks 
                if log.details and log.details.get("check_result") is True
            )
            total_checks = len(permission_checks)
            success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0
            
            # 统计缓存命中率
            cache_hits = sum(
                1 for log in permission_checks 
                if log.details and log.details.get("cache_hit") is True
            )
            cache_hit_rate = (cache_hits / total_checks * 100) if total_checks > 0 else 0
            
            # 统计用户活动
            active_users = set(
                log.user_id for log in logs 
                if log.user_id is not None
            )
            
            return {
                "analysis_period_days": days,
                "total_permission_events": len(logs),
                "permission_checks": {
                    "total": total_checks,
                    "successful": successful_checks,
                    "success_rate": round(success_rate, 2),
                    "cache_hit_rate": round(cache_hit_rate, 2)
                },
                "role_changes": {
                    "total": len(role_changes),
                    "assignments": len([
                        log for log in role_changes 
                        if log.action == AuditAction.UPDATE
                    ]),
                    "revocations": len([
                        log for log in role_changes 
                        if log.action == AuditAction.DELETE
                    ])
                },
                "batch_operations": {
                    "total": len(batch_checks),
                    "total_permissions_checked": sum(
                        log.details.get("total_permissions", 0) 
                        for log in batch_checks 
                        if log.details
                    )
                },
                "most_used_permissions": dict(permission_usage.most_common(10)),
                "active_users_count": len(active_users),
                "security_alerts": await self._count_permission_security_alerts(
                    tenant_id, start_date, db
                )
            }
            
        except Exception as e:
            self.logger.error(f"分析权限使用情况失败: {e}")
            return {"error": str(e)}
    
    async def _count_permission_security_alerts(
        self,
        tenant_id: str,
        start_date: datetime,
        db: Session
    ) -> Dict[str, int]:
        """统计权限相关的安全告警"""
        try:
            stmt = select(AuditLogModel).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.resource_type == "security_alert"
                )
            )
            alerts = db.execute(stmt).scalars().all()
            
            alert_counts = Counter()
            for alert in alerts:
                if alert.details and "alert_type" in alert.details:
                    alert_counts[alert.details["alert_type"]] += 1
            
            return dict(alert_counts)
            
        except Exception as e:
            self.logger.error(f"统计安全告警失败: {e}")
            return {}
    
    async def generate_permission_report(
        self,
        tenant_id: str,
        report_type: str = "summary",
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """生成权限报告"""
        try:
            usage_analysis = await self.analyze_permission_usage(tenant_id, days, db)
            
            if report_type == "summary":
                return {
                    "report_type": "permission_summary",
                    "tenant_id": tenant_id,
                    "period_days": days,
                    "generated_at": datetime.utcnow().isoformat(),
                    "summary": {
                        "total_events": usage_analysis.get("total_permission_events", 0),
                        "permission_success_rate": usage_analysis.get("permission_checks", {}).get("success_rate", 0),
                        "cache_efficiency": usage_analysis.get("permission_checks", {}).get("cache_hit_rate", 0),
                        "active_users": usage_analysis.get("active_users_count", 0),
                        "security_alerts": sum(usage_analysis.get("security_alerts", {}).values())
                    },
                    "recommendations": await self._generate_permission_recommendations(usage_analysis)
                }
            elif report_type == "detailed":
                return {
                    "report_type": "permission_detailed",
                    "tenant_id": tenant_id,
                    "period_days": days,
                    "generated_at": datetime.utcnow().isoformat(),
                    "detailed_analysis": usage_analysis,
                    "recommendations": await self._generate_permission_recommendations(usage_analysis)
                }
            else:
                return {"error": f"Unsupported report type: {report_type}"}
                
        except Exception as e:
            self.logger.error(f"生成权限报告失败: {e}")
            return {"error": str(e)}
    
    async def _generate_permission_recommendations(
        self,
        usage_analysis: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """生成权限优化建议"""
        recommendations = []
        
        try:
            # 检查缓存命中率
            cache_hit_rate = usage_analysis.get("permission_checks", {}).get("cache_hit_rate", 0)
            if cache_hit_rate < 80:
                recommendations.append({
                    "type": "performance",
                    "priority": "medium",
                    "title": "提高权限缓存命中率",
                    "description": f"当前缓存命中率为{cache_hit_rate:.1f}%，建议优化缓存策略或增加缓存预热"
                })
            
            # 检查权限成功率
            success_rate = usage_analysis.get("permission_checks", {}).get("success_rate", 0)
            if success_rate < 70:
                recommendations.append({
                    "type": "security",
                    "priority": "high",
                    "title": "权限配置需要优化",
                    "description": f"权限检查成功率仅为{success_rate:.1f}%，可能存在权限配置问题"
                })
            
            # 检查安全告警
            total_alerts = sum(usage_analysis.get("security_alerts", {}).values())
            if total_alerts > 10:
                recommendations.append({
                    "type": "security",
                    "priority": "high",
                    "title": "安全告警需要关注",
                    "description": f"检测到{total_alerts}个安全告警，建议及时处理"
                })
            
            # 检查批量操作
            batch_ops = usage_analysis.get("batch_operations", {}).get("total", 0)
            total_checks = usage_analysis.get("permission_checks", {}).get("total", 0)
            if batch_ops > 0 and total_checks > 0:
                batch_ratio = (batch_ops / total_checks) * 100
                if batch_ratio < 20:
                    recommendations.append({
                        "type": "performance",
                        "priority": "low",
                        "title": "考虑使用更多批量权限检查",
                        "description": f"批量操作占比仅{batch_ratio:.1f}%，使用批量检查可以提高性能"
                    })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"生成权限建议失败: {e}")
            return []


# 全局实例
_permission_audit_integration = None


def get_permission_audit_integration() -> PermissionAuditIntegration:
    """获取权限审计集成实例"""
    global _permission_audit_integration
    if _permission_audit_integration is None:
        _permission_audit_integration = PermissionAuditIntegration()
    return _permission_audit_integration