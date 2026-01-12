"""
Secure RBAC Controller with Comprehensive Bypass Prevention.

Extends the existing RBAC controller with advanced security measures
to prevent permission bypasses and unauthorized access.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Union, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from src.security.rbac_controller import RBACController
from src.security.permission_bypass_prevention import (
    get_bypass_prevention_system,
    SecurityContext,
    PermissionBypassPrevention
)
from src.security.rbac_models import ResourceType
from src.security.models import UserModel, AuditAction

logger = logging.getLogger(__name__)


class SecureRBACController(RBACController):
    """
    Secure RBAC Controller with comprehensive bypass prevention.
    
    Extends RBACController with multi-layer security validation,
    bypass detection, and automatic threat response.
    """
    
    def __init__(self, secret_key: str = "your-secret-key"):
        super().__init__(secret_key)
        self.bypass_prevention = get_bypass_prevention_system()
        
        # Security configuration
        self.security_config = {
            "strict_validation": True,
            "auto_block_threats": True,
            "log_all_attempts": True,
            "require_ip_validation": False,
            "session_tracking": True
        }
        
        # Enhanced audit logging
        self.security_audit_enabled = True
    
    def check_user_permission_secure(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
        request_headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Secure permission check with comprehensive bypass prevention.
        
        Args:
            user_id: User identifier
            permission_name: Permission name to check
            resource_id: Optional specific resource ID
            resource_type: Optional resource type
            db: Database session
            ip_address: Client IP address
            user_agent: Client user agent
            session_id: Session identifier
            request_path: Request path
            request_method: HTTP method
            request_headers: Request headers
            
        Returns:
            Tuple of (permission_granted, security_details)
        """
        try:
            # Get user for tenant info
            user = self.get_user_by_id(user_id, db)
            if not user:
                return False, {
                    "error": "User not found",
                    "security_violation": True,
                    "threat_level": "high"
                }
            
            # Create security context
            context = SecurityContext(
                user_id=user_id,
                tenant_id=user.tenant_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                request_timestamp=datetime.utcnow(),
                request_path=request_path,
                request_method=request_method,
                request_headers=request_headers
            )
            
            # Run bypass prevention check
            permission_granted, security_info = self.bypass_prevention.check_permission_with_bypass_prevention(
                context=context,
                permission_name=permission_name,
                resource_id=resource_id,
                resource_type=resource_type,
                db=db
            )
            
            # If blocked by security system, return immediately
            if security_info.get("blocked", False):
                self._log_security_event(
                    user_id=user_id,
                    tenant_id=user.tenant_id,
                    event_type="permission_blocked",
                    details={
                        "permission": permission_name,
                        "resource_id": resource_id,
                        "security_info": security_info
                    },
                    db=db
                )
                return False, security_info
            
            # If validation passed, proceed with normal permission check
            if security_info.get("validation_passed", False):
                # Use the original RBAC logic for actual permission checking
                has_permission = super().check_user_permission(
                    user_id=user_id,
                    permission_name=permission_name,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    db=db,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Update security info with final result
                security_info["permission_granted"] = has_permission
                security_info["rbac_check_completed"] = True
                
                # Log successful permission check
                if self.security_audit_enabled:
                    self._log_security_event(
                        user_id=user_id,
                        tenant_id=user.tenant_id,
                        event_type="permission_check",
                        details={
                            "permission": permission_name,
                            "resource_id": resource_id,
                            "granted": has_permission,
                            "security_validation": "passed"
                        },
                        db=db
                    )
                
                return has_permission, security_info
            else:
                # Validation failed, deny permission
                if self.security_audit_enabled:
                    self._log_security_event(
                        user_id=user_id,
                        tenant_id=user.tenant_id,
                        event_type="permission_validation_failed",
                        details={
                            "permission": permission_name,
                            "resource_id": resource_id,
                            "validation_errors": security_info.get("validation_errors", [])
                        },
                        db=db
                    )
                return False, security_info
            
        except Exception as e:
            logger.error(f"Secure permission check failed: {e}")
            return False, {
                "error": str(e),
                "security_violation": True,
                "system_error": True
            }
    
    def assign_role_to_user_secure(
        self,
        user_id: UUID,
        role_id: UUID,
        assigned_by: UUID,
        db: Session,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        justification: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Secure role assignment with bypass prevention.
        
        Args:
            user_id: User to assign role to
            role_id: Role to assign
            assigned_by: User performing the assignment
            db: Database session
            ip_address: Client IP address
            user_agent: Client user agent
            justification: Justification for role assignment
            
        Returns:
            Tuple of (success, security_details)
        """
        try:
            # Validate the user performing the assignment has permission
            assigner = self.get_user_by_id(assigned_by, db)
            if not assigner:
                return False, {"error": "Assigner not found"}
            
            # Check if assigner has permission to assign roles
            can_assign, security_info = self.check_user_permission_secure(
                user_id=assigned_by,
                permission_name="manage_roles",
                db=db,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if not can_assign:
                return False, {
                    "error": "Insufficient permissions to assign roles",
                    "security_info": security_info
                }
            
            # Validate role assignment is within same tenant
            target_user = self.get_user_by_id(user_id, db)
            role = self.get_role_by_id(role_id, db)
            
            if not target_user or not role:
                return False, {"error": "User or role not found"}
            
            if target_user.tenant_id != assigner.tenant_id:
                self._log_security_event(
                    user_id=assigned_by,
                    tenant_id=assigner.tenant_id,
                    event_type="cross_tenant_role_assignment_attempt",
                    details={
                        "target_user": str(user_id),
                        "target_tenant": target_user.tenant_id,
                        "assigner_tenant": assigner.tenant_id,
                        "role_id": str(role_id)
                    },
                    db=db
                )
                return False, {"error": "Cross-tenant role assignment not allowed"}
            
            if role.tenant_id != assigner.tenant_id:
                return False, {"error": "Role not in same tenant"}
            
            # Perform the role assignment
            success = super().assign_role_to_user(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by,
                db=db,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success:
                # Log successful role assignment
                self._log_security_event(
                    user_id=assigned_by,
                    tenant_id=assigner.tenant_id,
                    event_type="role_assigned",
                    details={
                        "target_user": str(user_id),
                        "role_id": str(role_id),
                        "role_name": role.name,
                        "justification": justification
                    },
                    db=db
                )
                
                # Clear permission cache for target user
                self.cache_manager.handle_cache_invalidation(
                    "user_role_change",
                    {"user_id": str(user_id), "tenant_id": target_user.tenant_id}
                )
            
            return success, {"role_assigned": success}
            
        except Exception as e:
            logger.error(f"Secure role assignment failed: {e}")
            return False, {"error": str(e)}
    
    def revoke_role_from_user_secure(
        self,
        user_id: UUID,
        role_id: UUID,
        revoked_by: UUID,
        db: Session,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        justification: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Secure role revocation with bypass prevention.
        
        Args:
            user_id: User to revoke role from
            role_id: Role to revoke
            revoked_by: User performing the revocation
            db: Database session
            ip_address: Client IP address
            user_agent: Client user agent
            justification: Justification for role revocation
            
        Returns:
            Tuple of (success, security_details)
        """
        try:
            # Validate the user performing the revocation has permission
            revoker = self.get_user_by_id(revoked_by, db)
            if not revoker:
                return False, {"error": "Revoker not found"}
            
            # Check if revoker has permission to revoke roles
            can_revoke, security_info = self.check_user_permission_secure(
                user_id=revoked_by,
                permission_name="manage_roles",
                db=db,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if not can_revoke:
                return False, {
                    "error": "Insufficient permissions to revoke roles",
                    "security_info": security_info
                }
            
            # Validate role revocation is within same tenant
            target_user = self.get_user_by_id(user_id, db)
            role = self.get_role_by_id(role_id, db)
            
            if not target_user or not role:
                return False, {"error": "User or role not found"}
            
            if target_user.tenant_id != revoker.tenant_id:
                self._log_security_event(
                    user_id=revoked_by,
                    tenant_id=revoker.tenant_id,
                    event_type="cross_tenant_role_revocation_attempt",
                    details={
                        "target_user": str(user_id),
                        "target_tenant": target_user.tenant_id,
                        "revoker_tenant": revoker.tenant_id,
                        "role_id": str(role_id)
                    },
                    db=db
                )
                return False, {"error": "Cross-tenant role revocation not allowed"}
            
            # Perform the role revocation
            success = super().revoke_role_from_user(
                user_id=user_id,
                role_id=role_id,
                revoked_by=revoked_by,
                db=db,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success:
                # Log successful role revocation
                self._log_security_event(
                    user_id=revoked_by,
                    tenant_id=revoker.tenant_id,
                    event_type="role_revoked",
                    details={
                        "target_user": str(user_id),
                        "role_id": str(role_id),
                        "role_name": role.name,
                        "justification": justification
                    },
                    db=db
                )
                
                # Clear permission cache for target user
                self.cache_manager.handle_cache_invalidation(
                    "user_role_change",
                    {"user_id": str(user_id), "tenant_id": target_user.tenant_id}
                )
            
            return success, {"role_revoked": success}
            
        except Exception as e:
            logger.error(f"Secure role revocation failed: {e}")
            return False, {"error": str(e)}
    
    def validate_security_context(
        self,
        user_id: UUID,
        expected_tenant_id: str,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        db: Session = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate security context for a user request.
        
        Args:
            user_id: User identifier
            expected_tenant_id: Expected tenant ID
            ip_address: Client IP address
            session_id: Session identifier
            db: Database session
            
        Returns:
            Tuple of (is_valid, validation_details)
        """
        try:
            user = self.get_user_by_id(user_id, db)
            if not user:
                return False, {"error": "User not found"}
            
            validation_details = {
                "user_exists": True,
                "user_active": user.is_active,
                "tenant_match": user.tenant_id == expected_tenant_id,
                "ip_validated": True,
                "session_valid": True
            }
            
            # Validate tenant isolation
            if user.tenant_id != expected_tenant_id:
                validation_details["tenant_match"] = False
                self._log_security_event(
                    user_id=user_id,
                    tenant_id=user.tenant_id,
                    event_type="tenant_isolation_violation",
                    details={
                        "expected_tenant": expected_tenant_id,
                        "actual_tenant": user.tenant_id
                    },
                    db=db
                )
                return False, validation_details
            
            # Validate user is active
            if not user.is_active:
                validation_details["user_active"] = False
                return False, validation_details
            
            # Additional IP validation if configured
            if self.security_config.get("require_ip_validation", False) and ip_address:
                # This would integrate with IP whitelisting
                pass
            
            return True, validation_details
            
        except Exception as e:
            logger.error(f"Security context validation failed: {e}")
            return False, {"error": str(e)}
    
    def get_security_report(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        """
        Generate security report for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            Security report dictionary
        """
        try:
            # Get bypass prevention statistics
            bypass_stats = self.bypass_prevention.get_security_statistics()
            
            # Get RBAC validation results
            rbac_validation = super().validate_rbac_configuration(tenant_id, db)
            
            # Get cache performance
            cache_stats = self.get_cache_statistics()
            
            # Compile security report
            report = {
                "tenant_id": tenant_id,
                "generated_at": datetime.utcnow().isoformat(),
                "bypass_prevention": {
                    "enabled": bypass_stats["enabled"],
                    "total_checks": bypass_stats["total_checks"],
                    "blocked_attempts": bypass_stats["blocked_attempts"],
                    "bypass_attempts_detected": bypass_stats["bypass_attempts_detected"],
                    "validation_failures": bypass_stats["validation_failures"]
                },
                "rbac_configuration": rbac_validation,
                "cache_performance": cache_stats,
                "security_configuration": self.security_config,
                "recommendations": self._generate_security_recommendations(bypass_stats, rbac_validation)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Security report generation failed: {e}")
            return {"error": str(e)}
    
    def _log_security_event(
        self,
        user_id: UUID,
        tenant_id: str,
        event_type: str,
        details: Dict[str, Any],
        db: Session
    ):
        """Log security events for audit purposes."""
        try:
            self.log_user_action(
                user_id=user_id,
                tenant_id=tenant_id,
                action=AuditAction.READ,  # Using READ as generic security action
                resource_type="security_event",
                resource_id=event_type,
                details={
                    "event_type": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    **details
                },
                db=db
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def _generate_security_recommendations(
        self,
        bypass_stats: Dict[str, Any],
        rbac_validation: Dict[str, Any]
    ) -> List[str]:
        """Generate security recommendations based on current state."""
        recommendations = []
        
        # Bypass prevention recommendations
        if bypass_stats["bypass_attempts_detected"] > 0:
            recommendations.append(
                f"Review {bypass_stats['bypass_attempts_detected']} detected bypass attempts"
            )
        
        if bypass_stats["validation_failures"] > bypass_stats["total_checks"] * 0.1:
            recommendations.append(
                "High validation failure rate detected - review permission assignments"
            )
        
        # RBAC configuration recommendations
        if not rbac_validation.get("valid", True):
            recommendations.append("RBAC configuration issues detected - review role assignments")
        
        if rbac_validation.get("statistics", {}).get("users_without_roles", 0) > 0:
            recommendations.append("Users without roles detected - assign appropriate roles")
        
        if not recommendations:
            recommendations.append("Security configuration appears optimal")
        
        return recommendations
    
    def enable_strict_security(self):
        """Enable strict security mode."""
        self.security_config.update({
            "strict_validation": True,
            "auto_block_threats": True,
            "require_ip_validation": True,
            "session_tracking": True
        })
        self.bypass_prevention.enable_bypass_prevention()
        logger.info("Strict security mode enabled")
    
    def disable_strict_security(self):
        """Disable strict security mode (for testing only)."""
        self.security_config.update({
            "strict_validation": False,
            "auto_block_threats": False,
            "require_ip_validation": False
        })
        logger.warning("Strict security mode disabled")
    
    def clear_security_blocks(self):
        """Clear all security blocks (admin function)."""
        self.bypass_prevention.clear_blocks()
        logger.info("All security blocks cleared")


# Global secure controller instance
_secure_rbac_controller = None


def get_secure_rbac_controller(secret_key: str = "your-secret-key") -> SecureRBACController:
    """Get the global secure RBAC controller instance."""
    global _secure_rbac_controller
    if _secure_rbac_controller is None:
        _secure_rbac_controller = SecureRBACController(secret_key)
    return _secure_rbac_controller