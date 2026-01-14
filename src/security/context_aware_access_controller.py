"""
Context-Aware Access Controller for SuperInsight Platform.

Implements context-based dynamic permission control:
- Management scenario permissions
- Annotation scenario permissions
- Query scenario permissions
- API scenario permissions
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.security.data_permission_engine import DataPermissionEngine, get_data_permission_engine
from src.schemas.data_permission import PermissionResult, ScenarioType

logger = logging.getLogger(__name__)


# Scenario-specific permission mappings
SCENARIO_PERMISSIONS = {
    ScenarioType.MANAGEMENT: {
        "allowed_actions": ["read", "write", "delete", "export", "admin"],
        "resource_types": ["system_config", "user", "role", "tenant", "workflow"],
        "requires_roles": ["admin", "manager"]
    },
    ScenarioType.ANNOTATION: {
        "allowed_actions": ["read", "write", "annotate", "review"],
        "resource_types": ["dataset", "annotation", "task", "label"],
        "requires_roles": ["annotator", "reviewer", "admin"]
    },
    ScenarioType.QUERY: {
        "allowed_actions": ["read", "export"],
        "resource_types": ["dataset", "annotation", "report", "statistics"],
        "requires_roles": ["viewer", "analyst", "admin"]
    },
    ScenarioType.API: {
        "allowed_actions": ["read", "write", "export"],
        "resource_types": ["api", "dataset", "annotation"],
        "requires_roles": ["api_user", "developer", "admin"]
    }
}


class ContextAwareAccessController:
    """
    Context-Aware Access Controller.
    
    Provides dynamic permission control based on context:
    - Management context (system configuration, user management)
    - Annotation context (viewing, editing, submitting annotations)
    - Query context (searching, filtering, statistics)
    - API context (API access, data export)
    """
    
    def __init__(self, permission_engine: Optional[DataPermissionEngine] = None):
        self.logger = logging.getLogger(__name__)
        self._permission_engine = permission_engine or get_data_permission_engine()
    
    # ========================================================================
    # Scenario-Based Permission Checks
    # ========================================================================
    
    async def check_management_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> PermissionResult:
        """
        Check management scenario permission.
        
        Management scenario includes:
        - System configuration
        - User management
        - Role management
        - Tenant settings
        """
        # Validate action is allowed in management context
        if action not in SCENARIO_PERMISSIONS[ScenarioType.MANAGEMENT]["allowed_actions"]:
            return PermissionResult(
                allowed=False,
                reason=f"Action '{action}' not allowed in management context"
            )
        
        # Check role requirements
        if user_roles:
            required_roles = SCENARIO_PERMISSIONS[ScenarioType.MANAGEMENT]["requires_roles"]
            if not any(role in required_roles for role in user_roles):
                return PermissionResult(
                    allowed=False,
                    reason="User does not have required role for management context"
                )
        
        # Check underlying data permission
        return await self._permission_engine.check_dataset_permission(
            user_id=user_id,
            dataset_id=resource,
            action=action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
    
    async def check_annotation_permission(
        self,
        user_id: str,
        task_id: str,
        action: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> PermissionResult:
        """
        Check annotation scenario permission.
        
        Annotation scenario includes:
        - View annotations
        - Edit annotations
        - Submit annotations
        - Review annotations
        """
        # Map annotation actions
        action_mapping = {
            "view": "read",
            "edit": "write",
            "submit": "write",
            "review": "review"
        }
        mapped_action = action_mapping.get(action, action)
        
        # Validate action is allowed in annotation context
        if mapped_action not in SCENARIO_PERMISSIONS[ScenarioType.ANNOTATION]["allowed_actions"]:
            return PermissionResult(
                allowed=False,
                reason=f"Action '{action}' not allowed in annotation context"
            )
        
        # Check role requirements
        if user_roles:
            required_roles = SCENARIO_PERMISSIONS[ScenarioType.ANNOTATION]["requires_roles"]
            if not any(role in required_roles for role in user_roles):
                return PermissionResult(
                    allowed=False,
                    reason="User does not have required role for annotation context"
                )
        
        # Additional annotation-specific checks
        if action == "review":
            # Reviewers cannot review their own annotations
            # In production, check if user is the annotator
            pass
        
        # Check underlying data permission
        return await self._permission_engine.check_dataset_permission(
            user_id=user_id,
            dataset_id=task_id,
            action=mapped_action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
    
    async def check_query_permission(
        self,
        user_id: str,
        query_type: str,
        scope: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> PermissionResult:
        """
        Check query scenario permission.
        
        Query scenario includes:
        - Search operations
        - Filter operations
        - Statistics queries
        - Report generation
        """
        # Map query types to actions
        query_action_mapping = {
            "search": "read",
            "filter": "read",
            "statistics": "read",
            "report": "export"
        }
        action = query_action_mapping.get(query_type, "read")
        
        # Validate action is allowed in query context
        if action not in SCENARIO_PERMISSIONS[ScenarioType.QUERY]["allowed_actions"]:
            return PermissionResult(
                allowed=False,
                reason=f"Query type '{query_type}' not allowed in query context"
            )
        
        # Check role requirements
        if user_roles:
            required_roles = SCENARIO_PERMISSIONS[ScenarioType.QUERY]["requires_roles"]
            if not any(role in required_roles for role in user_roles):
                return PermissionResult(
                    allowed=False,
                    reason="User does not have required role for query context"
                )
        
        # Check scope-based permissions
        # Scope can be: "own", "team", "tenant", "all"
        if scope == "all" and "admin" not in (user_roles or []):
            return PermissionResult(
                allowed=False,
                reason="Only admins can query all data"
            )
        
        # Check underlying data permission
        return await self._permission_engine.check_dataset_permission(
            user_id=user_id,
            dataset_id=scope,
            action=action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
    
    async def check_api_permission(
        self,
        user_id: str,
        endpoint: str,
        method: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> PermissionResult:
        """
        Check API scenario permission.
        
        API scenario includes:
        - REST API access
        - Data export via API
        - Webhook access
        """
        # Map HTTP methods to actions
        method_action_mapping = {
            "GET": "read",
            "POST": "write",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "delete"
        }
        action = method_action_mapping.get(method.upper(), "read")
        
        # Validate action is allowed in API context
        if action not in SCENARIO_PERMISSIONS[ScenarioType.API]["allowed_actions"]:
            return PermissionResult(
                allowed=False,
                reason=f"Method '{method}' not allowed in API context"
            )
        
        # Check role requirements
        if user_roles:
            required_roles = SCENARIO_PERMISSIONS[ScenarioType.API]["requires_roles"]
            if not any(role in required_roles for role in user_roles):
                return PermissionResult(
                    allowed=False,
                    reason="User does not have required role for API context"
                )
        
        # Check endpoint-specific permissions
        # Extract resource from endpoint
        resource = self._extract_resource_from_endpoint(endpoint)
        
        # Check underlying data permission
        return await self._permission_engine.check_dataset_permission(
            user_id=user_id,
            dataset_id=resource,
            action=action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
    
    # ========================================================================
    # Effective Permissions
    # ========================================================================
    
    async def get_effective_permissions(
        self,
        user_id: str,
        context: ScenarioType,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's effective permissions in a specific context.
        
        Args:
            user_id: User ID
            context: Scenario context
            tenant_id: Tenant context
            db: Database session
            user_roles: Optional user roles
            
        Returns:
            List of effective permissions
        """
        # Get base permissions from permission engine
        base_permissions = await self._permission_engine.get_user_permissions(
            user_id=user_id,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
        
        # Filter by context
        context_config = SCENARIO_PERMISSIONS.get(context, {})
        allowed_actions = context_config.get("allowed_actions", [])
        allowed_resource_types = context_config.get("resource_types", [])
        
        effective = []
        for perm in base_permissions:
            # Check if permission action is allowed in context
            if perm.action.value in allowed_actions:
                # Check if resource type is allowed in context
                if perm.resource_type in allowed_resource_types or not allowed_resource_types:
                    effective.append({
                        "resource_type": perm.resource_type,
                        "resource_id": perm.resource_id,
                        "action": perm.action.value,
                        "context": context.value,
                        "conditions": perm.conditions
                    })
        
        return effective
    
    async def get_all_context_permissions(
        self,
        user_id: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get user's permissions across all contexts.
        
        Args:
            user_id: User ID
            tenant_id: Tenant context
            db: Database session
            user_roles: Optional user roles
            
        Returns:
            Dictionary mapping context to permissions
        """
        result = {}
        
        for context in ScenarioType:
            permissions = await self.get_effective_permissions(
                user_id=user_id,
                context=context,
                tenant_id=tenant_id,
                db=db,
                user_roles=user_roles
            )
            result[context.value] = permissions
        
        return result
    
    # ========================================================================
    # Context Switching
    # ========================================================================
    
    async def switch_context(
        self,
        user_id: str,
        from_context: ScenarioType,
        to_context: ScenarioType,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Handle context switch and return permission changes.
        
        Args:
            user_id: User ID
            from_context: Current context
            to_context: Target context
            tenant_id: Tenant context
            db: Database session
            user_roles: Optional user roles
            
        Returns:
            Dictionary with permission changes
        """
        # Get permissions in both contexts
        from_permissions = await self.get_effective_permissions(
            user_id=user_id,
            context=from_context,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
        
        to_permissions = await self.get_effective_permissions(
            user_id=user_id,
            context=to_context,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
        
        # Calculate changes
        from_set = {(p["resource_type"], p["resource_id"], p["action"]) for p in from_permissions}
        to_set = {(p["resource_type"], p["resource_id"], p["action"]) for p in to_permissions}
        
        gained = to_set - from_set
        lost = from_set - to_set
        
        return {
            "from_context": from_context.value,
            "to_context": to_context.value,
            "permissions_gained": [
                {"resource_type": r, "resource_id": i, "action": a}
                for r, i, a in gained
            ],
            "permissions_lost": [
                {"resource_type": r, "resource_id": i, "action": a}
                for r, i, a in lost
            ],
            "total_permissions": len(to_permissions)
        }
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    def _extract_resource_from_endpoint(self, endpoint: str) -> str:
        """Extract resource identifier from API endpoint."""
        # Parse endpoint like /api/v1/datasets/123
        parts = endpoint.strip("/").split("/")
        
        # Skip api and version
        if len(parts) >= 3 and parts[0] == "api":
            parts = parts[2:]
        
        # Return resource type or full path
        if parts:
            return parts[0]
        
        return endpoint


# Global instance
_context_aware_controller: Optional[ContextAwareAccessController] = None


def get_context_aware_controller() -> ContextAwareAccessController:
    """Get or create the global context-aware access controller instance."""
    global _context_aware_controller
    if _context_aware_controller is None:
        _context_aware_controller = ContextAwareAccessController()
    return _context_aware_controller
