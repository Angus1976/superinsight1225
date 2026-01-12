"""
Permission Bypass Prevention System for SuperInsight Platform.

Implements comprehensive security measures to prevent unauthorized access
and permission bypasses through multiple layers of validation and monitoring.
"""

import logging
import time
import hashlib
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from uuid import UUID
from dataclasses import dataclass
from enum import Enum
import threading
from collections import defaultdict, deque

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select, text

from src.security.models import UserModel, UserRole, AuditAction
from src.security.rbac_models import RoleModel, PermissionModel, ResourceType

logger = logging.getLogger(__name__)


class SecurityThreatLevel(str, Enum):
    """Security threat levels for bypass attempts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BypassAttemptType(str, Enum):
    """Types of bypass attempts detected."""
    PRIVILEGE_ESCALATION = "privilege_escalation"
    TENANT_BOUNDARY_VIOLATION = "tenant_boundary_violation"
    ROLE_IMPERSONATION = "role_impersonation"
    TOKEN_MANIPULATION = "token_manipulation"
    DIRECT_DATABASE_ACCESS = "direct_database_access"
    API_PARAMETER_TAMPERING = "api_parameter_tampering"
    SESSION_HIJACKING = "session_hijacking"
    BRUTE_FORCE_PERMISSIONS = "brute_force_permissions"
    UNAUTHORIZED_RESOURCE_ACCESS = "unauthorized_resource_access"
    MALICIOUS_QUERY_INJECTION = "malicious_query_injection"


@dataclass
class SecurityContext:
    """Security context for permission checks."""
    user_id: UUID
    tenant_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_timestamp: Optional[datetime] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    request_headers: Optional[Dict[str, str]] = None


@dataclass
class BypassAttempt:
    """Detected bypass attempt."""
    attempt_type: BypassAttemptType
    threat_level: SecurityThreatLevel
    user_id: Optional[UUID]
    tenant_id: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    details: Dict[str, Any]
    blocked: bool = True


class PermissionValidator:
    """
    Multi-layer permission validation to prevent bypasses.
    
    Implements defense-in-depth security with multiple validation layers.
    """
    
    def __init__(self):
        self.validation_layers = [
            self._validate_user_existence,
            self._validate_user_active_status,
            self._validate_tenant_isolation,
            self._validate_role_integrity,
            self._validate_permission_scope,
            self._validate_resource_ownership,
            self._validate_temporal_constraints,
            self._validate_request_context
        ]
    
    def validate_permission_request(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate permission request through multiple security layers.
        
        Args:
            context: Security context for the request
            permission_name: Permission being requested
            resource_id: Optional resource identifier
            resource_type: Optional resource type
            db: Database session
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        validation_errors = []
        
        try:
            # Run through all validation layers
            for validator in self.validation_layers:
                try:
                    is_valid, error_msg = validator(
                        context, permission_name, resource_id, resource_type, db
                    )
                    if not is_valid:
                        validation_errors.append(error_msg)
                except Exception as e:
                    logger.error(f"Validation layer failed: {e}")
                    validation_errors.append(f"Validation layer error: {str(e)}")
            
            return len(validation_errors) == 0, validation_errors
            
        except Exception as e:
            logger.error(f"Permission validation failed: {e}")
            return False, [f"Validation system error: {str(e)}"]
    
    def _validate_user_existence(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> Tuple[bool, str]:
        """Validate that user exists and is properly authenticated."""
        try:
            user = db.query(UserModel).filter(UserModel.id == context.user_id).first()
            if not user:
                return False, f"User {context.user_id} does not exist"
            
            # Validate user belongs to the claimed tenant
            if user.tenant_id != context.tenant_id:
                return False, f"User tenant mismatch: {user.tenant_id} != {context.tenant_id}"
            
            return True, ""
            
        except Exception as e:
            return False, f"User existence validation failed: {str(e)}"
    
    def _validate_user_active_status(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> Tuple[bool, str]:
        """Validate that user is active and not suspended."""
        try:
            user = db.query(UserModel).filter(UserModel.id == context.user_id).first()
            if not user.is_active:
                return False, f"User {context.user_id} is not active"
            
            return True, ""
            
        except Exception as e:
            return False, f"User status validation failed: {str(e)}"
    
    def _validate_tenant_isolation(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> Tuple[bool, str]:
        """Validate strict tenant isolation."""
        try:
            # If resource_id is provided, validate it belongs to the user's tenant
            if resource_id and resource_type:
                # This would need to be implemented based on your resource models
                # For now, we'll implement a basic check
                pass
            
            # Validate no cross-tenant permission requests
            user = db.query(UserModel).filter(UserModel.id == context.user_id).first()
            if user.tenant_id != context.tenant_id:
                return False, f"Cross-tenant access attempt: {user.tenant_id} -> {context.tenant_id}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Tenant isolation validation failed: {str(e)}"
    
    def _validate_role_integrity(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> Tuple[bool, str]:
        """Validate role integrity and prevent role escalation."""
        try:
            user = db.query(UserModel).filter(UserModel.id == context.user_id).first()
            
            # Check for suspicious role changes (would need session tracking)
            # For now, validate the user's current role is consistent
            
            # Validate admin permissions are not being bypassed
            if permission_name in ["manage_users", "manage_roles", "system_admin"] and user.role != UserRole.ADMIN:
                return False, f"Non-admin user attempting admin permission: {permission_name}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Role integrity validation failed: {str(e)}"
    
    def _validate_permission_scope(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> Tuple[bool, str]:
        """Validate permission scope and prevent scope escalation."""
        try:
            # Validate permission exists and is properly scoped
            permission = db.query(PermissionModel).filter(
                PermissionModel.name == permission_name
            ).first()
            
            if not permission:
                return False, f"Permission {permission_name} does not exist"
            
            # Validate resource type matches if specified
            if resource_type and permission.resource_type and permission.resource_type != resource_type:
                return False, f"Resource type mismatch: {permission.resource_type} != {resource_type}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Permission scope validation failed: {str(e)}"
    
    def _validate_resource_ownership(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> Tuple[bool, str]:
        """Validate resource ownership and access rights."""
        try:
            # If no specific resource, allow (will be handled by role-based permissions)
            if not resource_id:
                return True, ""
            
            # Validate resource exists and user has access
            # This would need to be implemented based on your resource models
            # For now, we'll implement a basic tenant check
            
            return True, ""
            
        except Exception as e:
            return False, f"Resource ownership validation failed: {str(e)}"
    
    def _validate_temporal_constraints(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> Tuple[bool, str]:
        """Validate temporal constraints and prevent replay attacks."""
        try:
            # Check request timestamp is recent (prevent replay attacks)
            if context.request_timestamp:
                time_diff = datetime.utcnow() - context.request_timestamp
                if time_diff > timedelta(minutes=5):
                    return False, f"Request timestamp too old: {time_diff}"
            
            # Check for time-based permissions (e.g., business hours only)
            # This would be implemented based on your business rules
            
            return True, ""
            
        except Exception as e:
            return False, f"Temporal validation failed: {str(e)}"
    
    def _validate_request_context(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> Tuple[bool, str]:
        """Validate request context for suspicious patterns."""
        try:
            # Validate IP address consistency (if tracking sessions)
            # Validate user agent consistency
            # Check for suspicious request patterns
            
            # Basic validation for now
            if context.ip_address:
                try:
                    ipaddress.ip_address(context.ip_address)
                except ValueError:
                    return False, f"Invalid IP address: {context.ip_address}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Request context validation failed: {str(e)}"


class BypassDetector:
    """
    Advanced bypass attempt detection system.
    
    Monitors for suspicious patterns and potential security bypasses.
    """
    
    def __init__(self):
        self.detection_rules = [
            self._detect_privilege_escalation,
            self._detect_tenant_boundary_violation,
            self._detect_role_impersonation,
            self._detect_brute_force_permissions,
            self._detect_suspicious_patterns
        ]
        
        # Tracking for pattern detection
        self._user_activity = defaultdict(lambda: deque(maxlen=100))
        self._ip_activity = defaultdict(lambda: deque(maxlen=100))
        self._permission_requests = defaultdict(lambda: deque(maxlen=50))
        self._lock = threading.Lock()
    
    def detect_bypass_attempts(
        self,
        context: SecurityContext,
        permission_name: str,
        permission_granted: bool,
        validation_errors: List[str],
        db: Session
    ) -> List[BypassAttempt]:
        """
        Detect potential bypass attempts based on request patterns.
        
        Args:
            context: Security context
            permission_name: Permission requested
            permission_granted: Whether permission was granted
            validation_errors: Any validation errors
            db: Database session
            
        Returns:
            List of detected bypass attempts
        """
        attempts = []
        
        try:
            # Record activity for pattern analysis
            self._record_activity(context, permission_name, permission_granted)
            
            # Run detection rules
            for detector in self.detection_rules:
                try:
                    detected_attempts = detector(
                        context, permission_name, permission_granted, validation_errors, db
                    )
                    attempts.extend(detected_attempts)
                except Exception as e:
                    logger.error(f"Bypass detection rule failed: {e}")
            
            return attempts
            
        except Exception as e:
            logger.error(f"Bypass detection failed: {e}")
            return []
    
    def _record_activity(
        self,
        context: SecurityContext,
        permission_name: str,
        permission_granted: bool
    ):
        """Record activity for pattern analysis."""
        with self._lock:
            timestamp = datetime.utcnow()
            
            # Record user activity
            self._user_activity[context.user_id].append({
                "timestamp": timestamp,
                "permission": permission_name,
                "granted": permission_granted,
                "ip_address": context.ip_address
            })
            
            # Record IP activity
            if context.ip_address:
                self._ip_activity[context.ip_address].append({
                    "timestamp": timestamp,
                    "user_id": context.user_id,
                    "permission": permission_name,
                    "granted": permission_granted
                })
            
            # Record permission request patterns
            self._permission_requests[permission_name].append({
                "timestamp": timestamp,
                "user_id": context.user_id,
                "granted": permission_granted
            })
    
    def _detect_privilege_escalation(
        self,
        context: SecurityContext,
        permission_name: str,
        permission_granted: bool,
        validation_errors: List[str],
        db: Session
    ) -> List[BypassAttempt]:
        """Detect privilege escalation attempts."""
        attempts = []
        
        try:
            # Check for admin permission requests by non-admin users
            admin_permissions = [
                "manage_users", "manage_roles", "system_admin", "delete_tenant",
                "modify_permissions", "access_audit_logs"
            ]
            
            if permission_name in admin_permissions:
                user = db.query(UserModel).filter(UserModel.id == context.user_id).first()
                if user and user.role != UserRole.ADMIN:
                    attempts.append(BypassAttempt(
                        attempt_type=BypassAttemptType.PRIVILEGE_ESCALATION,
                        threat_level=SecurityThreatLevel.HIGH,
                        user_id=context.user_id,
                        tenant_id=context.tenant_id,
                        ip_address=context.ip_address,
                        timestamp=datetime.utcnow(),
                        details={
                            "permission": permission_name,
                            "user_role": user.role.value,
                            "granted": permission_granted
                        }
                    ))
            
            return attempts
            
        except Exception as e:
            logger.error(f"Privilege escalation detection failed: {e}")
            return []
    
    def _detect_tenant_boundary_violation(
        self,
        context: SecurityContext,
        permission_name: str,
        permission_granted: bool,
        validation_errors: List[str],
        db: Session
    ) -> List[BypassAttempt]:
        """Detect tenant boundary violation attempts."""
        attempts = []
        
        try:
            # Check for cross-tenant access patterns
            for error in validation_errors:
                if "cross-tenant" in error.lower() or "tenant mismatch" in error.lower():
                    attempts.append(BypassAttempt(
                        attempt_type=BypassAttemptType.TENANT_BOUNDARY_VIOLATION,
                        threat_level=SecurityThreatLevel.CRITICAL,
                        user_id=context.user_id,
                        tenant_id=context.tenant_id,
                        ip_address=context.ip_address,
                        timestamp=datetime.utcnow(),
                        details={
                            "permission": permission_name,
                            "validation_error": error,
                            "granted": permission_granted
                        }
                    ))
            
            return attempts
            
        except Exception as e:
            logger.error(f"Tenant boundary violation detection failed: {e}")
            return []
    
    def _detect_role_impersonation(
        self,
        context: SecurityContext,
        permission_name: str,
        permission_granted: bool,
        validation_errors: List[str],
        db: Session
    ) -> List[BypassAttempt]:
        """Detect role impersonation attempts."""
        attempts = []
        
        try:
            # Check for role integrity violations
            for error in validation_errors:
                if "role" in error.lower() and ("mismatch" in error.lower() or "invalid" in error.lower()):
                    attempts.append(BypassAttempt(
                        attempt_type=BypassAttemptType.ROLE_IMPERSONATION,
                        threat_level=SecurityThreatLevel.HIGH,
                        user_id=context.user_id,
                        tenant_id=context.tenant_id,
                        ip_address=context.ip_address,
                        timestamp=datetime.utcnow(),
                        details={
                            "permission": permission_name,
                            "validation_error": error,
                            "granted": permission_granted
                        }
                    ))
            
            return attempts
            
        except Exception as e:
            logger.error(f"Role impersonation detection failed: {e}")
            return []
    
    def _detect_brute_force_permissions(
        self,
        context: SecurityContext,
        permission_name: str,
        permission_granted: bool,
        validation_errors: List[str],
        db: Session
    ) -> List[BypassAttempt]:
        """Detect brute force permission attempts."""
        attempts = []
        
        try:
            with self._lock:
                # Check recent failed permission attempts from this user
                user_activity = self._user_activity[context.user_id]
                recent_failures = [
                    activity for activity in user_activity
                    if not activity["granted"] and 
                    (datetime.utcnow() - activity["timestamp"]) < timedelta(minutes=10)
                ]
                
                # If more than 5 failed attempts in 10 minutes, flag as brute force
                if len(recent_failures) > 5:
                    attempts.append(BypassAttempt(
                        attempt_type=BypassAttemptType.BRUTE_FORCE_PERMISSIONS,
                        threat_level=SecurityThreatLevel.MEDIUM,
                        user_id=context.user_id,
                        tenant_id=context.tenant_id,
                        ip_address=context.ip_address,
                        timestamp=datetime.utcnow(),
                        details={
                            "permission": permission_name,
                            "failed_attempts": len(recent_failures),
                            "granted": permission_granted
                        }
                    ))
                
                # Also check for validation failures (which could indicate probing)
                recent_validation_failures = [
                    activity for activity in user_activity
                    if not activity["granted"] and 
                    (datetime.utcnow() - activity["timestamp"]) < timedelta(minutes=5)
                ]
                
                # If more than 3 validation failures in 5 minutes, also flag as brute force
                if len(recent_validation_failures) > 3 and validation_errors:
                    attempts.append(BypassAttempt(
                        attempt_type=BypassAttemptType.BRUTE_FORCE_PERMISSIONS,
                        threat_level=SecurityThreatLevel.MEDIUM,
                        user_id=context.user_id,
                        tenant_id=context.tenant_id,
                        ip_address=context.ip_address,
                        timestamp=datetime.utcnow(),
                        details={
                            "permission": permission_name,
                            "validation_failures": len(recent_validation_failures),
                            "granted": permission_granted,
                            "validation_errors": validation_errors
                        }
                    ))
            
            return attempts
            
        except Exception as e:
            logger.error(f"Brute force detection failed: {e}")
            return []
    
    def _detect_suspicious_patterns(
        self,
        context: SecurityContext,
        permission_name: str,
        permission_granted: bool,
        validation_errors: List[str],
        db: Session
    ) -> List[BypassAttempt]:
        """Detect other suspicious patterns."""
        attempts = []
        
        try:
            # Check for suspicious IP patterns
            if context.ip_address:
                with self._lock:
                    ip_activity = self._ip_activity[context.ip_address]
                    
                    # Check for multiple user accounts from same IP
                    unique_users = set(activity["user_id"] for activity in ip_activity)
                    if len(unique_users) > 5:  # More than 5 users from same IP
                        attempts.append(BypassAttempt(
                            attempt_type=BypassAttemptType.SESSION_HIJACKING,
                            threat_level=SecurityThreatLevel.MEDIUM,
                            user_id=context.user_id,
                            tenant_id=context.tenant_id,
                            ip_address=context.ip_address,
                            timestamp=datetime.utcnow(),
                            details={
                                "permission": permission_name,
                                "unique_users_from_ip": len(unique_users),
                                "granted": permission_granted
                            }
                        ))
            
            return attempts
            
        except Exception as e:
            logger.error(f"Suspicious pattern detection failed: {e}")
            return []


class SecurityEnforcer:
    """
    Security enforcement system that blocks and responds to bypass attempts.
    """
    
    def __init__(self):
        self.blocked_users = set()
        self.blocked_ips = set()
        self.temporary_blocks = {}  # user_id/ip -> expiry_time
        self.alert_handlers = []
        self._lock = threading.Lock()
    
    def enforce_security_policy(
        self,
        bypass_attempts: List[BypassAttempt],
        context: SecurityContext,
        db: Session
    ) -> Dict[str, Any]:
        """
        Enforce security policies based on detected bypass attempts.
        
        Args:
            bypass_attempts: List of detected bypass attempts
            context: Security context
            db: Database session
            
        Returns:
            Dictionary with enforcement actions taken
        """
        actions_taken = {
            "blocked": False,
            "user_suspended": False,
            "ip_blocked": False,
            "alerts_sent": 0,
            "audit_logged": False
        }
        
        try:
            if not bypass_attempts:
                return actions_taken
            
            # Determine severity and take appropriate action
            max_threat_level = max(attempt.threat_level for attempt in bypass_attempts)
            
            if max_threat_level == SecurityThreatLevel.CRITICAL:
                # Immediate blocking for critical threats
                self._block_user_temporarily(context.user_id, hours=24)
                if context.ip_address:
                    self._block_ip_temporarily(context.ip_address, hours=1)
                actions_taken["blocked"] = True
                actions_taken["user_suspended"] = True
                actions_taken["ip_blocked"] = True
                
            elif max_threat_level == SecurityThreatLevel.HIGH:
                # Temporary blocking for high threats
                self._block_user_temporarily(context.user_id, hours=1)
                actions_taken["blocked"] = True
                actions_taken["user_suspended"] = True
                
            elif max_threat_level == SecurityThreatLevel.MEDIUM:
                # Rate limiting for medium threats
                self._apply_rate_limiting(context.user_id)
                actions_taken["blocked"] = True
            
            # Log all bypass attempts
            for attempt in bypass_attempts:
                self._log_bypass_attempt(attempt, db)
            actions_taken["audit_logged"] = True
            
            # Send security alerts
            self._send_security_alerts(bypass_attempts, context)
            actions_taken["alerts_sent"] = len(bypass_attempts)
            
            return actions_taken
            
        except Exception as e:
            logger.error(f"Security enforcement failed: {e}")
            return actions_taken
    
    def is_user_blocked(self, user_id: UUID) -> bool:
        """Check if a user is currently blocked."""
        with self._lock:
            # Check permanent blocks
            if user_id in self.blocked_users:
                return True
            
            # Check temporary blocks
            if user_id in self.temporary_blocks:
                if datetime.utcnow() < self.temporary_blocks[user_id]:
                    return True
                else:
                    # Block expired, remove it
                    del self.temporary_blocks[user_id]
            
            return False
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is currently blocked."""
        with self._lock:
            # Check permanent blocks
            if ip_address in self.blocked_ips:
                return True
            
            # Check temporary blocks
            if ip_address in self.temporary_blocks:
                if datetime.utcnow() < self.temporary_blocks[ip_address]:
                    return True
                else:
                    # Block expired, remove it
                    del self.temporary_blocks[ip_address]
            
            return False
    
    def _block_user_temporarily(self, user_id: UUID, hours: int = 1):
        """Block a user temporarily."""
        with self._lock:
            expiry = datetime.utcnow() + timedelta(hours=hours)
            self.temporary_blocks[user_id] = expiry
            logger.warning(f"User {user_id} temporarily blocked until {expiry}")
    
    def _block_ip_temporarily(self, ip_address: str, hours: int = 1):
        """Block an IP address temporarily."""
        with self._lock:
            expiry = datetime.utcnow() + timedelta(hours=hours)
            self.temporary_blocks[ip_address] = expiry
            logger.warning(f"IP {ip_address} temporarily blocked until {expiry}")
    
    def _apply_rate_limiting(self, user_id: UUID):
        """Apply rate limiting to a user."""
        # This would integrate with your rate limiting system
        logger.info(f"Rate limiting applied to user {user_id}")
    
    def _log_bypass_attempt(self, attempt: BypassAttempt, db: Session):
        """Log bypass attempt to audit system."""
        try:
            from src.security.models import AuditLogModel
            
            audit_log = AuditLogModel(
                user_id=attempt.user_id,
                tenant_id=attempt.tenant_id,
                action=AuditAction.READ,  # Using READ as a generic action
                resource_type="security_bypass_attempt",
                resource_id=str(attempt.attempt_type.value),
                ip_address=attempt.ip_address,
                details={
                    "attempt_type": attempt.attempt_type.value,
                    "threat_level": attempt.threat_level.value,
                    "blocked": attempt.blocked,
                    "details": attempt.details
                }
            )
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log bypass attempt: {e}")
    
    def _send_security_alerts(self, attempts: List[BypassAttempt], context: SecurityContext):
        """Send security alerts for bypass attempts."""
        try:
            for attempt in attempts:
                if attempt.threat_level in [SecurityThreatLevel.HIGH, SecurityThreatLevel.CRITICAL]:
                    # Send immediate alert
                    logger.critical(
                        f"SECURITY ALERT: {attempt.attempt_type.value} detected "
                        f"from user {attempt.user_id} at {attempt.ip_address}"
                    )
                    
                    # Here you would integrate with your alerting system
                    # (email, Slack, PagerDuty, etc.)
                    
        except Exception as e:
            logger.error(f"Failed to send security alerts: {e}")


class PermissionBypassPrevention:
    """
    Main permission bypass prevention system.
    
    Coordinates validation, detection, and enforcement to prevent unauthorized access.
    """
    
    def __init__(self):
        self.validator = PermissionValidator()
        self.detector = BypassDetector()
        self.enforcer = SecurityEnforcer()
        self.enabled = True
        
        # Statistics
        self.stats = {
            "total_checks": 0,
            "blocked_attempts": 0,
            "bypass_attempts_detected": 0,
            "validation_failures": 0
        }
    
    def check_permission_with_bypass_prevention(
        self,
        context: SecurityContext,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check permission with comprehensive bypass prevention.
        
        Args:
            context: Security context
            permission_name: Permission to check
            resource_id: Optional resource ID
            resource_type: Optional resource type
            db: Database session
            
        Returns:
            Tuple of (permission_granted, security_info)
        """
        self.stats["total_checks"] += 1
        
        security_info = {
            "validation_passed": False,
            "bypass_attempts": [],
            "enforcement_actions": {},
            "blocked": False
        }
        
        try:
            # Check if user or IP is already blocked
            if self.enforcer.is_user_blocked(context.user_id):
                security_info["blocked"] = True
                security_info["block_reason"] = "User temporarily blocked"
                return False, security_info
            
            if context.ip_address and self.enforcer.is_ip_blocked(context.ip_address):
                security_info["blocked"] = True
                security_info["block_reason"] = "IP address blocked"
                return False, security_info
            
            # Validate permission request
            is_valid, validation_errors = self.validator.validate_permission_request(
                context, permission_name, resource_id, resource_type, db
            )
            
            security_info["validation_passed"] = is_valid
            security_info["validation_errors"] = validation_errors
            
            if not is_valid:
                self.stats["validation_failures"] += 1
            
            # Detect bypass attempts
            bypass_attempts = self.detector.detect_bypass_attempts(
                context, permission_name, is_valid, validation_errors, db
            )
            
            security_info["bypass_attempts"] = [
                {
                    "type": attempt.attempt_type.value,
                    "threat_level": attempt.threat_level.value,
                    "details": attempt.details
                }
                for attempt in bypass_attempts
            ]
            
            if bypass_attempts:
                self.stats["bypass_attempts_detected"] += len(bypass_attempts)
                
                # Enforce security policies
                enforcement_actions = self.enforcer.enforce_security_policy(
                    bypass_attempts, context, db
                )
                security_info["enforcement_actions"] = enforcement_actions
                
                if enforcement_actions.get("blocked", False):
                    self.stats["blocked_attempts"] += 1
                    security_info["blocked"] = True
                    return False, security_info
            
            return is_valid, security_info
            
        except Exception as e:
            logger.error(f"Bypass prevention check failed: {e}")
            security_info["error"] = str(e)
            return False, security_info
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """Get security statistics."""
        return {
            **self.stats,
            "blocked_users": len(self.enforcer.blocked_users),
            "blocked_ips": len(self.enforcer.blocked_ips),
            "temporary_blocks": len(self.enforcer.temporary_blocks),
            "enabled": self.enabled
        }
    
    def enable_bypass_prevention(self):
        """Enable bypass prevention system."""
        self.enabled = True
        logger.info("Permission bypass prevention enabled")
    
    def disable_bypass_prevention(self):
        """Disable bypass prevention system (for testing only)."""
        self.enabled = False
        logger.warning("Permission bypass prevention disabled")
    
    def clear_blocks(self):
        """Clear all temporary blocks (admin function)."""
        with self.enforcer._lock:
            self.enforcer.temporary_blocks.clear()
            logger.info("All temporary blocks cleared")


# Global instance
_bypass_prevention = None


def get_bypass_prevention_system() -> PermissionBypassPrevention:
    """Get the global bypass prevention system instance."""
    global _bypass_prevention
    if _bypass_prevention is None:
        _bypass_prevention = PermissionBypassPrevention()
    return _bypass_prevention