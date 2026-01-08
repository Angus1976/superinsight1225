"""
Tenant-Level Audit Logging System

Provides comprehensive audit logging for tenant operations and data access.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import json
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.database.connection import get_db_session
from src.security.models import AuditLogModel, AuditAction
from src.middleware.tenant_middleware import get_current_tenant, get_current_user

logger = logging.getLogger(__name__)


class AuditLevel(str, Enum):
    """Audit logging levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(str, Enum):
    """Audit event categories."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_ADMIN = "system_admin"
    TENANT_ADMIN = "tenant_admin"
    SECURITY = "security"
    COMPLIANCE = "compliance"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    action: AuditAction
    resource_type: str
    resource_id: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    category: AuditCategory = AuditCategory.DATA_ACCESS
    level: AuditLevel = AuditLevel.INFO
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}


class TenantAuditLogger:
    """Tenant-aware audit logging system."""
    
    def __init__(self):
        self.sensitive_fields = {
            'password', 'password_hash', 'secret_key', 'api_key',
            'token', 'private_key', 'credit_card', 'ssn', 'phone'
        }
    
    def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event to the database."""
        
        try:
            # Auto-populate tenant and user if not provided
            if event.tenant_id is None:
                try:
                    event.tenant_id = get_current_tenant()
                except:
                    pass
            
            if event.user_id is None:
                try:
                    event.user_id = get_current_user()
                except:
                    pass
            
            # Sanitize sensitive data
            sanitized_details = self._sanitize_details(event.details)
            
            with get_db_session() as session:
                audit_log = AuditLogModel(
                    user_id=event.user_id,
                    tenant_id=event.tenant_id,
                    action=event.action,
                    resource_type=event.resource_type,
                    resource_id=event.resource_id,
                    ip_address=event.ip_address,
                    user_agent=event.user_agent,
                    details={
                        **sanitized_details,
                        'category': event.category.value,
                        'level': event.level.value,
                        'timestamp': event.timestamp.isoformat()
                    }
                )
                session.add(audit_log)
                session.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False
    
    def log_authentication(self, user_id: str, tenant_id: str, 
                          success: bool, ip_address: str = None,
                          details: Dict[str, Any] = None) -> bool:
        """Log authentication attempt."""
        
        event = AuditEvent(
            action=AuditAction.LOGIN if success else AuditAction.LOGIN,
            resource_type="authentication",
            tenant_id=tenant_id,
            user_id=user_id if success else None,
            category=AuditCategory.AUTHENTICATION,
            level=AuditLevel.INFO if success else AuditLevel.WARNING,
            ip_address=ip_address,
            details={
                **(details or {}),
                'success': success,
                'failure_reason': details.get('failure_reason') if not success else None
            }
        )
        
        return self.log_event(event)
    
    def log_authorization_failure(self, resource_type: str, action: str,
                                 resource_id: str = None, 
                                 details: Dict[str, Any] = None) -> bool:
        """Log authorization failure."""
        
        event = AuditEvent(
            action=AuditAction.READ,  # The attempted action
            resource_type=resource_type,
            resource_id=resource_id,
            category=AuditCategory.AUTHORIZATION,
            level=AuditLevel.WARNING,
            details={
                **(details or {}),
                'attempted_action': action,
                'authorization_failed': True
            }
        )
        
        return self.log_event(event)
    
    def log_data_access(self, resource_type: str, resource_id: str = None,
                       action: AuditAction = AuditAction.READ,
                       details: Dict[str, Any] = None) -> bool:
        """Log data access event."""
        
        event = AuditEvent(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            category=AuditCategory.DATA_ACCESS,
            level=AuditLevel.INFO,
            details=details or {}
        )
        
        return self.log_event(event)
    
    def log_data_modification(self, resource_type: str, resource_id: str,
                             action: AuditAction, old_values: Dict = None,
                             new_values: Dict = None,
                             details: Dict[str, Any] = None) -> bool:
        """Log data modification event."""
        
        event = AuditEvent(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            category=AuditCategory.DATA_MODIFICATION,
            level=AuditLevel.INFO,
            details={
                **(details or {}),
                'old_values': self._sanitize_details(old_values) if old_values else None,
                'new_values': self._sanitize_details(new_values) if new_values else None
            }
        )
        
        return self.log_event(event)
    
    def log_security_event(self, event_type: str, severity: AuditLevel,
                          details: Dict[str, Any] = None) -> bool:
        """Log security-related event."""
        
        event = AuditEvent(
            action=AuditAction.READ,  # Generic action for security events
            resource_type="security",
            category=AuditCategory.SECURITY,
            level=severity,
            details={
                **(details or {}),
                'event_type': event_type
            }
        )
        
        return self.log_event(event)
    
    def log_admin_action(self, action: str, target_resource: str,
                        target_id: str = None, 
                        details: Dict[str, Any] = None) -> bool:
        """Log administrative action."""
        
        event = AuditEvent(
            action=AuditAction.ADMIN,
            resource_type=target_resource,
            resource_id=target_id,
            category=AuditCategory.TENANT_ADMIN,
            level=AuditLevel.INFO,
            details={
                **(details or {}),
                'admin_action': action
            }
        )
        
        return self.log_event(event)
    
    def get_audit_trail(self, tenant_id: str, 
                       start_date: datetime = None,
                       end_date: datetime = None,
                       user_id: str = None,
                       resource_type: str = None,
                       action: AuditAction = None,
                       limit: int = 1000) -> List[Dict[str, Any]]:
        """Get audit trail for a tenant."""
        
        try:
            with get_db_session() as session:
                query = session.query(AuditLogModel).filter(
                    AuditLogModel.tenant_id == tenant_id
                )
                
                # Apply filters
                if start_date:
                    query = query.filter(AuditLogModel.timestamp >= start_date)
                
                if end_date:
                    query = query.filter(AuditLogModel.timestamp <= end_date)
                
                if user_id:
                    query = query.filter(AuditLogModel.user_id == user_id)
                
                if resource_type:
                    query = query.filter(AuditLogModel.resource_type == resource_type)
                
                if action:
                    query = query.filter(AuditLogModel.action == action)
                
                # Order by timestamp descending and limit
                query = query.order_by(AuditLogModel.timestamp.desc()).limit(limit)
                
                results = []
                for log in query.all():
                    results.append({
                        'id': str(log.id),
                        'timestamp': log.timestamp.isoformat(),
                        'user_id': log.user_id,
                        'action': log.action.value if log.action else None,
                        'resource_type': log.resource_type,
                        'resource_id': log.resource_id,
                        'ip_address': log.ip_address,
                        'user_agent': log.user_agent,
                        'details': log.details,
                        'success': log.success
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return []
    
    def get_security_summary(self, tenant_id: str, 
                           days: int = 30) -> Dict[str, Any]:
        """Get security summary for a tenant."""
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            with get_db_session() as session:
                # Total events
                total_events = session.query(AuditLogModel).filter(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp >= start_date
                ).count()
                
                # Failed login attempts
                failed_logins = session.query(AuditLogModel).filter(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.action == AuditAction.LOGIN,
                    AuditLogModel.success == False,
                    AuditLogModel.timestamp >= start_date
                ).count()
                
                # Authorization failures
                auth_failures = session.query(AuditLogModel).filter(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.details.contains({'authorization_failed': True}),
                    AuditLogModel.timestamp >= start_date
                ).count()
                
                # Data access events
                data_access = session.query(AuditLogModel).filter(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.action.in_([AuditAction.READ, AuditAction.EXPORT]),
                    AuditLogModel.timestamp >= start_date
                ).count()
                
                # Data modification events
                data_modifications = session.query(AuditLogModel).filter(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.action.in_([
                        AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE
                    ]),
                    AuditLogModel.timestamp >= start_date
                ).count()
                
                # Top users by activity
                top_users = session.query(
                    AuditLogModel.user_id,
                    func.count(AuditLogModel.id).label('event_count')
                ).filter(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.user_id.isnot(None)
                ).group_by(AuditLogModel.user_id).order_by(
                    func.count(AuditLogModel.id).desc()
                ).limit(10).all()
                
                return {
                    'period_days': days,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'total_events': total_events,
                    'failed_logins': failed_logins,
                    'authorization_failures': auth_failures,
                    'data_access_events': data_access,
                    'data_modification_events': data_modifications,
                    'top_users': [
                        {'user_id': user_id, 'event_count': count}
                        for user_id, count in top_users
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to generate security summary: {e}")
            return {}
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive information from audit details."""
        
        if not details:
            return {}
        
        sanitized = {}
        
        for key, value in details.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


# Global audit logger instance
audit_logger = TenantAuditLogger()


# Convenience functions for common audit operations
def log_authentication(user_id: str, tenant_id: str, success: bool, 
                      ip_address: str = None, **kwargs):
    """Log authentication attempt."""
    return audit_logger.log_authentication(user_id, tenant_id, success, ip_address, kwargs)


def log_authorization_failure(resource_type: str, action: str, 
                            resource_id: str = None, **kwargs):
    """Log authorization failure."""
    return audit_logger.log_authorization_failure(resource_type, action, resource_id, kwargs)


def log_data_access(resource_type: str, resource_id: str = None, 
                   action: AuditAction = AuditAction.READ, **kwargs):
    """Log data access."""
    return audit_logger.log_data_access(resource_type, resource_id, action, kwargs)


def log_data_modification(resource_type: str, resource_id: str, action: AuditAction,
                         old_values: Dict = None, new_values: Dict = None, **kwargs):
    """Log data modification."""
    return audit_logger.log_data_modification(
        resource_type, resource_id, action, old_values, new_values, kwargs
    )


def log_security_event(event_type: str, severity: AuditLevel = AuditLevel.INFO, **kwargs):
    """Log security event."""
    return audit_logger.log_security_event(event_type, severity, kwargs)


def log_admin_action(action: str, target_resource: str, target_id: str = None, **kwargs):
    """Log administrative action."""
    return audit_logger.log_admin_action(action, target_resource, target_id, kwargs)


def get_audit_logger() -> TenantAuditLogger:
    """Get the global audit logger instance."""
    return audit_logger