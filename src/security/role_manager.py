"""
Role Manager for SuperInsight Platform RBAC System.

Provides high-level role management operations and predefined role templates.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select

from src.security.rbac_controller import RBACController
from src.security.rbac_models import (
    RoleModel, PermissionModel, PermissionScope, ResourceType
)
from src.security.models import UserRole, AuditAction

logger = logging.getLogger(__name__)


class RoleManager:
    """
    High-level role management system.
    
    Provides convenient methods for managing roles, permissions, and user assignments
    with predefined role templates and best practices.
    """
    
    def __init__(self, rbac_controller: Optional[RBACController] = None):
        """Initialize role manager with RBAC controller."""
        self.rbac_controller = rbac_controller or RBACController()
        self._role_templates = self._initialize_role_templates()
    
    def initialize_tenant_roles(
        self,
        tenant_id: str,
        admin_user_id: UUID,
        db: Session
    ) -> bool:
        """
        Initialize default roles for a new tenant.
        
        Args:
            tenant_id: Tenant identifier
            admin_user_id: Admin user creating the roles
            db: Database session
            
        Returns:
            True if initialization successful
        """
        try:
            logger.info(f"Initializing default roles for tenant {tenant_id}")
            
            # Create default roles from templates
            created_roles = {}
            for role_name, template in self._role_templates.items():
                role = self.rbac_controller.create_role(
                    name=role_name,
                    description=template["description"],
                    tenant_id=tenant_id,
                    created_by=admin_user_id,
                    permissions=template["permissions"],
                    db=db
                )
                
                if role:
                    created_roles[role_name] = role
                    logger.info(f"Created role: {role_name} for tenant {tenant_id}")
                else:
                    logger.error(f"Failed to create role: {role_name}")
            
            # Assign admin role to the creating user
            if "Tenant Admin" in created_roles:
                success = self.rbac_controller.assign_role_to_user(
                    user_id=admin_user_id,
                    role_id=created_roles["Tenant Admin"].id,
                    assigned_by=admin_user_id,
                    db=db
                )
                
                if success:
                    logger.info(f"Assigned Tenant Admin role to user {admin_user_id}")
                else:
                    logger.error(f"Failed to assign Tenant Admin role to user {admin_user_id}")
            
            return len(created_roles) > 0
            
        except Exception as e:
            logger.error(f"Failed to initialize tenant roles for {tenant_id}: {e}")
            return False
    
    def create_custom_role(
        self,
        name: str,
        description: str,
        tenant_id: str,
        permissions: List[str],
        created_by: UUID,
        db: Session
    ) -> Optional[RoleModel]:
        """
        Create a custom role with specified permissions.
        
        Args:
            name: Role name
            description: Role description
            tenant_id: Tenant identifier
            permissions: List of permission names
            created_by: User creating the role
            db: Database session
            
        Returns:
            Created RoleModel or None if failed
        """
        try:
            # Validate permissions exist
            valid_permissions = []
            for perm_name in permissions:
                permission = self.rbac_controller.get_permission_by_name(perm_name, db)
                if permission:
                    valid_permissions.append(perm_name)
                else:
                    logger.warning(f"Permission {perm_name} not found, skipping")
            
            if not valid_permissions:
                logger.error("No valid permissions provided for role creation")
                return None
            
            # Create role
            role = self.rbac_controller.create_role(
                name=name,
                description=description,
                tenant_id=tenant_id,
                created_by=created_by,
                permissions=valid_permissions,
                db=db
            )
            
            if role:
                logger.info(f"Created custom role: {name} with {len(valid_permissions)} permissions")
            
            return role
            
        except Exception as e:
            logger.error(f"Failed to create custom role {name}: {e}")
            return None
    
    def clone_role(
        self,
        source_role_id: UUID,
        new_name: str,
        new_description: str,
        tenant_id: str,
        created_by: UUID,
        db: Session
    ) -> Optional[RoleModel]:
        """
        Clone an existing role with a new name.
        
        Args:
            source_role_id: ID of role to clone
            new_name: Name for new role
            new_description: Description for new role
            tenant_id: Tenant identifier
            created_by: User creating the role
            db: Database session
            
        Returns:
            Cloned RoleModel or None if failed
        """
        try:
            # Get source role
            source_role = self.rbac_controller.get_role_by_id(source_role_id, db)
            if not source_role:
                logger.error(f"Source role {source_role_id} not found")
                return None
            
            # Get source role permissions
            source_permissions = db.query(PermissionModel).join(
                self.rbac_controller.RolePermissionModel,
                PermissionModel.id == self.rbac_controller.RolePermissionModel.permission_id
            ).filter(
                self.rbac_controller.RolePermissionModel.role_id == source_role_id
            ).all()
            
            permission_names = [perm.name for perm in source_permissions]
            
            # Create cloned role
            cloned_role = self.rbac_controller.create_role(
                name=new_name,
                description=new_description,
                tenant_id=tenant_id,
                created_by=created_by,
                permissions=permission_names,
                db=db
            )
            
            if cloned_role:
                logger.info(f"Cloned role {source_role.name} to {new_name}")
            
            return cloned_role
            
        except Exception as e:
            logger.error(f"Failed to clone role {source_role_id}: {e}")
            return None
    
    def bulk_assign_users_to_role(
        self,
        user_ids: List[UUID],
        role_id: UUID,
        assigned_by: UUID,
        db: Session
    ) -> Dict[str, Any]:
        """
        Assign multiple users to a role in bulk.
        
        Args:
            user_ids: List of user IDs to assign
            role_id: Role ID to assign
            assigned_by: User performing the assignment
            db: Database session
            
        Returns:
            Dict with assignment results
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(user_ids)
        }
        
        try:
            for user_id in user_ids:
                success = self.rbac_controller.assign_role_to_user(
                    user_id=user_id,
                    role_id=role_id,
                    assigned_by=assigned_by,
                    db=db
                )
                
                if success:
                    results["successful"].append(str(user_id))
                else:
                    results["failed"].append(str(user_id))
            
            logger.info(f"Bulk role assignment: {len(results['successful'])} successful, {len(results['failed'])} failed")
            
        except Exception as e:
            logger.error(f"Bulk role assignment failed: {e}")
            results["failed"] = [str(uid) for uid in user_ids]
        
        return results
    
    def get_role_hierarchy(
        self,
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get role hierarchy for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            Dict representing role hierarchy
        """
        try:
            roles = self.rbac_controller.get_roles_for_tenant(tenant_id, db=db)
            
            # Build hierarchy structure
            hierarchy = {
                "roles": [],
                "relationships": []
            }
            
            role_map = {}
            for role in roles:
                role_data = {
                    "id": str(role.id),
                    "name": role.name,
                    "description": role.description,
                    "is_system_role": role.is_system_role,
                    "user_count": len(role.user_assignments),
                    "permission_count": len(role.permissions)
                }
                hierarchy["roles"].append(role_data)
                role_map[role.id] = role_data
                
                # Add parent-child relationships
                if role.parent_role_id:
                    hierarchy["relationships"].append({
                        "parent": str(role.parent_role_id),
                        "child": str(role.id)
                    })
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"Failed to get role hierarchy for tenant {tenant_id}: {e}")
            return {"roles": [], "relationships": []}
    
    def analyze_role_usage(
        self,
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Analyze role usage patterns for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            Dict with usage analysis
        """
        try:
            roles = self.rbac_controller.get_roles_for_tenant(tenant_id, db=db)
            
            analysis = {
                "total_roles": len(roles),
                "system_roles": 0,
                "custom_roles": 0,
                "unused_roles": [],
                "most_used_roles": [],
                "role_statistics": []
            }
            
            role_usage = []
            
            for role in roles:
                user_count = len(role.user_assignments)
                permission_count = len(role.permissions)
                
                if role.is_system_role:
                    analysis["system_roles"] += 1
                else:
                    analysis["custom_roles"] += 1
                
                role_stat = {
                    "id": str(role.id),
                    "name": role.name,
                    "user_count": user_count,
                    "permission_count": permission_count,
                    "is_system_role": role.is_system_role,
                    "created_at": role.created_at.isoformat()
                }
                
                analysis["role_statistics"].append(role_stat)
                role_usage.append((role.name, user_count))
                
                # Track unused roles
                if user_count == 0:
                    analysis["unused_roles"].append({
                        "name": role.name,
                        "id": str(role.id)
                    })
            
            # Sort by usage
            role_usage.sort(key=lambda x: x[1], reverse=True)
            analysis["most_used_roles"] = [
                {"name": name, "user_count": count}
                for name, count in role_usage[:5]
            ]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze role usage for tenant {tenant_id}: {e}")
            return {}
    
    def suggest_role_optimizations(
        self,
        tenant_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Suggest role optimizations for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        try:
            analysis = self.analyze_role_usage(tenant_id, db)
            
            # Suggest removing unused roles
            if analysis.get("unused_roles"):
                suggestions.append({
                    "type": "remove_unused_roles",
                    "priority": "medium",
                    "description": f"Consider removing {len(analysis['unused_roles'])} unused roles",
                    "details": analysis["unused_roles"]
                })
            
            # Suggest consolidating similar roles
            roles = self.rbac_controller.get_roles_for_tenant(tenant_id, db=db)
            similar_roles = self._find_similar_roles(roles, db)
            
            if similar_roles:
                suggestions.append({
                    "type": "consolidate_similar_roles",
                    "priority": "low",
                    "description": f"Consider consolidating {len(similar_roles)} pairs of similar roles",
                    "details": similar_roles
                })
            
            # Suggest creating missing standard roles
            missing_roles = self._find_missing_standard_roles(tenant_id, db)
            if missing_roles:
                suggestions.append({
                    "type": "add_missing_standard_roles",
                    "priority": "high",
                    "description": f"Consider adding {len(missing_roles)} standard roles",
                    "details": missing_roles
                })
            
        except Exception as e:
            logger.error(f"Failed to generate role optimization suggestions: {e}")
        
        return suggestions
    
    def _find_similar_roles(
        self,
        roles: List[RoleModel],
        db: Session
    ) -> List[Dict[str, Any]]:
        """Find roles with similar permission sets."""
        similar_pairs = []
        
        try:
            # Get permissions for each role
            role_permissions = {}
            for role in roles:
                permissions = db.query(PermissionModel).join(
                    self.rbac_controller.RolePermissionModel,
                    PermissionModel.id == self.rbac_controller.RolePermissionModel.permission_id
                ).filter(
                    self.rbac_controller.RolePermissionModel.role_id == role.id
                ).all()
                
                role_permissions[role.id] = set(perm.name for perm in permissions)
            
            # Compare permission sets
            role_ids = list(role_permissions.keys())
            for i in range(len(role_ids)):
                for j in range(i + 1, len(role_ids)):
                    role1_id, role2_id = role_ids[i], role_ids[j]
                    perms1, perms2 = role_permissions[role1_id], role_permissions[role2_id]
                    
                    # Calculate similarity (Jaccard index)
                    if perms1 or perms2:
                        similarity = len(perms1 & perms2) / len(perms1 | perms2)
                        
                        if similarity > 0.8:  # 80% similarity threshold
                            role1 = next(r for r in roles if r.id == role1_id)
                            role2 = next(r for r in roles if r.id == role2_id)
                            
                            similar_pairs.append({
                                "role1": {"name": role1.name, "id": str(role1.id)},
                                "role2": {"name": role2.name, "id": str(role2.id)},
                                "similarity": round(similarity * 100, 1)
                            })
            
        except Exception as e:
            logger.error(f"Failed to find similar roles: {e}")
        
        return similar_pairs
    
    def _find_missing_standard_roles(
        self,
        tenant_id: str,
        db: Session
    ) -> List[str]:
        """Find missing standard roles for a tenant."""
        existing_roles = {
            role.name for role in 
            self.rbac_controller.get_roles_for_tenant(tenant_id, db=db)
        }
        
        standard_roles = set(self._role_templates.keys())
        missing_roles = standard_roles - existing_roles
        
        return list(missing_roles)
    
    def _initialize_role_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize predefined role templates."""
        return {
            "Tenant Admin": {
                "description": "Full administrative access within tenant",
                "permissions": [
                    "user.read", "user.write", "user.delete",
                    "role.read", "role.write", "role.delete",
                    "project.read", "project.write", "project.delete",
                    "dataset.read", "dataset.write", "dataset.delete",
                    "audit.read", "audit.export",
                    "desensitization.read", "desensitization.write"
                ]
            },
            
            "Project Manager": {
                "description": "Manage projects and datasets within tenant",
                "permissions": [
                    "user.read",
                    "project.read", "project.write", "project.delete",
                    "dataset.read", "dataset.write", "dataset.delete",
                    "audit.read"
                ]
            },
            
            "Data Analyst": {
                "description": "Analyze data and create reports",
                "permissions": [
                    "project.read",
                    "dataset.read", "dataset.write",
                    "audit.read"
                ]
            },
            
            "Data Viewer": {
                "description": "Read-only access to data and reports",
                "permissions": [
                    "project.read",
                    "dataset.read"
                ]
            },
            
            "Security Officer": {
                "description": "Manage security and compliance",
                "permissions": [
                    "user.read",
                    "role.read",
                    "audit.read", "audit.export",
                    "desensitization.read", "desensitization.write"
                ]
            },
            
            "Auditor": {
                "description": "Read-only access for auditing purposes",
                "permissions": [
                    "user.read",
                    "role.read",
                    "project.read",
                    "dataset.read",
                    "audit.read", "audit.export"
                ]
            }
        }
    
    def export_role_configuration(
        self,
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Export role configuration for backup or migration.
        
        Args:
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            Dict with complete role configuration
        """
        try:
            roles = self.rbac_controller.get_roles_for_tenant(tenant_id, db=db)
            
            export_data = {
                "tenant_id": tenant_id,
                "export_timestamp": datetime.utcnow().isoformat(),
                "roles": []
            }
            
            for role in roles:
                # Get role permissions
                permissions = db.query(PermissionModel).join(
                    self.rbac_controller.RolePermissionModel,
                    PermissionModel.id == self.rbac_controller.RolePermissionModel.permission_id
                ).filter(
                    self.rbac_controller.RolePermissionModel.role_id == role.id
                ).all()
                
                role_data = {
                    "name": role.name,
                    "description": role.description,
                    "is_system_role": role.is_system_role,
                    "permissions": [perm.name for perm in permissions],
                    "role_metadata": role.role_metadata,
                    "created_at": role.created_at.isoformat()
                }
                
                export_data["roles"].append(role_data)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export role configuration for tenant {tenant_id}: {e}")
            return {}
    
    def import_role_configuration(
        self,
        tenant_id: str,
        import_data: Dict[str, Any],
        imported_by: UUID,
        db: Session
    ) -> bool:
        """
        Import role configuration from backup or migration.
        
        Args:
            tenant_id: Tenant identifier
            import_data: Exported role configuration
            imported_by: User performing the import
            db: Database session
            
        Returns:
            True if import successful
        """
        try:
            roles_data = import_data.get("roles", [])
            
            for role_data in roles_data:
                # Skip system roles if they already exist
                if role_data.get("is_system_role"):
                    existing_role = db.query(RoleModel).filter(
                        and_(
                            RoleModel.name == role_data["name"],
                            RoleModel.tenant_id == tenant_id
                        )
                    ).first()
                    
                    if existing_role:
                        continue
                
                # Create role
                role = self.rbac_controller.create_role(
                    name=role_data["name"],
                    description=role_data["description"],
                    tenant_id=tenant_id,
                    created_by=imported_by,
                    permissions=role_data.get("permissions", []),
                    db=db
                )
                
                if role:
                    logger.info(f"Imported role: {role_data['name']}")
                else:
                    logger.warning(f"Failed to import role: {role_data['name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to import role configuration: {e}")
            return False