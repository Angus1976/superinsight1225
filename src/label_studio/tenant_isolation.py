"""
Label Studio Multi-Tenant Isolation System

Provides tenant-aware project management and data isolation for Label Studio integration.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
import json
from urllib.parse import urljoin

from src.config.settings import settings
from src.middleware.tenant_middleware import get_current_tenant, get_current_user
from src.security.tenant_audit import log_data_access, log_data_modification, AuditAction
from src.database.connection import get_db_session
from src.security.models import UserModel

logger = logging.getLogger(__name__)


@dataclass
class LabelStudioProject:
    """Label Studio project configuration."""
    id: int
    title: str
    description: str
    tenant_id: str
    created_by: str
    label_config: str
    is_published: bool = False
    maximum_annotations: int = 1
    show_instruction: bool = True
    show_skip_button: bool = True
    enable_empty_annotation: bool = True
    show_annotation_history: bool = False
    organization: Optional[int] = None
    color: str = "#FFFFFF"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "title": f"[{self.tenant_id}] {self.title}",
            "description": self.description,
            "label_config": self.label_config,
            "is_published": self.is_published,
            "maximum_annotations": self.maximum_annotations,
            "show_instruction": self.show_instruction,
            "show_skip_button": self.show_skip_button,
            "enable_empty_annotation": self.enable_empty_annotation,
            "show_annotation_history": self.show_annotation_history,
            "color": self.color
        }


class LabelStudioTenantManager:
    """Manages tenant isolation for Label Studio projects."""
    
    def __init__(self):
        self.base_url = settings.label_studio.label_studio_url
        self.api_token = settings.label_studio.label_studio_api_token
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
        self.tenant_projects_cache = {}
    
    def _make_request(self, method: str, endpoint: str, 
                     data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to Label Studio API."""
        
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Label Studio API request failed: {e}")
            raise Exception(f"Label Studio API error: {str(e)}")
    
    def create_tenant_project(self, project_config: LabelStudioProject) -> Dict[str, Any]:
        """Create a new project for a tenant."""
        
        try:
            # Validate tenant access
            current_tenant = get_current_tenant()
            if project_config.tenant_id != current_tenant:
                raise Exception("Cannot create project for different tenant")
            
            # Create project in Label Studio
            project_data = project_config.to_dict()
            
            # Add tenant-specific metadata
            project_data["description"] += f"\n\nTenant: {project_config.tenant_id}"
            
            response = self._make_request("POST", "/api/projects/", project_data)
            
            # Store tenant mapping
            project_id = response.get("id")
            if project_id:
                self._store_tenant_project_mapping(project_id, project_config.tenant_id)
                
                # Clear cache
                self.tenant_projects_cache.pop(project_config.tenant_id, None)
                
                # Log audit event
                log_data_modification(
                    resource_type="label_studio_project",
                    resource_id=str(project_id),
                    action=AuditAction.CREATE,
                    new_values={"title": project_config.title, "tenant_id": project_config.tenant_id}
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to create tenant project: {e}")
            raise
    
    def get_tenant_projects(self, tenant_id: str = None) -> List[Dict[str, Any]]:
        """Get all projects for a tenant."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        # Check cache first
        if tenant_id in self.tenant_projects_cache:
            return self.tenant_projects_cache[tenant_id]
        
        try:
            # Get all projects from Label Studio
            all_projects = self._make_request("GET", "/api/projects/")
            
            # Filter projects by tenant
            tenant_projects = []
            for project in all_projects:
                if self._is_tenant_project(project, tenant_id):
                    tenant_projects.append(project)
            
            # Cache results
            self.tenant_projects_cache[tenant_id] = tenant_projects
            
            # Log audit event
            log_data_access(
                resource_type="label_studio_projects",
                action=AuditAction.READ,
                tenant_id=tenant_id,
                count=len(tenant_projects)
            )
            
            return tenant_projects
            
        except Exception as e:
            logger.error(f"Failed to get tenant projects: {e}")
            return []
    
    def get_tenant_project(self, project_id: int, tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Get a specific project if it belongs to the tenant."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            # Get project from Label Studio
            project = self._make_request("GET", f"/api/projects/{project_id}/")
            
            # Verify tenant ownership
            if not self._is_tenant_project(project, tenant_id):
                raise Exception(f"Project {project_id} does not belong to tenant {tenant_id}")
            
            # Remove tenant prefix from title
            title = project.get("title", "")
            if title.startswith(f"[{tenant_id}] "):
                project["title"] = title[len(f"[{tenant_id}] "):]
            
            # Log audit event
            log_data_access(
                resource_type="label_studio_project",
                resource_id=str(project_id),
                action=AuditAction.READ
            )
            
            return project
            
        except Exception as e:
            logger.error(f"Failed to get tenant project {project_id}: {e}")
            return None
    
    def update_tenant_project(self, project_id: int, updates: Dict[str, Any], 
                             tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Update a project if it belongs to the tenant."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            # Verify tenant ownership first
            existing_project = self.get_tenant_project(project_id, tenant_id)
            if not existing_project:
                raise Exception(f"Project {project_id} not found or access denied")
            
            # Prepare update data
            update_data = updates.copy()
            
            # Add tenant prefix to title if being updated
            if "title" in update_data:
                update_data["title"] = f"[{tenant_id}] {update_data['title']}"
            
            # Update project in Label Studio
            response = self._make_request("PATCH", f"/api/projects/{project_id}/", update_data)
            
            # Clear cache
            self.tenant_projects_cache.pop(tenant_id, None)
            
            # Log audit event
            log_data_modification(
                resource_type="label_studio_project",
                resource_id=str(project_id),
                action=AuditAction.UPDATE,
                old_values=existing_project,
                new_values=updates
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to update tenant project {project_id}: {e}")
            return None
    
    def delete_tenant_project(self, project_id: int, tenant_id: str = None) -> bool:
        """Delete a project if it belongs to the tenant."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            # Verify tenant ownership first
            existing_project = self.get_tenant_project(project_id, tenant_id)
            if not existing_project:
                raise Exception(f"Project {project_id} not found or access denied")
            
            # Delete project from Label Studio
            self._make_request("DELETE", f"/api/projects/{project_id}/")
            
            # Remove tenant mapping
            self._remove_tenant_project_mapping(project_id)
            
            # Clear cache
            self.tenant_projects_cache.pop(tenant_id, None)
            
            # Log audit event
            log_data_modification(
                resource_type="label_studio_project",
                resource_id=str(project_id),
                action=AuditAction.DELETE,
                old_values=existing_project
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete tenant project {project_id}: {e}")
            return False
    
    def get_project_tasks(self, project_id: int, tenant_id: str = None) -> List[Dict[str, Any]]:
        """Get tasks for a tenant project."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            # Verify tenant ownership first
            project = self.get_tenant_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found or access denied")
            
            # Get tasks from Label Studio
            tasks = self._make_request("GET", f"/api/projects/{project_id}/tasks/")
            
            # Log audit event
            log_data_access(
                resource_type="label_studio_tasks",
                resource_id=str(project_id),
                action=AuditAction.READ,
                count=len(tasks) if isinstance(tasks, list) else 0
            )
            
            return tasks if isinstance(tasks, list) else []
            
        except Exception as e:
            logger.error(f"Failed to get tasks for project {project_id}: {e}")
            return []
    
    def create_project_task(self, project_id: int, task_data: Dict[str, Any], 
                           tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Create a task in a tenant project."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            # Verify tenant ownership first
            project = self.get_tenant_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found or access denied")
            
            # Create task in Label Studio
            response = self._make_request("POST", f"/api/projects/{project_id}/tasks/", task_data)
            
            # Log audit event
            log_data_modification(
                resource_type="label_studio_task",
                resource_id=str(response.get("id")) if response else None,
                action=AuditAction.CREATE,
                new_values=task_data
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to create task in project {project_id}: {e}")
            return None
    
    def get_project_annotations(self, project_id: int, tenant_id: str = None) -> Dict[str, Any]:
        """Get annotations for a tenant project."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            # Verify tenant ownership first
            project = self.get_tenant_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found or access denied")
            
            # Get annotations from Label Studio
            annotations = self._make_request("GET", f"/api/projects/{project_id}/annotations/")
            
            # Log audit event
            log_data_access(
                resource_type="label_studio_annotations",
                resource_id=str(project_id),
                action=AuditAction.READ,
                count=len(annotations) if isinstance(annotations, list) else 0
            )
            
            # Return in expected format
            if isinstance(annotations, list):
                return {"results": annotations}
            else:
                return annotations
            
        except Exception as e:
            logger.error(f"Failed to get annotations for project {project_id}: {e}")
            return {"results": []}
    
    def export_project_data(self, project_id: int, export_format: str = "JSON", 
                           tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Export data from a tenant project."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            # Verify tenant ownership first
            project = self.get_tenant_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found or access denied")
            
            # Export data from Label Studio
            export_data = self._make_request(
                "GET", 
                f"/api/projects/{project_id}/export",
                params={"exportType": export_format}
            )
            
            # Log audit event
            log_data_access(
                resource_type="label_studio_export",
                resource_id=str(project_id),
                action=AuditAction.EXPORT,
                export_format=export_format
            )
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export project {project_id}: {e}")
            return None
    
    def _is_tenant_project(self, project: Dict[str, Any], tenant_id: str) -> bool:
        """Check if a project belongs to a tenant."""
        
        title = project.get("title", "")
        description = project.get("description", "")
        
        # Check title prefix
        if title.startswith(f"[{tenant_id}] "):
            return True
        
        # Check description for tenant marker
        if f"Tenant: {tenant_id}" in description:
            return True
        
        # Check stored mapping
        project_id = project.get("id")
        if project_id and self._get_project_tenant_mapping(project_id) == tenant_id:
            return True
        
        return False
    
    def _store_tenant_project_mapping(self, project_id: int, tenant_id: str):
        """Store project-tenant mapping in database."""
        
        # This could be stored in a dedicated table or in project metadata
        # For now, we'll use the project title prefix as the primary method
        pass
    
    def _remove_tenant_project_mapping(self, project_id: int):
        """Remove project-tenant mapping from database."""
        pass
    
    def _get_project_tenant_mapping(self, project_id: int) -> Optional[str]:
        """Get tenant ID for a project from stored mapping."""
        return None
    
    def get_tenant_statistics(self, tenant_id: str = None) -> Dict[str, Any]:
        """Get statistics for a tenant's Label Studio usage."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            projects = self.get_tenant_projects(tenant_id)
            
            total_projects = len(projects)
            total_tasks = 0
            total_annotations = 0
            
            for project in projects:
                project_id = project.get("id")
                if project_id:
                    tasks = self.get_project_tasks(project_id, tenant_id)
                    annotations = self.get_project_annotations(project_id, tenant_id)
                    
                    total_tasks += len(tasks)
                    total_annotations += len(annotations)
            
            return {
                "tenant_id": tenant_id,
                "total_projects": total_projects,
                "total_tasks": total_tasks,
                "total_annotations": total_annotations,
                "avg_annotations_per_task": total_annotations / total_tasks if total_tasks > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get tenant statistics: {e}")
            return {}


class LabelStudioUserManager:
    """Manages tenant-specific user access to Label Studio."""
    
    def __init__(self, tenant_manager: LabelStudioTenantManager):
        self.tenant_manager = tenant_manager
    
    def create_tenant_user(self, user_id: str, tenant_id: str, 
                          role: str = "annotator") -> Optional[Dict[str, Any]]:
        """Create or update a user for Label Studio with tenant-specific permissions."""
        
        try:
            # Get user information from database
            with get_db_session() as session:
                user = session.query(UserModel).filter(
                    UserModel.id == user_id,
                    UserModel.tenant_id == tenant_id
                ).first()
                
                if not user:
                    raise Exception(f"User {user_id} not found in tenant {tenant_id}")
            
            # Create user in Label Studio (if not exists)
            user_data = {
                "username": f"{tenant_id}_{user.username}",
                "email": user.email,
                "first_name": user.full_name.split()[0] if user.full_name else "",
                "last_name": " ".join(user.full_name.split()[1:]) if user.full_name else "",
                "is_active": user.is_active
            }
            
            # This would require Label Studio user management API
            # For now, we'll return the user data structure
            
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to create Label Studio user: {e}")
            return None
    
    def assign_user_to_project(self, user_id: str, project_id: int, 
                              role: str = "annotator", tenant_id: str = None) -> bool:
        """Assign a user to a tenant project with specific role."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        try:
            # Verify project belongs to tenant
            project = self.tenant_manager.get_tenant_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found or access denied")
            
            # Verify user belongs to tenant
            with get_db_session() as session:
                user = session.query(UserModel).filter(
                    UserModel.id == user_id,
                    UserModel.tenant_id == tenant_id
                ).first()
                
                if not user:
                    raise Exception(f"User {user_id} not found in tenant {tenant_id}")
            
            # This would use Label Studio's project membership API
            # For now, we'll log the assignment
            
            log_data_modification(
                resource_type="label_studio_project_membership",
                resource_id=f"{project_id}_{user_id}",
                action=AuditAction.CREATE,
                new_values={"user_id": user_id, "project_id": project_id, "role": role}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign user to project: {e}")
            return False


# Global instances
tenant_manager = LabelStudioTenantManager()
user_manager = LabelStudioUserManager(tenant_manager)


def get_tenant_manager() -> LabelStudioTenantManager:
    """Get the global tenant manager instance."""
    return tenant_manager


def get_user_manager() -> LabelStudioUserManager:
    """Get the global user manager instance."""
    return user_manager