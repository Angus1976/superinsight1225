"""
增强审计日志模块

提供企业级审计日志功能，包括：
- 安全事件记录
- 认证失败追踪
- 源 IP 记录
- 敏感操作审计
- 完整性保护

Validates: 需求 14.4, 14.5
"""

import logging
import hashlib
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import UUID, uuid4
from collections import defaultdict

from src.i18n.translations import get_translation

logger = logging.getLogger(__name__)


# ============================================================================
# 枚举和数据类
# ============================================================================

class AuditEventType(str, Enum):
    """审计事件类型"""
    # 认证事件
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    SESSION_EXPIRED = "session_expired"
    
    # 授权事件
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    ACCESS_DENIED = "access_denied"
    
    # 资源事件
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    RESOURCE_ACCESSED = "resource_accessed"
    RESOURCE_EXPORTED = "resource_exported"
    
    # 安全事件
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IP_BLOCKED = "ip_blocked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_ALERT = "security_alert"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"
    
    # 系统事件
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIG_CHANGED = "config_changed"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"


class AuditSeverity(str, Enum):
    """审计事件严重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: AuditEventType = AuditEventType.RESOURCE_ACCESSED
    severity: AuditSeverity = AuditSeverity.INFO
    
    # 用户信息
    user_id: Optional[str] = None
    username: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # 请求信息
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    
    # 资源信息
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    
    # 操作详情
    action: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    
    # 结果
    success: bool = True
    error_message: Optional[str] = None
    
    # 完整性
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """计算校验和"""
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """计算事件校验和"""
        data = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "success": self.success
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """验证事件完整性"""
        expected = self._calculate_checksum()
        return self.checksum == expected
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        result["event_type"] = self.event_type.value
        result["severity"] = self.severity.value
        return result


# ============================================================================
# 审计日志服务
# ============================================================================

class EnhancedAuditLogger:
    """
    增强审计日志服务
    
    提供完整的审计日志功能
    """
    
    def __init__(
        self,
        max_events: int = 100000,
        retention_days: int = 365,
        enable_integrity_check: bool = True
    ):
        self._events: List[AuditEvent] = []
        self._max_events = max_events
        self._retention_days = retention_days
        self._enable_integrity_check = enable_integrity_check
        self._callbacks: List[Callable[[AuditEvent], None]] = []
        self._lock = asyncio.Lock()
        
        # 统计信息
        self._stats = defaultdict(int)
        self._failed_logins: Dict[str, List[datetime]] = defaultdict(list)
    
    async def log(self, event: AuditEvent) -> str:
        """
        记录审计事件
        
        Args:
            event: 审计事件
            
        Returns:
            事件 ID
        """
        async with self._lock:
            # 验证完整性
            if self._enable_integrity_check and not event.verify_integrity():
                logger.error(f"Audit event integrity check failed: {event.id}")
                event.checksum = event._calculate_checksum()
            
            # 添加事件
            self._events.append(event)
            
            # 更新统计
            self._stats[event.event_type.value] += 1
            self._stats["total"] += 1
            
            # 追踪失败登录
            if event.event_type == AuditEventType.LOGIN_FAILED and event.ip_address:
                self._failed_logins[event.ip_address].append(event.timestamp)
            
            # 清理旧事件
            await self._cleanup_old_events()
            
            # 触发回调
            for callback in self._callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Audit callback error: {e}")
            
            # 记录到日志
            self._log_event(event)
            
            return event.id
    
    def _log_event(self, event: AuditEvent):
        """记录事件到日志"""
        log_level = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }.get(event.severity, logging.INFO)
        
        message = (
            f"[AUDIT] {event.event_type.value} | "
            f"user={event.username or event.user_id or 'anonymous'} | "
            f"ip={event.ip_address or 'unknown'} | "
            f"resource={event.resource_type}:{event.resource_id} | "
            f"success={event.success}"
        )
        
        logger.log(log_level, message, extra={"audit_event": event.to_dict()})
    
    async def _cleanup_old_events(self):
        """清理旧事件"""
        if len(self._events) <= self._max_events:
            return
        
        cutoff = datetime.utcnow() - timedelta(days=self._retention_days)
        self._events = [
            e for e in self._events
            if e.timestamp > cutoff
        ][-self._max_events:]
    
    # ========================================================================
    # 便捷方法
    # ========================================================================
    
    async def log_login_success(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        tenant_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录登录成功"""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            tenant_id=tenant_id,
            action="login",
            details=details or {},
            success=True
        )
        return await self.log(event)
    
    async def log_login_failed(
        self,
        username: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录登录失败"""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_FAILED,
            severity=AuditSeverity.WARNING,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            action="login",
            details=details or {},
            success=False,
            error_message=reason or "Invalid credentials"
        )
        return await self.log(event)
    
    async def log_logout(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        tenant_id: Optional[str] = None
    ) -> str:
        """记录登出"""
        event = AuditEvent(
            event_type=AuditEventType.LOGOUT,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            tenant_id=tenant_id,
            action="logout",
            success=True
        )
        return await self.log(event)
    
    async def log_access_denied(
        self,
        user_id: Optional[str],
        username: Optional[str],
        ip_address: str,
        resource_type: str,
        resource_id: str,
        reason: str,
        tenant_id: Optional[str] = None
    ) -> str:
        """记录访问拒绝"""
        event = AuditEvent(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action="access",
            success=False,
            error_message=reason
        )
        return await self.log(event)
    
    async def log_resource_created(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        resource_type: str,
        resource_id: str,
        resource_name: Optional[str] = None,
        new_value: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> str:
        """记录资源创建"""
        event = AuditEvent(
            event_type=AuditEventType.RESOURCE_CREATED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            action="create",
            new_value=new_value,
            success=True
        )
        return await self.log(event)
    
    async def log_resource_updated(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        resource_type: str,
        resource_id: str,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> str:
        """记录资源更新"""
        event = AuditEvent(
            event_type=AuditEventType.RESOURCE_UPDATED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action="update",
            old_value=old_value,
            new_value=new_value,
            success=True
        )
        return await self.log(event)
    
    async def log_resource_deleted(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        resource_type: str,
        resource_id: str,
        old_value: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> str:
        """记录资源删除"""
        event = AuditEvent(
            event_type=AuditEventType.RESOURCE_DELETED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action="delete",
            old_value=old_value,
            success=True
        )
        return await self.log(event)
    
    async def log_rate_limit_exceeded(
        self,
        ip_address: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        endpoint: Optional[str] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> str:
        """记录速率限制超限"""
        event = AuditEvent(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            request_path=endpoint,
            action="rate_limit",
            details={
                "limit": limit,
                "window": window
            },
            success=False,
            error_message="Rate limit exceeded"
        )
        return await self.log(event)
    
    async def log_suspicious_activity(
        self,
        ip_address: str,
        activity_type: str,
        description: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录可疑活动"""
        event = AuditEvent(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.ERROR,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            action=activity_type,
            details=details or {},
            success=False,
            error_message=description
        )
        return await self.log(event)
    
    async def log_security_alert(
        self,
        alert_type: str,
        description: str,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录安全告警"""
        event = AuditEvent(
            event_type=AuditEventType.SECURITY_ALERT,
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            ip_address=ip_address,
            action=alert_type,
            details=details or {},
            success=False,
            error_message=description
        )
        return await self.log(event)
    
    # ========================================================================
    # 查询方法
    # ========================================================================
    
    async def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """
        查询审计事件
        
        Args:
            event_type: 事件类型过滤
            user_id: 用户 ID 过滤
            ip_address: IP 地址过滤
            resource_type: 资源类型过滤
            start_time: 开始时间
            end_time: 结束时间
            success: 成功状态过滤
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            审计事件列表
        """
        async with self._lock:
            filtered = self._events
            
            if event_type:
                filtered = [e for e in filtered if e.event_type == event_type]
            
            if user_id:
                filtered = [e for e in filtered if e.user_id == user_id]
            
            if ip_address:
                filtered = [e for e in filtered if e.ip_address == ip_address]
            
            if resource_type:
                filtered = [e for e in filtered if e.resource_type == resource_type]
            
            if start_time:
                filtered = [e for e in filtered if e.timestamp >= start_time]
            
            if end_time:
                filtered = [e for e in filtered if e.timestamp <= end_time]
            
            if success is not None:
                filtered = [e for e in filtered if e.success == success]
            
            # 按时间倒序排序
            filtered.sort(key=lambda e: e.timestamp, reverse=True)
            
            return filtered[offset:offset + limit]
    
    async def get_failed_login_count(
        self,
        ip_address: str,
        window_minutes: int = 30
    ) -> int:
        """获取指定 IP 的失败登录次数"""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        attempts = self._failed_logins.get(ip_address, [])
        return len([t for t in attempts if t > cutoff])
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        async with self._lock:
            return {
                "total_events": self._stats["total"],
                "events_by_type": dict(self._stats),
                "event_count": len(self._events),
                "max_events": self._max_events,
                "retention_days": self._retention_days
            }
    
    async def verify_all_integrity(self) -> Dict[str, Any]:
        """验证所有事件的完整性"""
        async with self._lock:
            total = len(self._events)
            valid = sum(1 for e in self._events if e.verify_integrity())
            invalid = total - valid
            
            return {
                "total": total,
                "valid": valid,
                "invalid": invalid,
                "integrity_rate": valid / total if total > 0 else 1.0
            }
    
    def add_callback(self, callback: Callable[[AuditEvent], None]):
        """添加事件回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[AuditEvent], None]):
        """移除事件回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


# ============================================================================
# 全局实例
# ============================================================================

_audit_logger: Optional[EnhancedAuditLogger] = None


def get_audit_logger() -> EnhancedAuditLogger:
    """获取审计日志服务实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = EnhancedAuditLogger()
    return _audit_logger


# ============================================================================
# 便捷函数
# ============================================================================

async def audit_login_success(
    user_id: str,
    username: str,
    ip_address: str,
    **kwargs
) -> str:
    """记录登录成功"""
    return await get_audit_logger().log_login_success(
        user_id, username, ip_address, **kwargs
    )


async def audit_login_failed(
    username: str,
    ip_address: str,
    **kwargs
) -> str:
    """记录登录失败"""
    return await get_audit_logger().log_login_failed(
        username, ip_address, **kwargs
    )


async def audit_resource_created(
    user_id: str,
    username: str,
    ip_address: str,
    resource_type: str,
    resource_id: str,
    **kwargs
) -> str:
    """记录资源创建"""
    return await get_audit_logger().log_resource_created(
        user_id, username, ip_address, resource_type, resource_id, **kwargs
    )


async def audit_resource_updated(
    user_id: str,
    username: str,
    ip_address: str,
    resource_type: str,
    resource_id: str,
    **kwargs
) -> str:
    """记录资源更新"""
    return await get_audit_logger().log_resource_updated(
        user_id, username, ip_address, resource_type, resource_id, **kwargs
    )


async def audit_resource_deleted(
    user_id: str,
    username: str,
    ip_address: str,
    resource_type: str,
    resource_id: str,
    **kwargs
) -> str:
    """记录资源删除"""
    return await get_audit_logger().log_resource_deleted(
        user_id, username, ip_address, resource_type, resource_id, **kwargs
    )


async def audit_security_alert(
    alert_type: str,
    description: str,
    **kwargs
) -> str:
    """记录安全告警"""
    return await get_audit_logger().log_security_alert(
        alert_type, description, **kwargs
    )
