"""
Permission Manager for SuperInsight Platform.

Implements fine-grained permission control with dynamic policies including:
- Time-based access control
- IP whitelist restrictions
- Sensitivity level checks
- Attribute-based access control (ABAC)
- Permission decision logging
"""

import logging
import ipaddress
from datetime import datetime, time
from typing import Dict, List, Optional, Any, Set
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.security.rbac_engine import RBACEngine, AccessDecision, Permission, get_rbac_engine
from src.models.security import (
    DynamicPolicyModel, PolicyType, AuditLogModel,
    IPWhitelistModel
)

logger = logging.getLogger(__name__)


@dataclass
class AccessContext:
    """Context information for access decisions."""
    ip_address: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    sensitivity_level: Optional[int] = None


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    allowed: bool
    policy_name: Optional[str] = None
    policy_type: Optional[PolicyType] = None
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class PermissionManager:
    """
    Permission Manager with dynamic policy support.
    
    Extends RBAC with context-aware access control:
    - Time-based restrictions
    - IP whitelist enforcement
    - Sensitivity level checks
    - Attribute-based policies
    - Comprehensive audit logging
    """
    
    def __init__(self, rbac_engine: Optional[RBACEngine] = None):
        self.logger = logging.getLogger(__name__)
        self.rbac_engine = rbac_engine or get_rbac_engine()
        
        # Policy evaluation order (higher priority first)
        self.policy_priority = [
            PolicyType.IP_WHITELIST,
            PolicyType.TIME_RANGE,
            PolicyType.SENSITIVITY_LEVEL,
            PolicyType.RATE_LIMIT,
            PolicyType.ATTRIBUTE
        ]
    
    # ========================================================================
    # Main Access Check
    # ========================================================================
    
    def check_access(
        self,
        user_id: UUID,
        resource: str,
        action: str,
        tenant_id: str,
        context: Optional[AccessContext] = None,
        db: Session = None
    ) -> AccessDecision:
        """
        Check access with RBAC and dynamic policies.
        
        Args:
            user_id: User requesting access
            resource: Resource identifier
            action: Action to perform
            tenant_id: Tenant context
            context: Optional access context
            db: Database session
            
        Returns:
            AccessDecision with result and details
        """
        context = context or AccessContext()
        
        # Step 1: Check RBAC permissions
        rbac_decision = self.rbac_engine.check_permission(
            user_id=user_id,
            resource=resource,
            action=action,
            tenant_id=tenant_id,
            db=db
        )
        
        if not rbac_decision.allowed:
            self._log_decision(
                user_id=user_id,
                resource=resource,
                action=action,
                tenant_id=tenant_id,
                decision=rbac_decision,
                context=context,
                db=db
            )
            return rbac_decision
        
        # Step 2: Check dynamic policies
        policy_result = self._check_dynamic_policies(
            user_id=user_id,
            resource=resource,
            action=action,
            tenant_id=tenant_id,
            context=context,
            db=db
        )
        
        if not policy_result.allowed:
            decision = AccessDecision(
                allowed=False,
                reason=policy_result.reason,
                policy_applied=policy_result.policy_name
            )
            self._log_decision(
                user_id=user_id,
                resource=resource,
                action=action,
                tenant_id=tenant_id,
                decision=decision,
                context=context,
                db=db
            )
            return decision
        
        # Access granted
        decision = AccessDecision(
            allowed=True,
            reason="Access granted",
            matched_permission=rbac_decision.matched_permission
        )
        
        self._log_decision(
            user_id=user_id,
            resource=resource,
            action=action,
            tenant_id=tenant_id,
            decision=decision,
            context=context,
            db=db
        )
        
        return decision
    
    # ========================================================================
    # Dynamic Policy Checks
    # ========================================================================
    
    def _check_dynamic_policies(
        self,
        user_id: UUID,
        resource: str,
        action: str,
        tenant_id: str,
        context: AccessContext,
        db: Session
    ) -> PolicyResult:
        """Check all applicable dynamic policies."""
        # Get active policies for tenant, ordered by priority
        policies = db.query(DynamicPolicyModel).filter(
            and_(
                DynamicPolicyModel.tenant_id == tenant_id,
                DynamicPolicyModel.enabled == True
            )
        ).order_by(DynamicPolicyModel.priority.desc()).all()
        
        # Filter policies that apply to this resource
        applicable_policies = [
            p for p in policies
            if self._policy_applies_to_resource(p.resource_pattern, resource)
        ]
        
        # Evaluate policies in priority order
        for policy in applicable_policies:
            result = self._evaluate_policy(policy, user_id, context, db)
            if not result.allowed:
                return result
        
        return PolicyResult(allowed=True)
    
    def _policy_applies_to_resource(self, pattern: str, resource: str) -> bool:
        """Check if policy pattern matches resource."""
        import fnmatch
        return fnmatch.fnmatch(resource, pattern)
    
    def _evaluate_policy(
        self,
        policy: DynamicPolicyModel,
        user_id: UUID,
        context: AccessContext,
        db: Session
    ) -> PolicyResult:
        """Evaluate a single policy."""
        try:
            if policy.policy_type == PolicyType.TIME_RANGE:
                return self._check_time_range(policy, context)
            elif policy.policy_type == PolicyType.IP_WHITELIST:
                return self._check_ip_whitelist(policy, context, db)
            elif policy.policy_type == PolicyType.SENSITIVITY_LEVEL:
                return self._check_sensitivity_level(policy, user_id, context, db)
            elif policy.policy_type == PolicyType.ATTRIBUTE:
                return self._check_attribute_policy(policy, user_id, context, db)
            elif policy.policy_type == PolicyType.RATE_LIMIT:
                return self._check_rate_limit(policy, user_id, context, db)
            else:
                self.logger.warning(f"Unknown policy type: {policy.policy_type}")
                return PolicyResult(allowed=True)
        except Exception as e:
            self.logger.error(f"Error evaluating policy {policy.name}: {e}")
            # Fail open or closed based on policy configuration
            if policy.deny_by_default:
                return PolicyResult(
                    allowed=False,
                    policy_name=policy.name,
                    policy_type=policy.policy_type,
                    reason=f"Policy evaluation error: {str(e)}"
                )
            return PolicyResult(allowed=True)
    
    # ========================================================================
    # Time Range Policy
    # ========================================================================
    
    def _check_time_range(
        self,
        policy: DynamicPolicyModel,
        context: AccessContext
    ) -> PolicyResult:
        """
        Check time-based access restrictions.
        
        Config format:
        {
            "start_hour": 9,
            "end_hour": 18,
            "allowed_days": [0, 1, 2, 3, 4],  # Monday-Friday
            "timezone": "UTC"
        }
        """
        config = policy.config
        
        start_hour = config.get("start_hour", 0)
        end_hour = config.get("end_hour", 24)
        allowed_days = config.get("allowed_days", [0, 1, 2, 3, 4, 5, 6])
        
        current_hour = context.timestamp.hour
        current_day = context.timestamp.weekday()
        
        # Check day of week
        if current_day not in allowed_days:
            return PolicyResult(
                allowed=False,
                policy_name=policy.name,
                policy_type=policy.policy_type,
                reason=f"Access not allowed on day {current_day}",
                details={"current_day": current_day, "allowed_days": allowed_days}
            )
        
        # Check time of day
        if not (start_hour <= current_hour < end_hour):
            return PolicyResult(
                allowed=False,
                policy_name=policy.name,
                policy_type=policy.policy_type,
                reason=f"Access not allowed at hour {current_hour}",
                details={
                    "current_hour": current_hour,
                    "start_hour": start_hour,
                    "end_hour": end_hour
                }
            )
        
        return PolicyResult(allowed=True)
    
    # ========================================================================
    # IP Whitelist Policy
    # ========================================================================
    
    def _check_ip_whitelist(
        self,
        policy: DynamicPolicyModel,
        context: AccessContext,
        db: Session
    ) -> PolicyResult:
        """
        Check IP whitelist restrictions.
        
        Config format:
        {
            "whitelist": ["192.168.1.0/24", "10.0.0.0/8"],
            "use_database_whitelist": true,
            "allow_private": true
        }
        """
        if not context.ip_address:
            # No IP address in context - policy may allow or deny
            if policy.deny_by_default:
                return PolicyResult(
                    allowed=False,
                    policy_name=policy.name,
                    policy_type=policy.policy_type,
                    reason="No IP address provided"
                )
            return PolicyResult(allowed=True)
        
        config = policy.config
        whitelist = config.get("whitelist", [])
        use_db_whitelist = config.get("use_database_whitelist", True)
        allow_private = config.get("allow_private", True)
        
        try:
            ip = ipaddress.ip_address(context.ip_address)
            
            # Allow private IPs if configured
            if allow_private and ip.is_private:
                return PolicyResult(allowed=True)
            
            # Check config whitelist
            for pattern in whitelist:
                try:
                    network = ipaddress.ip_network(pattern, strict=False)
                    if ip in network:
                        return PolicyResult(allowed=True)
                except ValueError:
                    continue
            
            # Check database whitelist
            if use_db_whitelist:
                db_whitelist = db.query(IPWhitelistModel).filter(
                    and_(
                        IPWhitelistModel.tenant_id == policy.tenant_id,
                        IPWhitelistModel.is_active == True
                    )
                ).all()
                
                for entry in db_whitelist:
                    try:
                        if entry.ip_range:
                            network = ipaddress.ip_network(entry.ip_range, strict=False)
                            if ip in network:
                                return PolicyResult(allowed=True)
                        else:
                            if str(ip) == str(entry.ip_address):
                                return PolicyResult(allowed=True)
                    except ValueError:
                        continue
            
            return PolicyResult(
                allowed=False,
                policy_name=policy.name,
                policy_type=policy.policy_type,
                reason=f"IP {context.ip_address} not in whitelist"
            )
            
        except ValueError as e:
            self.logger.warning(f"Invalid IP address {context.ip_address}: {e}")
            if policy.deny_by_default:
                return PolicyResult(
                    allowed=False,
                    policy_name=policy.name,
                    policy_type=policy.policy_type,
                    reason=f"Invalid IP address: {context.ip_address}"
                )
            return PolicyResult(allowed=True)
    
    # ========================================================================
    # Sensitivity Level Policy
    # ========================================================================
    
    def _check_sensitivity_level(
        self,
        policy: DynamicPolicyModel,
        user_id: UUID,
        context: AccessContext,
        db: Session
    ) -> PolicyResult:
        """
        Check sensitivity level restrictions.
        
        Config format:
        {
            "required_level": 3,
            "user_level_attribute": "clearance_level"
        }
        """
        config = policy.config
        required_level = config.get("required_level", 0)
        level_attribute = config.get("user_level_attribute", "clearance_level")
        
        # Get user's clearance level from context or database
        user_level = context.attributes.get(level_attribute)
        
        if user_level is None:
            # Try to get from user profile (would need user service)
            user_level = 0
        
        if user_level < required_level:
            return PolicyResult(
                allowed=False,
                policy_name=policy.name,
                policy_type=policy.policy_type,
                reason=f"Insufficient clearance level: {user_level} < {required_level}",
                details={
                    "user_level": user_level,
                    "required_level": required_level
                }
            )
        
        return PolicyResult(allowed=True)
    
    # ========================================================================
    # Attribute-Based Policy (ABAC)
    # ========================================================================
    
    def _check_attribute_policy(
        self,
        policy: DynamicPolicyModel,
        user_id: UUID,
        context: AccessContext,
        db: Session
    ) -> PolicyResult:
        """
        Check attribute-based access control policy.
        
        Config format:
        {
            "conditions": [
                {"attribute": "department", "operator": "eq", "value": "engineering"},
                {"attribute": "role", "operator": "in", "value": ["admin", "manager"]}
            ],
            "match_all": true
        }
        """
        config = policy.config
        conditions = config.get("conditions", [])
        match_all = config.get("match_all", True)
        
        if not conditions:
            return PolicyResult(allowed=True)
        
        results = []
        for condition in conditions:
            attr_name = condition.get("attribute")
            operator = condition.get("operator", "eq")
            expected_value = condition.get("value")
            
            actual_value = context.attributes.get(attr_name)
            
            match = self._evaluate_condition(actual_value, operator, expected_value)
            results.append(match)
        
        if match_all:
            allowed = all(results)
        else:
            allowed = any(results)
        
        if not allowed:
            return PolicyResult(
                allowed=False,
                policy_name=policy.name,
                policy_type=policy.policy_type,
                reason="Attribute conditions not met",
                details={"conditions": conditions, "results": results}
            )
        
        return PolicyResult(allowed=True)
    
    def _evaluate_condition(
        self,
        actual: Any,
        operator: str,
        expected: Any
    ) -> bool:
        """Evaluate a single attribute condition."""
        if actual is None:
            return operator == "is_null"
        
        if operator == "eq":
            return actual == expected
        elif operator == "ne":
            return actual != expected
        elif operator == "in":
            return actual in expected
        elif operator == "not_in":
            return actual not in expected
        elif operator == "gt":
            return actual > expected
        elif operator == "gte":
            return actual >= expected
        elif operator == "lt":
            return actual < expected
        elif operator == "lte":
            return actual <= expected
        elif operator == "contains":
            return expected in actual
        elif operator == "starts_with":
            return str(actual).startswith(str(expected))
        elif operator == "ends_with":
            return str(actual).endswith(str(expected))
        elif operator == "is_null":
            return actual is None
        elif operator == "is_not_null":
            return actual is not None
        else:
            self.logger.warning(f"Unknown operator: {operator}")
            return False
    
    # ========================================================================
    # Rate Limit Policy
    # ========================================================================
    
    def _check_rate_limit(
        self,
        policy: DynamicPolicyModel,
        user_id: UUID,
        context: AccessContext,
        db: Session
    ) -> PolicyResult:
        """
        Check rate limiting policy.
        
        Config format:
        {
            "max_requests": 100,
            "window_seconds": 60,
            "by_ip": true,
            "by_user": true
        }
        """
        # Rate limiting would typically use Redis or similar
        # This is a simplified implementation
        config = policy.config
        max_requests = config.get("max_requests", 100)
        window_seconds = config.get("window_seconds", 60)
        
        # For now, always allow (full implementation would check Redis)
        return PolicyResult(allowed=True)
    
    # ========================================================================
    # Decision Logging
    # ========================================================================
    
    def _log_decision(
        self,
        user_id: UUID,
        resource: str,
        action: str,
        tenant_id: str,
        decision: AccessDecision,
        context: AccessContext,
        db: Session
    ) -> None:
        """Log permission decision to audit log."""
        try:
            import hashlib
            
            # Get previous hash for chain
            last_log = db.query(AuditLogModel).filter(
                AuditLogModel.tenant_id == tenant_id
            ).order_by(AuditLogModel.timestamp.desc()).first()
            
            previous_hash = last_log.hash if last_log else None
            
            # Create log entry
            log_data = {
                "event_type": "permission_decision",
                "user_id": str(user_id),
                "tenant_id": tenant_id,
                "resource": resource,
                "action": action,
                "result": decision.allowed,
                "timestamp": context.timestamp.isoformat(),
                "previous_hash": previous_hash
            }
            
            # Calculate hash
            hash_input = f"{log_data['event_type']}|{log_data['user_id']}|{log_data['resource']}|{log_data['action']}|{log_data['timestamp']}|{previous_hash}"
            log_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            audit_log = AuditLogModel(
                event_type="permission_decision",
                user_id=user_id,
                tenant_id=tenant_id,
                resource=resource,
                action=action,
                result=decision.allowed,
                details={
                    "reason": decision.reason,
                    "policy_applied": decision.policy_applied,
                    "context": {
                        "ip_address": context.ip_address,
                        "user_agent": context.user_agent,
                        "session_id": context.session_id
                    }
                },
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                session_id=context.session_id,
                request_id=context.request_id,
                timestamp=context.timestamp,
                previous_hash=previous_hash,
                hash=log_hash
            )
            
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to log permission decision: {e}")
            # Don't fail the access check due to logging failure
            db.rollback()
    
    # ========================================================================
    # Policy Management
    # ========================================================================
    
    def create_policy(
        self,
        name: str,
        description: str,
        tenant_id: str,
        policy_type: PolicyType,
        resource_pattern: str,
        config: Dict[str, Any],
        priority: int = 0,
        created_by: Optional[UUID] = None,
        db: Session = None
    ) -> Optional[DynamicPolicyModel]:
        """Create a new dynamic policy."""
        try:
            policy = DynamicPolicyModel(
                name=name,
                description=description,
                tenant_id=tenant_id,
                policy_type=policy_type,
                resource_pattern=resource_pattern,
                config=config,
                priority=priority,
                created_by=created_by
            )
            
            db.add(policy)
            db.commit()
            db.refresh(policy)
            
            self.logger.info(f"Created policy {name} for tenant {tenant_id}")
            return policy
            
        except Exception as e:
            self.logger.error(f"Failed to create policy {name}: {e}")
            db.rollback()
            return None
    
    def list_policies(
        self,
        tenant_id: str,
        policy_type: Optional[PolicyType] = None,
        include_disabled: bool = False,
        db: Session = None
    ) -> List[DynamicPolicyModel]:
        """List policies for a tenant."""
        query = db.query(DynamicPolicyModel).filter(
            DynamicPolicyModel.tenant_id == tenant_id
        )
        
        if policy_type:
            query = query.filter(DynamicPolicyModel.policy_type == policy_type)
        
        if not include_disabled:
            query = query.filter(DynamicPolicyModel.enabled == True)
        
        return query.order_by(DynamicPolicyModel.priority.desc()).all()
    
    def update_policy(
        self,
        policy_id: UUID,
        updates: Dict[str, Any],
        db: Session
    ) -> bool:
        """Update a policy."""
        try:
            policy = db.query(DynamicPolicyModel).filter(
                DynamicPolicyModel.id == policy_id
            ).first()
            
            if not policy:
                return False
            
            allowed_fields = ['name', 'description', 'config', 'enabled', 'priority', 'resource_pattern']
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(policy, field, value)
            
            policy.updated_at = datetime.utcnow()
            db.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update policy {policy_id}: {e}")
            db.rollback()
            return False
    
    def delete_policy(self, policy_id: UUID, db: Session) -> bool:
        """Delete a policy."""
        try:
            policy = db.query(DynamicPolicyModel).filter(
                DynamicPolicyModel.id == policy_id
            ).first()
            
            if not policy:
                return False
            
            db.delete(policy)
            db.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete policy {policy_id}: {e}")
            db.rollback()
            return False


# Global permission manager instance
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get or create the global permission manager instance."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
